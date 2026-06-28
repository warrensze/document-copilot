# Phase 3 — Chat Streaming Endpoint + Frontend Chat UI

## Objective

Wire up a stub chat loop: user types a message → backend calls Ollama directly → streams response back → frontend renders it. No retrieval, no grounding, no persistence — that comes in Phases 5–8.

## Dependencies

- [x] AI SDK (`ai` 7.0.3 + `@ai-sdk/react` 4.0.4) installed
- [x] Backend auth dependency (`get_current_user`) exists
- [x] Frontend HTTP client + API layer exist

## Backend Tasks

### 1. `backend/app/api/chat.py` — POST /chat/stream

**Request model** — matches what `DefaultChatTransport` actually sends:

> **Deviation from `architecture.md:257`:** The architecture shows `threadId` in the sample body. The AI SDK v4 transport sends `id` (derived from `options.chatId`). We match the SDK wire format per the architecture's own caveat at line 134: *"The exact API surface should be verified during implementation against the installed AI SDK version."*

```python
class ChatMessage(BaseModel):
    id: str
    role: str          # "user" | "assistant"
    content: str

class ChatRequest(BaseModel):
    id: str             # thread ID (sent by DefaultChatTransport)
    messages: list[ChatMessage]
    trigger: str = "submit-message"
    messageId: str | None = None
```

**Response** — SSE stream (`media_type="text/event-stream"`) with events matching `uiMessageChunkSchema` (the Zod schema the AI SDK client uses to parse the stream):

```
data: {"type":"text-start","id":"<assistant-msg-id>"}

data: {"type":"text-delta","id":"<assistant-msg-id>","delta":"Hello"}

data: {"type":"text-delta","id":"<assistant-msg-id>","delta":" world"}

data: {"type":"text-end","id":"<assistant-msg-id>"}
```

Each event separated by `\n\n`. The `id` is a UUID generated server-side for the assistant message.

**Flow:**

1. `get_current_user` dependency validates Supabase JWT (returns 401 if invalid).
2. Parse `ChatRequest` body (returns 422 if malformed).
3. Convert messages to OpenAI SDK format. Prepend a system message: *"You are a helpful assistant that answers questions about SEC filings. You are currently in stub mode and do not have access to the document corpus."*
4. Call `client.chat.completions.create(stream=True)` against Ollama `llama3.1:8b`.
5. Iterate over streaming chunks, yield SSE `text-delta` events.
6. On stream end, yield `text-end`.
7. On Ollama connection error, yield `{"type":"error","errorText":"Ollama unreachable"}` and raise `HTTPException(502)`.

**Error event format** (also from the schema):

```
data: {"type":"error","errorText":"Ollama unreachable"}
```

### 2. `backend/app/api/__init__.py`

Empty package marker.

### 3. `backend/app/main.py`

Add `app.include_router(chat_router)`.

### Router wiring details

The router in `api/chat.py` uses `APIRouter(prefix="/chat")` and defines the route as `@router.post("/stream")`, producing the full path `POST /chat/stream`. This matches what the frontend transport calls (`${API_BASE_URL}/chat/stream`) and what the architecture recommends (line 248).

### Auth

Endpoint is protected by `get_current_user`. The auth dependency returns 401 for missing/expired tokens. Architecture docs also specify 502 for upstream failures and 422 for bad payloads — both covered.

### Files changed

| Action | File |
|---|---|
| Create | `backend/app/api/__init__.py` |
| Create | `backend/app/api/chat.py` |
| Edit | `backend/app/main.py` |

## Frontend Tasks

### 1. Wire `useChat` with `DefaultChatTransport`

`src/pages/Chat.tsx`:

```tsx
const { messages, sendMessage, status, error } = useChat({
  id: threadId,
  transport: new DefaultChatTransport({
    api: `${API_BASE_URL}/chat/stream`,
    headers: async () => ({
      Authorization: `Bearer ${await getAccessToken()}`,
    }),
  }),
})
```

`threadId` is a UUID generated client-side via `crypto.randomUUID()` for new chats. For existing threads it's loaded from the route param.

### 2. Chat UI components

| Component | File | Responsibility |
|---|---|---|
| `ChatPage` | `src/pages/Chat.tsx` | Route-level component, owns `useChat` hook, layout |
| `MessageList` | `src/components/chat/MessageList.tsx` | Scrollable list of messages, auto-scroll on new content |
| `ChatInput` | `src/components/chat/ChatInput.tsx` | Text input + send button, calls `sendMessage` |

### 3. Wire `/chat` route

Add `<Route path="/chat" element={<ChatPage />} />` to `App.tsx`. Replace the Home component's "Signed in as..." placeholder with a redirect to `/chat`.

### Files created

| Action | File |
|---|---|
| Create | `frontend/src/pages/Chat.tsx` |
| Create | `frontend/src/components/chat/MessageList.tsx` |
| Create | `frontend/src/components/chat/ChatInput.tsx` |

### Files modified

| Action | File |
|---|---|
| Edit | `frontend/src/App.tsx` |

## Stream Protocol Reference

The AI SDK v4 `DefaultChatTransport` extends `HttpChatTransport`, which:

1. **Sends** a POST to the configured `api` URL with body `{ id, messages, trigger, messageId }`.
2. **Receives** a `ReadableStream<Uint8Array>` which it pipes through `parseJsonEventStream` with `uiMessageChunkSchema`.

`parseJsonEventStream` reads SSE-formatted data: lines starting with `data: ` are parsed as JSON. The schema is a discriminated union on `type`. For a plain text answer (no tools), the relevant event types are:

| Event | Fields | When |
|---|---|---|
| `text-start` | `type: "text-start"`, `id: string` | Start of assistant message |
| `text-delta` | `type: "text-delta"`, `id: string`, `delta: string` | Each token/chunk from Ollama |
| `text-end` | `type: "text-end"`, `id: string` | End of assistant message |
| `error` | `type: "error"`, `errorText: string` | Fatal error during generation |

The `id` in all text events must match so the client can assemble deltas into the right message.

## What this phase does NOT do

- No document retrieval (Phase 5)
- No PydanticAI agent (Phase 6)
- No grounding / citation validation (Phase 7)
- No chat persistence (Phase 8)
- No thread history sidebar (Phase 9)

The stub calls Ollama directly without context — answers will not reference filings.

## Verification

1. `pnpm tsc --noEmit` — TypeScript clean
2. `pnpm build` — Vite build succeeds
3. Start backend (`uv run uvicorn app.main:app`) + frontend (`pnpm dev`)
4. Log in, navigate to `/chat`, type a message, see streaming response
