# Project Context

## Status
Phases 0–9 complete. All core features implemented.

## What's Built

### Backend (Python + FastAPI)
- **Config**: Single `app/config.py` pydantic-settings module — source of truth for all env vars.
- **Database**: Supabase Postgres + pgvector. 6 SQLAlchemy models. Alembic migrations. HNSW + GIN indexes.
- **Auth**: JWT verification via Supabase Auth. `current_user` dependency on protected routes.
- **Ingestion**: 25 SEC 10-K filings → 22,209 chunks with 768d embeddings (nomic-embed-text) + full-text search vectors.
- **Retrieval**: `DocumentRetriever` — embed query → pgvector semantic search + Postgres FTS → RRF fusion. Graceful degradation (empty results, missing search vector, missing DB config). **Query refinement** pre-processes the user's NL query: NLTK stopword removal + domain noise filtering, ticker/year entity extraction, company name → ticker resolution via DB lookup. FTS leg uses refined query with optional `WHERE ticker IN (...)` / `WHERE year IN (...)` filters for precision.
- **Assistant**: PydanticAI `Agent[DocumentAgentDeps, GroundedAnswer]` — `OllamaProvider`, `retries=2`, `prompted` output mode. `search_filings` tool. Structured citations.
- **Grounding**: `GroundingValidator` — validates citations against retrieved chunk set, checks required fields, empty-citation disclaimer rule.
- **Chat**: Full pipeline orchestration (`ChatPipeline`) — retrieve → agent → ground → persist → SSE stream. Thread CRUD routes. Auto-title from first message. SSE events: status, text-start/delta/end, citations, error.

### Frontend (Vite + React + TypeScript)
- Supabase email auth (login/signup pages, AuthContext).
- Chat UI: message list with status indicator (Searching → Generating → Validating stages), citation badges + expandable citation panel, thread list sidebar with rename, auto-scroll, empty state.
- Custom `DefaultChatTransport` with `onChunk` for pipeline status + structured citations.
- Thread list: auto-titled, inline rename on double-click, click to switch threads.

## Test Coverage (unit tests pass)
| Module | Tests |
|---|---|
| `tests/retrieval/test_fusion.py` | 12 |
| `tests/assistant/test_agent.py` | 11 unit + 4 integration |
| `tests/grounding/test_validator.py` | 9 |
| `tests/chat/test_events.py` | SSE event format builders |

## Key Configuration
| Setting | Value | File |
|---|---|---|
| LLM | `llama3.2:3b` (Ollama) | `app/config.py` |
| Embeddings | `nomic-embed-text` (768d) | `app/config.py` |
| Ollama URL | `http://localhost:11434/v1` | `.env` |
| Retrieval top_k | 15 | `app/config.py` |
| Retrieval inner_top_k | 20 | `app/config.py` |
| Retrieval RRF k | 60 | `app/config.py` |
| DB | `postgresql+psycopg://` via Supabase pooler | `.env` |
