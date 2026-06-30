# Build checklist

## Phase 0 — Foundation
- [x] Install Ollama + pull models (`ollama pull llama3.1:8b && ollama pull nomic-embed-text`)
- [x] Set up Supabase project (collect API keys, DB URL, enable email auth)
- [x] Configure `backend/.env` from `.env.example`
- [x] Configure `frontend/.env` from `.env.example`

## Phase 1 — Backend scaffold
- [x] `backend/`: add deps
- [x] `backend/app/main.py` — FastAPI entrypoint
- [x] `backend/app/config.py` — Pydantic settings (single source of truth for env)
- [x] `backend/app/database/models/` — SQLAlchemy models (6 tables, split by entity)
- [x] `backend/app/database/supabase.py` — Supabase client wrapper (user + admin)
- [x] Alembic init + config (wire to `config.py`)
- [x] Initial migration (pgvector, source_documents, document_chunks, chat tables, HNSW + GIN indexes)

## Phase 2 — Auth
- [x] `backend/app/auth/dependencies.py` — JWT verification + current user dependency
- [x] Frontend: scaffold Vite + React SPA (`pnpm create vite`, add deps)
- [x] Frontend: Tailwind CSS v4 + `@tailwindcss/vite` wired
- [x] Frontend: path alias (`@/` → `./src`) configured
- [x] Frontend: shadcn/ui initialized + deps installed
- [x] `frontend/src/lib/env.ts` — env validation module
- [x] `frontend/src/lib/supabase.ts` — Supabase browser client
- [x] `frontend/src/lib/http.ts` — fetch wrapper with bearer token injection
- [x] `frontend/src/lib/api.ts` — typed API methods
- [x] Supabase email auth UI (login/signup pages)
- [x] `frontend/src/lib/auth.tsx` — AuthContext + provider

## Phase 3 — Stub chat (backend SSE endpoint + frontend UI)
- [x] `backend/app/api/chat.py` — POST `/chat/stream` (SSE, Ollama stub, auth guard)
- [x] `frontend/src/pages/Chat.tsx` — chat page with `useChat` + `DefaultChatTransport`
- [x] `frontend/src/components/chat/MessageList.tsx` — message bubbles, auto-scroll, empty state
- [x] `frontend/src/components/chat/ChatInput.tsx` — text input + send on Enter
- [x] `frontend/src/components/chat/Sidebar.tsx` — app branding, new chat button, sign out
- [x] Wire `/chat` route in App.tsx
- [x] `frontend/src/lib/supabase.ts` — export `getAccessToken` for shared use
- [x] `frontend/tsconfig.app.json` — fix TS6 `baseUrl` deprecation for build mode

## Phase 4 — Ingestion pipeline
- [x] Install Ollama + pull `nomic-embed-text` model
- [x] `data/convert_md.py` — batch-convert 25 SEC HTML filings to Markdown via docling
- [x] `backend/ingest/load_source_documents.py` — read `manifest.json`, insert 25 filings into `source_documents`
- [x] `backend/ingest/chunk_and_load.py` — docling → HybridChunker → section detection → Ollama embeddings → Supabase insert → `search_vector` update
- [x] Test mode: `--ticker AAPL --year 2025` (695 chunks, verified end-to-end)
- [x] Full batch: 25 filings, 22,209 chunks, all embedded + search_vector populated

## Phase 5 — Retrieval (`backend/app/retrieval/`)
- [x] `backend/app/retrieval/__init__.py`
- [x] `backend/app/retrieval/queries.py` — pgvector semantic search (`<=>` cosine distance)
- [x] `backend/app/retrieval/queries.py` — Postgres full-text search (`plainto_tsquery` + `ts_rank`)
- [x] `backend/app/retrieval/fusion.py` — Reciprocal Rank Fusion (`score = 1 / (k + rank)`)
- [x] `backend/app/retrieval/retriever.py` — `DocumentRetriever` (embed query → run both searches → fuse → return `SearchResult`s)
- [x] `backend/tests/retrieval/test_fusion.py` — unit tests for RRF, edge cases (empty, disjoint, overlapping)

## Phase 6 — LLM assistant (`backend/app/assistant/`)
- [x] `backend/app/assistant/__init__.py`
- [x] `backend/app/assistant/outputs.py` — `GroundedAnswer`, `Citation`, `SourcePassage` Pydantic models
- [x] `backend/app/assistant/deps.py` — `DocumentAgentDeps` dataclass (user_id, thread_id, retriever)
- [x] `backend/app/assistant/instructions.md` — system prompt with product contract
- [x] `backend/app/assistant/agent.py` — PydanticAI `Agent[DocumentAgentDeps, GroundedAnswer]` + `run_agent()`
- [x] `backend/tests/assistant/test_agent.py` — unit tests (tool schema, deps construction, instructions loaded)

## Phase 7 — Grounding (`backend/app/grounding/`)
- [x] `backend/app/grounding/__init__.py`
- [x] `backend/app/grounding/validator.py` — `GroundingValidator` (checks each citation chunk_id against retrieved set)
- [x] `backend/tests/grounding/test_validator.py` — unit tests (valid, unretrieved citation, missing disclaimer)

## Phase 8 — Chat orchestration (`backend/app/chat/` + update `api/chat.py`)
- [ ] `backend/app/chat/__init__.py`
- [ ] `backend/app/chat/messages.py` — AI SDK wire format ↔ internal message conversion
- [ ] `backend/app/chat/streaming.py` — SSE event generators (text-start/delta/end, citation event, error event)
- [ ] `backend/app/chat/orchestrator.py` — `ChatOrchestrator.run_turn()`: retrieve → generate → ground → persist → stream
- [ ] `backend/app/api/chat.py` — replace stub: wire `ChatOrchestrator` into `/chat/stream` endpoint
- [ ] Persist user message, assistant `GroundedAnswer`, and citations to Supabase on success
- [ ] Return controlled error event on grounding failure

## Phase 9 — Final UI polish (frontend + backend)
- [ ] Backend: `GET /chat/threads` — list authenticated user's threads
- [ ] Backend: `GET /chat/{thread_id}/messages` — full message history with citations
- [ ] `frontend/src/components/chat/CitationBadge.tsx` — inline citation reference (superscript, tooltip)
- [ ] `frontend/src/components/chat/CitationPanel.tsx` — full citation list with expandable source passages
- [ ] `frontend/src/components/chat/ThreadList.tsx` — thread history sidebar, click to switch threads
- [ ] `frontend/src/components/chat/LoadingSkeleton.tsx` — placeholder animation during load
- [ ] `frontend/src/components/chat/ErrorState.tsx` — structured error display (auth, network, grounding, generic)
- [ ] Update `MessageList.tsx` — render citations inline + citation panel below each assistant message
- [ ] Update `Chat.tsx` — thread switching via `key={threadId}`, load history, wire thread list
