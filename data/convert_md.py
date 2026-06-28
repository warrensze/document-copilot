from __future__ import annotations

import json
import shutil
from pathlib import Path

from docling.document_converter import DocumentConverter

DOWNLOADS_DIR = Path(__file__).resolve().parent / "downloads"
MARKDOWN_DIR = Path(__file__).resolve().parent / "markdown"
MANIFEST_PATH = DOWNLOADS_DIR / "manifest.json"


def main() -> None:
    converter = DocumentConverter()

    if MARKDOWN_DIR.exists():
        shutil.rmtree(MARKDOWN_DIR)

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    filings = manifest["filings"]
    total = len(filings)
    converted = 0
    errors = 0

    for i, entry in enumerate(filings, 1):
        # year comes from the first path component of local_path (e.g. "2025/...")
        year = Path(entry["local_path"]).parts[0]
        local_path = DOWNLOADS_DIR / entry["local_path"]
        out_path = MARKDOWN_DIR / Path(entry["local_path"]).with_suffix(".md")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"[{i}/{total}] {entry['ticker']} {year} ...", end=" ")

        try:
            result = converter.convert(str(local_path))
            markdown = result.document.export_to_markdown()
            out_path.write_text(markdown, encoding="utf-8")
            converted += 1
            print(f"OK ({len(markdown):,} chars)")
        except Exception as e:
            errors += 1
            print(f"FAIL: {e}")

    print(f"\nDone. {converted} converted, {errors} errors.")


if __name__ == "__main__":
    main()
