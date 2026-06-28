# Phase 3 — Frontend Chat UI

## Objective

Build the chat page UI and wire it to the backend streaming endpoint using the AI SDK's `useChat` hook with `DefaultChatTransport`. The user can send a message and see the assistant's response stream in real time.

## Dependencies

- [x] AI SDK installed (`ai` 7.0.3, `@ai-sdk/react` 4.0.4)
- [x] `DefaultChatTransport` available (exports from `ai`)
- [x] `API_BASE_URL` from `@/lib/env`
- [x] `getAccessToken` capability from `@/lib/supabase` (via `supabase.auth.getSession()`)
- [x] Existing routing setup in `App.tsx`

## Wire format reference

The `DefaultChatTransport` sends this POST body to `${API_BASE_URL}/chat/stream`:

```json
{
  "id": "<thread-id>",
  "messages": [
    {"id": "1", "role": "user", "content": "..."},
    {"id": "2", "role": "assistant", "content": "..."}
  ],
  "trigger": "submit-message",
  "messageId": "2"
}
```

And expects an SSE stream with `data:` lines containing JSON objects typed by a `type` discriminator:

```
data: {"type":"text-start","id":"<msg-id>"}

data: {"type":"text-delta","id":"<msg-id>","delta":"Hello"}

data: {"type":"text-delta","id":"<msg-id>","delta":" world"}

data: {"type":"text-end","id":"<msg-id>"}
```

Error event:

```
data: {"type":"error","errorText":"Ollama unreachable"}
```

## Tasks

### 1. Create `src/pages/Chat.tsx`

Route-level page component. Responsibilities:

- Generate a thread ID via `crypto.randomUUID()` on mount (if no existing thread).
- Initialize `useChat` with `DefaultChatTransport` pointed at the backend.
- Render the layout: `MessageList` on top, `ChatInput` pinned at the bottom.
- Show streaming status indicator while `status === "streaming"`.
- Show error banner when `error` is set.

**Layout sketch:**

```
┌─────────────────────────────────┐
│  (status indicator / error)     │
│                                 │
│  ┌─── MessageList ───────────┐  │
│  │  User message              │  │
│  │  Assistant response        │  │
│  │  (streaming cursor...)     │  │
│  └────────────────────────────┘  │
│                                 │
│  ┌─── ChatInput ─────────────┐  │
│  │  [Type a message...] [→]  │  │
│  └────────────────────────────┘  │
└─────────────────────────────────┘
```

**Key decisions:**

- `useChat` initialized outside the render tree? No — call it inside the component. The hook manages its own state.
- `threadId` stored in state, passed as `id` to `useChat` options.
- No thread persistence yet (that's Phase 8). The thread ID is scoped to the session.

**Draft interface:**

```tsx
import { useChat } from "@ai-sdk/react"
import { DefaultChatTransport } from "ai"
import { API_BASE_URL } from "@/lib/env"
import { getAccessToken } from "@/lib/supabase"

export default function ChatPage() {
  const [threadId] = useState(() => crypto.randomUUID())

  const { messages, sendMessage, status, error } = useChat({
    id: threadId,
    transport: new DefaultChatTransport({
      api: `${API_BASE_URL}/chat/stream`,
      headers: async () => ({
        Authorization: `Bearer ${await getAccessToken()}`,
      }),
    }),
  })

  return (
    <div className="flex flex-col h-screen">
      <MessageList messages={messages} status={status} />
      <ChatInput onSend={sendMessage} disabled={status === "streaming"} />
    </div>
  )
}
```

### 2. Create `src/components/chat/MessageList.tsx`

Renders the list of messages. Responsibilities:

- Scrollable container (flex-col, overflow-y-auto).
- Maps over `messages`, renders each message as a bubble.
- User messages right-aligned, assistant messages left-aligned.
- Auto-scrolls to bottom when new content arrives (useEffect on `messages.length` and last message content).
- Shows a subtle "streaming" indicator when `status === "streaming"` (e.g. a pulsing cursor after the last assistant message).
- Empty state when no messages: "Ask a question about SEC filings."

**Props:**

```typescript
interface MessageListProps {
  messages: Array<{ id: string; role: string; content: string; parts?: unknown[] }>
  status: "ready" | "streaming" | "submitted" | "error"
}
```

**Styling:**

- Simple bubbles with rounded corners (`rounded-lg`, `px-4`, `py-2`).
- User bubble: `bg-primary text-primary-foreground ml-auto`.
- Assistant bubble: `bg-muted text-muted-foreground`.
- Streaming cursor: a thin animated vertical bar after the last assistant message.

### 3. Create `src/components/chat/ChatInput.tsx`

Text input + send button. Responsibilities:

- Controlled text input (native `<textarea>` or `<input>` with enough height).
- Send button (disabled when input is empty or `disabled` prop is true).
- Send on Enter (not Shift+Enter) or button click.
- Clear input after send.

**Props:**

```typescript
interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
}
```

**Key details:**

- `onSend` wraps `sendMessage` from `useChat`. The `sendMessage` signature from AI SDK v4 is: `sendMessage({ content: string })` or similar — verify the exact signature during implementation.
- If `sendMessage` expects a `formMessage` or `CreateUIMessage`, wrap appropriately.
- The textarea should resize naturally (use `rows={1}` with CSS or a simple auto-resize).
- Send button uses the `Button` shadcn component (`@/components/ui/button`).

### 4. Wire route in `App.tsx`

Replace the current `Home` component (which just shows "Signed in as ...") with a redirect to `/chat`.

**Changes to `App.tsx`:**

- Add `import ChatPage from "@/pages/Chat"`.
- Replace the `Home` component with a Navigate-to-chat or render ChatPage inline.
- Route structure:

```tsx
<Routes>
  <Route path="/login" element={<Login />} />
  <Route path="/signup" element={<SignUp />} />
  <Route path="/chat" element={<ChatPage />} />
  <Route path="*" element={<Navigate to="/chat" replace />} />
</Routes>
```

- The auth guard is already handled by `useSession` inside `ChatPage` — redirect to `/login` if no session. But the existing pattern uses `Navigate` in `Home`. Keep the same guard: redirect unauthenticated users to `/login`.

**Option:** Extract an `AuthGuard` wrapper or keep the check inline. Since there's only one protected route for now, a simple check in `ChatPage` is fine:

```tsx
const { session } = useSession()
if (!session) return <Navigate to="/login" replace />
```

### 5. Add `getAccessToken` export from `@/lib/supabase`

The `DefaultChatTransport`'s `headers` option needs to inject the Bearer token. Currently `src/lib/supabase.ts` creates the client but doesn't export a token getter.

**Add to `src/lib/supabase.ts`:**

```typescript
export async function getAccessToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}
```

(Currently `getAccessToken` is defined inside `src/lib/http.ts` as a module-private function. Either export it from supabase.ts or re-use the existing one. Best to export from supabase.ts so both http.ts and the transport can import it.)

**Actually, re-examine:** The `http.ts` already has a private `getAccessToken`. The `ChatPage` needs to pass headers to `DefaultChatTransport`. Two options:

1. Export `getAccessToken` from `supabase.ts` and use it in both `http.ts` and `Chat.tsx`.
2. Create an `api`-style wrapper that the transport uses.

Option 1 is simpler. Move the function to `supabase.ts` and import it in `http.ts`.

### 6. Empty state

When `messages` is empty and `status !== "streaming"`, `ChatPage` should show a centered empty state instead of `MessageList`:

```
┌─────────────────────────────────┐
│                                 │
│       Ask a question about      │
│         SEC filings             │
│                                 │
│    (subtle icon or graphic)     │
│                                 │
│       [Type a message...]       │
│                                 │
└─────────────────────────────────┘
```

This can live in `ChatPage` itself or as a sub-component.

## Error handling

- Network errors: If the fetch fails, `useChat` sets `error`. Show a red banner with the error message and a "Retry" button that calls `sendMessage` again.
- HTTP errors (4xx/5xx): The transport throws on non-ok responses. The error is surfaced through `useChat`'s `error` state.
- In-stream errors: The SSE `error` event type sets an error in the chat state. Render the `errorText` in the error banner.

## Files summary

### Create

| File | Lines (est.) | Content |
|---|---|---|
| `src/pages/Chat.tsx` | ~80 | Page component, useChat, layout, error/empty states |
| `src/components/chat/MessageList.tsx` | ~60 | Message bubbles, auto-scroll, streaming indicator |
| `src/components/chat/ChatInput.tsx` | ~50 | Input + send button, Enter-to-send |

### Modify

| File | Change |
|---|---|
| `src/lib/supabase.ts` | Export `getAccessToken` function |
| `src/lib/http.ts` | Import `getAccessToken` from `supabase.ts` instead of private definition |
| `src/App.tsx` | Replace Home with `/chat` route + ChatPage import |

## Verification

1. `pnpm tsc --noEmit` — zero errors
2. `pnpm build` — production build succeeds
3. Login flow still works (/login, /signup redirect to /chat after auth)
4. Chat page opens, shows empty state
5. Type a message, see streaming response
6. Error state renders properly when backend is down (test by stopping the backend)
