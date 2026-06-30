from __future__ import annotations

from app.assistant.outputs import Citation, GroundedAnswer
from app.grounding.validator import GroundingValidator


class TestValidCitations:
    def test_all_citations_in_retrieved_set(self) -> None:
        c1 = Citation(
            chunk_id="chunk-a",
            excerpt="Revenue grew 10%",
            ticker="AAPL",
            company_name="Apple Inc.",
            year="2025",
            section="Item 7",
        )
        c2 = Citation(
            chunk_id="chunk-b",
            excerpt="Operating income was $100B",
            ticker="AAPL",
            company_name="Apple Inc.",
            year="2025",
            section="Item 8",
        )
        answer = GroundedAnswer(answer="Apple's revenue grew.", citations=[c1, c2])
        validator = GroundingValidator(retrieved_chunk_ids={"chunk-a", "chunk-b"})
        result = validator.validate(answer)

        assert result.passed
        assert len(result.citations) == 2
        assert result.errors == []

    def test_single_valid_citation(self) -> None:
        c = Citation(
            chunk_id="chunk-1",
            excerpt="Net sales were $391B",
            ticker="AAPL",
            company_name="Apple Inc.",
            year="2025",
        )
        answer = GroundedAnswer(answer="$391B", citations=[c])
        validator = GroundingValidator(retrieved_chunk_ids={"chunk-1"})
        result = validator.validate(answer)

        assert result.passed
        assert len(result.citations) == 1
        assert result.errors == []


class TestUnretrievedCitations:
    def test_citation_not_in_retrieved_set(self) -> None:
        c = Citation(
            chunk_id="chunk-made-up",
            excerpt="Fake data",
            ticker="AAPL",
            company_name="Apple Inc.",
            year="2025",
        )
        answer = GroundedAnswer(answer="Something", citations=[c])
        validator = GroundingValidator(retrieved_chunk_ids={"chunk-real-1", "chunk-real-2"})
        result = validator.validate(answer)

        assert not result.passed
        assert len(result.citations) == 0
        assert any("not in the retrieved set" in e for e in result.errors)

    def test_mixed_valid_and_invalid(self) -> None:
        valid = Citation(
            chunk_id="chunk-real",
            excerpt="Real data",
            ticker="AAPL",
            company_name="Apple Inc.",
            year="2025",
        )
        invalid = Citation(
            chunk_id="chunk-fake",
            excerpt="Fake data",
            ticker="AAPL",
            company_name="Apple Inc.",
            year="2025",
        )
        answer = GroundedAnswer(answer="Mixed citations.", citations=[valid, invalid])
        validator = GroundingValidator(retrieved_chunk_ids={"chunk-real"})
        result = validator.validate(answer)

        assert not result.passed
        assert len(result.citations) == 1
        assert result.citations[0].chunk_id == "chunk-real"
        assert any("not in the retrieved set" in e for e in result.errors)


class TestMissingFields:
    def test_citation_missing_excerpt(self) -> None:
        c = Citation(
            chunk_id="chunk-1",
            excerpt="",
            ticker="AAPL",
            company_name="Apple Inc.",
            year="2025",
        )
        answer = GroundedAnswer(answer="Something", citations=[c])
        validator = GroundingValidator(retrieved_chunk_ids={"chunk-1"})
        result = validator.validate(answer)

        assert not result.passed
        assert any("missing required fields" in e for e in result.errors)

    def test_citation_missing_ticker(self) -> None:
        c = Citation(
            chunk_id="chunk-1",
            excerpt="Some text",
            ticker="",
            company_name="Apple Inc.",
            year="2025",
        )
        answer = GroundedAnswer(answer="Something", citations=[c])
        validator = GroundingValidator(retrieved_chunk_ids={"chunk-1"})
        result = validator.validate(answer)

        assert not result.passed
        assert any("missing required fields" in e for e in result.errors)

    def test_citation_missing_company_name(self) -> None:
        c = Citation(
            chunk_id="chunk-1",
            excerpt="Some text",
            ticker="AAPL",
            company_name="",
            year="2025",
        )
        answer = GroundedAnswer(answer="Something", citations=[c])
        validator = GroundingValidator(retrieved_chunk_ids={"chunk-1"})
        result = validator.validate(answer)

        assert not result.passed
        assert any("missing required fields" in e for e in result.errors)


class TestEmptyCitations:
    def test_empty_citations_with_disclaimer(self) -> None:
        answer = GroundedAnswer(
            answer="The corpus does not contain enough evidence to answer this question.",
            citations=[],
        )
        validator = GroundingValidator(retrieved_chunk_ids=set())
        result = validator.validate(answer)

        assert result.passed
        assert result.citations == []
        assert result.errors == []

    def test_empty_citations_no_disclaimer(self) -> None:
        answer = GroundedAnswer(
            answer="I think the answer might be $100B.",
            citations=[],
        )
        validator = GroundingValidator(retrieved_chunk_ids=set())
        result = validator.validate(answer)

        assert not result.passed
        assert any("no citations" in e for e in result.errors)
