from __future__ import annotations

from collections.abc import Sequence

from app.config import settings
from app.retrieval.queries import SearchResult


def reciprocal_rank_fusion(
    semantic: Sequence[SearchResult],
    fulltext: Sequence[SearchResult],
    top_k: int | None = None,
    k: int | None = None,
) -> list[SearchResult]:
    top_k = top_k or settings.retrieval_top_k
    k = k or settings.retrieval_rrf_k
    fused: dict[str, float] = {}
    seen: dict[str, SearchResult] = {}

    for rank, result in enumerate(semantic, start=1):
        fused[result.chunk_id] = fused.get(result.chunk_id, 0.0) + 1.0 / (k + rank)
        if result.chunk_id not in seen:
            seen[result.chunk_id] = result

    for rank, result in enumerate(fulltext, start=1):
        fused[result.chunk_id] = fused.get(result.chunk_id, 0.0) + 1.0 / (k + rank)
        if result.chunk_id not in seen:
            seen[result.chunk_id] = result

    sorted_ids = sorted(fused.keys(), key=lambda cid: fused[cid], reverse=True)

    results = []
    for cid in sorted_ids[:top_k]:
        result = seen[cid]
        result.score = fused[cid]
        results.append(result)

    return results
