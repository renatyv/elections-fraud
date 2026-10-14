#!/usr/bin/env python3
"""Разведка Form 20 (поучастковые итоги) в Wayback Machine по доменам CEO штатов.

Form 20 — финальные поучастковые (booth-level) результаты по каждому
ассембли-сегменту: электорат, голоса по каждому кандидату на каждой
избирательной участка. Публикуются сайтами CEO (Chief Electoral Officer)
штатов как PDF/Excel. Живые сайты .gov.in недоступны из нашей сети,
поэтому ищем снимки в web.archive.org.

Скрипт опрашивает CDX-индекс по каждому домену, фильтрует URL с 'form20'
и 2024/2025-ми timestamps, считает покрытие. Результат — таблица.

Запуск:  uv run python survey_form20_wayback.py
Выход:   ../data/form20/form20_wayback_survey.csv
"""
from __future__ import annotations

import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "data" / "form20" / "form20_wayback_survey.csv"

# домены CEO штатов (старые .nic.in и новые .gov.in) + названия штатов
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
    """(всего form20-URL, из них со снапшотами 2024+, примеры URL)."""
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
