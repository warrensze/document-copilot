# Phase 7 — Grounding and Citation Validation

**Goal**: Enforce the product contract — every citation in the assistant's answer must map to a chunk that was actually retrieved for the current request.

## Context

From `architecture.md:321-333`:
- Every answer has at least one citation unless the answer explicitly says there's not enough evidence.
- Every citation maps to a retrieved source passage.
- Cited passages include enough metadata for the frontend to show company, filing, date, section.
- The model cannot cite documents that were not retrieved for the current request.
- If citation validation fails, return a controlled failure instead of a polished unsupported answer.

## Files to create

### `app/grounding/__init__.py`
Package marker.

### `app/grounding/validator.py` — GroundingValidator

```python
@dataclass
class GroundingValidator:
    retrieved_chunk_ids: set[str]

    def validate(self, answer: GroundedAnswer) -> GroundingResult:
        ...
```

**`class GroundingResult`**:
- `passed: bool`
- `citations: list[Citation]` — validated citations
- `errors: list[str]` — e.g. "Citation chunk X was not in retrieved set", "Answer has no citations but does not state evidence is insufficient"

**Validation rules**:
1. Every `Citation.chunk_id` must be in `self.retrieved_chunk_ids`. If any citation references an unretrieved chunk → hard fail (the model invented a citation).
2. Every citation must have non-empty `excerpt`, `ticker`, `company_name`.
3. If the answer has zero citations and the answer text does not contain a disclaimer phrase (e.g., "does not contain enough evidence", "the corpus does not", "no information in the provided documents") → warning (not a hard fail, but noted).
4. If all citations pass → `passed=True`.
5. If any citation fails rule 1 → `passed=False` with error details.

Aligned with `architecture.md:327-331`.

### `tests/grounding/test_validator.py`

- `test_valid_citations` — all chunk_ids in retrieved set, all have required fields → passed
- `test_citation_not_in_retrieved_set` — chunk_id absent from retrieved_chunk_ids → hard fail
- `test_citation_missing_fields` — missing excerpt → hard fail
- `test_empty_citations_with_disclaimer` — no citations but answer says "not enough evidence" → passed with note
- `test_empty_citations_no_disclaimer` — no citations, no disclaimer → warning flag

Aligned with `backend/AGENTS.md:78` — "Required test coverage: grounding enforcement".

## Wiring (Phase 8)

The `GroundingValidator` is instantiated per-request in the chat orchestrator with `retrieved_chunk_ids` collected during retrieval. After the agent returns a `GroundedAnswer`, the orchestrator:

1. Collects all `chunk_id`s from the `GroundedAnswer.citations`.
2. Calls `validator.validate(grounded_answer)`.
3. If `passed=False`: return an error event to the frontend instead of the answer (or strip invalid citations and flag the answer as potentially unsupported).
4. If `passed=True`: proceed to persist the answer and citations.

## Key decisions

- **Validates against retrieved_chunk_ids, not the full DB**: Prevents the model from citing arbitrary chunks it wasn't given. The validator doesn't need a DB connection.
- **Disclaimer detection**: Simple substring match rather than NLU. Acceptable for Phase 7 — the system prompt explicitly tells the model what phrasing to use.
- **Hard fail vs soft fail**: Invalid chunk_ids = hard fail (answer not sent to user). Missing disclaimer = soft flag (logged but answer still delivered).
