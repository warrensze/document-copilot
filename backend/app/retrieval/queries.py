from __future__ import annotations

from dataclasses import dataclass

from psycopg import Connection

from app.config import settings


@dataclass
class SearchResult:
    chunk_id: str
    chunk_text: str
    section: str | None
    document_id: str
    ticker: str
    company_name: str
    year: str
    score: float


SEMANTIC_SQL = """
SELECT dc.id            AS chunk_id,
       dc.chunk_text,
       dc.section,
       dc.document_id,
       sd.ticker,
       sd.company_name,
       sd.year,
       1 - (dc.embedding <=> %s::vector) AS score
FROM document_chunks dc
JOIN source_documents sd ON dc.document_id = sd.id
ORDER BY dc.embedding <=> %s::vector
LIMIT %s
"""

FULLTEXT_SQL = """
SELECT dc.id            AS chunk_id,
       dc.chunk_text,
       dc.section,
       dc.document_id,
       sd.ticker,
       sd.company_name,
       sd.year,
       ts_rank(dc.search_vector, plainto_tsquery('english', %s)) AS score
FROM document_chunks dc
JOIN source_documents sd ON dc.document_id = sd.id
WHERE dc.search_vector @@ plainto_tsquery('english', %s)
ORDER BY score DESC
LIMIT %s
"""

REFINED_FTS_SQL = """
SELECT dc.id            AS chunk_id,
       dc.chunk_text,
       dc.section,
       dc.document_id,
       sd.ticker,
       sd.company_name,
       sd.year,
       ts_rank(dc.search_vector, plainto_tsquery('english', %(query)s)) AS score
FROM document_chunks dc
JOIN source_documents sd ON dc.document_id = sd.id
WHERE dc.search_vector @@ plainto_tsquery('english', %(query)s)
  AND (COALESCE(%(tickers)s::text[], '{}') = '{}' OR sd.ticker = ANY(%(tickers)s))
  AND (COALESCE(%(years)s::text[], '{}') = '{}' OR sd.year = ANY(%(years)s))
ORDER BY score DESC
LIMIT %(top_k)s
"""


def _vec_str(embedding: list[float]) -> str:
    return "[" + ",".join(str(v) for v in embedding) + "]"


def semantic_search(
    conn: Connection,
    embedding: list[float],
    top_k: int | None = None,
) -> list[SearchResult]:
    top_k = top_k or settings.retrieval_inner_top_k
    vec = _vec_str(embedding)
    rows = conn.execute(SEMANTIC_SQL, (vec, vec, top_k)).fetchall()
    return [_row_to_result(r) for r in rows]


def fulltext_search(
    conn: Connection,
    query: str,
    top_k: int | None = None,
) -> list[SearchResult]:
    top_k = top_k or settings.retrieval_inner_top_k
    rows = conn.execute(FULLTEXT_SQL, (query, query, top_k)).fetchall()
    return [_row_to_result(r) for r in rows]


def refined_fulltext_search(
    conn: Connection,
    query: str,
    tickers: list[str] | None = None,
    years: list[str] | None = None,
    top_k: int | None = None,
) -> list[SearchResult]:
    top_k = top_k or settings.retrieval_inner_top_k
    rows = conn.execute(
        REFINED_FTS_SQL,
        {
            "query": query,
            "tickers": tickers or None,
            "years": years or None,
            "top_k": top_k,
        },
    ).fetchall()
    return [_row_to_result(r) for r in rows]


def _row_to_result(row: tuple) -> SearchResult:
    return SearchResult(
        chunk_id=str(row[0]),
        chunk_text=row[1],
        section=row[2],
        document_id=str(row[3]),
        ticker=row[4],
        company_name=row[5],
        year=row[6],
        score=float(row[7]),
    )
