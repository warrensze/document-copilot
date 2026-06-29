# Phase 5 — Retrieval Pipeline

**Goal**: Hybrid search over 22,209 document chunks — semantic (pgvector cosine) + keyword (Postgres FTS) → RRF fusion → clean `SearchResult` results ready for PydanticAI in Phase 6.

Reference patterns: [daveebbelaar/ai-cookbook](https://github.com/daveebbelaar/ai-cookbook) — `knowledge/hybrid-retrieval/` (BM25 + Dense + RRF + Reranker) and `knowledge/agentic-rag/` (PydanticAI agent with structured citations).

## Architecture

```
User query string
    │
    ├── ollama.embeddings.create("nomic-embed-text", query) → 768d vector
    │
    ├── semantic_search(conn, vector, 20)    → 20 SearchResult items (by cosine similarity)
    │
    ├── fulltext_search(conn, query, 20)     → 20 SearchResult items (by ts_rank)
    │
    └── reciprocal_rank_fusion(sem, ft, k=60, top_k=15)
         │
         └── 15 SearchResult items, sorted by RRF score, ready for Phase 6 agent context
```

## Patterns adopted from ai-cookbook

| ai-cookbook pattern | Our adaptation |
|---|---|
| `BM25Retriever` + `DenseRetriever` → `reciprocal_rank_fusion` | `semantic_search()` + `fulltext_search()` → `reciprocal_rank_fusion()` |
| Retriever as a service class (`search(query, k)`) | `DocumentRetriever.search(query, top_k)` |
| RRF: `score = Σ 1/(k + rank)` per document | Same formula, k=60, operates on chunk IDs |
| Graceful degradation (try each retriever independently) | If embedding fails → FTS-only. If FTS fails → semantic-only. If both fail → empty. |
| Structured citations in agent output | `SearchResult` carries chunk_id + ticker + year + section so Phase 6 agent can cite them |
| `SearchAnswer { answer, citations }` Pydantic model | Defined in Phase 6; Phase 5 returns raw `list[SearchResult]` |
| Tool-based agent retrieval (`grep`/`read_file` tools) | In Phase 6, retriever becomes one tool of the PydanticAI agent |

## Dependencies

No new dependencies. Uses:

- `psycopg` (already installed) — direct SQL queries against Supabase Postgres. Needed because pgvector `<=>` operator and `ts_query` functions require raw SQL; the Supabase Python client's query builder doesn't support vector operators.
- `openai` (already installed) — embed queries via Ollama `nomic-embed-text`
- `pgvector` (already installed) — Vector type used in models; query-time SQL is raw

## Files to create / modify

### `app/retrieval/queries.py` — raw SQL

Two functions, each returning `list[SearchResult]` where the list position = rank (0-indexed).

```python
@dataclass
class SearchResult:
    chunk_id: str
    chunk_text: str
    section: str | None
    document_id: str
    ticker: str
    company_name: str
    year: str
    score: float       # cosine similarity [0,1] or ts_rank; overwritten by RRF score
```

1. **`semantic_search(conn, embedding: list[float], top_k: int = 20) -> list[SearchResult]`**
   - Raw SQL: `SELECT dc.id, dc.chunk_text, dc.section, dc.document_id, sd.ticker, sd.company_name, sd.year, 1 - (dc.embedding <=> %s::vector) AS score FROM document_chunks dc JOIN source_documents sd ON dc.document_id = sd.id ORDER BY dc.embedding <=> %s::vector LIMIT %s`
   - Returns cosine **similarity** (1 - distance), higher = more relevant.
   - Uses the existing HNSW index (`idx_document_chunks_embedding`) with `vector_cosine_ops`.

2. **`fulltext_search(conn, query: str, top_k: int = 20) -> list[SearchResult]`**
   - Raw SQL: `SELECT dc.id, dc.chunk_text, dc.section, dc.document_id, sd.ticker, sd.company_name, sd.year, ts_rank(dc.search_vector, plainto_tsquery('english', %s)) AS score FROM document_chunks dc JOIN source_documents sd ON dc.document_id = sd.id WHERE dc.search_vector @@ plainto_tsquery('english', %s) ORDER BY score DESC LIMIT %s`
   - Uses `plainto_tsquery` (user types raw words, no special syntax needed).
   - Uses the existing GIN index (`idx_document_chunks_search`) on `search_vector`.

### `app/retrieval/fusion.py` — Reciprocal Rank Fusion

**`reciprocal_rank_fusion(semantic: list[SearchResult], fulltext: list[SearchResult], top_k: int = 15, k: int = 60) -> list[SearchResult]`**

Algorithm (mirrors ai-cookbook `utils/fusion.py`):

1. Initialize `fused: dict[str, float]` — maps chunk_id → RRF score
2. For each result in `semantic` at rank `r` (1-indexed position): `fused[chunk_id] += 1 / (k + r)`
3. For each result in `fulltext` at rank `r` (1-indexed position): `fused[chunk_id] += 1 / (k + r)`
4. Sort unique chunk IDs by fused score descending, take `top_k`
5. Preserve the first `SearchResult` encountered for each chunk (carries metadata)
6. Overwrite `.score` on each returned result with the fused score

Edge cases:
- **Empty lists**: Return empty list.
- **One list empty**: Pass through the non-empty list as-is.
- **Disjoint results**: Items from each list interleave correctly by RRF score.
- **Overlapping results**: Same chunk in both lists gets boosted.
- **Duplicate within one list**: Shouldn't occur (SQL guarantees uniqueness), but if it does, only the first occurrence counts.

### `app/retrieval/retriever.py` — orchestrator

**`class DocumentRetriever`**:

- **`__init__(self, db_url: str, ollama_client: OpenAI)`**: Stores connection parameters and Ollama client.
- **`search(self, query: str, top_k: int = 15) -> list[SearchResult]`**:
  1. **Embed query**: `ollama_client.embeddings.create(model="nomic-embed-text", input=query)` → 768d vector.
  2. **Open connection**: `psycopg.connect(db_url)`.
  3. **Run searches** sequentially on the same connection:
     - `semantic_search(conn, embedding, top_k=20)`
     - `fulltext_search(conn, query, top_k=20)`
  4. **Fuse**: `reciprocal_rank_fusion(semantic_results, fulltext_results, top_k=top_k)`
  5. **Return** fused list.

**Error handling** (graceful degradation):
- If Ollama embedding fails (timeout, model not loaded): log warning, run FTS-only, return fulltext results.
- If either search fails: log warning, try the other, return what we have.
- If both fail: log error, return empty list (caller handles gracefully).

### `app/retrieval/__init__.py`

Update the existing empty `__init__.py` to export the public API:
```python
from app.retrieval.retriever import DocumentRetriever
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.queries import SearchResult
```

### `tests/retrieval/test_fusion.py`

| Test | What it verifies |
|---|---|
| `test_empty_lists` | Both empty → empty result |
| `test_only_semantic` | FTS empty → semantic results passed through unchanged |
| `test_only_fulltext` | Semantic empty → FTS results passed through unchanged |
| `test_overlapping_same_rank` | Same item at rank 1 in both → RRF score = 2/(60+1) |
| `test_overlapping_diff_rank` | Same item rank 1 in semantic, rank 10 in FTS → boosted correctly |
| `test_disjoint` | Different items from each list, verify interleaving order |
| `test_top_k_respected` | top_k=3 returns exactly 3 items, even with more candidates |
| `test_k_smoothing` | Higher k flattens score differences (verifiable by score values) |

These tests use fake `SearchResult` lists directly — no database or Ollama needed.

## Connection to Phase 6

`DocumentRetriever` is designed to be wrapped as a PydanticAI tool in Phase 6:

```python
# Phase 6 sketch (for context only — not built here)
retriever = DocumentRetriever(db_url, ollama_client)

def search_docs(query: str, top_k: int = 10) -> list[SourcePassage]:
    return retriever.search(query, top_k=top_k)

agent = Agent(
    model=ollama_model,
    tools=[Tool(search_docs)],
    output_type=SearchAnswer,  # defined in Phase 6
)
```

The `SearchResult` dataclass parallels ai-cookbook's `Citation` model — each result carries document identity (ticker + year + section) so the Phase 6 agent can cite sources when composing answers. The re-scoring step during RRF ensures the agent sees the highest-quality passages first regardless of which search method found them.

## Key decisions

- **Raw SQL, not Supabase client**: `psycopg` connections used directly because pgvector `<=>` operator and `ts_query` functions need raw SQL; Supabase client doesn't support vector operators.
- **Sequential, single-connection**: Both queries complete in <10ms for 22K chunks. No parallelism needed.
- **Synchronous**: Acceptable for now. Phase 8 wraps in `run_in_executor` for the async chat endpoint.
- **One connection per `search()` call**: Simple and stateless. Pooling deferred to Phase 8.
- **k=60**: Standard RRF smoothing constant from the Cormack 2009 paper, matching ai-cookbook.
- **top_k=20 for individual searches, top_k=15 for fused result**: Each search over-retrieves, then RRF discards low-fusion results. Provides enough candidates for the fusion to work well.

## Out of scope

- `SourcePassage` / `SearchAnswer` Pydantic models — defined in Phase 6; Phase 5 uses a local `SearchResult` dataclass
- Async — Phase 8 converts the retriever to async when integrating with the chat endpoint
- Connection pooling — Phase 8
- Cross-encoder reranking — can be added in Phase 7 grounding layer if needed
- Metadata filtering (by ticker, year) — future enhancement
