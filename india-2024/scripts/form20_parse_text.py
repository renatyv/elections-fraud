"""Parse UP Form 20 text extractions into a booth-level CSV.

Works on both pdftotext output (digital PDFs) and OCR text (scans) without
knowing the candidate count: every data row is

    serial[, ps_no,] n x candidate votes, valid, rejected, nota, total[, tendered]

Some scanned layouts omit the ps_no column, others leave tendered blank, so we
search for the unique (leading-column count, n) pair where
    sum(candidate votes) == valid  and  valid + nota + rejected == total.
A line is accepted only if exactly one pair validates.  Rows whose split
disagrees with the file's modal layout are re-checked at the modal layout and
dropped if they still fail (a silently shifted candidate column is worse than
a missing row).

Outputs (data/form20/parsed/):
    up_form20_booths.csv   long: one row per (file, polling station, candidate)
    up_form20_files.csv    per-file summary with AC metadata and coverage
"""

from __future__ import annotations

import argparse
import dataclasses
import re
from collections import Counter
from pathlib import Path

import pandas as pd
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
TEXT_DIR = ROOT / "data" / "form20" / "text"
OUT_DIR = ROOT / "data" / "form20" / "parsed"

INT_RE = re.compile(r"\d{1,3}(?:,\d{3})+|\d+")
PAGE_RE = re.compile(r"=====\s*page\s+(\d+)")
AC_RES = [
    re.compile(r"segment\s*\.{2,}\s*(\d+)\s*-\s*(.+?)\s+Assembly", re.IGNORECASE),
    re.compile(r"segment\s*[-–]?\s*(\d{1,3})\s*[-–]\s*(\S.*)$", re.IGNORECASE),
]
ELECTORS_RE = re.compile(
    r"Electors .*?segment\s*\.{2,}\s*([\d,]+)", re.IGNORECASE)


@dataclasses.dataclass
class Row:
    page: int
    line_no: int
    ps_serial: int
    ps_no: int | None
    cand: list[int]
    valid: int
    rejected: int
    nota: int
    total: int
    tendered: int
    layout: tuple[int, int]  # (leading columns, candidate count)


def line_ints(line: str) -> list[int]:
    out = []
    for m in INT_RE.finditer(line):
        out.append(int(m.group().replace(",", "")))
    return out


def line_cells_ints(line: str) -> list[int]:
    """Numbers from fully-numeric cells of a tab-separated line.

    A PS-name column may contain stray digits ("...को नं. 1"), which
    finditer-style extraction would wrongly fold into the data row.
    """
    out = []
    for cell in line.split("\t"):
        c = cell.strip().replace(",", "")
        if c.isdigit():
            out.append(int(c))
    return out


def tail_options(k: int, tail: list[int]) -> list[tuple[int, int, int, int]]:
    """Plausible (rejected, nota, total, tendered) readings of the numbers
    after `valid`.  Form 20 variants drop or reorder tail columns; total==-1
    means total is not printed and defaults to valid + rejected + nota."""
    if k <= 0:
        return [(-1, 0, -1, 0)]
    if k == 1:
        return [(tail[0], 0, -1, 0), (0, tail[0], -1, 0),
                (0, 0, tail[0], 0)]
    if k == 2:
        return [(tail[0], tail[1], -1, 0), (tail[0], 0, tail[1], 0),
                (0, tail[0], tail[1], 0)]
    if k == 3:
        return [(tail[0], tail[1], tail[2], 0),
                (tail[0], 0, tail[1], tail[2]),
                (0, tail[0], tail[1], tail[2]),
                (tail[0], tail[1], -1, tail[2])]
    return [(tail[0], tail[1], tail[2], tail[3]),
            (tail[1], 0, tail[2], tail[3])]


def row_candidates(nums: list[int],
                   forced: tuple[int, int] | None = None,
                   allow_skip: bool = True
                   ) -> list[tuple[tuple[int, int, int, int, int], Row]]:
    """All (off, n, tail reading, skip, variant) combos that make the row
    consistent: sum(candidate votes) == valid and
    valid + nota + rejected == total.

    skip=1 handles rows with one uninterpretable extra column (turnout
    breakdowns etc.) between the candidate votes and the tail; then valid
    is taken as the candidate sum.  variant=1 handles sheets that count
    NOTA inside the printed valid column; valid is normalised to the
    candidate sum.
    """
    combos = ([forced] if forced
              else [(off, n) for off in (1, 2) for n in range(1, 65)])
    out = []
    for off, n in combos:
        cand = nums[off:off + n]
        for skip in ((0, 1) if allow_skip else (0,)):
            base = off + n + 1 + skip
            if not base <= len(nums) <= base + 4:
                continue
            # skip=1: one uninterpretable column sits between the candidate
            # votes and the tail, so valid is the candidate sum itself
            valid = sum(cand) if skip else nums[off + n]
            tail = nums[base:]
            for oi, (re_, no_, t_, td_) in enumerate(
                    tail_options(len(tail), tail)):
                if skip and t_ == -1:
                    # valid is the candidate sum here, so a computed total
                    # would make the consistency check a tautology -- demand
                    # a printed total
                    continue
                if t_ == -1:
                    t_ = valid + re_ + no_
                ps_no = nums[1] if off == 2 else None
                if sum(cand) == valid and valid + no_ + re_ == t_:
                    out.append(((off, n, oi, skip, 0),
                                Row(0, 0, nums[0], ps_no, cand, valid,
                                    re_, no_, t_, td_, (off, n))))
                    continue
                # variant: the printed "valid" column includes NOTA
                if no_ > 0 and sum(cand) == valid - no_ and valid == t_:
                    out.append(((off, n, oi, skip, 1),
                                Row(0, 0, nums[0], ps_no, cand, sum(cand),
                                    re_, no_, t_, td_, (off, n))))
    return out


def split_row(nums: list[int],
              forced: tuple[int, int] | None = None) -> Row | None:
    """Unique consistent reading of a row, or None (ambiguous/none)."""
    cands = row_candidates(nums, forced=forced)
    if len({repr(r) for _, r in cands}) != 1:
        return None
    return cands[0][1]


def _parse_segment(lines: list[tuple[int, int, list[int]]]
                  ) -> tuple[list[Row], int, bool]:
    """Modal-layout parse of one serial-contiguous segment of lines."""
    first = [(pg, no, row_candidates(nums, allow_skip=False))
             for pg, no, nums in lines]
    spec_counts: Counter = Counter()
    on_counts: Counter = Counter()
    for _, _, cands in first:
        seen: set[tuple[int, int]] = set()
        for (off, n, oi, _skip, _var), _r in cands:
            spec_counts[(off, n, oi, 0, 0)] += 1
            seen.add((off, n))
        for on in seen:
            on_counts[on] += 1
    modal_spec = spec_counts.most_common(1)[0][0] if spec_counts else None
    best_on, best_cnt = (on_counts.most_common(1)[0]
                         if on_counts else (None, 0))
    ambiguous = (best_cnt >= 50 and any(c > 0.5 * best_cnt
                                        for on, c in on_counts.items()
                                        if on != best_on))
    modal_on = (modal_spec[0], modal_spec[1]) if modal_spec else None
    rows: list[Row] = []
    dropped = 0
    for (pg, no, nums), (_, _, cands) in zip(lines, first):
        at_modal = [(spec, r) for spec, r in cands
                    if spec[:2] == modal_on]
        pick = None
        for spec, r in at_modal:
            if spec == modal_spec:
                pick = r
                break
        if pick is None and at_modal:
            pick = at_modal[0][1]
        if pick is None:
            # repair pass: retry with the skip layout at the modal shape
            for spec, r in row_candidates(nums, forced=modal_on):
                if spec[:2] == modal_on:
                    pick = r
                    break
        if pick is None:
            dropped += 1
            continue
        pick.page, pick.line_no = pg, no
        rows.append(pick)
    promote_identity(rows)
    rows, dups = dedupe_serials(rows)
    rows, tail = drop_non_monotone(rows)
    return rows, dropped + dups + tail, ambiguous


def parse_lines(text: str) -> tuple[list[Row], int, bool]:
    """Parse all number lines, keeping only rows that match each segment's
    modal (leading columns, candidate count) pair.

    A file splits into segments at polling-station serial resets, so one
    PDF holding several assembly segments (each restarting at serial 1)
    parses each part with its own layout.  The tail reading (which trailing
    columns exist) may vary per row within the modal pair; rows admitting a
    different (off, n) than the modal are dropped.  `ambiguous` reports
    that a competing (off, n) pair is nearly as common as the modal one.

    Returns (rows, n_dropped, ambiguous).
    """
    page = 0
    lines: list[tuple[int, int, list[int]]] = []
    for line_no, line in enumerate(text.splitlines()):
        m = PAGE_RE.search(line)
        if m:
            page = int(m.group(1))
            continue
        if "Serial" in line or "FORM 20" in line:
            continue
        nums = line_cells_ints(line) if "\t" in line else line_ints(line)
        if len(nums) < 8:
            continue
        lines.append((page, line_no, nums))

    segments: list[list[tuple[int, int, list[int]]]] = []
    cur: list[tuple[int, int, list[int]]] = []
    prev_serial = 0
    for item in lines:
        nums = item[2]
        counting_header = nums[:5] == [1, 2, 3, 4, 5]
        if nums[0] == 1 and prev_serial >= 20 and not counting_header:
            segments.append(cur)
            cur = []
        cur.append(item)
        prev_serial = nums[0]
    if cur:
        segments.append(cur)

    rows: list[Row] = []
    dropped = 0
    ambiguous = False
    for seg in segments:
        seg_rows, seg_dropped, seg_amb = _parse_segment(seg)
        rows.extend(seg_rows)
        dropped += seg_dropped
        ambiguous = ambiguous or seg_amb
    return rows, dropped, ambiguous


def parse_pdf_positional(pdf_path: Path, tol: float = 6.0) -> list[Row]:
    """Group PDF words into visual rows by y-coordinate, read numbers left
    to right. Recovers rows that pdftotext splits across lines."""
    doc = fitz.open(pdf_path)
    rows: list[Row] = []
    for pno, page in enumerate(doc, start=1):
        words = [w for w in page.get_text("words") if INT_RE.fullmatch(w[4])
                 or all(c.isdigit() or c == "," for c in w[4])]
        words.sort(key=lambda w: (w[1], w[0]))
        line: list[tuple[float, int]] = []
        last_y = None
        lines: list[list[int]] = []
        for w in words:
            y = w[1]
            if last_y is not None and y - last_y > tol:
                lines.append([n for _, n in sorted(line)])
                line = []
            line.append((w[0], int(w[4].replace(",", ""))))
            last_y = y
        if line:
            lines.append([n for _, n in sorted(line)])
        for line_no, nums in enumerate(lines):
            if len(nums) < 8:
                continue
            row = split_row(nums)
            if row is not None:
                row.page = pno
                row.line_no = line_no
                rows.append(row)
    doc.close()
    return rows


def promote_identity(rows: list[Row]) -> None:
    """Some sheets repeat one constant 'serial' (e.g. the AC number) and
    carry the real polling-station number in the ps_no column; promote it."""
    if len({r.ps_serial for r in rows}) > max(3, len(rows) // 10):
        return
    psnos = {r.ps_no for r in rows if r.ps_no is not None}
    if len(psnos) > len({r.ps_serial for r in rows}):
        for r in rows:
            if r.ps_no is not None:
                r.ps_serial = r.ps_no


def dedupe_serials(rows: list[Row]) -> tuple[list[Row], int]:
    """Drop repeated serials whose votes are identical (OCR page repeats)."""
    seen: dict[int, Row] = {}
    out: list[Row] = []
    dups = 0
    for r in rows:
        prev = seen.get(r.ps_serial)
        if prev is not None and (prev.cand == r.cand
                                 and prev.total == r.total):
            dups += 1
            continue
        seen[r.ps_serial] = r
        out.append(r)
    return out, dups


def drop_non_monotone(rows: list[Row]) -> tuple[list[Row], int]:
    """Keep the strictly increasing serial prefix.

    Catches OCR artifacts past the last real polling station: end-of-file
    result-summary tables, all-zero lines, re-transcribed page fragments.
    """
    out: list[Row] = []
    last = 0
    dropped = 0
    for r in rows:
        if r.ps_serial > last:
            out.append(r)
            last = r.ps_serial
        else:
            dropped += 1
    return out, dropped


def parse_file(txt_path: Path) -> tuple[list[Row], str | None, str | None,
                                        int | None, int, bool]:
    text = txt_path.read_text()
    ac_no = ac_name = None
    electors = None
    for line in text.splitlines():
        if ac_no is None:
            for rx in AC_RES:
                m = rx.search(line)
                if m:
                    ac_no, ac_name = int(m.group(1)), m.group(2).strip(" .")
                    break
        if electors is None:
            m = ELECTORS_RE.search(line)
            if m and m.group(1).replace(",", "").isdigit():
                electors = int(m.group(1).replace(",", ""))
    rows, dropped, ambiguous = parse_lines(text)
    return (rows, ac_no, ac_name, electors, dropped, ambiguous)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default="digital,ocr,ocr_rows",
                    help="comma list of text/ subdirs to parse")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    long_rows: list[dict] = []
    file_rows: list[dict] = []

    ocr_stems = {p.stem for p in (TEXT_DIR / "ocr").glob("*.txt")}
    ocrrows_stems = {p.stem for p in (TEXT_DIR / "ocr_rows").glob("*.txt")}
    for sub in args.sources.split(","):
        for txt in sorted((TEXT_DIR / sub).glob("*.txt")):
            if sub == "digital" and txt.stem in ocr_stems:
                continue  # rescued copy supersedes the corrupt text layer
            if sub in ("digital", "ocr") and txt.stem in ocrrows_stems:
                continue  # vision-extracted rows supersede both
            rows, ac_no, ac_name, electors, n_dropped, ambiguous = (
                parse_file(txt))
            pdf_path = ROOT / "data" / "form20" / "up" / (txt.stem + ".pdf")
            note = ""
            if sub == "digital" and (len(rows) < 30 or n_dropped > 0):
                pos = parse_pdf_positional(pdf_path)
                if len(pos) > len(rows):
                    rows = pos
                    n_dropped = 0
                    ambiguous = False
                    note = "positional"
            district = txt.stem.split("__")[0]
            widths = sorted({len(r.cand) for r in rows})
            n_cand = max(widths) if widths else 0
            serials = [r.ps_serial for r in rows]
            # a reset to 1 starts the next assembly segment in multi-AC files
            monotone = all(b > a or b == 1
                           for a, b in zip(serials, serials[1:]))
            # layout-soup guard: some PDFs carry extra (often empty) columns
            # before the candidate votes; a leading near-all-zero candidate
            # column means prefix columns were absorbed as candidates and
            # every index is shifted -- exclude the file from the CSV.
            zero_prefix = False
            for i in range(min(n_cand, 3)):
                vals = [r.cand[i] for r in rows if len(r.cand) > i]
                if vals and sum(v == 0 for v in vals) / len(vals) > 0.9:
                    zero_prefix = True
                    break
            zero_serials = (sum(r.ps_serial == 0 for r in rows) > 0.1 * len(rows)
                            if rows else False)
            ok = (bool(rows) and len(widths) <= 2 and n_dropped == 0
                  and not zero_prefix and not ambiguous and not zero_serials)
            file_rows.append({
                "source": sub, "pdf": txt.stem + ".pdf", "district": district,
                "ac_no": ac_no, "ac_name": ac_name, "electors": electors,
                "n_stations": len(rows), "n_candidates": n_cand,
                "widths": ",".join(map(str, widths)),
                "n_dropped": n_dropped,
                "serials_monotone": monotone, "parses_clean": ok,
                "method": ("zero_col_prefix" if zero_prefix else
                           "ambiguous_layout" if ambiguous else
                           "zero_serials" if zero_serials else note),
            })
            if zero_prefix or ambiguous or zero_serials:
                continue
            for r in rows:
                for i, v in enumerate(r.cand):
                    long_rows.append({
                        "source": sub, "pdf": txt.stem + ".pdf",
                        "district": district, "ac_no": ac_no,
                        "ac_name": ac_name, "page": r.page,
                        "ps_serial": r.ps_serial, "ps_no": r.ps_no,
                        "candidate": i + 1, "votes": v,
                        "valid": r.valid, "rejected": r.rejected,
                        "nota": r.nota, "total": r.total,
                        "tendered": r.tendered,
                    })

    pd.DataFrame(file_rows).to_csv(OUT_DIR / "up_form20_files.csv", index=False)
    pd.DataFrame(long_rows).to_csv(OUT_DIR / "up_form20_booths.csv", index=False)

    files = pd.DataFrame(file_rows)
    clean = files["parses_clean"].sum()
    print(f"{len(files)} files, {clean} clean, "
          f"{len(long_rows)} station-candidate rows, "
          f"{files['n_stations'].sum()} stations")
    bad = files[~files["parses_clean"]]
    print(f"{len(bad)} files not clean:")
    print(bad[["source", "pdf", "n_stations", "n_candidates", "widths",
               "n_dropped", "serials_monotone"]].to_string())


if __name__ == "__main__":
    main()
