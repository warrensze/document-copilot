# Skill: Building AI Chat Apps with Grounded Retrieval

Build a Python/FastAPI backend + React/TypeScript frontend AI chatbot
that answers questions grounded in a retrieval corpus (e.g. SEC filings,
internal docs, knowledge base) with citations and structured output.

---

## Core Architecture

```
User → FastAPI SSE → ChatPipeline → Agent (LLM + tools) → Retriever → DB
                                        ↓
                               GroundingValidator
                                        ↓
                              SSE stream to frontend
```

**Backend** (Python 3.12+, FastAPI, structlog, psycopg, openai SDK)
**Frontend** (Vite + React SPA, Tailwind, @ai-sdk/react useChat)

## The Right Fixes vs The Treadmill

### ✓ Tool-level guardrails (scalable)
If a tool's input lacks needed signal (ticker, year, domain keyword),
short-circuit the tool instead of running it with noise. Data-driven,
not pattern-list-driven.

```
Before: search_filings accepts any query → returns garbage → model hallucinates
After:  search_filings checks {ticker|year|keyword} → skips search if none found
```

### ✗ Instruction skip-lists (not scalable)
Adding "do not search for X, Y, Z" to the system prompt. Every new edge
case is another patch. The model also ignores them unpredictably.

### ✗ Query-string guesswork
Letting the model compose its own search queries with no guardrails.
Small models (llama3.2:3b) hallucinate search queries from the system
prompt text instead of using the user's actual question.

## The Failure Chain Pattern

Every garbage-response bug follows the same chain:

1. **Model calls a tool with a bad input** → e.g. searches "financial
   analyst assistant for SEC filing analysis" instead of the user's
   actual question ("who are you").
2. **Retrieval returns noise** → query refinement strips all signal,
   false-positive tickers filter the results to irrelevant boilerplate.
3. **Model fabricates from garbage** → forces the noise into the
   required structured output format → invalid fields → validation
   failure → retry loop → fallback.

### Fix at each link

| # | Problem | Fix | Level |
|---|---|---|---|
| 1 | Model searches for wrong thing | Add relevance pre-check to tool | Tool |
| 2 | Query refinement degrades signal | Filter false-positive tickers | Retriever |
| 3 | Fabrication with invalid fields | Strengthen validation rules | Output |
| 4 | Fallback hides real error | Internal try/except in agent | Orchestration |

## Retrospective (development patterns)

### Do up front
1. **Trace the full failure chain before touching code.**
   Read the actual LLM input/output/logs. Identify which link in
   the chain to break. A fix at link 3 (validation) doesn't help if
   link 1 (tool call) is the root cause.

2. **Ask "what outcome matters?" before implementing.**
   Speed of fix? Maintainability? Correctness? User experience?
   They can conflict. Get alignment first.

3. **Understand the data before the code.**
   What does the retrieval corpus actually contain? What do the
   chunk text, citations, tickers look like? Many bugs come from
   assuming the data is structured differently than it actually is.

4. **Design for the model's real capabilities, not its spec sheet.**
   llama3.2:3b cannot reliably:
   - Compose good search queries from natural language
   - Follow nuanced "do this, but not that" instructions
   - Produce valid structured JSON alongside tool calls
   
   Work around these constraints with code, not more prompting.

### Do NOT do
1. **Guess at the problem without reading the actual output.**
   The "blinking square" bug was obvious once the user said it. The
   "who are you" bug required reading the LLM log traces. Don't
   propose fixes for symptoms you haven't observed.

2. **Propose infinite-patch solutions.**
   Any fix that requires adding to a list (skip-search categories,
   more instructions, more examples) is a treadmill. The model will
   find new edge cases faster than you can list them.

3. **Architecture changes disguised as small fixes.**
   The user explicitly locked the architecture. Stay within the
   declared constraints. If the constraint is wrong, argue it with
   data, not by sneaking around it.

4. **Info-dump at the start of a response.**
   Answer the user's question in 1-3 sentences, then offer details
   on request. Buried context makes the conversation hard to follow.

5. **Skip the plan review step.**
   Before editing files, show the plan as a diff or bullet list.
   Let the user approve the direction before you write code.

## SSE Protocol for AI SDK v7

The `@ai-sdk/react` `useChat` hook v7 uses `DefaultChatTransport`.
It validates all `data:` lines against `uiMessageChunkSchema` (Zod union).

### Rules
- Custom events must use `type: "data-<name>"` (e.g. `data-status`)
- Include `"transient": true` in the JSON payload
- Events route through the `onData` callback, NOT `onChunk`
- Standard `text-start/delta/end` and `error` types are built-in

### Event flow
```
| SSE type            | onData type      | Purpose           |
|---------------------|------------------|--------------------|
| data: {type:...}    | onChunk/onData   | V7 uses onData    |
| data-status         | transit handlers | Pipeline stages   |
| data-citations      | attach to msg    | Citation data     |
| data-error          | show error       | Error messages    |
```

### Pipeline stage transitions
```
submitted → retrieving (active) → generating (active) → grounding (active) → complete → (hidden)
```

For the StatusIndicator component: show all stages as "waiting" during
the submitted state (before the first SSE event arrives), not a
blinking square or generic spinner.

## Recovery Patterns

### When the model fabricates bad citations
Catch at the grounding layer:
```python
validator = GroundingValidator(retrieved_chunk_ids=deps.retrieved_chunk_ids)
validation = validator.validate(answer)
if not validation.passed:
    answer.citations = []  # strip bad citations, keep answer text
```

This tells the user something useful instead of "connection lost."

### When the LLM API call fails
Wrap in try/except inside the agent runner, not the pipeline:
```python
try:
    result = await agent.run(user_message, deps=deps)
    return result.output
except Exception:
    logger.exception("agent_run_failed", ...)
    return GroundedAnswer(answer="...", citations=[])
```

The pipeline sees a valid `GroundedAnswer` either way — no SSE errors,
no "Connection lost" on the frontend.

## Ingest Pipeline for SEC Filings

```
HTML filing → DoclingDocument → HybridChunker (1024 tokens) →
  nomic-embed-text (768d) → Supabase document_chunks table
```

Each chunk row carries: `ticker`, `company_name`, `year`, `section`,
`chunk_text`, `embedding` (vector), `search_vector` (tsvector for FTS).

## Logging That Scales

Don't log every intermediate step. Log at key boundaries:

```
pipeline_start (thread_id, message[:200])
search (query, tickers, results=N)
pipeline_complete (thread_id, elapsed_s, citations=N)
agent_run_failed (thread_id, message[:200], +traceback)
pipeline_crash (thread_id, elapsed_s, +traceback)
```

Default level: INFO. Set `LOG_LEVEL=DEBUG` when debugging specific
retrieval quality issues. Remove per-request middleware (uvicorn
already logs HTTP).
