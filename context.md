# Context

## Project
**Document Copilot** — internal AI chatbot for Driftwood Capital analysts. Query SEC filings in natural language, get grounded citable answers.

## State
Phase 4 (ingestion) complete. 25 SEC 10-K filings ingested — 22,209 chunks with 768d embeddings and full-text search vectors in Supabase. Phase 5 plan written. Ollama installed and running.

## Stack
- **Backend:** Python 3.12+, FastAPI, Pydantic v2, PydanticAI, httpx, structlog, SQLAlchemy, Alembic, Supabase Python client, OpenAI SDK (pointed at Ollama)
- **Frontend:** Vite + React SPA + TypeScript, Tailwind CSS, shadcn/ui, React Router, @supabase/supabase-js, Vercel AI SDK
- **DB:** Supabase Postgres + pgvector
- **Auth:** Supabase Auth (email only)
- **Retrieval:** Hybrid (pgvector semantic + Postgres full-text + RRF fusion)
- **Hosting:** Railway
- **LLM + embeddings:** Ollama (local — llama3.1:8b + nomic-embed-text)

## Repo layout
```
/workspaces/Projects/GenAIFullStackDemoProject/document-copilot/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI + /health + chat router
│   │   ├── config.py            # Pydantic settings
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── chat.py          # POST /chat/stream (SSE, Ollama stub)
│   │   ├── auth/
│   │   │   └── dependencies.py  # JWT verification
│   │   └── database/
│   │       ├── models/          # 6 table models
│   │       └── supabase.py      # client factories
│   ├── alembic/
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── lib/        # env, supabase, http, api, auth
│   │   ├── pages/      # Chat, Login, SignUp
│   │   ├── components/
│   │   │   ├── ui/     # shadcn button
│   │   │   └── chat/   # Sidebar, MessageList, ChatInput
│   │   ├── App.tsx     # router with /chat
│   │   └── main.tsx
│   ├── tsconfig.app.json
│   ├── components.json
│   └── vite.config.ts
├── data/               # 25 SEC 10-K filings
├── docs/               # architecture, plans, guides, client brief
├── AGENTS.md
├── context.md
├── prompts.md
└── todo.md
```

## Session log
- Initial project review completed. All docs read. Ready to build.
- Installed prerequisites: Python 3.12.13 (via uv), uv 0.11.24, Node.js 22.23.1 (via nvm), pnpm 11.9.0 (via corepack).
- Ran `data/download.py` — downloaded 25 SEC 10-K filings (5 companies × 5 years) into `data/downloads/`.
- Created `todo.md` with full build checklist (9 phases, 40+ items).
- Switched from OpenAI to Ollama (local AI) across all docs, config, and plans. Models: `llama3.1:8b` (LLM) + `nomic-embed-text` (embeddings, 768d).
- Initialized git repo.
- Installed backend deps: fastapi, uvicorn, pydantic, pydantic-settings, httpx, structlog, openai, supabase, pydantic-ai, sqlalchemy, alembic, psycopg[binary], pgvector (168 packages).
- Scaffolded backend Phase 1: config.py, main.py, database/models/, database/supabase.py, Alembic init. All imports verified. Health endpoint returns 200.
- Ran initial Alembic migration — 6 tables created in Supabase (users, source_documents, document_chunks, chat_threads, chat_messages, message_citations).
- Phase 2 (auth + frontend scaffold): auth/dependencies.py, lib/env.ts, lib/supabase.ts, lib/http.ts, lib/api.ts, lib/auth.tsx, Login/SignUp pages, App.tsx router with auth guards, main.tsx with BrowserRouter + AuthProvider. TypeScript compiles clean.
- Created test user via admin API: test@driftwood.com / test123456.
- Auth flow verified end-to-end (login -> redirects to "/" -> shows "Signed in as test@driftwood.com").
- Accidental: installed `ai` 7.0.3 + `@ai-sdk/react` 4.0.4 during this session (was not asked to start Phase 3).
- Phase 3 backend: created `api/chat.py` with `POST /chat/stream` — receives AI SDK v4 wire format (`id`, `messages`, `trigger`, `messageId`), streams Ollama response as SSE `text-start`/`text-delta`/`text-end` events, protected by `get_current_user`. Verified server starts and returns 401 without auth.
- Phase 3 frontend: `getAccessToken` exported from `supabase.ts` and shared with `http.ts`. Created `Chat.tsx` (useChat + DefaultChatTransport + auth guard), `MessageList.tsx` (bubbles, auto-scroll, empty state, streaming cursor), `ChatInput.tsx` (form + send on Enter), `Sidebar.tsx` (app branding, new chat button, sign out). Wired `/chat` route in `App.tsx`. Both `tsc --noEmit` and `pnpm build` pass clean.
- Fixed `tsconfig.app.json` — added `ignoreDeprecations: "6.0"` for TypeScript 6 `baseUrl` deprecation in build mode.
- Created `docs/phase-3-plan.md` and `docs/phase-3-frontend-plan.md` during planning.
- Phase 4: installed Ollama (`ollama serve`), pulled `nomic-embed-text`. 25/25 HTML→Markdown conversion via docling + 25 `source_documents` inserted.
- Phase 4 ingestion script: `backend/ingest/chunk_and_load.py` — converts HTML to DoclingDocument, chunks via HybridChunker (~800 chars avg), detects 10-K Item sections from document structure, embeds via Ollama `nomic-embed-text` (768d, batch 8), inserts into `document_chunks`, updates `search_vector` via `to_tsvector()`. Tested single filing (AAPL 2025, 695 chunks), then batch all 25 (22,209 total). Added `get_admin_connection()` + `execute_sql()` to `app/database/supabase.py` for raw Postgres queries.
- Phase 4 verified: all 25 filings present in `document_chunks` with embeddings, sections, search_vector, and metadata (ticker, year, company_name via `source_documents` join).
- Updated `todo.md` Phase 4 items to match actual implementation.
- Updated `docs/phase-5-plan.md` incorporating hybrid search patterns from `daveebbelaar/ai-cookbook`: RRF with k=60, graceful degradation, `DocumentRetriever` designed as PydanticAI tool for Phase 6.
