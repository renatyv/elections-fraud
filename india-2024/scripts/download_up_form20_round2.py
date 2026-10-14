#!/usr/bin/env python3
"""Round 2 of UP Form 20 collection: recover districts missed in round 1.

Round 1 (download_up_form20.py) left three gaps:
  1. six cached pages whose PDF links were rejected by the label filter
     ("AC-178 Tiloi", "AC No 58- Dhaulana", Hindi "click here" labels,
     bare AC names under /uploads/2025/);
  2. EXTRA_PAGES fetches that reused the per-district cache file, so the
     extra page was never actually downloaded (e.g. Jaunpur part-2);
  3. 28 districts whose page fetch failed on the first try (only the latest
     Wayback capture was attempted).

This script:
  A. re-extracts links from every cached page with relaxed filters
     (uploads from 2024 on; AC-… / AC No … / row-derived labels);
  B. fetches the EXTRA_PAGES under a separate "<district>__extra" cache;
  C. retries page-less districts across up to 3 of their captures;
  D. merges with the existing manifest, downloads new PDFs from the
     cdn.s3waas.gov.in CDN, rewrites data/form20/up_manifest.csv.

Run:     cd india-2024 && uv run python scripts/download_up_form20_round2.py
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
FORM20 = DATA / "form20"
OUT = FORM20 / "up"
PAGES = FORM20 / "up_pages"
DISTRICTS_JSON = FORM20 / "up_form20_districts_cdx.json"
MANIFEST = FORM20 / "up_manifest.csv"

UA = {"User-Agent": "Mozilla/5.0 (election-forensics-research)"}
WB = "https://web.archive.org/web/{ts}id_/{url}"
DELAY_WB = 3.0
DELAY_CDN = 0.7

EXTRA_PAGES: dict[str, str] = {
    "Jaunpur": "https://jaunpur.nic.in/lok-sabha-general-election-2024-praroop-20part-2",
    "Mau": "https://mau.nic.in/en/format-20-lok-sabha-general-election-2024/",
    "Fatehpur": "https://fatehpur.nic.in/lok-sabha-general-election-2024-election-result-form-20/",
    "Maharajganj": "https://maharajganj.nic.in/lok-sabha-general-election-2024-form-20-part-1/",
    "Unnao": "https://unnao.nic.in/general-lok-sabha-election-2024-33-unnao-form-20/",
    "Rae Bareli": "https://raebareli.nic.in/lok-sabha-general-election-2024-praroop-20-part-1/",
    "Hapur": "https://hapur.nic.in/lok-sabha-general-election-2024-format-20-part-1/",
}

AC_LINK_RE = re.compile(
    r"<a[^>]+href=[\"']([^\"']+\.pdf)[\"'][^>]*>(.*?)</a>",
    re.I | re.S,
)
TAG_RE = re.compile(r"<[^>]+>")
NUM_START_RE = re.compile(r"^\d{1,3}\s*[-–.]\s*\S|^\d{1,3}\s+\S")
AC_PREFIX_RE = re.compile(r"^AC(\s*(No\.?|number)?)?\s*[-–]?\s*\d{1,3}\b", re.I)
FORM20_RE = re.compile(r"form\s*-?\s*20", re.I)
VIEW_WORDS = ("view", "download", "pdf", "click")
NAME_RE = re.compile(r"^[A-Za-z\u0900-\u097F][A-Za-z\u0900-\u097F .()]{1,39}$")
STOP_WORDS = re.compile(
    r"gazette|holiday|guide|tender|budget|calendar|list of|mlc|electoral roll|roll|circuit", re.I
)
CLICK_RE = re.compile(r"click|यहाँ|यहां|клик", re.I)
# GE-2024 Form 20 upload window: April 2024 .. March 2025
UPLOAD_RE = re.compile(r"/uploads/(2024|2025)/")
# round 1 observed Form 20 uploads in Sep 2024; late re-uploads in 2025
UPLOAD_STRICT_RE = re.compile(r"/uploads/(2024/09|2025)/")


def fetch(url: str, delay: float, tries: int = 3) -> bytes | None:
    for a in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=90)
            if r.status_code == 200:
                return r.content
            print(f"  HTTP {r.status_code} {url[:100]}", flush=True)
        except requests.RequestException as e:
            print(f"  ERR {type(e).__name__} {url[:100]}", flush=True)
        time.sleep(delay * (a + 1))
    return None


def get_snap(url: str) -> str | None:
    api = "http://archive.org/wayback/available?url=" + urllib.parse.quote(url, safe="")
    try:
        r = requests.get(api, headers=UA, timeout=30).json()
        s = r.get("archived_snapshots", {}).get("closest", {})
        if s.get("available") and str(s.get("status")) == "200":
            return s["timestamp"]
    except requests.RequestException:
        pass
    return None


def row_label(html: str, link_start: int) -> str | None:
    """AC label from the table row around the anchor, e.g. '353-मधुबन'."""
    tr0 = html.rfind("<tr", 0, link_start)
    tr1 = html.find("</tr>", link_start)
    if tr0 == -1 or tr1 == -1:
        return None
    row = re.sub(r"\s+", " ", TAG_RE.sub(" ", html[tr0:link_start])).strip()
    row = re.sub(r"^(?:tr|tbody|thead)?[^A-Za-z0-9\u0900-\u097F]*", "", row, flags=re.I)
    row = re.sub(r"^\d{1,2}\s+(?=\d{1,3}\s*[-–])", "", row)  # drop row serial
    return row[:60] or None


def extract_links(html: str, base_url: str) -> list[dict]:
    """PDF links that look like GE-2024 Form 20 uploads, with labels."""
    found: list[dict] = []
    for m in AC_LINK_RE.finditer(html):
        href, inner = m.group(1), m.group(2)
        label = re.sub(r"\s+", " ", TAG_RE.sub(" ", inner)).strip(" \xa0-–.")
        low = label.lower()
        href_abs = urllib.parse.urljoin(base_url, href)
        if "/uploads/" not in href_abs or not UPLOAD_RE.search(href_abs):
            continue  # anything outside the GE-2024 upload window is junk
        accepted = False
        if NUM_START_RE.match(label) or FORM20_RE.search(label):
            accepted = True
        elif AC_PREFIX_RE.match(label):
            accepted = True
        elif CLICK_RE.search(label) or (low.startswith(VIEW_WORDS) and "form" not in low):
            label = row_label(html, m.start()) or "view"
            accepted = True
        elif NAME_RE.match(label) and UPLOAD_STRICT_RE.search(href_abs) \
                and not STOP_WORDS.search(label):
            accepted = True  # bare AC name (Fatehpur 2025/03, Unnao)
        if accepted and not STOP_WORDS.search(label):
            found.append({"ac_label": label, "pdf_url": href_abs})
    return found


def safe_name(district: str, label: str, pdf_url: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9()-]+", "_", label)[:60].strip("_-")
    if not safe:
        safe = Path(urllib.parse.urlparse(pdf_url).path).stem
    return f"{district}__{safe}.pdf"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PAGES.mkdir(exist_ok=True)
    districts = json.load(open(DISTRICTS_JSON))

    cached = {p.name for p in PAGES.glob("*.htm")}

    # --- B: extra pages under non-colliding cache names -------------------
    for district, page_url in EXTRA_PAGES.items():
        safe = re.sub(r"[^A-Za-z0-9]+", "_", district).lower()
        cache = PAGES / f"{safe}__extra.htm"
        if not cache.exists():
            ts = get_snap(page_url)
            if not ts:
                print(f"extra: {district} — no snapshot")
                time.sleep(1.0)
                continue
            raw = fetch(WB.format(ts=ts, url=page_url), DELAY_WB)
            time.sleep(DELAY_WB)
            if raw is None:
                print(f"extra: {district} — fetch failed")
                continue
            cache.write_bytes(raw)
            print(f"extra: {district} -> cached ({len(raw)//1024} KB)")

    # --- C: retry districts whose page was never cached -------------------
    for d in districts:
        if not d["captures"]:
            continue
        safe = re.sub(r"[^A-Za-z0-9]+", "_", d["district"]).lower()
        if f"{safe}.htm" in cached:
            continue
        done = False
        for cap in reversed(d["captures"][-3:]):
            raw = fetch(WB.format(ts=cap["ts"], url=cap["url"]), DELAY_WB)
            time.sleep(DELAY_WB)
            if raw is None:
                continue
            (PAGES / f"{safe}.htm").write_bytes(raw)
            print(f"retry: {d['district']} -> cached ts={cap['ts']} ({len(raw)//1024} KB)")
            done = True
            break
        if not done:
            print(f"retry: {d['district']} — all captures failed")

    # --- A: extraction over all caches ------------------------------------
    old = pd.read_csv(MANIFEST)
    seen_urls = set(old["pdf_url"])
    rows: list[dict] = []
    for p in sorted(PAGES.glob("*.htm")):
        html = p.read_text(encoding="utf-8", errors="replace")
        stem = p.stem.removesuffix("__extra")
        district = stem
        match = [d for d in districts
                 if re.sub(r"[^A-Za-z0-9]+", "_", d["district"]).lower() == stem]
        if match:
            district = match[0]["district"]
        base = f"https://{stem.replace('_', '')}.nic.in/"
        for hit in extract_links(html, base):
            if hit["pdf_url"] in seen_urls:
                continue
            seen_urls.add(hit["pdf_url"])
            rows.append({"district": district, **hit})

    man = pd.concat([old, pd.DataFrame(rows)], ignore_index=True)
    man = man.drop_duplicates(subset=["pdf_url"]).reset_index(drop=True)
    print(f"new links: {len(rows)}, manifest now: {len(man)}")

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
    n_files = len(list(OUT.glob("*.pdf")))
    print(f"done: downloaded={ok}, failed={fail}, already={skip}; files on disk={n_files}")


if __name__ == "__main__":
    main()
