# Context

## Project
**Document Copilot** — internal AI chatbot for Driftwood Capital analysts. Query SEC filings in natural language, get grounded citable answers.

## State
Greenfield/scaffolding. Backend and frontend are empty shells (config only).

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
├── backend/          # FastAPI service (empty, needs building)
├── frontend/         # React SPA (empty, needs building)
├── data/             # download.py for SEC EDGAR 10-K corpus
├── docs/             # architecture spec, client brief, setup guides
├── AGENTS.md         # universal agent rules
├── context.md        # this file
```

## Session log
- Initial project review completed. All docs read. Ready to build.
- Installed prerequisites: Python 3.12.13 (via uv), uv 0.11.24, Node.js 22.23.1 (via nvm), pnpm 11.9.0 (via corepack).
- Ran `data/download.py` — downloaded 25 SEC 10-K filings (5 companies × 5 years) into `data/downloads/`.
- Created `todo.md` with full build checklist (9 phases, 40+ items).
- Switched from OpenAI to Ollama (local AI) across all docs, config, and plans. Models: `llama3.1:8b` (LLM) + `nomic-embed-text` (embeddings, 768d).
- Initialized git repo.
- Installed backend deps: fastapi, uvicorn, pydantic, pydantic-settings, httpx, structlog, openai, supabase, pydantic-ai, sqlalchemy, alembic, psycopg[binary], pgvector (168 packages).
- Scaffolded backend Phase 1: config.py, main.py, database/models.py, database/supabase.py, Alembic init. All imports verified. Health endpoint returns 200.
