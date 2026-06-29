from __future__ import annotations

import pytest

from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.queries import SearchResult


def _r(
    chunk_id: str,
    ticker: str = "AAPL",
    year: str = "2025",
    score: float = 1.0,
) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        chunk_text=f"content of {chunk_id}",
        section="Item 1: Business",
        document_id="doc-1",
        ticker=ticker,
        company_name="Apple Inc.",
        year=year,
        score=score,
    )


class TestEmptyLists:
    def test_both_empty(self) -> None:
        assert reciprocal_rank_fusion([], []) == []

    def test_semantic_empty(self) -> None:
        ft = [_r("c1"), _r("c2")]
        result = reciprocal_rank_fusion([], ft)
        assert len(result) == 2
        assert result[0].chunk_id == "c1"

    def test_fulltext_empty(self) -> None:
        sem = [_r("c1"), _r("c2")]
        result = reciprocal_rank_fusion(sem, [])
        assert len(result) == 2
        assert result[0].chunk_id == "c1"


class TestOverlapping:
    def test_same_chunk_both_lists(self) -> None:
        sem = [_r("c1", score=0.9), _r("c2", score=0.8)]
        ft = [_r("c1", score=0.7), _r("c3", score=0.6)]
        result = reciprocal_rank_fusion(sem, ft, top_k=3)
        ids = [r.chunk_id for r in result]
        assert ids == ["c1", "c2", "c3"]

    def test_overlapping_gets_boosted(self) -> None:
        c1_ft = _r("c1")
        c1_sem = _r("c1")
        result = reciprocal_rank_fusion([c1_sem], [c1_ft], top_k=1)
        assert len(result) == 1
        # RRF: 1/(60+1) + 1/(60+1) = 2/61 ≈ 0.0328
        assert abs(result[0].score - 2.0 / 61.0) < 1e-10


class TestDisjoint:
    def test_disjoint_interleaving(self) -> None:
        sem = [_r("a"), _r("b")]
        ft = [_r("x"), _r("y")]
        result = reciprocal_rank_fusion(sem, ft, top_k=4)
        ids = [r.chunk_id for r in result]
        # RRF: a=1/61, x=1/61, b=1/62, y=1/62 → a, x, b, y
        assert ids == ["a", "x", "b", "y"]


class TestTopK:
    def test_respects_top_k(self) -> None:
        sem = [_r(f"c{i}") for i in range(10)]
        ft = [_r(f"d{i}") for i in range(10)]
        result = reciprocal_rank_fusion(sem, ft, top_k=3)
        assert len(result) == 3

    def test_top_k_larger_than_candidates(self) -> None:
        sem = [_r("c1")]
        result = reciprocal_rank_fusion(sem, [], top_k=10)
        assert len(result) == 1

    def test_exact_count_match(self) -> None:
        sem = [_r(f"c{i}") for i in range(5)]
        result = reciprocal_rank_fusion(sem, [], top_k=5)
        assert len(result) == 5


class TestScore:
    def test_rrf_score_calculation(self) -> None:
        c = _r("c1")
        result = reciprocal_rank_fusion([c], [], top_k=1, k=60)
        assert abs(result[0].score - 1.0 / 61.0) < 1e-10

    def test_different_k_smoothing(self) -> None:
        result_k1 = reciprocal_rank_fusion([_r("c1")], [], top_k=1, k=1)
        result_k60 = reciprocal_rank_fusion([_r("c2")], [], top_k=1, k=60)
        assert result_k1[0].score > result_k60[0].score

    def test_rejects_negative_k(self) -> None:
        with pytest.raises(ZeroDivisionError):
            reciprocal_rank_fusion([_r("c1")], [], k=-1)
