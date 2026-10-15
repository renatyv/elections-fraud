"""Re-OCR problem Form 20 PDFs into strictly numeric table rows.

For PDFs whose text-layer/OCR output defeats the layout parser (column
soup, truncated tables, alien formats), render pages and ask luna to emit
ONLY the polling-station rows as TSV numbers:

    serial, vote per candidate ..., valid, rejected, nota, total, tendered

Output: data/form20/text/ocr_rows/<stem>.txt with the same `===== page i/N
=====` markers as the other extractions, so form20_parse_text.py can parse
it with --sources ocr_rows.

Idempotent: skips PDFs already extracted unless --force.

Run:  cd india-2024 && set -a && source ../.env && set +a && \
      uv run python scripts/form20_ocr_rows.py [--only SUBSTR] [--force]
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
import time
from pathlib import Path

import httpx
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from form20_extract_text import (  # noqa: E402
    n_pages, render_page, upright,
)

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "data" / "form20" / "up"
FILES_CSV = ROOT / "data" / "form20" / "parsed" / "up_form20_files.csv"
OUT_DIR = ROOT / "data" / "form20" / "text" / "ocr_rows"
TMP = ROOT / "data" / "form20" / "text" / "tmp"

MODEL = "~openai/gpt-luna-latest"

PROMPT = (
    "This is a scanned page of an Indian election Form 20 result sheet. "
    "The page image may be rotated. Find the polling-station vote table and "
    "transcribe EVERY data row. Output ONLY data lines, one per polling "
    "station, TAB-separated, in this order: serial number of the polling "
    "station, polling station number if printed separately, the votes for "
    "each candidate in printed left-to-right order, total valid votes, "
    "rejected votes, NOTA votes, total votes, tendered votes. Copy every "
    "number exactly as printed; do not compute, fix or omit anything. If "
    "the table has any other columns (electors, turnout, gender "
    "breakdowns, progressive totals), SKIP them: never output those values. "
    "Every output line must have the same number of vote columns. No "
    "station names, no candidate names, no headers, no page numbers, no "
    "commentary, no blank lines. Never truncate a row: if the rightmost "
    "columns are cut off, still output the columns you can read plus the "
    "total votes. If the page has no polling-station table, output nothing "
    "at all."
)


def select_pdfs(only: str | None) -> list[Path]:
    f = pd.read_csv(FILES_CSV)
    guards = {"zero_col_prefix", "ambiguous_layout", "zero_serials"}
    bad = f[(f.n_stations == 0) | (f.method.isin(guards))]
    names = set(bad.pdf)
    pdfs = sorted(PDF_DIR / p for p in names)
    if only:
        pdfs = [p for p in pdfs if only.lower() in p.name.lower()]
    return pdfs


def ocr_page_rows(client: httpx.Client, key: str, img: Path) -> str:
    b64 = base64.b64encode(img.read_bytes()).decode()
    resp = client.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": MODEL,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/png;base64,{b64}"}},
                ],
            }],
            "max_tokens": 16000,
        },
        timeout=300,
    )
    resp.raise_for_status()
    data = resp.json()
    if "choices" not in data:
        raise RuntimeError(str(data)[:300])
    return data["choices"][0]["message"]["content"]


def extract_pdf(pdf: Path, key: str, cli: httpx.Client) -> None:
    out = OUT_DIR / (pdf.stem + ".txt")
    part = out.with_suffix(".txt.part")
    total = n_pages(pdf)
    with open(part, "w") as fh:
        for page in range(1, total + 1):
            img = render_page(pdf, page, TMP)
            upright(img)
            for attempt in range(4):
                try:
                    text = ocr_page_rows(cli, key, img)
                    break
                except Exception:  # noqa: BLE001 - retry transient API errors
                    if attempt == 3:
                        raise
                    time.sleep(5 * (attempt + 1))
            fh.write(f"===== page {page}/{total} =====\n{text}\n")
            fh.flush()
            img.unlink(missing_ok=True)
    part.rename(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="substring filter on pdf name")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    key = os.environ.get("OPENROUTER_KEY")
    if not key:
        print("OPENROUTER_KEY missing", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pdfs = select_pdfs(args.only)
    jobs = [p for p in pdfs
            if args.force or not (OUT_DIR / (p.stem + ".txt")).exists()]
    print(f"{len(jobs)} of {len(pdfs)} residual PDFs to process", flush=True)

    import concurrent.futures as cf

    with httpx.Client() as cli:
        def run(pdf: Path) -> None:
            try:
                extract_pdf(pdf, key, cli)
                print(f"OK   {pdf.name}", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"FAIL {pdf.name}: {e}", flush=True)

        with cf.ThreadPoolExecutor(max_workers=4) as ex:
            futs = [ex.submit(run, p) for p in jobs]
            for f in cf.as_completed(futs):
                f.result()
    return 0


if __name__ == "__main__":
    sys.exit(main())
