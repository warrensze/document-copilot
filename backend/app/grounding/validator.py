from __future__ import annotations

from dataclasses import dataclass, field

from app.assistant.outputs import Citation, GroundedAnswer

_DISCLAIMER_PHRASES = (
    "does not contain enough evidence",
    "the corpus does not",
    "no information in the provided documents",
    "cannot answer",
    "not enough evidence",
)


@dataclass
class GroundingResult:
    passed: bool
    citations: list[Citation]
    errors: list[str] = field(default_factory=list)


@dataclass
class GroundingValidator:
    retrieved_chunk_ids: set[str]

    def validate(self, answer: GroundedAnswer) -> GroundingResult:
        errors: list[str] = []
        valid_citations: list[Citation] = []

        for c in answer.citations:
            if c.chunk_id not in self.retrieved_chunk_ids:
                errors.append(
                    f"Citation chunk_id '{c.chunk_id}' was not in the retrieved set "
                    f"(model cited an unretrieved chunk)"
                )
                continue

            if not c.excerpt or not c.ticker or not c.company_name:
                errors.append(
                    f"Citation chunk_id '{c.chunk_id}' is missing required fields "
                    f"(excerpt={bool(c.excerpt)}, ticker={bool(c.ticker)}, company_name={bool(c.company_name)})"
                )
                continue

            valid_citations.append(c)

        if not answer.citations:
            has_disclaimer = any(p in answer.answer.lower() for p in _DISCLAIMER_PHRASES)
            if not has_disclaimer:
                errors.append(
                    "Answer has no citations but does not state that evidence is insufficient"
                )

        return GroundingResult(
            passed=len(errors) == 0,
            citations=valid_citations,
            errors=errors,
        )
