"""Capture CIK round-2 (tur2, 1 Nov 2026) totals and numeric section protocols.

Same pipeline as check_official_results.py, pointed at the tur2 subtree with
the runoff ballot (candidate pair 4 Gyurov, 25 Yotova, plus "nobody").
Cached HTML is never overwritten. Run with bulgaria-oct-2026/.venv/bin/python.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import threading

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "scripts"))
from scrape_cik import Fetcher, parse_results_page
from check_official_results import Protocol, parse_protocol

URL = "https://results.cik.bg/pvr202610/tur2/"
CACHE = BASE / "data" / "official_20261102_tur2"
EXPECTED = {"4", "25"}  # runoff ballot: Gyurov, Yotova
LOCAL = threading.local()


def fetch(path: str) -> bytes:
    target = CACHE / path
    if target.exists():
        return target.read_bytes()
    if not hasattr(LOCAL, "fetcher"):
        LOCAL.fetcher = Fetcher(timeout=20, retries=1)
    status, body = LOCAL.fetcher.get(URL + path)
    if status != 200:
        raise ValueError(f"HTTP {status}: {URL + path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    return body


def capture_section(job: tuple[str, str, dict[str, int]]) -> Protocol:
    district, suffix, forms = job
    # Aggregate form 0 includes machine totals; form 1 alone may omit candidates.
    key = "0" if "0" in forms else "1"
    section = district + suffix.zfill(7)
    path = f"protokoli/256/{district}/{section}.{key}.html"
    return parse_protocol(fetch(path), section, district, forms[key], URL + path,
                          expected=EXPECTED)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sections", action="store_true", help="also capture all indexed section protocols")
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    national = parse_results_page(fetch("rezultati/index.html").decode())
    if len(national["candidates"]) != 3 or national["processed_pct"] != 100:
        raise ValueError("Expected 2 runoff pairs plus nobody at 100% processed")
    summary = {"checked_utc": datetime.now(timezone.utc).isoformat(), "source": URL + "rezultati/index.html",
               "national": national, "listed_votes": sum(r["votes"] for r in national["candidates"])}
    index = fetch("protokoli/data.js").decode()
    match = re.search(r"HAS_PROTO\s*=\s*(.*?);", index)
    if not match:
        raise ValueError("Missing protocol index")
    districts = json.loads(match[1])["256"]
    jobs = [(district, suffix, forms) for district, sections in districts.items() for suffix, forms in sections.items()]
    summary["indexed_sections"] = len(jobs)
    if args.sections:
        with ThreadPoolExecutor(max_workers=8) as pool:
            protocols = []
            for i, protocol in enumerate(pool.map(capture_section, jobs), 1):
                protocols.append(protocol)
                if i % 500 == 0:
                    print(f"Captured {i}/{len(jobs)} sections", flush=True)
        (CACHE / "sections.json").write_text(json.dumps([asdict(p) for p in protocols], ensure_ascii=False))
        summary["invalid_balances"] = [p.section for p in protocols if sum(p.votes.values()) + p.nobody > p.voted or p.voted > p.registered + p.added]
        summary["balance_discrepancies"] = [
            {"section": p.section, "source": p.source, "registered_opening": p.registered,
             "added": p.added, "signatures": p.voted, "listed_votes": sum(p.votes.values()) + p.nobody}
            for p in protocols if p.section in summary["invalid_balances"]
        ]
        totals = {cid: sum(p.votes[cid] for p in protocols) for cid in EXPECTED}
        totals["-"] = sum(p.nobody for p in protocols)
        differences = {str(r["no"] or "-"): totals[str(r["no"] or "-")] - r["votes"] for r in national["candidates"]}
        summary["section_minus_national"] = differences
        summary["sections_reconcile"] = all(v == 0 for v in differences.values())
    (CACHE / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k not in ("national", "balance_discrepancies")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
