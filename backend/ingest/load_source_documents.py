from __future__ import annotations

import json
from pathlib import Path

from app.config import settings
from app.database.supabase import create_admin_client

HERE = Path(__file__).resolve().parent
MARKDOWN_DIR = HERE.parent.parent / "data" / "markdown"
MANIFEST_PATH = HERE.parent.parent / "data" / "downloads" / "manifest.json"

TICKER_TO_COMPANY: dict[str, str] = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
}


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    filings = manifest["filings"]

    client = create_admin_client()
    inserted = 0
    skipped = 0

    for entry in filings:
        accession = entry["accession_number"]

        resp = (
            client.table("source_documents")
            .select("id")
            .eq("accession_number", accession)
            .limit(1)
            .execute()
        )
        if resp.data:
            print(f"[skip] {entry['ticker']} {accession} — already exists")
            skipped += 1
            continue

        md_path = MARKDOWN_DIR / Path(entry["local_path"]).with_suffix(".md")
        if not md_path.exists():
            print(f"[fail] {entry['ticker']} {accession} — {md_path} not found")
            skipped += 1
            continue

        content_markdown = md_path.read_text(encoding="utf-8")
        year = entry["filing_date"][:4]

        row = {
            "ticker": entry["ticker"],
            "company_name": TICKER_TO_COMPANY[entry["ticker"]],
            "form": entry["form"],
            "filing_date": entry["filing_date"],
            "report_date": entry["report_date"],
            "accession_number": accession,
            "source_url": entry["source_url"],
            "year": year,
            "content_markdown": content_markdown,
        }

        client.table("source_documents").insert(row).execute()
        inserted += 1
        print(f"[ ok ] {entry['ticker']} {year} {accession}")

    print(f"\nDone. {inserted} inserted, {skipped} skipped.")


if __name__ == "__main__":
    main()
