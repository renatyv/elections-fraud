"""Capture CIK totals and numeric section protocols; validate before forensics.

Run with bulgaria-oct-2026/.venv/bin/python. Cached HTML is never overwritten.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import threading

from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from scrape_cik import Fetcher, parse_results_page

URL = "https://results.cik.bg/pvr202610/"
CACHE = BASE / "data" / "official_20261027"
LOCAL = threading.local()


@dataclass
class Protocol:
    section: str
    district: str
    form: int
    registered: int
    added: int
    voted: int
    nobody: int
    votes: dict[str, int]
    source: str


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


def parse_protocol(body: bytes, section: str, district: str, form: int, source: str) -> Protocol:
    soup = BeautifulSoup(body, "lxml")
    text = soup.get_text(" ", strip=True)
    if f"№ {section}" not in text:
        raise ValueError(f"Wrong section identity: {source}")
    registered = added = voted = nobody = None
    votes: dict[str, int] = {}
    for row in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"], recursive=False)]
        if len(cells) < 2:
            continue
        label, raw = cells[0], re.sub(r"\s", "", cells[-1])
        if not raw.isdigit():
            continue
        value = int(raw)
        if "при предаването му на СИК" in label:
            registered = value
        elif "вписани в допълнителната" in label:
            added = value
        elif "според положените подписи" in label:
            voted = value
        elif "действителните гласове" in label and "Не подкрепям никого" in label:
            nobody = value
        elif len(cells) == 3 and label.isdigit():
            if label in votes:
                raise ValueError(f"Duplicate candidate: {source}")
            votes[label] = value
    if None in (registered, added, voted, nobody) or set(votes) != {str(i) for i in range(1, 28)}:
        raise ValueError(f"Incomplete protocol schema: {source}")
    assert registered is not None and added is not None and voted is not None and nobody is not None
    return Protocol(section, district, form, registered, added, voted, nobody, votes, source)


def capture_section(job: tuple[str, str, dict[str, int]]) -> Protocol:
    district, suffix, forms = job
    # Aggregate form 0 includes machine totals; form 1 alone may omit candidates.
    key = "0" if "0" in forms else "1"
    section = district + suffix.zfill(7)
    path = f"protokoli/256/{district}/{section}.{key}.html"
    return parse_protocol(fetch(path), section, district, forms[key], URL + path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sections", action="store_true", help="also capture all indexed section protocols")
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    national = parse_results_page(fetch("rezultati/index.html").decode())
    if len(national["candidates"]) != 28 or national["processed_pct"] != 100:
        raise ValueError("Expected 27 candidate pairs plus nobody at 100% processed")
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
        totals = {str(i): sum(p.votes[str(i)] for p in protocols) for i in range(1, 28)}
        totals["-"] = sum(p.nobody for p in protocols)
        differences = {str(r["no"] or "-"): totals[str(r["no"] or "-")] - r["votes"] for r in national["candidates"]}
        summary["section_minus_national"] = differences
        summary["sections_reconcile"] = all(v == 0 for v in differences.values())
    (CACHE / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k not in ("national", "balance_discrepancies")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
