"""Extract text layer from UP Form 20 PDFs.

Digital PDFs (Encore, text layer): pdftotext -layout.
Scanned PDFs (no usable text layer): render pages, OCR via OpenRouter
(~openai/gpt-luna-latest per workspace guidance).

Idempotent: skips PDFs already extracted unless --force.
"""

from __future__ import annotations

import argparse
import base64
import concurrent.futures as cf
import dataclasses
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn
from rich.progress import TimeElapsedColumn, TimeRemainingColumn

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "data" / "form20" / "up"
OUT_DIR = ROOT / "data" / "form20" / "text"
MANIFEST = OUT_DIR / "extraction_manifest.csv"

OCR_MODEL = "~openai/gpt-luna-latest"

OCR_PROMPT = (
    "This is a scanned page of an Indian election Form 20 result sheet. "
    "The page image may be rotated 90 degrees. Transcribe the ENTIRE page "
    "content, reading it in its correct upright orientation. Output TSV: one "
    "row per line, cells separated by tabs, preserving every number and word "
    "exactly as printed. Include the header lines (FORM 20, electors, name of "
    "assembly segment) and every table row. Do not skip any polling-station "
    "row. Do not add commentary."
)


@dataclasses.dataclass
class Job:
    pdf: Path
    kind: str  # "digital" | "scan"
    out: Path


def classify(pdf: Path) -> str:
    r = subprocess.run(
        ["pdftotext", "-l", "2", str(pdf), "-"], capture_output=True
    )
    txt = r.stdout.decode("utf-8", "ignore")
    return "digital" if sum(c.isalnum() for c in txt) > 200 else "scan"


def build_jobs(force: bool, forced_scans: set[str] | None = None) -> list[Job]:
    jobs: list[Job] = []
    for pdf in sorted(PDF_DIR.glob("*.pdf")):
        kind = classify(pdf)
        if forced_scans and pdf.name in forced_scans:
            kind = "scan"
        sub = "digital" if kind == "digital" else "ocr"
        out = OUT_DIR / sub / (pdf.stem + ".txt")
        if force or not out.exists() or out.stat().st_size == 0:
            jobs.append(Job(pdf, kind, out))
    return jobs


def extract_digital(job: Job) -> str:
    r = subprocess.run(
        ["pdftotext", "-layout", str(job.pdf), "-"], capture_output=True
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode()[:200])
    return r.stdout.decode("utf-8", "ignore")


def render_page(pdf: Path, page: int, tmp: Path) -> Path:
    img = tmp / f"{pdf.stem}-{page:04d}"
    subprocess.run(
        ["pdftoppm", "-r", "200", "-gray", "-png",
         "-f", str(page), "-l", str(page), str(pdf), str(img)],
        check=True, capture_output=True,
    )
    produced = sorted(tmp.glob(f"{pdf.stem}-{page:04d}*.png"))
    if not produced:
        raise RuntimeError(f"pdftoppm produced nothing for page {page}")
    return produced[0]


def upright(img: Path) -> None:
    """Rotate the image to upright based on tesseract OSD; keep as-is on failure."""
    r = subprocess.run(
        ["tesseract", str(img), "stdout", "--psm", "0"],
        capture_output=True,
    )
    for line in r.stdout.decode("utf-8", "ignore").splitlines():
        if line.startswith("Rotate:"):
            deg = int(line.split(":")[1].strip())
            if deg:
                import PIL.Image
                with PIL.Image.open(img) as im:
                    im.rotate(-deg, expand=True).save(img)
            return


def ocr_page(client: httpx.Client, key: str, img: Path) -> str:
    b64 = base64.b64encode(img.read_bytes()).decode()
    resp = client.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": OCR_MODEL,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": OCR_PROMPT},
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
        raise RuntimeError(json.dumps(data)[:300])
    return data["choices"][0]["message"]["content"]


def n_pages(pdf: Path) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True).stdout.decode()
    for line in out.splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    raise RuntimeError(f"no page count for {pdf}")


def extract_scan(job: Job, key: str, tmp: Path, cli: httpx.Client,
                 on_page) -> str:
    total = n_pages(job.pdf)
    part_path = job.out.with_suffix(".txt.part")
    with open(part_path, "w") as part:
        for page in range(1, total + 1):
            img = render_page(job.pdf, page, tmp)
            upright(img)
            for attempt in range(4):
                try:
                    text = ocr_page(cli, key, img)
                    break
                except Exception as e:  # noqa: BLE001 - retry on transient API errors
                    if attempt == 3:
                        raise RuntimeError(f"page {page}: {e}") from e
                    time.sleep(5 * (attempt + 1))
            part.write(f"===== page {page}/{total} =====\n{text}\n")
            part.flush()
            img.unlink(missing_ok=True)
            on_page(job, page, total)
    part_path.rename(job.out)
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", help="substring filter on pdf name")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--rescue-from", dest="rescue_from",
                    help="CSV with parses_clean column (up_form20_files.csv): "
                         "re-OCR digital PDFs that failed to parse")
    args = ap.parse_args()

    forced: set[str] = set()
    if args.rescue_from:
        import csv
        with open(args.rescue_from) as f:
            for row in csv.DictReader(f):
                if row["source"] == "digital" and row["parses_clean"] != "True":
                    forced.add(row["pdf"])
        print(f"rescuing {len(forced)} digital PDFs as scans")

    key = os.environ.get("OPENROUTER_KEY")
    if not key:
        print("OPENROUTER_KEY missing", file=sys.stderr)
        return 1

    (OUT_DIR / "digital").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "ocr").mkdir(parents=True, exist_ok=True)
    tmp = OUT_DIR / "tmp"
    tmp.mkdir(exist_ok=True)

    jobs = build_jobs(args.force, forced)
    if args.only:
        jobs = [j for j in jobs if args.only.lower() in j.pdf.name.lower()]
    scans = [j for j in jobs if j.kind == "scan"]
    print(f"{len(jobs)} jobs ({len(scans)} scans)", flush=True)

    def log(msg: str) -> None:
        print(msg, flush=True)

    done = 0
    with httpx.Client() as cli:
        digital = [j for j in jobs if j.kind == "digital"]
        for job in digital:
            job.out.write_text(extract_digital(job))
            done += 1
        log(f"digital done: {done}")

        def do_scan(job: Job, page_task: int, prog: Progress) -> Job:
            def on_page(j: Job, page: int, total: int) -> None:
                prog.update(page_task, description=(
                    f"OCR {j.pdf.stem[:40]} [{page}/{total}]"), advance=1)

            extract_scan(job, key, tmp, cli, on_page)
            return job

        scan_pages = sum(n_pages(j.pdf) for j in scans)
        with (Progress(TextColumn("{task.description}"), BarColumn(),
                       TaskProgressColumn(), TimeElapsedColumn(),
                       TimeRemainingColumn()) as prog,
              cf.ThreadPoolExecutor(max_workers=args.workers) as ex):
            files_task = prog.add_task(
                f"files {done}/{len(jobs)}", total=len(scans))
            page_task = prog.add_task("pages", total=scan_pages)
            futs = {ex.submit(do_scan, j, page_task, prog): j for j in scans}
            for fut in cf.as_completed(futs):
                job = futs[fut]
                try:
                    fut.result()
                    done += 1
                    prog.update(files_task, advance=1,
                                description=f"files {done}/{len(jobs)}")
                except Exception as e:  # noqa: BLE001
                    log(f"FAIL {job.pdf.name}: {e}")

    with open(MANIFEST, "w") as f:
        f.write("source,pdf,out\n")
        for sub in ("digital", "ocr"):
            for txt in sorted((OUT_DIR / sub).glob("*.txt")):
                f.write(f"{sub},{txt.stem}.pdf,{txt.relative_to(OUT_DIR)}\n")
    print("manifest written", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
