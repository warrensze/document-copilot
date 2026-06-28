# Phase 8 — Chat Orchestration

**Goal**: Wire the real agent + retriever + grounding validator into the `/chat/stream` endpoint. Turn the Phase 3 stub into a full turn lifecycle: retrieve → generate → ground → persist.

## Context

From `architecture.md:148-152`:
- `backend/app/chat/orchestrator.py` — Coordinates one chat turn end-to-end (line 149)
- `backend/app/chat/messages.py` — Converts AI SDK messages to/from internal types (line 150)
- `backend/app/chat/streaming.py` — Emits AI SDK-compatible streaming events (line 151)

From `todo.md:64-67`:
- `backend/app/chat/messages.py` — AI SDK message ↔ internal type conversion
- `backend/app/chat/streaming.py` — AI SDK-compatible streaming events
- `backend/app/chat/orchestrator.py` — full turn lifecycle
- Wire real agent into `/chat/stream` endpoint

## Files to create

### `app/chat/__init__.py`
Package marker.

### `app/chat/messages.py` — Message conversion

Functions:
- **`ai_sdk_messages_to_internal(messages: list[ChatMessage]) -> list[InternalMessage]`** — Converts the AI SDK wire format (from Phase 3's `ChatRequest`) to internal message types. Extracts role, content, metadata.
- **`assistant_message_to_events(assistant_msg_id: str, answer: GroundedAnswer) -> list[SSEEvent]`** — Converts a `GroundedAnswer` into the SSE event format expected by the AI SDK (text-start, text-delta for answer, a structured data event for citations).

The AI SDK wire format currently uses `id`, `role`, `content` per message (defined in Phase 3's `ChatMessage` model). The assistant response emits `text-start`/`text-delta`/`text-end`/`error` events as defined in Phase 3.

Aligned with `architecture.md:262` — "The `messages` payload should use the AI SDK UI message format at the frontend boundary."

### `app/chat/streaming.py` — SSE helpers

Functions:
- **`async def generate_sse_events(assistant_msg_id: str, answer: GroundedAnswer) -> AsyncGenerator[str, None]`** — Yields properly formatted SSE strings (`data: {...}\n\n`) for each event type:
  1. `text-start` with assistant_msg_id
  2. `text-delta` events for each chunk of answer text (split on word boundaries, ~5 words per delta for natural streaming feel)
  3. `text-end` with the final answer
  4. Optional `citation` structured event with the full citation list (JSON payload)
- **`async def generate_error_event(error_text: str) -> str`** — Yields a single `error` SSE event.

Aligned with `architecture.md:266-269` — "Send text deltas as the answer is generated. Send citation/source metadata as structured parts once available."

### `app/chat/orchestrator.py` — Turn lifecycle

**`class ChatOrchestrator`**:
- **`__init__(self, db_url: str, ollama_client: OpenAI)`** — Stores shared resources.
- **`async def run_turn(user_id: str, thread_id: str, messages: list[ChatMessage]) -> AsyncGenerator[str, None]`**:
  1. **Extract user message**: Get the last user message from the `messages` list.
  2. **Retrieve**: Create `DocumentRetriever`, call `retriever.search(user_message.text, top_k=15)` → list of `SourcePassage`.
  3. **Build deps**: Create `DocumentAgentDeps(user_id, thread_id, retriever)` — note: the retriever was already called; the agent receives the results, not the retriever itself (or it receives the retriever and can call it again if needed for follow-ups).
  4. **Generate**: Call `run_agent(deps, user_message.text)` → `GroundedAnswer` (this step may internally call `search_filings` tool which calls the retriever again).
  5. **Ground**: Create `GroundingValidator(retrieved_chunk_ids={c.chunk_id for c in answer.citations})`. Call `validator.validate(answer)`.
  6. **Fail or proceed**: If `validation.passed=False` → yield `generate_error_event("The answer could not be verified against the source documents.")`. Stop.
  7. **Save** (if validation passed): Persist user message, assistant answer, and citations to Supabase via admin client.
     - Insert `chat_message` for user (role="user", content=user_message.text, thread_id, meta={}).
     - Insert `chat_message` for assistant (role="assistant", content=answer.answer, thread_id, meta={citations: ...}).
     - Insert `message_citation` for each citation (message_id, chunk_id, excerpt).
  8. **Stream**: Yield SSE events via `generate_sse_events(assistant_msg_id, answer)`.

### File to update: `app/api/chat.py`

Replace the Phase 3 stub's `event_stream()` with:

```python
@router.post("/stream")
async def chat_stream(body: ChatRequest, user: dict = Depends(get_current_user)) -> StreamingResponse:
    assistant_msg_id = str(uuid.uuid4())
    orchestrator = ChatOrchestrator(...)

    async def event_stream():
        async for event in orchestrator.run_turn(
            user_id=user["id"],
            thread_id=body.id,
            messages=body.messages,
        ):
            yield event

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

## Key decisions

- **Thread ID from `body.id`**: The AI SDK's `request.body.id` maps to `thread_id`. This matches the Phase 3 wire format where `ChatRequest.id` is the thread identifier.
- **DB persistence via Supabase admin client**: Uses `create_admin_client()` (service-role key) for writes, same as ingestion. Messages are explicitly tied to `user_id` from the auth dependency.
- **Sync vs async**: The `ChatOrchestrator.run_turn` is async. The retriever's `search()` call runs in a thread pool executor via `asyncio.to_thread()` since it does blocking psycopg and HTTP (Ollama) calls. The agent's `run_agent()` uses PydanticAI's async interface.
- **Agent tool calls**: In Phase 8, the agent receives the already-retrieved passages as context rather than calling the retriever as a tool again (simpler, avoids double-embedding, and the retriever is stateless so caching doesn't help). The `search_filings` tool reads from a provided context list.
- **Citation persistence**: `message_citations` rows link `chat_message.id` to `document_chunk.id` with the excerpt text, enabling the frontend to render source passages in Phase 9.

## Out of scope

- Connection pooling for psycopg — can be added if performance is an issue.
- Chat thread title generation — deferred.
- Editing/retracting messages — not in scope.
