#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27", "rich>=13", "python-dotenv>=1.0"]
# ///
"""
LLM parsing of section-level PDFs (AR-2025) via OpenRouter (chat completions).

Each PDF is sent as a separate request (default model openai/gpt-6-luna):
prompt + PDF as a data-URL file part. The model returns strict CSV with rows
per precinct section (or freguesia). Each PDF's result is saved NEXT TO THE
SOURCE — <pdf_name>.csv; the merged llm_seccoes.csv, report.txt and costs.json
go to the --out directory.

With --check, after the main pass every PDF is run through a second model
(--check-model, default google/gemini-3.8-flash) with the same prompt; the
transcriptions are compared cell by cell and discrepancies go to the report
(<pdf_name>.check.csv next to the PDF).

A re-run skips PDFs that already have a CSV next to them (resume); --force
re-runs everything.

Example:
    uv run portugal-2025/scripts/llm_seccoes.py portugal-2025/data/seccoes/*/*.pdf
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import (BarColumn, MofNCompleteColumn, Progress,
                           SpinnerColumn, TextColumn, TimeElapsedColumn)
from rich.table import Table

API_BASE = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-6-luna"
DEFAULT_CHECK_MODEL = "google/gemini-3.8-flash"
MAX_TOKENS = 16384
CHECK_MAX_TOKENS = 40000

# Canonical AR-2025 list order, same as the MAI export (results_freguesias.csv)
MAI_PARTY_ORDER = [
    "PPD/PSD.CDS-PP", "PS", "CH", "IL", "L", "PCP-PEV", "B.E.", "PAN", "ADN",
    "PPD/PSD.CDS-PP.PPM", "JPP", "R.I.R.", "VP", "PCTP/MRPP", "ND", "E",
    "PLS", "PPM", "NC", "MPT", "PTP",
]
BASE_COLUMNS = ["nivel", "freguesia", "local", "secao",
                "eleitores", "votantes", "brancos", "nulos", "abst"]

console = Console()

# ---------------------------------------------------------------- env / paths

def find_dotenv() -> Path | None:
    """Look for .env upwards from the CWD and from the script directory (key in the repo root)."""
    script_dir = Path(__file__).resolve().parent
    for start in (Path.cwd(), script_dir):
        for d in [start, *start.parents]:
            cand = d / ".env"
            if cand.is_file():
                return cand
    return None


def get_api_key() -> str:
    env_file = find_dotenv()
    if env_file:
        load_dotenv(env_file)
    for var in ("OPENROUTER_KEY", "OPENROUTER_API_KEY"):
        val = os.environ.get(var, "").strip()
        if val:
            return val
    console.print("[red]No API key: set OPENROUTER_KEY in .env[/red]")
    sys.exit(2)

# ---------------------------------------------------------------- MAI hints

def load_mai_parties(mai_csv: Path) -> dict[str, list[str]]:
    """dico (4 digits) -> the lists that actually ran in the municipality
    (non-zero votes in at least one freguesia), canonical MAI spelling."""
    hints: dict[str, list[str]] = {}
    try:
        with open(mai_csv, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            party_cols = [c for c in reader.fieldnames or [] if c.startswith("votes:")]
            for row in reader:
                m = re.match(r"LOCAL-(\d{4})", row.get("key", ""))
                if not m or row.get("level") not in ("3", "freguesia"):
                    continue
                dico = m.group(1)
                nz = hints.setdefault(dico, [])
                for c in party_cols:
                    if (row.get(c) or "").strip() not in ("", "0") and c not in nz:
                        nz.append(c)
    except OSError:
        return {}
    for d in hints:
        hints[d] = sorted({p[len("votes:"):] for p in hints[d]},
                          key=lambda x: MAI_PARTY_ORDER.index(x)
                          if x in MAI_PARTY_ORDER else 999)
    return hints

# ---------------------------------------------------------------- prompt

SYSTEM_PROMPT = """\
You are a precise data-extraction engine for official Portuguese election
results PDFs (Eleição da Assembleia da República, 18.05.2025: "MAPA POR
SECÇÃO DE VOTO", apuramento tables, edital results). You transcribe the
table(s) in the attached PDF into CSV exactly, with zero interpretation
beyond the mapping rules you are given. You never invent numbers."""


def user_prompt(parties: list[str] | None) -> str:
    party_line = ", ".join(parties) if parties else ", ".join(MAI_PARTY_ORDER)
    expected_header = ",".join(BASE_COLUMNS + [f"votes:{p}" for p in (parties or MAI_PARTY_ORDER)])
    return f"""\
Transcribe the results table(s) from the attached PDF into CSV.

OUTPUT FORMAT — strict rules:
1. Output ONLY CSV: first line is the header below, then data rows. No markdown
   fences, no commentary, no blank lines.
2. Header (use exactly this line):
{expected_header}
   If the PDF has a political list that is NOT in the header (check carefully),
   append an extra column named `votes:<name as printed in the PDF>` at the end
   of every row.
3. One row per the most detailed territorial unit in the PDF:
   - if the PDF has per-section rows (columns "Secção", "Mesa", "Secção de Voto"
     or numbered sections under freguesia/place headers) → one row per section,
     nivel=secao, fill `secao` with the section/mesa number;
   - if the PDF only has per-freguesia rows → one row per freguesia,
     nivel=freguesia, leave `secao` empty.
   NEVER output both a freguesia total row and its per-section rows — if
   section detail exists for a freguesia, emit only the section rows.
4. If you write any notes at all (e.g. about an unreadable page), they MUST
   be in English.

COLUMNS:
- freguesia: from a freguesia column, or from sub-header/section-title rows
  (a title row above a block of sections applies to all rows of that block).
  Transcribe names as printed. If the PDF has none, leave empty.
- local: place/local/venue column if present (e.g. "Local"), else empty.
- secao: section/mesa number (integer, as printed).
- eleitores, votantes, brancos, nulos, abst: absolute counts when present
  (Inscritos/Eleitores, Votantes, Brancos, Nulos, Abstenções). Leave EMPTY if
  the PDF does not report a value — never write 0 for a missing value.
- votes:<LIST>: absolute votes for each list. Same rule: empty if not reported.

NUMBERS: plain integers, no thousand separators, no % signs. "2 989" → 2989,
"1.497" → 1497, "61,33" (percent) → ignore. IGNORE all percent columns and
percent rows entirely. Percent values (containing "," or "." as decimal
separator) are NEVER vote counts.

COLUMN ALIGNMENT (critical): some PDFs label ONLY the party columns in the
header row; the unlabeled numeric columns that come BEFORE the party columns
are, in order: eleitores (Inscritos), votantes (Votantes), abst (Abstenções,
if present), brancos (Brancos), nulos (Nulos). Count how many numeric
columns each data row has versus the party count to align correctly.

MANDATORY SELF-CHECK before you answer — for EVERY row verify:
  votantes == brancos + nulos + sum(all party votes)
  eleitores >= votantes  (and eleitores == votantes + abst when abst present)
If any row violates this, your column alignment or digit transcription is
wrong: re-read that row, re-align, and re-verify. Do not output rows that
violate the identity.

Every data row must have exactly as many fields as the header line.

SKIP rows: TOTAL / TOTAIS / Totais / "Total Concelho" / "TOTAL -" rows, all
"%" rows, and any subtotal rows (e.g. per-freguesia totals inside a section
table, "Secção nº X" subtotal rows when section detail rows exist).

PARTY NAME MAPPING — map the printed column name to the canonical name:
  CHEGA/CH → CH; CDU/PCP-PEV → PCP-PEV; BE/B.E. → B.E.; VOLT/VP → VP;
  LIVRE/L → L; RIR/R.I.R. → R.I.R.; PCTP/PCTP/MRPP → PCTP/MRPP;
  NOS/NC → NC; ERG/ERGUER/E → E; PS → PS; IL → IL; PAN → PAN; ADN → ADN;
  JPP → JPP; PLS → PLS; PPM → PPM; MPT → MPT; PTP → PTP; ND → ND.
  AD / PPD/PSD.CDS-PP / "PPD/PSD. CDS-PP" / PSD.CDS-PP and similar variants →
  copy EXACTLY the one PPD/PSD.CDS-PP... entry from this expected list:
  {party_line}
  The expected list below is the set of lists that were actually on the
  ballot in this municipality (from the official MAI portal); map every party
  column of the PDF onto it. Extra lists not in it → extra votes:<printed> column.
  Expected lists: {party_line}

If the PDF contains no results table, output only the header line."""

# ---------------------------------------------------------------- API client

class OpenRouter:
    def __init__(self, key: str):
        self.client = httpx.Client(
            headers={"Authorization": f"Bearer {key}",
                     "X-Title": "elections-analysis-seccoes"},
            timeout=httpx.Timeout(connect=30.0, read=900.0, write=600.0, pool=30.0),
        )

    def chat(self, body: dict) -> httpx.Response:
        """POST /chat/completions with retries on 429/5xx."""
        delay = 2.0
        resp = None
        for attempt in range(8):
            resp = self.client.post(f"{API_BASE}/chat/completions", json=body)
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < 7:
                retry_after = resp.headers.get("retry-after")
                pause = float(retry_after) if retry_after and retry_after.isdigit() else delay
                time.sleep(pause)
                delay *= 2
                continue
            return resp
        return resp

# ---------------------------------------------------------------- helpers

def sha1_file(p: Path) -> str:
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_messages(pdf: Path, parties: list[str] | None) -> list[dict]:
    data = base64.b64encode(pdf.read_bytes()).decode()
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": [
            {"type": "file", "file": {"filename": pdf.name,
                                      "file_data": f"data:application/pdf;base64,{data}"}},
            {"type": "text", "text": user_prompt(parties)},
        ]},
    ]


def content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(part.get("text", ""))
        return "\n".join(parts)
    return ""


def clean_csv(text: str) -> str:
    """Strip ``` fences and junk before/after the CSV."""
    text = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text.strip())
    lines = [ln for ln in text.splitlines() if ln.strip()]
    for i, ln in enumerate(lines):  # from the first header line to the end
        if ln.lstrip("#, ").startswith("nivel"):
            return "\n".join(lines[i:])
    return "\n".join(lines)


def parse_result_csv(text: str) -> tuple[list[str], list[list[str]]]:
    rows = [r for r in csv.reader(io.StringIO(clean_csv(text))) if r]
    if not rows or not rows[0] or not rows[0][0].startswith("nivel"):
        raise ValueError("no nivel,... header row found")
    return rows[0], rows[1:]


def check_sums(header: list[str], rows: list[list[str]]) -> int:
    """votantes == brancos + nulos + Σvotes (wherever all fields are filled)."""
    hmap = {n: i for i, n in enumerate(header)}
    votes_idx = [i for n, i in hmap.items() if n.startswith("votes:")]
    bad = 0
    for r in rows:
        try:
            vot = int(r[hmap["votantes"]])
            parts = [int(r[hmap[k]]) for k in ("brancos", "nulos") if hmap[k] < len(r)]
            parts += [int(r[i]) for i in votes_idx if i < len(r) and r[i] != ""]
        except (ValueError, KeyError, IndexError):
            continue
        if parts and vot != sum(parts):
            bad += 1
    return bad


def apply_mesa_fix(header: list[str], rows: list[list[str]]) -> list[str]:
    """nivel=secao with an empty mesa number -> mesa 1, if the freguesia has
    exactly one such row in the file (a single-mesa freguesia; otherwise leave
    as is and wait for manual review). Returns a list of notes."""
    hmap = {n: i for i, n in enumerate(header)}
    i_sec, i_fre = hmap["secao"], hmap.get("freguesia", 0)
    empty = [r for r in rows
             if r and r[0] == "secao" and len(r) > i_sec and r[i_sec].strip() == ""]
    notes = []
    for r in empty:
        fre = r[i_fre].strip()
        same_fre = [x for x in rows
                    if x and x[0] == "secao" and len(x) > i_fre and x[i_fre].strip() == fre]
        if len(same_fre) == 1:
            r[i_sec] = "1"
            notes.append(f"mesa=1 filled in for the only section of freguesia {fre!r}")
        else:
            notes.append(f"WARNING: {len(same_fre)} sections of freguesia {fre!r} without a mesa number")
    return notes


def compare_csv(primary: Path, check: Path) -> tuple[bool, list[str]]:
    """Cell-by-cell comparison of the primary and check transcriptions.
    Row pairs are matched by (freguesia_norm, secao); leftovers are matched
    by numeric tuples (different name transcription is not a data mismatch)."""
    def load(p: Path):
        with open(p, newline="", encoding="utf-8") as f:
            rd = csv.reader(f)
            h = next(rd, None)
            return h, [r for r in rd if r]

    ph, pr = load(primary)
    ch, cr = load(check)
    issues: list[str] = []
    pmap = {n: i for i, n in enumerate(ph)}
    cmap = {n: i for i, n in enumerate(ch)}
    missing = [n for n in ph if n not in cmap]
    if missing:
        issues.append(f"columns missing in check: {','.join(missing)}")
    common = [n for n in ph if n in cmap]
    numeric = [n for n in common if n not in ("nivel", "freguesia", "local")]

    def rkey(r, m):
        f = r[m["freguesia"]] if m.get("freguesia", 99) < len(r) else ""
        s = r[m["secao"]] if m.get("secao", 99) < len(r) else ""
        return (f.strip().upper(), s.strip())

    def numtuple(r, m):
        return tuple((r[m[n]] if m[n] < len(r) else "").strip() for n in numeric)

    if len(pr) != len(cr):
        issues.append(f"row count: {len(pr)} vs {len(cr)}")
    text_cols = {"nivel", "freguesia", "local"}
    cidx: dict[tuple, list[list[str]]] = {}
    for r in cr:
        cidx.setdefault(rkey(r, cmap), []).append(r)
    leftover: list[list[str]] = []
    diffs = 0
    name_diffs = 0
    for prow in pr:
        lst = cidx.get(rkey(prow, pmap))
        if not lst:
            leftover.append(prow)
            continue
        crow = lst.pop(0)
        d_num, d_txt = [], []
        for n in common:
            a = (prow[pmap[n]] if pmap[n] < len(prow) else "").strip()
            b = (crow[cmap[n]] if cmap[n] < len(crow) else "").strip()
            if a != b:
                (d_txt if n in text_cols else d_num).append(f"{n}: {a}≠{b}")
        if d_num:
            diffs += 1
            if len(issues) < 12:
                k = rkey(prow, pmap)
                issues.append(f"{k[0]} sec {k[1]}: " + "; ".join(d_num[:4]))
        elif d_txt:
            name_diffs += 1
    if name_diffs:
        issues.append(f"name transcription differs in {name_diffs} rows "
                      "(data/numbers match)")
    # leftovers: the same data row under a different name spelling?
    cnums = {}
    for lst in cidx.values():
        for r in lst:
            cnums.setdefault(numtuple(r, cmap), []).append(r)
    for prow in leftover:
        t = numtuple(prow, pmap)
        if cnums.get(t):
            cnums[t].pop(0)
        else:
            diffs += 1
            if len(issues) < 12:
                issues.append(f"unmatched row: {rkey(prow, pmap)} {t[:4]}")
    ok = diffs == 0 and len(pr) == len(cr)
    return ok, issues


def write_merged(all_rows: list[dict], out_dir: Path) -> None:
    if not all_rows:
        return
    extras = sorted({k for row in all_rows for k in row
                     if k.startswith("votes:") and k[6:] not in MAI_PARTY_ORDER})
    party_cols = [f"votes:{p}" for p in MAI_PARTY_ORDER] + extras
    seen: set[str] = set()
    cols = [c for c in BASE_COLUMNS + party_cols if not (c in seen or seen.add(c))]
    with open(out_dir / "llm_seccoes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source_pdf"] + cols)
        for row in all_rows:
            w.writerow([row.get("source_pdf", "")] + [row.get(c, "") for c in cols])

# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdfs", nargs="*", help="PDF files (globs expanded by the shell)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--out", default="portugal-2025/data/seccoes/llm",
                    help="directory for the summary artifacts (llm_seccoes.csv, "
                         "report.txt, costs.json); per-file CSVs go next to the PDFs")
    ap.add_argument("--mai-csv", default="portugal-2025/data/legislativas2025_mai/"
                                         "results_freguesias.csv",
                    help="MAI CSV used for ballot-list hints")
    ap.add_argument("--force", action="store_true",
                    help="re-request even finished files (including check)")
    ap.add_argument("--check", action="store_true",
                    help="verification pass with a second model + cell-by-cell comparison")
    ap.add_argument("--check-model", default=DEFAULT_CHECK_MODEL,
                    help="model for the verification pass")
    ap.add_argument("--sleep", type=float, default=1.0,
                    help="pause between requests, seconds")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    pdfs = sorted({Path(p) for p in args.pdfs if Path(p).suffix.lower() == ".pdf"})
    if not pdfs:
        ap.error("no PDFs given (positional arguments)")
    missing = [p for p in pdfs if not p.exists()]
    if missing:
        ap.error("missing files: " + ", ".join(map(str, missing)))

    mai_hints = load_mai_parties(Path(args.mai_csv)) if Path(args.mai_csv).exists() else {}

    # resume: skip PDFs that already have a parsed CSV next to them
    todo = []
    skipped = []
    for pdf in pdfs:
        dst = pdf.with_suffix(".csv")
        (todo if args.force or not dst.exists() else skipped).append((pdf, dst))

    costs_path = out_dir / "costs.json"
    costs = json.loads(costs_path.read_text()) if costs_path.exists() else {}
    total_new_cost = 0.0

    # check pass: PDFs with a finished primary transcription; without a check
    # CSV — a request to the model, with a finished check CSV — a free re-comparison
    check_pairs: list[tuple[Path, Path, Path]] = []
    check_cached: list[tuple[Path, Path, Path]] = []
    if args.check:
        for pdf in pdfs:
            prim = pdf.with_suffix(".csv")
            chk = pdf.with_suffix(".check.csv")
            if not prim.exists():
                continue
            (check_pairs if args.force or not chk.exists()
             else check_cached).append((pdf, prim, chk))

    console.print(f"{len(pdfs)} PDFs: {len(todo)} to send, {len(skipped)} done "
                  f"(skipped); check: {len(check_pairs)} requests + "
                  f"{len(check_cached)} from cache. "
                  f"Model {args.model}, out: {out_dir}")

    api = OpenRouter(get_api_key())
    report: list[str] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.fields[fname]}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("${task.fields[cost]:.4f}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("llm", total=len(todo), fname="...", cost=0.0)
        for i, (pdf, dst) in enumerate(todo):
            dico_m = re.match(r"(\d{4})", pdf.parent.name)
            parties = mai_hints.get(dico_m.group(1)) if dico_m else None
            cid = f"{pdf.parent.name}-{sha1_file(pdf)[:10]}"
            progress.update(task, fname=f"{pdf.parent.name} ({i + 1}/{len(todo)})")
            t0 = time.monotonic()
            try:
                resp = api.chat({"model": args.model, "max_tokens": MAX_TOKENS,
                                 "messages": build_messages(pdf, parties)})
                if resp.status_code != 200:
                    msg = f"HTTP {resp.status_code}: {resp.text[:300]}"
                    console.print(f"[red]{pdf.parent.name}: {msg}[/red]")
                    report.append(f"FAIL {pdf}: {msg}")
                    progress.advance(task)
                    continue
                data = resp.json()
                choices = data.get("choices") or []
                content = content_to_text(choices[0]["message"]["content"]) if choices else ""
                usage = data.get("usage") or {}
                cost = float(usage.get("cost") or 0.0)
                total_new_cost += cost
                costs[cid] = {"pdf": str(pdf), "cost": cost,
                              "prompt_tokens": usage.get("prompt_tokens"),
                              "completion_tokens": usage.get("completion_tokens"),
                              "seconds": round(time.monotonic() - t0, 1)}
                header, rows = parse_result_csv(content)
                for note in apply_mesa_fix(header, rows):
                    report.append(f"NOTE {pdf}: {note}")
                with open(dst, "w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow(header)
                    w.writerows(rows)
                n_sec = sum(1 for r in rows if r and r[0] == "secao")
                n_fre = sum(1 for r in rows if r and r[0] == "freguesia")
                bad = check_sums(header, rows)
                note = f"sum-check fail: {bad} rows" if bad else "sum-check OK"
                report.append(f"OK {pdf}: {len(rows)} rows (secao={n_sec}, "
                              f"freguesia={n_fre}), {note}")
                progress.print(f"[green]✓[/green] {pdf.parent.name}: {len(rows)} rows, "
                               f"{note}, ${cost:.4f}, "
                               f"{time.monotonic() - t0:.0f}s")
            except Exception as e:  # noqa: BLE001
                report.append(f"FAIL {pdf}: {e!r}")
                progress.print(f"[red]✗ {pdf.parent.name}: {e!r}[/red]")
            costs_path.write_text(json.dumps(costs, ensure_ascii=False, indent=1))
            progress.update(task, cost=total_new_cost)
            progress.advance(task)
            if i < len(todo) - 1:
                time.sleep(args.sleep)

        # --- verification pass with the second model ---
        if check_pairs or check_cached:
            progress.reset(task, total=len(todo) + len(check_pairs) + len(check_cached),
                           completed=len(todo))
        for pdf, prim, chk in check_cached:  # re-comparison without a request
            label = f"{pdf.parent.name}/{pdf.stem}"
            try:
                ok, issues = compare_csv(prim, chk)
                if ok:
                    report.append(f"CHECK {label}: OK (cache)"
                                  + ("; " + "; ".join(issues) if issues else ""))
                    progress.print(f"[green]✓[/green] check {pdf.parent.name}: matches (cache)")
                else:
                    report.append(f"CHECK {label}: MISMATCHES (cache): "
                                  + " | ".join(issues[:10]))
                    progress.print(f"[red]✗ check {pdf.parent.name}: "
                                   + "; ".join(issues[:3]) + " (cache)")
            except Exception as e:  # noqa: BLE001
                report.append(f"CHECK-FAIL {label} (cache): {e!r}")
                progress.print(f"[red]✗ check {pdf.parent.name}: {e!r} (cache)[/red]")
            progress.advance(task)
        for i, (pdf, prim, chk) in enumerate(check_pairs):
            label = f"{pdf.parent.name}/{pdf.stem}"
            progress.update(task, fname=f"check {pdf.parent.name} ({i + 1}/{len(check_pairs)})")
            t0 = time.monotonic()
            try:
                dico_m = re.match(r"(\d{4})", pdf.parent.name)
                parties = mai_hints.get(dico_m.group(1)) if dico_m else None
                cid = f"check-{pdf.parent.name}-{sha1_file(pdf)[:10]}"
                content = ""
                finish = ""
                for attempt in range(2):
                    resp = api.chat({"model": args.check_model,
                                     "max_tokens": CHECK_MAX_TOKENS,
                                     "messages": build_messages(pdf, parties)})
                    if resp.status_code != 200:
                        report.append(f"CHECK-FAIL {label}: HTTP {resp.status_code}: "
                                      f"{resp.text[:200]}")
                        progress.print(f"[red]✗ check {pdf.parent.name}: "
                                       f"HTTP {resp.status_code}[/red]")
                        resp = None
                        break
                    data = resp.json()
                    choices = data.get("choices") or []
                    content = content_to_text(choices[0]["message"]["content"]) if choices else ""
                    finish = (choices[0].get("finish_reason") or "") if choices else ""
                    usage = data.get("usage") or {}
                    cost = float(usage.get("cost") or 0.0)
                    total_new_cost += cost
                    costs[cid] = {"pdf": str(pdf), "model": args.check_model,
                                  "cost": costs.get(cid, {}).get("cost", 0.0) + cost,
                                  "prompt_tokens": usage.get("prompt_tokens"),
                                  "completion_tokens": usage.get("completion_tokens"),
                                  "seconds": round(time.monotonic() - t0, 1)}
                    if finish == "length" and attempt == 0:
                        progress.print(f"[yellow]… check {pdf.parent.name}: response cut off "
                                       "at max_tokens, retrying[/yellow]")
                        continue
                    break
                if resp is None:
                    progress.advance(task)
                    continue
                if finish == "length":
                    report.append(f"CHECK-FAIL {label}: response cut off at max_tokens "
                                  "(finish_reason=length) even after a retry")
                    progress.print(f"[red]✗ check {pdf.parent.name}: TRUNCATED[/red]")
                    progress.advance(task)
                    continue
                header, rows = parse_result_csv(content)
                for note in apply_mesa_fix(header, rows):
                    report.append(f"NOTE check {label}: {note}")
                with open(chk, "w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow(header)
                    w.writerows(rows)
                ok, issues = compare_csv(prim, chk)
                if ok:
                    report.append(f"CHECK {label}: OK ({args.check_model})"
                                  + ("; " + "; ".join(issues) if issues else ""))
                    progress.print(f"[green]✓[/green] check {pdf.parent.name}: "
                                   f"matches, ${cost:.4f}")
                else:
                    report.append(f"CHECK {label}: MISMATCHES ({args.check_model}): "
                                  + " | ".join(issues[:10]))
                    progress.print(f"[red]✗ check {pdf.parent.name}: "
                                   + "; ".join(issues[:3]) + f", ${cost:.4f}")
            except Exception as e:  # noqa: BLE001
                report.append(f"CHECK-FAIL {label}: {e!r}")
                progress.print(f"[red]✗ check {pdf.parent.name}: {e!r}[/red]")
            costs_path.write_text(json.dumps(costs, ensure_ascii=False, indent=1))
            progress.update(task, cost=total_new_cost)
            progress.advance(task)
            if i < len(check_pairs) - 1:
                time.sleep(args.sleep)

    # merged CSV — incremental: load the previous one, replace the blocks of
    # the current files, keep the other sources (a partial run does not cut the dataset)
    merged_path = out_dir / "llm_seccoes.csv"
    by_src: dict[str, list[dict]] = {}
    if merged_path.exists():
        with open(merged_path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                by_src.setdefault(r.get("source_pdf", ""), []).append(r)
    # collect the results next to the sources: CSVs in the directories of the
    # submitted PDFs (recognized by the nivel,... header)
    src_dirs = sorted({p.parent for p in pdfs})
    for src_dir in src_dirs:
        for per_file in sorted(src_dir.glob("*.csv")):
            if per_file.name.endswith(".check.csv"):
                continue  # check transcriptions do not go into the merged CSV
            with open(per_file, newline="", encoding="utf-8") as f:
                rd = csv.reader(f)
                header = next(rd, None)
                if not header or not header[0].startswith("nivel"):
                    continue
                rows = [r for r in rd if r]
            notes = apply_mesa_fix(header, rows)
            label = f"{per_file.parent.name}/{per_file.stem}"
            for note in notes:
                report.append(f"NOTE {label}: {note}")
            if notes:  # record them in the per-file CSV as well
                with open(per_file, "w", newline="", encoding="utf-8") as fw:
                    w = csv.writer(fw)
                    w.writerow(header)
                    w.writerows(rows)
            n_sec = sum(1 for r in rows if r and r[0] == "secao")
            n_fre = sum(1 for r in rows if r and r[0] == "freguesia")
            bad = check_sums(header, rows)
            note = f"sum-check fail: {bad} rows" if bad else "sum-check OK"
            report.append(f"OK {label}: {len(rows)} rows "
                          f"(secao={n_sec}, freguesia={n_fre}), {note}")
            hmap = {n: j for j, n in enumerate(header)}
            block = []
            for r in rows:
                row = {"source_pdf": label}
                for n, j in hmap.items():
                    row[n] = r[j] if j < len(r) else ""
                block.append(row)
            by_src[label] = block
    all_rows = [r for label in sorted(by_src) for r in by_src[label]]
    write_merged(all_rows, out_dir)
    report.append(f"MERGED: {len(by_src)} sources, {len(all_rows)} rows in "
                  f"llm_seccoes.csv")
    (out_dir / "report.txt").write_text("\n".join(report) + "\n")

    # cost table
    tbl = Table(title="Request costs")
    tbl.add_column("file"); tbl.add_column("rows", justify="right")
    tbl.add_column("in tok", justify="right"); tbl.add_column("out tok", justify="right")
    tbl.add_column("sec", justify="right"); tbl.add_column("$", justify="right")
    grand = 0.0
    for cid, c in sorted(costs.items()):
        grand += c.get("cost", 0.0)
        is_check = cid.startswith("check-")
        nrows = ""
        per_file = (Path(c["pdf"]).with_suffix(".check.csv") if is_check
                    else Path(c["pdf"]).with_suffix(".csv"))
        if per_file.exists():
            with open(per_file, newline="", encoding="utf-8") as f:
                nrows = str(max(sum(1 for _ in f) - 1, 0))
        tbl.add_row(Path(c["pdf"]).parent.name + (" ·check" if is_check else ""),
                    nrows,
                    str(c.get("prompt_tokens", "")), str(c.get("completion_tokens", "")),
                    str(c.get("seconds", "")), f"{c.get('cost', 0):.4f}")
    tbl.add_row("[bold]total[/bold]", "", "", "", "", f"[bold]{grand:.4f}[/bold]")
    console.print(tbl)
    console.print(f"\nFinal CSV: [bold]{out_dir / 'llm_seccoes.csv'}[/bold] "
                  f"({len(all_rows)} rows), report: {out_dir / 'report.txt'}")


if __name__ == "__main__":
    main()
