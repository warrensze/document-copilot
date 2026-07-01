from __future__ import annotations

import structlog

import psycopg
from openai import OpenAI

from app.config import settings
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.queries import SearchResult, fulltext_search, refined_fulltext_search, semantic_search
from app.retrieval.query_refinery import load_company_map, refine_query

logger = structlog.get_logger(__name__)


class DocumentRetriever:
    def __init__(self, db_url: str, ollama_client: OpenAI) -> None:
        self._db_url = db_url
        self._ollama_client = ollama_client
        self._company_map = load_company_map(db_url)

    def search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        top_k = top_k or settings.retrieval_top_k
        inner_top_k = max(top_k * 2, settings.retrieval_inner_top_k)

        refined = refine_query(query, company_map=self._company_map)

        embedding = self._embed_query(query)

        dsn = self._db_url.replace("+psycopg", "")

        semantic_results: list[SearchResult] | None = None
        fulltext_results: list[SearchResult] | None = None

        with psycopg.connect(dsn) as conn:
            if embedding is not None:
                try:
                    semantic_results = semantic_search(conn, embedding, top_k=inner_top_k)
                except Exception:
                    logger.warning("semantic search failed", exc_info=True)

            try:
                fulltext_results = refined_fulltext_search(
                    conn,
                    query=refined.clean_query,
                    tickers=refined.tickers if refined.has_filters else None,
                    years=refined.years if refined.has_filters else None,
                    top_k=inner_top_k,
                )
            except Exception:
                logger.warning("full-text search failed", exc_info=True)

        if semantic_results is None and fulltext_results is None:
            return []

        if semantic_results and semantic_results[0].score < settings.semantic_relevance_threshold:
            logger.info(
                "search_below_threshold",
                query=query,
                top_score=round(semantic_results[0].score, 3),
            )
            return []

        if semantic_results is None:
            results = list(fulltext_results)[:top_k]
        elif fulltext_results is None:
            results = list(semantic_results)[:top_k]
        else:
            results = reciprocal_rank_fusion(semantic_results, fulltext_results, top_k=top_k)

        logger.info("search", query=query, tickers=refined.tickers, results=len(results))
        return results

    def _embed_query(self, query: str) -> list[float] | None:
        try:
            resp = self._ollama_client.embeddings.create(
                model=settings.embedding_model,
                input=query,
            )
            return resp.data[0].embedding
        except Exception:
            logger.warning("query embedding failed, falling back to FTS-only", exc_info=True)
            return None
