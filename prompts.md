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

## Session 2

1. **Continue Phase 7** — Read grounding files, ask about next steps.
2. **Create grounding validator** — Built `app/grounding/__init__.py` + `app/grounding/validator.py` with `GroundingValidator` (checks chunk_id in retrieved set, required fields non-empty, empty-citation disclaimer rule).
3. **Update retrieval README** — Added config file path link and MacBook Air (16 GB) optimisation section with parameter rationale.
4. **Create tests** — `tests/grounding/test_validator.py` with 9 tests across 4 classes: valid, unretrieved, missing fields, empty citations.
5. **Update context files** — Updated `AGENTS.md` progress section, `todo.md` Phase 7 checkmarks, created `context.md`, appended to `prompts.md`.
