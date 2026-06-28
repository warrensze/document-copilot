# Phase 9 — Final UI Polish

**Goal**: Deliver a polished analyst-grade chat experience — threaded history, citation rendering with expandable source passages, loading states, and error handling.

## Context

From `client-brief.md:60-68`:
- "Always cite. Every claim links to the source filing + page."
- "Show the underlying passage so the analyst can verify in one click."

From `architecture.md:329-330`:
- "Cited passages include enough metadata for the frontend to show company, filing, date, page or section, and excerpt."

## Backend work

### New endpoint: `GET /chat/threads` (or `app/api/chat.py` additions)

Return authenticated user's thread list:
```json
[
  {"id": "uuid", "title": "Apple revenue mix analysis", "created_at": "...", "updated_at": "..."},
  ...
]
```

- Query `chat_threads WHERE owner_id = user_id ORDER BY updated_at DESC`.
- `title` may be null (no auto-title generation yet — user creates via "+ New chat" button which resets threadId).

### New endpoint: `GET /chat/{thread_id}/messages`

Return full message history including citations:
```json
{
  "messages": [
    {"id": "uuid", "role": "user", "content": "...", "created_at": "..."},
    {"id": "uuid", "role": "assistant", "content": "...", "citations": [...], "created_at": "..."}
  ]
}
```

- Join `chat_messages` with `message_citations` and `document_chunks` to return citations with full metadata (ticker, company_name, year, section, excerpt).

## Frontend work

### `src/components/chat/CitationBadge.tsx`

Inline citation reference rendered in assistant messages:
- Superscript number linking to a citation panel.
- On click/hover, show a tooltip with: ticker, company name, year, section.

### `src/components/chat/CitationPanel.tsx`

Side panel or bottom panel showing all citations for an assistant message:
- Each citation shows: ticker badge, company name, year, section, excerpt text.
- "Show source passage" expand/collapse button for each citation.
- Source passage shows the full `chunk_text` in a monospace block with a subtle background.

### `src/components/chat/ThreadList.tsx`

Thread history sidebar:
- Loaded from `GET /chat/threads` on chat page mount.
- List of thread items: title (or "Chat from {date}" if null), last updated timestamp.
- Click to switch threads (sets `threadId` in `useChat`, loads history from `GET /chat/{id}/messages`).
- If switching threads mid-stream, cancel current stream and load new thread.
- "New chat" button at the top (already exists in `Sidebar.tsx` — can stay or move here).

### `src/components/chat/LoadingSkeleton.tsx`

Shown during initial page load and thread switching:
- Placeholder rectangles mimicking message bubble shapes.
- Pulse animation (Tailwind `animate-pulse`).

### `src/components/chat/ErrorState.tsx`

Structured error display:
- Auth errors → "Session expired. Please sign in again."
- Network errors → "Could not reach the server. Check your connection."
- Grounding failures → "The assistant could not verify its answer against the source documents. Please try rephrasing your question."
- Generic errors → "Something went wrong. Please try again."

### Updates to existing files

**`MessageList.tsx`**:
- Render `CitationBadge` inline in assistant messages (parse citation markers from answer text).
- Below the assistant message, show a collapsible `CitationPanel`.
- Integrate `LoadingSkeleton` between messages while streaming.
- Integrate `ErrorState` at the bottom on error.

**`Chat.tsx`**:
- Add thread list sidebar (`ThreadList`) alongside the existing sidebar.
- On mount, fetch thread list.
- On thread click: set `threadId`, load history, switch active thread.
- On error from `useChat`: pass to `ErrorState`.
- Wire the `GET /chat/threads` and `GET /chat/{id}/messages` calls into the `useChat` initialization (`initialMessages` and `id`).

## Server state considerations

- The `useChat` hook from AI SDK manages in-flight state (streaming messages). Thread switching must:
  1. Stop any in-flight stream (`stop()` from `useChat`).
  2. Set `id` to the new thread's ID.
  3. Set `initialMessages` to the fetched history (this re-initializes `useChat`'s internal state).
- A React key change on the `Chat` component (or using a fresh component instance per thread) triggers a clean re-initialization.

## Key decisions

- **Citation rendering as React components, not Markdown**: The AI SDK doesn't natively parse citations from model output. The backend sends citations as a structured data event (Phase 8); the frontend stores them alongside messages and renders them separately (badges + panel), not inline.
- **Thread switching via key change**: Simplest approach — `key={threadId}` on the chat component forces React to unmount/remount, giving `useChat` a clean state.
- **No thread title generation**: Deferred. Threads display "Chat from {date}" until a future phase adds automatic titling.
- **Loading skeletons over spinners**: More professional feel for analyst tool.
- **Citation panel collapsible by default**: Keeps the chat clean; analysts click to verify when needed.

## Out of scope

- Message editing/deletion
- Auto-generated thread titles
- Dark mode
- Mobile responsiveness (internal desktop tool)
- Keyboard shortcuts
