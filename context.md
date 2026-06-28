# Context

## Project
**Document Copilot** — internal AI chatbot for Driftwood Capital analysts. Query SEC filings in natural language, get grounded citable answers.

## State
Phase 2 complete. Backend scaffolded, database live, frontend scaffolded, auth working end-to-end.

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
├── backend/          # FastAPI service
│   ├── app/
│   │   ├── main.py           # FastAPI entrypoint + /health
│   │   ├── config.py         # Pydantic settings
│   │   ├── auth/
│   │   │   └── dependencies.py  # JWT verification
│   │   └── database/
│   │       ├── models/       # 6 table models (split by file)
│   │       └── supabase.py   # client factories
│   ├── alembic/              # migrations
│   └── alembic.ini
├── frontend/         # React SPA
│   ├── src/
│   │   ├── lib/     # env, supabase, http, api, auth
│   │   ├── pages/   # Login, SignUp
│   │   ├── components/ui/  # shadcn button
│   │   ├── App.tsx  # router
│   │   └── main.tsx # BrowserRouter + AuthProvider
│   ├── components.json
│   └── vite.config.ts
├── data/             # 25 SEC 10-K filings downloaded
├── docs/             # architecture spec, client brief, setup guides
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
