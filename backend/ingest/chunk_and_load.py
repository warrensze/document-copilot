from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

from openai import OpenAI

from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker

from app.config import settings
from app.database.supabase import create_admin_client, execute_sql

HERE = Path(__file__).resolve().parent
DOWNLOADS_DIR = HERE.parent.parent / "data" / "downloads"
MANIFEST_PATH = DOWNLOADS_DIR / "manifest.json"

EMBEDDING_BATCH = 8
SUPABASE_INSERT_BATCH = 50

converter = DocumentConverter()


def build_section_map(
    chunks: list, doc
) -> dict[int, str]:
    ref_to_chunk: dict[str, int] = {}
    for ci, c in enumerate(chunks):
        for di in c.meta.doc_items:
            sr = getattr(di, "self_ref", None)
            if sr and sr not in ref_to_chunk:
                ref_to_chunk[sr] = ci

    boundaries: dict[int, str] = {}
    for k, v in doc.iterate_items():
        text = (getattr(k, "text", "") or "").strip()
        match = re.match(r"Item\s+(\d+[A-Za-z]?)\.\s+(.+)", text)
        if not match:
            continue
        title = match.group(2).strip()
        sr = getattr(k, "self_ref", "")
        ci = ref_to_chunk.get(str(sr))
        if ci is not None and ci not in boundaries:
            boundaries[ci] = f"Item {match.group(1)}: {title}"

    sections: dict[int, str] = {}
    current = "Cover / Preamble"
    for ci in range(len(chunks)):
        if ci in boundaries:
            current = boundaries[ci]
        sections[ci] = current
    return sections


def embed_texts(client: OpenAI, texts: list[str]) -> list[list[float]]:
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), EMBEDDING_BATCH):
        batch = texts[i : i + EMBEDDING_BATCH]
        resp = client.embeddings.create(
            model=settings.embedding_model, input=batch
        )
        all_embeddings.extend([d.embedding for d in resp.data])
        sys.stdout.write(".")
        sys.stdout.flush()
    return all_embeddings


def process_filing(
    client: OpenAI,
    supabase,
    html_path: Path,
    document_id: str,
    ticker: str,
    year: str,
    filing_label: str,
) -> int:
    print(f"\n  Converting to DoclingDocument...", end=" ")
    result = converter.convert(str(html_path))
    doc = result.document
    print(f"done ({sum(1 for _ in doc.iterate_items())} items)")

    print(f"  Chunking with HybridChunker...", end=" ")
    chunker = HybridChunker()
    chunks = list(chunker.chunk(dl_doc=doc))
    print(f"{len(chunks)} chunks")

    print(f"  Building section map...", end=" ")
    sections = build_section_map(chunks, doc)
    print("done")

    texts = [c.text for c in chunks]
    secs = [sections[i] for i in range(len(chunks))]

    print(f"  Embedding with {settings.embedding_model}...", end=" ")
    embeddings = embed_texts(client, texts)
    print(f" done ({len(embeddings)} vectors)")

    rows = []
    for i, (text, sec, emb) in enumerate(zip(texts, secs, embeddings)):
        rows.append({
            "document_id": document_id,
            "chunk_index": i,
            "section": sec,
            "chunk_text": text,
            "embedding": emb,
            "token_count": len(text) // 4,
            "meta": json.dumps({
                "headings": chunks[i].meta.headings if hasattr(chunks[i].meta, "headings") else None,
            }),
        })

    print(f"  Inserting into document_chunks table...", end=" ")
    inserted = 0
    for i in range(0, len(rows), SUPABASE_INSERT_BATCH):
        batch = rows[i : i + SUPABASE_INSERT_BATCH]
        supabase.table("document_chunks").insert(batch).execute()
        inserted += len(batch)
        sys.stdout.write(".")
        sys.stdout.flush()
    print(f" {inserted} rows")

    print(f"  Updating search_vector...", end=" ")
    execute_sql(
        "UPDATE document_chunks SET search_vector = to_tsvector('english', chunk_text) WHERE document_id = %s",
        (document_id,),
    )
    print("done")

    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chunk SEC filings, generate embeddings, load into Supabase."
    )
    parser.add_argument("--ticker", help="Filter by ticker (e.g. AAPL)")
    parser.add_argument("--year", help="Filter by year (e.g. 2025)")
    parser.add_argument(
        "--cool-down", type=int, default=30,
        help="Seconds to pause between filings to avoid overheating (default: 30)",
    )
    args = parser.parse_args()

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    filings = manifest["filings"]

    if args.ticker:
        filings = [f for f in filings if f["ticker"] == args.ticker.upper()]
    if args.year:
        filings = [f for f in filings if f["filing_date"].startswith(args.year)]

    if not filings:
        print("No filings match the given filters.")
        sys.exit(1)

    print(f"Processing {len(filings)} filing(s)...")

    openai_client = OpenAI(
        base_url=settings.ollama_base_url, api_key="ollama"
    )
    supabase = create_admin_client()

    total_chunks = 0
    total_docs = 0

    for entry in filings:
        ticker = entry["ticker"]
        year = entry["filing_date"][:4]
        accession = entry["accession_number"]
        filing_label = f"{ticker} {year} ({accession[:26]}...)"

        html_rel = entry["local_path"]
        html_path = DOWNLOADS_DIR / html_rel
        if not html_path.exists():
            print(f"\n[skip] {filing_label} — HTML not found at {html_path}")
            continue

        doc_resp = (
            supabase.table("source_documents")
            .select("id")
            .eq("accession_number", accession)
            .limit(1)
            .execute()
        )
        if not doc_resp.data:
            print(f"\n[skip] {filing_label} — not in source_documents")
            continue
        document_id = doc_resp.data[0]["id"]

        chunk_resp = (
            supabase.table("document_chunks")
            .select("id")
            .eq("document_id", document_id)
            .limit(1)
            .execute()
        )
        if chunk_resp.data:
            print(f"\n[skip] {filing_label} — chunks already exist")
            total_docs += 1
            continue

        print(f"\n{'='*60}")
        print(f"  {filing_label}")
        print(f"  document_id: {document_id}")
        print(f"  HTML: {html_path}")
        print(f"{'='*60}")

        t0 = time.time()
        n = process_filing(
            openai_client, supabase, html_path, document_id, ticker, year, filing_label
        )
        elapsed = time.time() - t0
        print(f"  [{elapsed:.1f}s] {n} chunks indexed")
        total_chunks += n
        total_docs += 1

        if args.cool_down > 0 and total_docs < len(filings):
            print(f"  Cooling down for {args.cool_down}s...")
            time.sleep(args.cool_down)

    print(f"\n{'='*60}")
    print(f"Done. {total_docs} documents, {total_chunks} total chunks.")


if __name__ == "__main__":
    main()
