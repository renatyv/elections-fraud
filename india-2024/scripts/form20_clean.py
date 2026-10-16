#!/usr/bin/env python3
"""Build the clean analysis-ready Form 20 tables for Uttar Pradesh.

Turns the raw parser outputs (up_form20_booths.csv + up_form20_files.csv)
into identity-resolved, duplicate-free tables in data/form20/parsed/:

  up_booths_clean.csv  long: one row per (AC, polling station, candidate)
                       with station totals, AC/PC identity from the mapping
  up_ac_clean.csv      one row per AC, ready for analysis-tool
                       (ElectionData-compatible: registered_voters, voted,
                       blank_votes, null_votes, votes:c1.., votes:NOTA)
  cleaning_log.txt     how every file was identified, what was dropped

AC identity is resolved per file, in order:
  parsed   AC number read from the Form 20 header inside the PDF
  pair     a "<number>_<name>" token run in the filename that agrees with
           the AC mapping ("156_8211_HARDOI" -> 156 Hardoi; 8211 is the
           en-dash HTML entity left in filenames)
  name     AC-name tokens of the filename, district-scoped first
  number   the only number left after dropping a leading row serial
  last     the only mapping AC of the district still unassigned
  named    the district's own city AC, when exactly one file is left

Several files can carry copies of one AC (the same AC published by two
districts, re-uploads, complementary "Part-1" scans).  Identical stations
are kept once from the preferred file (the AC's own district, then the
largest); stations only present in another copy are merged in.

Electors per AC come from the Form 20 header; most Encore digital forms
leave the field blank, so a rescue regex re-reads the text extractions
(spelling variants of "Electors in Assembly/Segement").

Run:  cd india-2024 && uv run python scripts/form20_clean.py
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import get_close_matches
from enum import StrEnum
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PARSED = ROOT / "data" / "form20" / "parsed"
MAPPING_CSV = ROOT / "data" / "form20" / "up_ac_pc_mapping.csv"
TEXT_DIR = ROOT / "data" / "form20" / "text"

MAX_AC = 403
# tokens that never belong to an AC name in filenames
NAME_JUNK = {"form", "format", "frm", "from", "form20", "format20", "pdf",
             "mb", "no", "ac", "ps", "booth", "assembly", "part", "final",
             "result", "sheet", "details"}
ELECTORS_PATTERNS = [
    re.compile(r"[Tt]otal\s+[Nn]o\.?\s*of\s+[Ee]lectors\D{0,80}?([\d,]{5,})"),
    re.compile(r"[Ee]lectors\D{0,80}?([\d,]{5,})"),
]
MIN_ELECTORS, MAX_ELECTORS = 100_000, 5_000_000


def norm(s: str) -> str:
    return re.sub(r"[^a-z]", "", str(s).lower())


class ACSource(StrEnum):
    PARSED = "parsed"
    PAIR = "filename-pair"
    NAME = "filename-name"
    NUMBER = "filename-number"
    LAST = "last-ac-in-district"
    NAMED = "district-name-ac"
    UNRESOLVED = "unresolved"


@dataclass
class ACRef:
    """Official identity of one assembly constituency."""
    ac_no: int
    ac_name: str
    pc_name: str
    district: str


@dataclass
class Assignment:
    """AC identity recovered for one Form 20 file."""
    pdf: str
    district: str
    n_stations: int
    ac_no: int | None = None
    source: ACSource = ACSource.UNRESOLVED
    notes: list[str] = field(default_factory=list)


@dataclass
class Segment:
    """Stations of one file kept for an AC: all of them, or a subset."""
    pdf: str
    serials: set[int] | None  # None = every station of the file


@dataclass
class ACFiles:
    """The file copies that together cover one AC."""
    ac_no: int
    segments: list[Segment] = field(default_factory=list)


@dataclass
class SegmentAC:
    """One assembly segment of a multi-AC file, as its own pseudo-file."""
    display: str
    ac_no: int
    electors: int | None


@dataclass
class Pools:
    """Lookup structures over the AC->PC mapping."""
    by_no: dict[int, ACRef]
    by_district: dict[str, dict[str, int]]  # norm(district) -> name -> ac_no
    by_name: dict[str, int]  # norm(name) -> ac_no

    def district_pool(self, district: str) -> dict[str, int]:
        d = norm(district)
        if d in self.by_district:
            return self.by_district[d]
        hits = get_close_matches(d, list(self.by_district), n=1, cutoff=0.8)
        return self.by_district[hits[0]] if hits else {}


def load_pools() -> Pools:
    m = pd.read_csv(MAPPING_CSV)
    by_no = {int(r.ac_no): ACRef(int(r.ac_no), str(r.ac_name).strip(),
                                 str(r.pc_name).strip(), str(r.district).strip())
             for r in m.itertuples()}
    by_district: dict[str, dict[str, int]] = {}
    by_name: dict[str, int] = {}
    for a in by_no.values():
        by_district.setdefault(norm(a.district), {})[norm(a.ac_name)] = a.ac_no
        by_name.setdefault(norm(a.ac_name), a.ac_no)
    return Pools(by_no, by_district, by_name)


def file_tokens(stem: str) -> list[str]:
    """Filename tokens with the Form-20 label and numeric noise removed.

    Drops the "20" of Form-20/Format-20 labels (a bare 20 would otherwise
    look like an AC number) and bare numbers above 403: the en-dash HTML
    entity 8211 left in filenames and CDN upload dates (20240917xx).
    """
    toks = [t for t in re.split(r"[^0-9A-Za-z]+", stem) if t]
    out: list[str] = []
    i = 0
    while i < len(toks):
        low = toks[i].lower()
        if low in {"form", "format", "frm", "from"} \
                and i + 1 < len(toks) and toks[i + 1] == "20":
            i += 2
            continue
        if re.fullmatch(r"(form|format|frm)-?20", low):
            i += 1
            continue
        if toks[i].isdigit() and int(toks[i]) > MAX_AC:
            i += 1
            continue
        out.append(toks[i])
        i += 1
    return out


def name_joins(run: list[str]) -> list[str]:
    """Progressive joins of the name-worthy tokens of one run:
    ["BELTHARA", "ROAD"] -> ["belthara", "belthararoad"]."""
    keep = [norm(t) for t in run
            if not t.isdigit() and len(norm(t)) >= 4
            and norm(t) not in NAME_JUNK]
    return ["".join(keep[:k]) for k in range(1, len(keep) + 1)]


def match_name(joins: list[str], pool: dict[str, int]) -> int | None:
    """Longest join first: "bareillycant" should reach Bareilly Cantt
    (fuzzy) before the short exact join "bareilly" hits Bareilly."""
    for j in reversed(joins):
        hits = get_close_matches(j, list(pool), n=2, cutoff=0.85)
        if len(hits) == 1:
            return pool[hits[0]]
    return None


def runs_of(toks: list[str]) -> list[list[str]]:
    """Maximal runs of non-digit tokens."""
    out: list[list[str]] = []
    cur: list[str] = []
    for t in toks:
        if t.isdigit():
            if cur:
                out.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        out.append(cur)
    return out


def norm_alnum(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def drop_district_prefix(toks: list[str], district: str) -> list[str]:
    """Remove the leading "<District>__" of a filename (may span several
    tokens: "Gautam Buddha Nagar__63-Jewar").  Without this the district
    word prefix-joins into every AC name ("Azamgarh__Sagri" would match
    the city AC Azamgarh first)."""
    dn = norm_alnum(district)
    for k in range(min(len(toks), 5), 0, -1):
        if norm_alnum("".join(toks[:k])) == dn:
            return toks[k:]
    return toks


def assign_ac(pdf: str, district: str, parsed_ac: float | None,
              n_stations: int, pools: Pools) -> Assignment:
    a = Assignment(pdf, district, n_stations)
    dpool = pools.district_pool(district)
    toks = drop_district_prefix(file_tokens(Path(pdf).stem), district)

    if pd.notna(parsed_ac) and 0 < int(parsed_ac) <= MAX_AC \
            and int(parsed_ac) in pools.by_no:
        a.ac_no, a.source = int(parsed_ac), ACSource.PARSED
        _crosscheck(a, toks, dpool)
        _note_district(a, pools)
        return a

    # 1) <number>_<name> runs agreeing with the mapping
    strong: list[int] = []
    for i, t in enumerate(toks):
        if not t.isdigit():
            continue
        run: list[str] = []
        for u in toks[i + 1:]:
            if u.isdigit():
                break
            run.append(u)
        js = name_joins(run)
        if not js:
            continue
        for pool in (dpool, pools.by_name):
            hit = match_name(js, pool)
            if hit == int(t):
                strong.append(int(t))
                break
    if strong and len(set(strong)) == 1:
        a.ac_no, a.source = strong[0], ACSource.PAIR
        _note_district(a, pools)
        return a
    if strong:
        a.notes.append(f"conflicting number-name pairs {sorted(set(strong))}")

    # 2) bare AC-name tokens, district pool first; a run that says nothing
    #    but the district word must not match the district's city AC
    for pool in (dpool, pools.by_name):
        hits: set[int] = set()
        for run in runs_of(toks):
            keep = [norm(t) for t in run
                    if not t.isdigit() and len(norm(t)) >= 4
                    and norm(t) not in NAME_JUNK]
            if keep == [norm(district)]:
                continue
            hit = match_name(name_joins(run), pool)
            if hit is not None:
                hits.add(hit)
        if len(hits) == 1:
            a.ac_no, a.source = hits.pop(), ACSource.NAME
            _note_district(a, pools)
            return a
        if len(hits) > 1:
            a.notes.append(f"several name matches {sorted(hits)}")
            break

    # 3) a single number once a leading row serial is dropped
    nums = [int(t) for t in toks if t.isdigit()]
    rest = nums[1:] if len(nums) > 1 and nums[0] <= 20 else nums
    if rest and len(set(rest)) == 1:
        a.ac_no, a.source = rest[0], ACSource.NUMBER
        _note_district(a, pools)
        return a

    return a


def _crosscheck(a: Assignment, toks: list[str], dpool: dict[str, int]) -> None:
    """Note when the filename suggests a different AC than the header did."""
    for i, t in enumerate(toks):
        if not t.isdigit():
            continue
        run = []
        for u in toks[i + 1:]:
            if u.isdigit():
                break
            run.append(u)
        js = name_joins(run)
        if js:
            hit = match_name(js, dpool)
            if hit is not None and hit != a.ac_no:
                a.notes.append(f"filename suggests AC {hit} ({js[0]})")
                return


def _note_district(a: Assignment, pools: Pools) -> None:
    ref = pools.by_no[a.ac_no]  # type: ignore[index]
    if norm(ref.district) != norm(a.district) \
            and not get_close_matches(norm(a.district), [norm(ref.district)],
                                      n=1, cutoff=0.8):
        a.notes.append(f"file district '{a.district}' != mapping "
                       f"'{ref.district}'")


def assign_remaining(assignments: list[Assignment], pools: Pools) -> None:
    """Last-resort identifications within one district."""
    taken = {a.ac_no for a in assignments if a.ac_no is not None}
    open_files = [a for a in assignments if a.ac_no is None]
    for district in sorted({a.district for a in open_files}):
        pool = pools.district_pool(district)
        cand = [a for a in open_files if a.district == district]
        if len(cand) != 1:
            continue
        remaining = [ac for ac in pool.values() if ac not in taken]
        if len(remaining) == 1:
            cand[0].ac_no, cand[0].source = remaining[0], ACSource.LAST
            taken.add(remaining[0])
        elif norm(district) in {n for n, ac in pool.items() if ac not in taken}:
            cand[0].ac_no = pool[norm(district)]
            cand[0].source = ACSource.NAMED
            taken.add(cand[0].ac_no)


def read_text(pdf: str) -> str | None:
    for sub in ("ocr_rows", "ocr", "digital"):
        txt = TEXT_DIR / sub / f"{Path(pdf).stem}.txt"
        if txt.exists():
            return txt.read_text(errors="replace")
    return None


def base_pdf(pdf: str) -> str:
    """Original filename of a (possibly per-segment) pseudo-file."""
    return pdf.split("#")[0]


def ac_header_sequence(pdf: str) -> list[tuple[int, int | None]]:
    """(AC number, electors) per segment header, in text order.

    Encore prints the electors line just above the segment-name line, and
    repeats both on every page; consecutive repeats are collapsed.  The
    "… Assembly" tail keeps electors totals ("segment .... 385393") from
    posing as AC numbers.
    """
    ac_re = re.compile(r"segment\s*\.{2,}\s*(\d+)\s*-\s*(.+?)\s+Assembly",
                       re.IGNORECASE)
    out: list[tuple[int, int | None]] = []
    pending: int | None = None
    for line in (read_text(pdf) or "").splitlines():
        for pat in ELECTORS_PATTERNS:
            m = pat.search(line)
            if m:
                v = int(m.group(1).replace(",", ""))
                if MIN_ELECTORS <= v <= MAX_ELECTORS:
                    pending = v
                break
        m = ac_re.search(line)
        if m and int(m.group(1)) <= MAX_AC:
            ac = int(m.group(1))
            if not out or out[-1][0] != ac:
                out.append((ac, pending))
            pending = None
    return out


def repair_booths(booths: pd.DataFrame, files: pd.DataFrame,
                  log: list[str]) -> tuple[pd.DataFrame,
                                            dict[str, list[SegmentAC]]]:
    """Fix parse defects the checksum-verified parser cannot see:

    multi-AC  one PDF holding several assembly segments (district combined
            sheets): serials restart per segment.  Split into per-AC
            pseudo-files "<pdf>#<ac>" using the AC header sequence from
            the text (Kheri__28 = ACs 137..142).
    blocks   Encore prints >10 candidates as several column pages over the
            same station list; the parser numbered each page's candidates
            1..11 again and kept the per-page tail subtotals.
            -> renumber candidates (block-1)*width+i and sum the station
            columns over the blocks.
    jitter  re-transcribed page ranges produce near-duplicate rows that
            differ slightly, so the parser's identical-row dedupe keeps
            them -> keep the first row per (file, station, candidate).
    nota    Hindi Form 20 sheets carry NOTA as the LAST candidate column
            and print [valid, rejected, total]; some readings put valid
            into nota (total doubles), others drop it (nota = 0).
            -> per station with nota==valid or nota==0: move the last
            candidate's votes to NOTA, subtract from valid, recompute
            total = valid + rejected + NOTA.
    """
    b = booths.copy()
    n_cand = dict(zip(files.pdf, files.n_candidates))
    multi: dict[str, list[SegmentAC]] = {}

    # ---- multi-AC files: split into per-AC pseudo-files -------------------
    for pdf in list(b.pdf.unique()):
        g = b[b.pdf == pdf]
        ser = g.ps_serial.tolist()
        restarts = sum(1 for i in range(1, len(ser)) if ser[i] < ser[i - 1])
        if restarts == 0:
            continue
        seq = ac_header_sequence(pdf)
        if not (2 <= len(seq) == restarts + 1):
            log.append(f"MULTI-AC skipped {pdf}: {restarts + 1} segments "
                       f"vs header sequence {[a for a, _ in seq]}")
            continue
        seg_id, prev, segs = 0, 0, []
        for s in ser:
            if s < prev:
                seg_id += 1
            segs.append(seg_id)
            prev = s
        display = [f"{pdf}#{seq[s][0]}" for s in segs]
        b.loc[g.index, "pdf"] = display
        multi[pdf] = [SegmentAC(f"{pdf}#{ac}", ac, el) for ac, el in seq]
        log.append(f"MULTI-AC {pdf}: split into {restarts + 1} segments "
                   f"{[a for a, _ in seq]}")

    # ---- multi-block files (same AC, candidates in column pages) ----------
    for pdf, g in list(b.groupby("pdf", sort=False)):
        ser = g.ps_serial.tolist()
        restarts = [(ser[i - 1], ser[i]) for i in range(1, len(ser))
                    if ser[i] < ser[i - 1]]
        if len(restarts) < 2 or not all(cur == 1 for _, cur in restarts):
            continue
        width = int(n_cand.get(pdf, 0))
        n_st = g.ps_serial.nunique()
        if width < 2 or len(g) < 0.6 * (len(restarts) + 1) * width * n_st:
            continue  # jitter re-reads, not candidate-column pages
        text = read_text(pdf)
        acs = set(re.findall(r"segment\s*\.{2,}\s*(\d+)", text or ""))
        if len(acs) > 1:
            log.append(f"BLOCKS skipped for {pdf}: several AC headers {acs}")
            continue
        block = 1
        blocks: list[int] = []
        prev = 0
        for s in ser:
            if s < prev:
                block += 1
            blocks.append(block)
            prev = s
        idx = b.index[b.pdf == pdf]
        b.loc[idx, "candidate"] = (pd.Series(blocks, index=g.index) - 1) \
            * width + b.loc[idx, "candidate"]
        # station totals are per-block subtotals: put the block sums on
        # every row so the usual first()-per-station collapse is correct
        for col in ("valid", "rejected", "nota", "total", "tendered"):
            sums = b.loc[idx].groupby("ps_serial")[col].sum()
            b.loc[idx, col] = b.loc[idx].ps_serial.map(sums)
        log.append(f"BLOCKS {pdf}: {len(restarts) + 1} column pages x "
                   f"{width} candidates renumbered, station totals summed")

    # ---- jitter dedupe ----------------------------------------------------
    dup = b.duplicated(["pdf", "ps_serial", "candidate"], keep="first")
    if dup.any():
        for pdf, n in b.loc[dup].groupby("pdf").size().items():
            log.append(f"JITTER {pdf}: dropped {int(n)} re-read rows")
        b = b[~dup].copy()

    # ---- NOTA-as-last-candidate repair -----------------------------------
    for pdf in list(b.pdf.unique()):
        width = int(n_cand.get(pdf, 0))
        idx = b.index[b.pdf == pdf]
        sub = b.loc[idx]
        g = sub.groupby("ps_serial")
        st_valid, st_nota = g.valid.first(), g.nota.first()
        if width < 3 or len(st_nota) < 10:
            continue
        bad = (st_nota >= 0.5 * st_valid) & (st_valid >= 10)
        if bool((st_nota == 0).all()):  # whole file read without NOTA
            bad = pd.Series(True, index=st_nota.index)
        if not bool(bad.any()):
            continue
        last = g.candidate.transform("max")
        is_last = sub.candidate == last
        nota_new = sub.loc[is_last].groupby("ps_serial").votes.sum()
        upd = bad.index[bad]
        valid_new = st_valid - nota_new
        total_new = valid_new + nota_new + g.rejected.first()
        drop_rows = sub.index[is_last & sub.ps_serial.isin(upd)]
        m_upd = sub.ps_serial.isin(upd)
        for col, series in (("nota", nota_new), ("valid", valid_new),
                            ("total", total_new)):
            b.loc[sub.index[m_upd], col] = sub.ps_serial[m_upd].map(series)
        b = b.drop(index=drop_rows)
        log.append(f"NOTA {pdf}: NOTA was the last candidate column; "
                   f"repaired {len(upd)} stations "
                   f"({len(drop_rows)} candidate rows moved to NOTA)")

    return b, multi


def station_table(booths: pd.DataFrame) -> pd.DataFrame:
    """One row per (file, station): the per-station columns of the long
    CSV repeat on every candidate row and must be collapsed once."""
    return booths.groupby(["pdf", "ps_serial"], as_index=False).agg(
        ps_no=("ps_no", "first"), valid=("valid", "first"),
        rejected=("rejected", "first"), nota=("nota", "first"),
        total=("total", "first"), tendered=("tendered", "first"),
    )


def resolve_duplicates(assignments: list[Assignment], booths: pd.DataFrame,
                       files: pd.DataFrame, pools: Pools,
                       log: list[str]) -> dict[int, ACFiles]:
    """One ACFiles entry per claimed AC: identical stations kept once from
    the preferred file, stations only present elsewhere merged in."""
    stations = station_table(booths)
    ser_by_pdf = {pdf: set(g) for pdf, g in
                  stations.groupby("pdf")["ps_serial"]}
    n_cand = dict(zip(files.pdf, files.n_candidates))
    claimed: dict[int, list[Assignment]] = {}
    for a in assignments:
        if a.ac_no is not None:
            claimed.setdefault(a.ac_no, []).append(a)

    out: dict[int, ACFiles] = {}
    for ac, group in sorted(claimed.items()):
        acf = ACFiles(ac)
        pref = [g for g in group
                if norm(g.district) == norm(pools.by_no[ac].district)]
        winner = max(pref or group, key=lambda g: len(ser_by_pdf[g.pdf]))
        acf.segments.append(Segment(winner.pdf, None))
        w_ser = ser_by_pdf[winner.pdf]
        if len(group) > 1:
            log.append(f"AC {ac} ({pools.by_no[ac].ac_name}): base "
                       f"{winner.pdf} ({len(w_ser)} stations)")
        for loser in sorted(group, key=lambda g: g.pdf):
            if loser is winner:
                continue
            l_ser = ser_by_pdf[loser.pdf]
            extra = l_ser - w_ser
            if extra and n_cand.get(base_pdf(loser.pdf)) == \
                    n_cand.get(base_pdf(winner.pdf)):
                acf.segments.append(Segment(loser.pdf, extra))
                log.append(f"  merged {len(extra)} extra stations from "
                           f"{loser.pdf} (of {len(l_ser)})")
            else:
                log.append(f"  ignored {loser.pdf} ({len(l_ser)} stations, "
                           f"{len(l_ser & w_ser)} shared)"
                           + ("" if not extra else
                              " [candidate widths differ - extra stations "
                              "not merged]"))
        out[ac] = acf
    return out


def electors_from_text(pdf: str) -> int | None:
    for sub in ("ocr_rows", "ocr", "digital"):
        txt = TEXT_DIR / sub / f"{Path(base_pdf(pdf)).stem}.txt"
        if not txt.exists():
            continue
        text = txt.read_text(errors="replace")
        for pat in ELECTORS_PATTERNS:
            m = pat.search(text)
            if m:
                v = int(m.group(1).replace(",", ""))
                if MIN_ELECTORS <= v <= MAX_ELECTORS:
                    return v
    return None


def find_electors(pdf: str, parsed: pd.Series) -> int | None:
    if "#" in pdf:
        return None  # multi-AC segments get electors from their header
    base = base_pdf(pdf)
    if pd.notna(parsed.get(base)):
        return int(parsed[base])
    return electors_from_text(pdf)


def build_outputs(booths: pd.DataFrame, files: pd.DataFrame,
                  assignments: list[Assignment], acf: dict[int, ACFiles],
                  pools: Pools, log: list[str],
                  multi: dict[str, list[SegmentAC]] | None = None) -> None:
    asg = {a.pdf: a for a in assignments}
    seg_by_pdf = {seg.pdf: seg.serials
                  for a in acf.values() for seg in a.segments}
    el_override = {s.display: s.electors
                   for segs in (multi or {}).values() for s in segs
                   if s.electors is not None}

    sel = pd.Series(False, index=booths.index)
    for pdf, serials in seg_by_pdf.items():
        m = booths.pdf == pdf
        if serials is not None:
            m &= booths.ps_serial.isin(serials)
        sel |= m
    b = booths[sel].copy()
    b["ac_no"] = b.pdf.map(lambda p: asg[p].ac_no)
    b["ac_name"] = b.ac_no.map(lambda a: pools.by_no[a].ac_name)  # type: ignore[index]
    b["pc_name"] = b.ac_no.map(lambda a: pools.by_no[a].pc_name)  # type: ignore[index]
    b["district"] = b.ac_no.map(lambda a: pools.by_no[a].district)  # type: ignore[index]

    # ---- long clean CSV -------------------------------------------------
    long = b[["district", "pc_name", "ac_no", "ac_name", "ps_serial", "ps_no",
              "candidate", "votes", "valid", "rejected", "nota", "total",
              "tendered", "pdf"]]
    long = long.sort_values(["ac_no", "ps_serial", "candidate"],
                            ignore_index=True)
    long.to_csv(PARSED / "up_booths_clean.csv", index=False)
    n_stations = long.groupby("ac_no")["ps_serial"].nunique().sum()
    log.append(f"\nup_booths_clean.csv: {len(long)} station-candidate rows, "
               f"{int(n_stations)} stations")

    # ---- AC-level CSV ---------------------------------------------------
    st = station_table(b)
    cand = b.pivot_table(index=["ac_no", "ps_serial"], columns="candidate",
                         values="votes", aggfunc="sum").groupby(level=0).sum()
    n_cand = int(cand.columns.max())
    parsed_el = files.set_index("pdf")["electors"]
    rows: list[dict] = []
    for ac, group in sorted(acf.items()):
        ref = pools.by_no[ac]
        winner = group.segments[0].pdf
        s = st[st.pdf.isin({seg.pdf for seg in group.segments})]
        el = el_override.get(winner)
        el_note = ""
        if el is None:
            el = find_electors(winner, parsed_el)
            if el is None:
                for other in group.segments[1:]:
                    el = find_electors(other.pdf, parsed_el)
                    if el is not None:
                        el_note = "electors from merged copy"
                        break
            elif pd.isna(parsed_el.get(base_pdf(winner))):
                el_note = "electors from OCR header"
        voted_total = int(s.total.sum())
        if el is not None and voted_total > 0.8 * el:
            # votes polled can never approach electors this closely; the
            # header value is truncated or misread (Deoband: 34130)
            fixed = electors_from_text(winner)
            if fixed is not None and voted_total <= 0.8 * fixed:
                el = fixed
                el_note = "electors re-read from text (header implausible)"
            else:
                el = None
                el_note = "electors dropped: implausible vs votes polled"
        cvals = ([int(cand.loc[ac, c]) for c in cand.columns]
                 if ac in cand.index else [])
        notes = "; ".join(x for x in
                          ["; ".join(asg[winner].notes), el_note,
                           f"merged from {len(group.segments) - 1} cop(ies)"
                           if len(group.segments) > 1 else ""]
                          if x)
        rows.append({
            "ac_no": ac, "ac_name": ref.ac_name, "pc_name": ref.pc_name,
            "district": ref.district, "n_stations": int(len(s)),
            "n_candidates": len(cand.columns) if ac in cand.index else 0,
            "n_files": len(group.segments),
            "ac_source": asg[winner].source.value,
            "registered_voters": el,
            "blank_votes": 0,
            "null_votes": int(s.rejected.sum()),
            "valid_votes": int(s.valid.sum()),
            "nota": int(s.nota.sum()),
            "voted": voted_total,
            **{f"votes:c{c}": cvals[c - 1] if c <= len(cvals) else 0
               for c in range(1, n_cand + 1)},
            "votes:NOTA": int(s.nota.sum()),
            "notes": notes,
        })
    ac_df = pd.DataFrame(rows)
    ac_df.to_csv(PARSED / "up_ac_clean.csv", index=False)
    log.append(f"up_ac_clean.csv: {len(ac_df)} ACs, "
               f"{int(ac_df.registered_voters.isna().sum())} without "
               f"electors, {int((ac_df.n_stations < 100).sum())} with "
               f"<100 stations")


def main() -> None:
    booths = pd.read_csv(PARSED / "up_form20_booths.csv",
                         dtype={"ac_name": "string"})
    files = pd.read_csv(PARSED / "up_form20_files.csv",
                        dtype={"ac_name": "string"})
    log = ["UP Form 20 cleaning log", "=" * 40]
    booths, multi = repair_booths(booths, files, log)
    n_st = booths.groupby("pdf")["ps_serial"].nunique()
    pools = load_pools()

    assignments: list[Assignment] = []
    for r in files.itertuples():
        n = int(n_st.get(r.pdf, 0))
        if n == 0:  # guard-flagged or split multi-AC files keep no rows
            continue
        assignments.append(assign_ac(r.pdf, str(r.district), r.ac_no, n,
                                     pools))
    district_of = dict(zip(files.pdf, files.district))
    for base, segs in multi.items():
        for seg in segs:
            assignments.append(Assignment(
                seg.display, district_of.get(base, ""),
                int(n_st.get(seg.display, 0)), seg.ac_no, ACSource.PARSED,
                [f"segment of multi-AC file {base}"]))
    assign_remaining(assignments, pools)

    src = pd.Series([a.source.value for a in assignments]).value_counts()
    log.append("AC identification: " + ", ".join(f"{k}: {v}" for k, v
                                                 in src.items()))
    unresolved = [a for a in assignments if a.ac_no is None]
    log.append(f"\nunresolved files ({len(unresolved)}):")
    for a in sorted(unresolved, key=lambda x: x.pdf):
        log.append(f"  {a.pdf} ({a.n_stations} stations)"
                   + (f"  [{'; '.join(a.notes)}]" if a.notes else ""))

    acf = resolve_duplicates(assignments, booths, files, pools, log)

    noted = [a for a in assignments if a.notes and a.ac_no is not None]
    log.append(f"\nassignments with notes ({len(noted)}):")
    for a in sorted(noted, key=lambda x: x.pdf):
        log.append(f"  {a.pdf} -> AC {a.ac_no}: {'; '.join(a.notes)}")

    build_outputs(booths, files, assignments, acf, pools, log, multi)
    text = "\n".join(log)
    (PARSED / "cleaning_log.txt").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
