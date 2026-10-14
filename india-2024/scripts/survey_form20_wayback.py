#!/usr/bin/env python3
"""Scout Form 20 (booth-level results) in the Wayback Machine across state CEO domains.

Form 20 holds the final booth-level results for each assembly segment:
electors and votes of every candidate at every polling station. State CEO
(Chief Electoral Officer) websites publish them as PDF/Excel. The live
.gov.in sites are unreachable from our network, so we look for snapshots
on web.archive.org.

The script queries the CDX index for each domain, filters URLs containing
'form20' with 2024/2025 timestamps, and measures coverage. The result is a table.

Run:     uv run python survey_form20_wayback.py
Output:  ../data/form20/form20_wayback_survey.csv
"""
from __future__ import annotations

import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "data" / "form20" / "form20_wayback_survey.csv"

# state CEO domains (old .nic.in and new .gov.in) + state names
DOMAINS = [
    ("Andhra Pradesh", "ceoandhra.nic.in"),
    ("Andhra Pradesh (new)", "ceoandhra.eci.gov.in"),
    ("Arunachal Pradesh", "ceoarunachal.nic.in"),
    ("Assam", "ceoassam.nic.in"),
    ("Bihar", "ceobihar.nic.in"),
    ("Chhattisgarh", "ceochhattisgarh.nic.in"),
    ("Goa", "ceogoa.gov.in"),
    ("Gujarat", "ceogujarat.nic.in"),
    ("Haryana", "ceoharyana.nic.in"),
    ("Himachal Pradesh", "himachal.nic.in"),
    ("Jharkhand", "ceojharkhand.nic.in"),
    ("Karnataka (old)", "ceokarnataka.kar.nic.in"),
    ("Karnataka (new)", "ceo.karnataka.gov.in"),
    ("Kerala", "ceokerala.gov.in"),
    ("Madhya Pradesh", "ceomadhyapradesh.nic.in"),
    ("Maharashtra", "ceo.maharashtra.gov.in"),
    ("Manipur", "ceomanipur.nic.in"),
    ("Meghalaya", "ceomeghalaya.gov.in"),
    ("Mizoram", "ceomizoram.nic.in"),
    ("Nagaland", "cenagasland.nic.in"),
    ("Odisha", "ceoodisha.nic.in"),
    ("Punjab", "ceopunjab.gov.in"),
    ("Rajasthan", "ceorajasthan.nic.in"),
    ("Sikkim", "ceosikkim.nic.in"),
    ("Tamil Nadu", "elections.tn.gov.in"),
    ("Telangana", "ceotelangana.nic.in"),
    ("Tripura", "ceotripura.nic.in"),
    ("Uttar Pradesh", "ceouttarpradesh.nic.in"),
    ("Uttarakhand", "ceouttarakhand.gov.in"),
    ("West Bengal", "ceowestbengal.nic.in"),
    ("NCT Delhi", "ceodelhi.gov.in"),
    ("Jammu & Kashmir", "ceojk.nic.in"),
]

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def cdx_count(domain: str) -> tuple[int, int, list[str]]:
    """(total form20 URLs, of them with 2024+ snapshots, example URLs)."""
    url = (
        "http://web.archive.org/cdx/search/cdx"
        f"?url={domain}*&output=text&fl=timestamp,original,statuscode"
        "&collapse=urlkey&limit=3000"
    )
    try:
        r = requests.get(url, headers=UA, timeout=120)
        lines = r.text.splitlines()
    except requests.RequestException:
        return (0, 0, [])
    total, recent, examples = 0, 0, []
    for ln in lines:
        parts = ln.split(" ")
        if len(parts) < 3:
            continue
        ts, orig, status = parts[0], parts[1], parts[2]
        low = orig.lower()
        if "form20" not in low and "form-20" not in low and "form_20" not in low:
            continue
        if any(x in low for x in (".jpg", ".png", ".gif", ".css", ".js")):
            continue
        total += 1
        if ts >= "20240601" and status == "200":
            recent += 1
            if len(examples) < 3:
                examples.append(f"{ts} {orig}")
    return (total, recent, examples)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for state, domain in DOMAINS:
        total, recent, examples = cdx_count(domain)
        rows.append((state, domain, total, recent, " | ".join(examples)))
        print(f"{state:25s} {domain:28s} form20_urls={total:4d} captured_2024+={recent:4d}", flush=True)
        time.sleep(2)
    with OUT.open("w") as f:
        f.write("state;domain;form20_urls;captured_2024plus;examples\n")
        for r in rows:
            f.write(";".join(str(x) for x in r) + "\n")
    print(f"\nsaved -> {OUT}")


if __name__ == "__main__":
    main()
