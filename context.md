# Project Context

## Status
Phases 0–7 complete. Phase 8 (chat orchestration) is next.

## What's Built

### Backend (Python + FastAPI)
- **Config**: Single `app/config.py` pydantic-settings module — source of truth for all env vars.
- **Database**: Supabase Postgres + pgvector. 6 SQLAlchemy models. Alembic migrations. HNSW + GIN indexes.
- **Auth**: JWT verification via Supabase Auth. `current_user` dependency on protected routes.
- **Ingestion**: 25 SEC 10-K filings → 22,209 chunks with 768d embeddings (nomic-embed-text) + full-text search vectors.
- **Retrieval**: `DocumentRetriever` — embed query → pgvector semantic search + Postgres FTS → RRF fusion. Graceful degradation (empty results, missing search vector, missing DB config).
- **Assistant**: PydanticAI `Agent[DocumentAgentDeps, GroundedAnswer]` — `OllamaProvider`, `retries=2`, `prompted` output mode. `search_filings` tool. Structured citations.
- **Grounding**: `GroundingValidator` — validates citations against retrieved chunk set, checks required fields, empty-citation disclaimer rule.

### Frontend (Vite + React + TypeScript)
- Supabase email auth (login/signup pages, AuthContext).
- Chat UI: message list (auto-scroll, empty state), input bar, sidebar (branding, new chat, sign out).
- All under `src/` with path alias `@/`.

## Test Coverage (32/32 unit tests pass)
| Module | Tests | Note |
|---|---|---|
| `tests/retrieval/test_fusion.py` | 12 | RRF algorithm, edge cases |
| `tests/assistant/test_agent.py` | 11 | Unit (tool schema, deps, models, instructions) |
| `tests/grounding/test_validator.py` | 9 | Valid, unretrieved, missing fields, empty citations |

+4 integration tests in `test_agent.py` (not run in CI — require Ollama, slow ~30–110s each).

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

## Next Steps
- Phase 8: Chat orchestration (persist threads/messages/citations in DB)
- Phase 9: UI polish (thread history sidebar, citation rendering, loading states)
