#!/usr/bin/env python3
"""Finalize UP Form 20: re-extract all links from cached pages, purge junk,
re-download files lost to filename collisions.

Lessons from rounds 1-3 baked in here:
  * identical labels within a district (Agra's ten "details.pdf") must get
    collision-safe destination names, else each download overwrites the last;
  * only GE-2024 Form 20s are kept: September-2024 CDN uploads and
    text-verified 2025 re-uploads (Fatehpur, Budaun); candidate expense docs,
    excise e-lotteries, polling-station lists and office forms are dropped;
  * duplicate content (same MD5) is kept once.

Run:     cd india-2024 && uv run python scripts/download_up_form20_finalize.py
"""
from __future__ import annotations

import hashlib
import re
import time
import urllib.parse
from pathlib import Path

import pandas as pd

from download_up_form20_round2 import DELAY_CDN, extract_links, fetch

HERE = Path(__file__).resolve().parent
FORM20 = HERE.parent / "data" / "form20"
OUT = FORM20 / "up"
PAGES = FORM20 / "up_pages"
MANIFEST = FORM20 / "up_manifest.csv"
DISTRICTS_JSON = FORM20 / "up_form20_districts_cdx.json"

JUNK_LABEL = re.compile(
    r"liquor|lottery|excise|interview|walk-in|manual|rate.?list|news|information"
    r"|vacan|verification|entrance|BSA|EPDS|deployment|12D|Forms_?\d|shop"
    r"|doctors|teacher|selection|seizure|polling_station",
    re.I,
)
# party markers in a label indicate a per-candidate document; AC labels never
# name a party. Applied to September uploads, where the upload month itself
# no longer separates candidates (spring) from results.
PARTY_LABEL = re.compile(
    r"party|samajwadi|bahujan|janata|congress|independent|bhartiya|samanta|vidhayak",
    re.I,
)


def form20_text(path: Path) -> bool:
    from pypdf import PdfReader

    try:
        r = PdfReader(str(path))
        t = " ".join((pg.extract_text() or "") for pg in r.pages[:2])
        return bool(re.search(r"FORM\s*20|FINAL RESULT", t, re.I))
    except Exception:
        return False


def url_stem(pdf_url: str) -> str:
    return Path(urllib.parse.urlparse(pdf_url).path).stem


def main() -> None:
    import json

    from download_up_form20_round3 import HOSTS

    districts = json.load(open(DISTRICTS_JSON))
    # canonical district name per lowercase key: round-1 json + round-3 HOSTS.
    # The FS is case-insensitive (macOS) while all name matching here is
    # case-sensitive, so dest names must use the canonical spelling.
    canonical = {re.sub(r"[^A-Za-z0-9]+", "_", n).lower(): n for n in
                 [d["district"] for d in districts] + list(HOSTS)}

    # 1. re-extract every link from all page caches -------------------------
    rows: list[dict] = []
    seen: set[str] = set()
    for p in sorted(PAGES.glob("*.htm")):
        stem = re.sub(r"__r3_\d+$", "", p.stem.removesuffix("__extra"))
        district = canonical.get(stem, stem.title())
        html = p.read_text(encoding="utf-8", errors="replace")
        for hit in extract_links(html, f"https://{stem}.nic.in/"):
            if hit["pdf_url"] in seen:
                continue
            seen.add(hit["pdf_url"])
            rows.append({"district": district, **hit})
    links = pd.DataFrame(rows)
    print(f"links extracted from caches: {len(links)}")

    # 2. junk purge by label ------------------------------------------------
    links = links[~links.ac_label.str.contains(JUNK_LABEL, regex=True, na=False)]
    print(f"after label purge: {len(links)}")

    # 3. collision-safe destination names -----------------------------------
    links["base"] = [re.sub(r"[^A-Za-z0-9()-]+", "_", l)[:60].strip("_-")
                     for l in links.ac_label]
    links["base"] = [
        b if b else url_stem(u)
        for b, u in zip(links.base, links.pdf_url)
    ]
    dup = links.groupby(["district", "base"]).pdf_url.transform("size") > 1
    links["dest"] = [
        f"{d}__{b}.pdf" if not is_dup else f"{d}__{b}__{url_stem(u)}.pdf"
        for d, b, is_dup, u in zip(links.district, links.base, dup, links.pdf_url)
    ]

    # 4. month filter --------------------------------------------------------
    # candidates post in spring, results land in Sep 2024 (some re-uploads in
    # 2025), so the month does most of the sorting; September labels only need
    # the party-marker check, 2025 uploads need real proof of being Form 20
    keep_mask, keep_rows = [], []
    for r in links.itertuples():
        if r.dest in keep_rows:  # same dest verified already (twin URL)
            keep_mask.append(True)
            continue
        dest = OUT / r.dest
        month = re.search(r"/uploads/(\d{4}/\d{2})/", r.pdf_url)
        month = month.group(1) if month else "?"
        if PARTY_LABEL.search(r.ac_label):
            ok = False
        elif month == "2024/09":
            ok = True
        elif month.startswith("2025"):
            if not (dest.exists() and dest.stat().st_size > 10000):
                raw = fetch(r.pdf_url, DELAY_CDN)
                if raw and raw[:5] == b"%PDF-":
                    dest.write_bytes(raw)
                time.sleep(DELAY_CDN)
            # scanned re-uploads carry no text layer; an explicit "Form 20"
            # label is accepted for them, anything else needs text proof
            explicit_f20 = bool(re.search(r"form\s*-?\s*20", r.ac_label, re.I))
            ok = (dest.exists() and form20_text(dest)) or explicit_f20
            if not ok:
                dest.unlink(missing_ok=True)
                print(f"drop (2025, not FORM 20): {r.dest}")
        else:
            ok = False
        keep_mask.append(ok)
        if ok:
            keep_rows.append(r.dest)
    links = links[keep_mask]
    print(f"after month/text filter: {len(links)}")

    # 5. download whatever is missing (collisions, failed runs) --------------
    ok = fail = skip = 0
    for i, r in enumerate(links.itertuples(), 1):
        dest = OUT / r.dest
        if dest.exists() and dest.stat().st_size > 10000:
            skip += 1
            continue
        raw = fetch(r.pdf_url, DELAY_CDN)
        if raw and raw[:5] == b"%PDF-":
            dest.write_bytes(raw)
            ok += 1
            print(f"PDF [{i}/{len(links)}] OK {dest.name} ({len(raw)//1024} KB)", flush=True)
        else:
            fail += 1
            print(f"PDF [{i}/{len(links)}] FAIL {r.district} {r.ac_label}", flush=True)
        time.sleep(DELAY_CDN)

    # 6. md5 dedupe (prefer files referenced by the manifest) ----------------
    h: dict[str, list[Path]] = {}
    for p in sorted(OUT.glob("*.pdf")):
        h.setdefault(hashlib.md5(p.read_bytes()).hexdigest(), []).append(p)
    referenced = set(links.dest)
    n_dup = 0
    survivors: set[str] = set()
    for group in h.values():
        keep_p = next((p for p in group if p.name in referenced), group[0])
        survivors.add(keep_p.name)
        n_dup += len(group) - 1
        for p in group:
            if p is not keep_p:
                p.unlink()

    man = links[links.dest.isin(survivors)].drop(columns=["base"])
    man.to_csv(MANIFEST, index=False)
    # orphan files from earlier naming mistakes
    n_orphan = 0
    for p in OUT.glob("*.pdf"):
        if p.name not in survivors:
            p.unlink()
            n_orphan += 1
    print(f"dup twins removed: {n_dup}; orphans removed: {n_orphan}")
    print(f"downloaded={ok}, failed={fail}, already={skip}")
    print(f"manifest: {len(man)} rows; files on disk: {len(survivors)}; "
          f"districts: {man.district.nunique()}")


if __name__ == "__main__":
    main()
