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

## Session 3

1. **Plan Phase 8+9 chat orchestration** — Discussed keyword extraction (deemed unnecessary), designed SSE protocol with pipeline status events, thread CRUD, citation rendering, StatusIndicator component.
2. **Implement backbone** — Created `app/chat/events.py` (SSE builders), `app/chat/persistence.py` (DB ops), `app/chat/pipeline.py` (retrieve→agent→ground→persist→stream), `app/chat/router.py` (routes), rewired `app/main.py`.
3. **Frontend chat components** — StatusIndicator (pipeline pills with checkmarks/active/done states), CitationBadge (superscript tooltip), CitationPanel (expandable citations with excerpt previews), ThreadList (sidebar with click-switch + inline rename).

## Session 4

1. **Revisit keyword extraction** — Re-analyzed the gap: FTS `plainto_tsquery` AND-s all non-stopwords including noise (show, tell, face). Real improvement comes from entity extraction (ticker → exact column filter, year → exact column filter), not from a third search leg.
2. **Plan query refinery** — Designed `query_refinery.py` with `RefinedQuery` dataclass, NLTK stopwords + domain noise words, ticker/year entity extraction, company name→ticker resolution via `source_documents` DB lookup, `refined_fulltext_search()` with optional `IN` filters.
3. **Implement query refinery** — Created `query_refinery.py`, modified `queries.py` (added `REFINED_FTS_SQL` + `refined_fulltext_search()`), modified `retriever.py` (wired `refine_query()` into `search()`). NLTK `stopwords` corpus for clean stopword removal without messy inline lists. Graceful fallbacks for missing NLTK data and DB connection failures.
4. **Tests** — `tests/retrieval/test_query_refinery.py` with 12 tests covering company→ticker, ticker pattern, false positives, year formats, multi-entity, noise filtering, all-noise fallback, unknown company.
4. **Update existing components** — MessageList renders StatusIndicator + CitationBadge + CitationPanel; Sidebar embeds ThreadList; Chat.tsx uses `useChat` with `onChunk` for pipeline status + structured citations, thread loading/switching.
5. **Tests** — `tests/chat/test_events.py` (SSE event format, edge cases).
