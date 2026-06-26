# Build checklist

## Phase 0 — Foundation
- [ ] Install Ollama + pull models (`ollama pull llama3.1:8b && ollama pull nomic-embed-text`)
- [ ] Set up Supabase project (collect API keys, DB URL, enable email auth)
- [ ] Configure `backend/.env` from `.env.example`
- [ ] Configure `frontend/.env` from `.env.example`

## Phase 1 — Backend scaffold
- [ ] `backend/`: add deps (`uv add fastapi uvicorn pydantic pydantic-settings httpx structlog openai supabase pydantic-ai sqlalchemy alembic psycopg[binary] pgvector`)
- [ ] `backend/app/main.py` — FastAPI entrypoint
- [ ] `backend/app/config.py` — Pydantic settings (single source of truth for env)
- [ ] `backend/app/database/models.py` — SQLAlchemy models
- [ ] `backend/app/database/supabase.py` — Supabase client wrapper
- [ ] Alembic init + config (`alembic init alembic`, wire to `config.py`)
- [ ] Initial migration (pgvector, source_documents, document_chunks, chat tables)

## Phase 2 — Auth
- [ ] `backend/app/auth/dependencies.py` — JWT verification + current user dependency
- [ ] Frontend: scaffold Vite + React SPA (`pnpm create vite`, add deps)
- [ ] `frontend/src/lib/env.ts` — env validation module
- [ ] `frontend/src/lib/supabase.ts` — Supabase browser client
- [ ] Supabase email auth UI (login/signup pages)

## Phase 3 — Frontend API client + stub chat
- [ ] `frontend/src/lib/http.ts` — fetch wrapper with bearer token injection
- [ ] `frontend/src/lib/api.ts` — typed API methods
- [ ] `backend/app/api/chat.py` — POST `/chat/stream` (stubbed)
- [ ] Frontend chat UI with AI SDK (`useChat` stub, message rendering)

## Phase 4 — Ingestion pipeline
- [ ] `backend/ingest/` — Markdown extraction from downloaded filings
- [ ] Chunking logic (section-aware, with metadata)
- [ ] Embedding generation (Ollama — `nomic-embed-text`)
- [ ] Write documents + chunks to Supabase

## Phase 5 — Retrieval
- [ ] `backend/app/retrieval/queries.py` — pgvector semantic search
- [ ] `backend/app/retrieval/queries.py` — Postgres full-text search
- [ ] `backend/app/retrieval/fusion.py` — Reciprocal Rank Fusion
- [ ] `backend/app/retrieval/retriever.py` — hybrid search orchestrator

## Phase 6 — LLM assistant
- [ ] `backend/app/assistant/outputs.py` — GroundedAnswer, Citation, SourcePassage
- [ ] `backend/app/assistant/deps.py` — DocumentAgentDeps
- [ ] `backend/app/assistant/agent.py` — PydanticAI agent with search tools
- [ ] `backend/app/assistant/instructions.md` — system prompt with product contract

## Phase 7 — Grounding
- [ ] `backend/app/grounding/validator.py` — citation → source verification
- [ ] Wire grounding into agent output pipeline

## Phase 8 — Chat orchestration
- [ ] `backend/app/chat/messages.py` — AI SDK message ↔ internal type conversion
- [ ] `backend/app/chat/streaming.py` — AI SDK-compatible streaming events
- [ ] `backend/app/chat/orchestrator.py` — full turn lifecycle (retrieve → generate → ground → persist)
- [ ] Wire real agent into `/chat/stream` endpoint

## Phase 9 — Final UI polish
- [ ] Citation rendering (source filing, page, excerpt)
- [ ] Source passage expand/collapse
- [ ] Empty states, loading skeletons, error handling
- [ ] Thread history sidebar
