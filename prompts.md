# Prompt History

## Session 1

1. **Review project files** — Read all docs and config to understand the codebase.
2. **Install prerequisites** — Python 3.12, uv, Node.js 22, pnpm.
3. **Run data download** — Execute `uv run data/download.py` for SEC filings.
4. **Explain .html vs .htm** — No difference; legacy 8.3 filename limit.
5. **Create todo.md** — Build checklist with 9 phases.
6. **Switch to local AI** — Replace OpenAI with Ollama (llama3.1:8b + nomic-embed-text, 768d) across all docs, config, and plans.
7. **Git init**
8. **Install backend deps** — `uv add fastapi uvicorn pydantic pydantic-settings httpx structlog openai supabase pydantic-ai sqlalchemy alembic psycopg[binary] pgvector` (168 packages).
9. **Scaffold Phase 1** — Created config.py, main.py, database/models.py (6 tables), database/supabase.py, Alembic init. All verified.
10. **Create prompts.md** — Track prompt history going forward.
