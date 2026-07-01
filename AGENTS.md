# Agent Instructions

This file is the source of truth for any coding agent (Claude Code, Cursor, Codex, etc.) working in this repo. Read it before touching code.

## SSE Status Events (frontend status indicator)

The `StatusIndicator` shows stages: **Searching → Generating → Validating**.

| SSE `type` | `status` value | Stage transition |
|---|---|---|
| `data-status` | `retrieving` | Searching → active |
| `data-status` | `generating` | Searching → done, Generating → active |
| `data-status` | `grounding` | Generating → done, Grounding → active |
| `data-status` | `grounding_failed` | Grounding → failed |
| `data-status` | `complete` | Grounding → done (component hides when all done) |
| `data-error` | — | Resets all to waiting |

Emitted from `pipeline.py` in order: retrieving → generating → (agent runs, may call `search_filings`) → grounding → complete.

## Stack

- **Backend:** Python + FastAPI
- **Frontend:** Vite + React SPA + TypeScript
- **Database:** Supabase Postgres (users, chats, source documents, chunks)
- **Migrations:** SQLAlchemy models + Alembic from the backend
- **Retrieval:** Supabase `pgvector` + Postgres full-text search
- **Auth:** Supabase Auth
- **Hosting:** Railway (backend service + frontend service)
- **LLM + embeddings:** Ollama (local — llama3.1:8b + nomic-embed-text)

Stack is locked unless explicitly changed. Don't propose alternatives without a stated reason.

## Repo layout

```text
document-copilot/
├── AGENTS.md           # this file
├── README.md
├── data/               # local corpus + download script (payloads gitignored)
├── docs/               # specs, briefs, design notes
├── backend/            # FastAPI service (see backend/AGENTS.md)
└── frontend/           # React SPA (see frontend/AGENTS.md)
```

## Dependency policy

**Default: write it yourself. Reach for a library only when the alternative would be non-trivial, error-prone, or reinvention of a standard.** Every dependency is a liability — bundle size, supply-chain risk, future upgrade work.

OK to depend on:

- Things that are genuinely hard to get right (HTTP clients, ASGI servers, SQL drivers, parsers, LLM SDKs, ORM, migrations, auth SDKs).
- The declared stack (FastAPI, React, Vite, Supabase clients, OpenAI SDK pointed at Ollama, etc.).

Not OK:

- Helper libraries that wrap 5–20 lines of stdlib or platform APIs.
- Frameworks where a function would do.
- "Nicer API" layers on top of an already-present dependency.

Before adding a runtime dep, answer in the commit message:

1. What exactly does it do that we can't write in <30 lines of clear code?
2. How often does it get used?
3. What's its maintenance / transitive-dep footprint?

Per-stack specifics live in `backend/AGENTS.md` and `frontend/AGENTS.md`.

## Configuration

A single settings module is the source of truth for environment per service (`backend/app/config.py`, `frontend/lib/env.ts`). Do not call `os.getenv` / read `process.env` directly in app code. Do not call `load_dotenv` anywhere. If a third-party SDK reads env vars directly, mirror them in the settings module — don't sprinkle `setdefault` elsewhere.

Fail fast on startup if required config is missing. No silent fallbacks that hide real config errors.

## SSE Status Events (frontend status indicator)

`StatusIndicator` shows stages: **Searching → Generating → Validating**.

| SSE `type` | `status` value | Frontend transition |
|---|---|---|
| `data-status` | `retrieving` | Searching → active |
| `data-status` | `generating` | Searching → done, Generating → active |
| `data-status` | `grounding` | Generating → done, Grounding → active |
| `data-status` | `grounding_failed` | Grounding → failed |
| `data-status` | `complete` | Grounding → done (component hides) |
| `data-error` | — | Resets all to waiting |

Emitted from `pipeline.py` in order: retrieving → generating → (agent runs) → grounding → complete.

"submitted" state (before first SSE event) renders StatusIndicator with all stages waiting.

## Key Fixes / Known Issues

- **"SEC" in `_TICKER_FALSE_POSITIVES`** (`backend/app/retrieval/query_refinery.py:91`): Prevents `refine_query` from extracting "SEC" as a stock ticker when the model searches for "SEC filing analysis" on non-filing questions.
- **Instructions explicitly list skip-search categories** (`backend/app/assistant/instructions.md:5-9`): "Do NOT search for these kinds of questions — just respond naturally" — identity, greetings, general knowledge, system questions.
- **Rule #8 — no fabricated citations** (`instructions.md:20`): "If you do not have valid, non-empty citation data, output 'citations': []".

## Code style (universal)

- **Small, obvious functions.** A 15-line function with clear names beats a three-class abstraction.
- **No premature abstraction.** Three similar lines is better than a badly-named base class. Extract when there's a third caller, not a hypothetical one.
- **No error handling for cases that can't happen.** Trust internal callers and framework guarantees. Validate only at boundaries: HTTP input, external APIs, DB writes, untrusted parsing.
- **No backwards-compat shims** unless explicitly asked for.
- **No feature flags** added speculatively.
- **Comments:** explain *why* when non-obvious, never *what*. Remove stale TODOs.
- **Keep files focused.** Prefer small modules.
