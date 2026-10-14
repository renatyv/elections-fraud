#!/usr/bin/env python3
"""Round 3 of UP Form 20 collection: hunt districts with no archived index page.

After rounds 1-2, 36 of UP's ~75 districts have Form 20 PDFs. The rest never
had their election page captured under the URL probed in round 1, so round 3
queries the Wayback CDX index per district domain and looks for ANY page that
plausibly holds Form 20 links (form20/format-20/prarup slugs, lok-sabha /
general-election 2024 pages), fetches the best candidates and extracts PDFs
with the same link rules as round 2.

Run:     cd india-2024 && uv run python scripts/download_up_form20_round3.py
Output:  appends to data/form20/up/*.pdf and data/form20/up_manifest.csv
"""
from __future__ import annotations

import re
import sys
import time
import urllib.parse
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from download_up_form20_round2 import (  # noqa: E402
    DELAY_CDN,
    UA,
    WB,
    extract_links,
    fetch,
    safe_name,
)

HERE = Path(__file__).resolve().parent
FORM20 = HERE.parent / "data" / "form20"
OUT = FORM20 / "up"
PAGES = FORM20 / "up_pages"
MANIFEST = FORM20 / "up_manifest.csv"

DELAY_CDX = 5.0
DELAY_WB = 8.0  # gentler on web.archive.org than round 2's 3s (it throttles)

# district -> host for the sweep (json hosts, with Mainpuri fixed)
HOSTS: dict[str, str] = {
    "Baghpat": "bagpat.nic.in", "Agra": "agra.nic.in", "Aligarh": "aligarh.nic.in",
    "Mainpuri": "mainpuri.nic.in", "Hathras": "hathras.nic.in", "Budaun": "budaun.nic.in",
    "Pilibhit": "pilibhit.nic.in", "Moradabad": "moradabad.nic.in", "Rampur": "rampur.nic.in",
    "Bijnor": "bijnor.nic.in", "Amroha": "amroha.nic.in", "Kanpur Dehat": "kanpurdehat.nic.in",
    "Etawah": "etawah.nic.in", "Farrukhabad": "farrukhabad.nic.in", "Kannauj": "kannauj.nic.in",
    "Pryagraj": "prayagraj.nic.in", "Lalitpur": "lalitpur.nic.in", "Hamirpur": "hamirpur.nic.in",
    "Banda": "banda.nic.in", "Chitrakoot": "chitrakoot.nic.in", "Varanasi": "varanasi.nic.in",
    "Chandauli": "chandauli.nic.in", "Sonbhadra": "sonbhadra.nic.in", "Azamgarh": "azamgarh.nic.in",
    "Ballia": "ballia.nic.in", "Maharajganj": "maharajganj.nic.in", "Deoria": "deoria.nic.in",
    "Kushinagar": "kushinagar.nic.in", "Sant Kabir Nagar": "sknagar.nic.in",
    "Gonda": "gonda.nic.in", "Sultanpur": "sultanpur.nic.in", "Ambedkar Nagar": "ambedkarnagar.nic.in",
    # never probed in round 1
    "Auraiya": "auraiya.nic.in", "Hardoi": "hardoi.nic.in", "Jalaun": "jalaun.nic.in",
    "Kaushambi": "kaushambi.nic.in", "Mahoba": "mahoba.nic.in", "Shravasti": "shravasti.nic.in",
}

FORM_SLUG_RE = re.compile(r"form\s*-?\s*20|format-?20|prarup|praroop", re.I)
ELECTION_SLUG_RE = re.compile(r"lok-?sabha|general-?election|election|parinam|result", re.I)
YEAR_RE = re.compile(r"202[45]")
EXCLUDE_RE = re.compile(
    r"\.(jpe?g|png|gif|css|js|pdf|woff2?|mp4|docx?|xlsx?)($|\?)|/wp-(content/themes|includes)|"
    r"xmlrpc|wp-login|/feed|/tag/|/author/|/category/|\.ico|sitemap",
    re.I,
)
MAX_PAGES_PER_DISTRICT = 8


def cdx_candidates(host: str) -> list[tuple[int, str, str]]:
    """(score, ts, url) pages worth fetching, best first."""
    url = (
        "http://web.archive.org/cdx/search/cdx"
        f"?url={host}*&output=text&fl=timestamp,original,statuscode"
        "&collapse=urlkey&filter=statuscode:200&limit=8000"
    )
    try:
        r = requests.get(url, headers=UA, timeout=120)
        lines = r.text.splitlines()
    except requests.RequestException as e:
        print(f"  CDX ERR {type(e).__name__} {host}", flush=True)
        return []
    def rank(score: int, ts: str) -> tuple[int, bool, str]:
        return (score, "202406" <= ts[:6] <= "202506", ts)

    best: dict[str, tuple[int, str, str]] = {}
    for ln in lines:
        parts = ln.split(" ")
        if len(parts) < 3:
            continue
        ts, orig = parts[0], parts[1]
        path = urllib.parse.unquote(orig)
        if EXCLUDE_RE.search(path):
            continue
        if FORM_SLUG_RE.search(path):
            score = 2
        elif ELECTION_SLUG_RE.search(path) and YEAR_RE.search(path):
            score = 1
        else:
            continue
        cur = best.get(orig)
        if cur is None or rank(score, ts) > rank(cur[0], cur[1]):
            best[orig] = (score, ts, orig)
    # score desc, then ts asc (the `better` rule above already kept a 2024H2-2025H1 snapshot)
    ranked = sorted(best.values(), key=lambda x: (-x[0], x[1]))
    return ranked[:MAX_PAGES_PER_DISTRICT]


def main() -> None:
    man = pd.read_csv(MANIFEST)
    seen_urls = set(man["pdf_url"])
    rows: list[dict] = []
    n_pages = 0

    for district, host in HOSTS.items():
        cands = cdx_candidates(host)
        time.sleep(DELAY_CDX)
        if not cands:
            print(f"[{district}] no candidate pages in CDX", flush=True)
            continue
        safe = re.sub(r"[^A-Za-z0-9]+", "_", district).lower()
        found_before = len(rows)
        for idx, (score, ts, page_url) in enumerate(cands):
            cache = PAGES / f"{safe}__r3_{idx}.htm"
            if not cache.exists():
                raw = fetch(WB.format(ts=ts, url=page_url), DELAY_WB, tries=2)
                time.sleep(DELAY_WB)
                if raw is None:
                    continue
                cache.write_bytes(raw)
            html = cache.read_text(encoding="utf-8", errors="replace")
            for hit in extract_links(html, page_url):
                if hit["pdf_url"] in seen_urls:
                    continue
                seen_urls.add(hit["pdf_url"])
                rows.append({"district": district, **hit})
            n_pages += 1
        print(f"[{district}] {len(cands)} pages, +{len(rows) - found_before} new links", flush=True)

    if rows:
        man = pd.concat([man, pd.DataFrame(rows)], ignore_index=True)
        man = man.drop_duplicates(subset=["pdf_url"]).reset_index(drop=True)

    ok = fail = skip = 0
    for i, r in enumerate(man.itertuples(), 1):
        dest = OUT / safe_name(r.district, r.ac_label, r.pdf_url)
        if dest.exists() and dest.stat().st_size > 10000:
            skip += 1
            continue
        raw = fetch(r.pdf_url, DELAY_CDN)
        if raw and raw[:5] == b"%PDF-":
            dest.write_bytes(raw)
            ok += 1
            print(f"PDF [{i}/{len(man)}] OK {dest.name} ({len(raw)//1024} KB)", flush=True)
        else:
            fail += 1
            print(f"PDF [{i}/{len(man)}] FAIL {r.district} {r.ac_label}", flush=True)
        time.sleep(DELAY_CDN)

    man.to_csv(MANIFEST, index=False)
    print(f"done: pages={n_pages}, new links={len(rows)}, downloaded={ok}, failed={fail}")


if __name__ == "__main__":
    main()
