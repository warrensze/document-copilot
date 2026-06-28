# Phase 5 — Retrieval Pipeline

**Goal**: Implement hybrid search over ingested document chunks — semantic (pgvector) + lexical (Postgres full-text) + Reciprocal Rank Fusion.

## Dependencies

No new dependencies. Uses:
- `psycopg` (already installed) for direct SQL queries against Supabase Postgres
- `openai` (already installed) to embed queries via Ollama `nomic-embed-text`
- `pgvector` SQLAlchemy type already installed (used in models, not needed at query time — queries are raw SQL)

## Files to create

### `app/retrieval/__init__.py`
Package marker.

### `app/retrieval/queries.py` — SQL queries

Two functions, each returning `(chunk_id, chunk_text, section, document_id, ticker, company_name, year, score)` tuples:

1. **`semantic_search(conn, embedding: list[float], top_k: int = 20) -> list[SearchResult]`**
   - Raw SQL: `SELECT dc.id, dc.chunk_text, dc.section, dc.document_id, sd.ticker, sd.company_name, sd.year, (dc.embedding <=> $1::vector) AS distance FROM document_chunks dc JOIN source_documents sd ON dc.document_id = sd.id ORDER BY distance LIMIT $2`
   - Returns results sorted by cosine distance ascending; convert distance to similarity score (1 - distance) for RRF.

2. **`fulltext_search(conn, query: str, top_k: int = 20) -> list[SearchResult]`**
   - Raw SQL: `SELECT dc.id, dc.chunk_text, dc.section, dc.document_id, sd.ticker, sd.company_name, sd.year, ts_rank(dc.search_vector, plainto_tsquery('english', $1)) AS rank FROM document_chunks dc JOIN source_documents sd ON dc.document_id = sd.id WHERE dc.search_vector @@ plainto_tsquery('english', $1) ORDER BY rank DESC LIMIT $2`
   - Returns results sorted by ts_rank descending.

Both use a lightweight `SearchResult` dataclass (id, chunk_text, section, document_id, ticker, company_name, year, score).

Aligned with `architecture.md:203-207` — "Run a semantic search... Run a lexical search...".

### `app/retrieval/fusion.py` — Reciprocal Rank Fusion

**`reciprocal_rank_fusion(semantic_results: list[SearchResult], fulltext_results: list[SearchResult], k: int = 60) -> list[SearchResult]`**

1. Assign each result a rank (1-indexed position in each list).
2. Compute fused score per unique chunk: `score = sum(1 / (k + rank))` for each list the chunk appears in.
3. Sort all unique chunks by fused score descending.
4. Re-rank and return top_k.

Aligned with `architecture.md:208` — "Fuse the two ranked lists in Python with Reciprocal Rank Fusion."

### `app/retrieval/retriever.py` — hybrid search orchestrator

**`class SearchResult`** dataclass (shared with queries.py, or import from there)

**`class DocumentRetriever`**:
- **`__init__(self, db_url: str, ollama_client: OpenAI)`** — stores connection parameters
- **`search(query: str, top_k: int = 15) -> list[SourcePassage]`**:
  1. Embed query with `ollama_client.embeddings.create(model="nomic-embed-text", input=query)` → 768d vector.
  2. Open psycopg connection.
  3. Run `semantic_search` (top_k=20) and `fulltext_search` (top_k=20) in parallel (or sequentially with a single connection).
  4. Call `reciprocal_rank_fusion` → top 15.
  5. Convert each result to `SourcePassage(id, chunk_text, section, document_id, ticker, company_name, year)` (reuses the Pydantic model that will be defined in Phase 6, or define a local dataclass now).
  6. Return list.

Aligned with `architecture.md:207-209` — "Fetch the selected chunks, source document metadata, and optional neighboring chunks for grounding."

### `tests/retrieval/test_fusion.py`
- `test_empty_lists`
- `test_only_semantic_results`
- `test_only_fulltext_results`
- `test_identical_results` — same chunk in both lists gets boosted
- `test_disjoint_results` — different chunks from each list interleaved correctly
- `test_top_k_respected`

Aligned with `backend/AGENTS.md:78` — "Required test coverage: retrieval."

## Key decisions

- **Raw SQL, not Supabase client**: `psycopg` connections are used directly because pgvector `<=>` operator and `ts_query` functions need raw SQL execution, and the Supabase Python client's query builder doesn't support vector operators natively.
- **Single-threaded**: For 25 filings (probably ~500–1000 chunks), both queries complete in milliseconds. No need for parallelism yet.
- **Query embedding**: Calls Ollama via OpenAI SDK (`client.embeddings.create`). Blocking call in a sync context (acceptable for now; will be wrapped in `run_in_executor` if needed when the retriever is called from async chat endpoints in Phase 8).
- **DB connection per search**: A `psycopg` connection opened and closed per `search()` call. Acceptable for per-request usage. Consider connection pooling in Phase 8.

## Out of scope

- `SourcePassage` Pydantic model — defined in Phase 6, used here as a local dataclass for now
- Async — Phase 8 converts to async
- Connection pooling — Phase 8
