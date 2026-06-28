# Phase 6 — LLM Assistant (PydanticAI Agent)

**Goal**: Replace the Phase 3 stub chat with a typed PydanticAI agent that uses the retriever to answer questions with citations.

## Context

From `architecture.md`:
- `backend/app/assistant/agent.py` — PydanticAI agent definition (line 153)
- `backend/app/assistant/deps.py` — Runtime dependency dataclass (line 154)
- `backend/app/assistant/outputs.py` — GroundedAnswer, Citation, SourcePassage (lines 155, 184-187)
- `backend/app/assistant/instructions.md` — System prompt and product contract (lines 156, 191-195)

Agent receives bounded tools: `search_filings`, `read_chunk`, `read_surrounding_chunks` (line 209).

## Dependency check

`pydantic-ai` is already installed (1.107.0). No new deps needed.

## Files to create

### `app/assistant/__init__.py`
Package marker.

### `app/assistant/outputs.py` — Typed output models

```python
class SourcePassage(BaseModel):
    id: str
    chunk_text: str
    section: str | None
    document_id: str
    ticker: str
    company_name: str
    year: str

class Citation(BaseModel):
    chunk_id: str
    excerpt: str
    ticker: str
    company_name: str
    year: str
    section: str | None

class GroundedAnswer(BaseModel):
    answer: str
    citations: list[Citation]
```

Aligned with `architecture.md:184-187`.

### `app/assistant/deps.py` — Agent dependencies

```python
@dataclass
class DocumentAgentDeps:
    user_id: str
    thread_id: str
    retriever: DocumentRetriever
```

Aligned with `architecture.md:176-181` (grounding_validator will come in Phase 7).

### `app/assistant/instructions.md` — System prompt

Product contract from `architecture.md:191-195` and `client-brief.md:60-68`:
- Answer only from retrieved passages. Cite every factual claim by including the source filing ticker and section.
- If retrieved context is insufficient, say the corpus does not contain enough evidence.
- Do not provide stock recommendations or investment advice.
- Keep answers concise but include enough cited evidence for analyst verification.
- Use Markdown formatting for readability (lists, bold for key figures).

### `app/assistant/agent.py` — PydanticAI agent

1. Load `instructions.md` as system prompt.
2. Define a `search_filings` tool:
   - Takes `query: str` and optional `top_k: int = 10`.
   - Calls `deps.retriever.search(query, top_k)` and returns formatted passages (ticker, year, section, excerpt) with their chunk IDs.
3. Create `Agent[DocumentAgentDeps, GroundedAnswer]` with:
   - System prompt from `instructions.md`
   - `search_filings` tool
   - `result_type=GroundedAnswer`
4. Expose `async def run_agent(deps: DocumentAgentDeps, user_message: str) -> GroundedAnswer`.

**Key concern — Ollama tool calling**: `llama3.1:8b` has limited native tool-calling support. PydanticAI supports fallback strategies:
- If the Ollama model supports OpenAI-compatible tool calling: use `agent.run()` with tools.
- If not: use PydanticAI's prompt-based tool extraction, where the model's text output is parsed into a structured result.

The plan should test this first with a single query. If tool calling fails, fall back to:
1. Append retrieved passages as context to the user message: `"Context:\n{passages}\n\nQuestion: {user_message}"`
2. Ask the model to return answer text with inline citation markers.
3. Parse the response to extract `GroundedAnswer`.

### `tests/assistant/test_agent.py`

- `test_search_filings_tool_signature` — verify tool schema matches expected
- `test_agent_deps_construction` — verify deps can be constructed
- `test_instructions_md_loaded` — verify file is readable and contains expected sections
- (Integration tests for actual LLM calls would be behind `@pytest.mark.integration`)

Aligned with `backend/AGENTS.md:78` — "Required test coverage: ...citation extraction".

## Key decisions

- **PydanticAI chosen over raw OpenAI SDK calls**: Provides typed result validation, dependency injection, and testability (per `architecture.md:51`).
- **Tool-calling fallback**: Because `llama3.1:8b` tool support may not work reliably with PydanticAI's tool protocol, the fallback path uses context injection + prompt-based extraction.
- **instructions.md as a standalone file**: Keeps the prompt editable without touching Python code. Loaded at module import time.
- **No grounding_validator in deps yet**: Phase 7 adds it. Phase 6 focuses on the agent boundary.
