# Phase 4 — Ingestion Pipeline

**Goal**: Parse the 25 downloaded SEC HTML filings, chunk them section-by-section, generate embeddings via Ollama, and write `source_documents` + `document_chunks` rows to Supabase.

## Dependency check

No new runtime dependencies needed:
- **HTML → text**: stdlib `html.parser` / `html.unescape` — SEC EDGAR HTML has a predictable structure (tables, `<ix:nonNumeric>` tags, `<p>` tags). No HTML library required.
- **Embeddings**: `openai` SDK already installed, pointed at Ollama.
- **Supabase writes**: `supabase` SDK already installed, admin client already creates service-role sessions.

(If stdlib parsing proves too brittle — e.g. irregular table layouts, broken tags — add `beautifulsoup4` as a justified exception per dep policy: "parsers" are listed as an OK dependency category.)

## Pipeline design (single-use script, not a service)

The pipeline lives in `backend/ingest/` per `backend/AGENTS.md:46`. It is a synchronous script run manually after `ollama pull nomic-embed-text` is confirmed.

## File-by-file breakdown

### 1. `ingest/__init__.py`
Empty package marker.

### 2. `ingest/extract.py` — HTML → normalized Markdown

**Input**: Path to an SEC EDGAR HTML file (raw `.htm` from `data/downloads/`).
**Output**: Clean Markdown string.

Approach:
1. Read the HTML file as bytes, decode, strip `<script>` and `<style>` blocks.
2. Walk the DOM with `html.parser.HTMLParser`, tracking heading tags (`<h1>`–`<h3>`) and `<p>` / `<div>` / `<table>` boundaries.
3. Convert detected headings to `#` / `##` / `###` Markdown heading lines.
4. Extract text from paragraphs, stripping inline tags.
5. For tables: extract cells row-by-row and format as a Markdown pipe table (or a simple text block if too irregular).
6. Normalize whitespace (collapse multiple blanks, normalize Unicode).
7. Return the Markdown string.

Aligned with `architecture.md:282` — "`source_documents` stores the normalized Markdown version of each filing".

### 3. `ingest/chunk.py` — section-aware chunking

**Input**: Markdown string + document metadata (ticker, year, filing date, etc.).
**Output**: List of `Chunk` dataclass instances (section, chunk_text, chunk_index, token_count, meta).

Chunking rules:
1. Split on Markdown headings that match 10-K section patterns — `## Item 1\b`, `## Item 1A\b`, `## Item 7\b`, `## Item 7A\b`, `## Item 8\b`, etc. Each section becomes a chunk boundary.
2. Within a section, enforce a maximum token size (~500 tokens, estimated as word count × 1.3). Oversized sections are split on paragraph boundaries (double newlines).
3. Each chunk records its section name in the `section` field (e.g. `"Item 1A. Risk Factors"`).
4. Each chunk's `meta` JSONB includes: `ticker`, `company_name`, `filing_date`, `year`, `accession_number`, `chunk_index`.
5. `token_count` is estimated as `len(chunk_text.split())` (close enough for chunk size decisions).

Aligned with `architecture.md:284-293` — `document_chunks` schema includes section metadata, chunk text, token count, and meta JSONB.

### 4. `ingest/embed.py` — embedding generation

**Input**: List of `Chunk` dataclass instances.
**Output**: Same list with `embedding` populated (list of 768 floats).

Approach:
1. Use `openai.OpenAI(base_url=settings.ollama_base_url, api_key="ollama")` (sync client — acceptable for a one-off script).
2. Call `client.embeddings.create(model=settings.embedding_model, input=[chunk.chunk_text for chunk in batch])` in batches of ~16.
3. Assign returned embeddings back to chunks.

Aligned with `architecture.md:70` — OpenAI SDK pointed at Ollama for embeddings.

### 5. `ingest/load.py` — Supabase writes

**Input**: Document metadata + full Markdown content + list of chunked/embedded chunks.
**Output**: Rows inserted into `source_documents` and `document_chunks`.

Approach:
1. Use `create_admin_client()` from `app.database.supabase` (service-role key — `architecture.md:229`).
2. Insert one row into `source_documents` table with all metadata fields.
3. Batch-insert all chunk rows into `document_chunks` table via the Supabase client.
4. After insert, run raw SQL to set `search_vector = to_tsvector('english', chunk_text)` on the inserted chunks (needed for full-text search in Phase 5, and the GIN index from the initial migration depends on it). Uses `supabase.rpc()` or a direct `psycopg` connection.

Aligned with `architecture.md:229` — "Use the service-role key only on the backend for privileged writes".

### 6. `ingest/pipeline.py` — orchestrate the full pipeline

A single `main()` function that:
1. Reads `data/downloads/manifest.json` to enumerate all filings.
2. For each filing entry:
   a. Run `extract.py` to produce Markdown.
   b. Run `chunk.py` to produce chunks.
   c. Run `embed.py` to generate embeddings.
   d. Run `load.py` to write to Supabase.
3. Print a summary (documents ingested, total chunks).

Invoked via: `cd backend && uv run python -m ingest.pipeline`

### 7–8. `tests/ingest/test_extract.py` and `tests/ingest/test_chunk.py`

Unit tests:
- `test_extract`: parse a small sample of real SEC HTML (checked in as a fixture), verify heading detection, table formatting, whitespace normalization.
- `test_chunk`: feed a mock Markdown document with known section headings, verify correct section boundaries and chunk splitting on oversized sections.

Aligned with `backend/AGENTS.md:78` — "Required test coverage: ingestion logic".

## Execution order

1. Create `backend/ingest/` package (4 files + `__init__.py`)
2. Write `extract.py` — parse one sample SEC filing to validate output
3. Write `chunk.py` — test against known 10-K sections
4. Write `embed.py` — verify Ollama `nomic-embed-text` produces 768d vectors
5. Write `load.py` — dry-run against Supabase (check for auth/permission issues)
6. Write `pipeline.py` — full orchestration
7. Write unit tests
8. **Run the pipeline** against all 25 filings
9. Verify: `SELECT COUNT(*) FROM source_documents` = 25, `SELECT COUNT(*) FROM document_chunks` > 0

## Edge cases to handle

- `manifest.json` path resolution (pipeline runs from `backend/`, manifest is at `../data/downloads/manifest.json`)
- Empty filings (SEC sometimes has placeholder HTML with no content)
- Sections that are tables-only (Item 8 Financial Statements) — extract as text block
- Encoding issues in SEC EDGAR (ISO-8859-1 encoded HTML) — detect and decode accordingly
- Embedding batch size — Ollama on a local machine may need smaller batches to avoid OOM
- Idempotency (re-running should not duplicate rows) — upsert on `(accession_number, chunk_index)` or skip if `accession_number` already exists in `source_documents`

## Out of scope

- RLS policies on `source_documents` / `document_chunks` (will be added when auth is wired to retrieval)
- Migration changes (the initial migration already has all needed columns and indexes)
- An API endpoint for ingestion (Phase 4 is a one-off script — `backend/AGENTS.md:46`)
