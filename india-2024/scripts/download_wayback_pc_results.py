#!/usr/bin/env python3
"""Скачивание финальных результатов Лок Сабха-2024 (PC-уровень, по кандидатам)
из Wayback Machine: страницы results.eci.gov.in/PcResultGenJune2024/ConstituencywiseSXXYY.htm.

Живой портал ECI удалён; в web.archive.org полные итоги каждого из 543 PC
(кандидат / партия / EVM / почтовые / всего / %). Скрипт берёт ПОСЛЕДНИЙ
снапшот со статусом 200 для каждой страницы из локального CDX-дампа,
сохраняет сырые HTML и собирает сводный CSV.

Запуск:  uv run --project ../../analysis-tool python download_wayback_pc_results.py
Выход:   data/wayback/pages_en/*.htm (сырые страницы)
         data/results_pc/eci2024_pc_results.csv (сводная таблица)
         data/results_pc/coverage_report.txt
"""
from __future__ import annotations

import gzip
import io
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
RAW_DIR = DATA / "wayback" / "pages_en"
OUT_DIR = DATA / "results_pc"
CDX = DATA / "wayback" / "cdx_PcResultGenJune2024.tsv"

BASE = "https://web.archive.org/web/{ts}id_/{url}"
UA = {"User-Agent": "election-forensics-research/1.0 (academic; contact: local)"}
DELAY = 3.5  # сек между запросами к Wayback (он душит частые запросы)

PC_RE = re.compile(r"/ConstituencywiseS(\d{2})(\d+)\.htm$")
PC_HEADER_RE = re.compile(
    r"Parliamentary Constituency\s+(\d+)\s*[-–]\s*", re.S
)
PC_HEADER_HI_RE = re.compile(
    r"लोक सभा क्षेत्र\s+(\d+)\s*[-–]\s*", re.S
)


def load_cdx(lang: str = "en") -> dict[str, tuple[str, str]]:
    """URL -> (latest_ts, statuscode) по страницам с кодом 200."""
    best: dict[str, tuple[str, str]] = {}
    for line in CDX.read_text().splitlines():
        parts = line.split(" ")
        if len(parts) < 3:
            continue
        ts, url, status = parts[0], parts[1], parts[2]
        if status != "200":
            continue
        if not PC_RE.search(url):
            continue
        is_hi = "/hi/" in url
        if lang == "hi" and not is_hi:
            continue
        if lang == "en" and is_hi:
            continue
        if url not in best or ts > best[url][0]:
            best[url] = (ts, status)
    return best


def fetch(url_ts: tuple[str, str]) -> bytes | None:
    url, ts = url_ts[0], url_ts[1]
    for attempt in range(3):
        try:
            r = requests.get(BASE.format(ts=ts, url=url), headers=UA, timeout=90)
            if r.status_code == 200:
                raw = r.content
                if raw[:2] == b"\x1f\x8b":
                    raw = gzip.decompress(raw)
                return raw
            time.sleep(2 * (attempt + 1))
        except requests.RequestException:
            time.sleep(2 * (attempt + 1))
    return None


def parse_html(raw: bytes, url: str) -> dict | None:
    try:
        tables = pd.read_html(io.BytesIO(raw))
    except ValueError:
        return None
    if not tables:
        return None
    # таблица результатов — та, где есть столбец "EVM Votes" (EN) или "ईवीएम मत" (hi)
    df = None
    for t in tables:
        cols = [re.sub(r"[\s.।]", "", str(c).lower()) for c in t.columns]
        if any("evm" in c or "ईवीएम" in c for c in cols):
            df = t
            break
    if df is None:
        return None
    text = re.sub(r"<[^>]+>", " ", raw.decode("utf-8", errors="replace"))
    text = re.sub(r"\s+", " ", text)
    m = PC_HEADER_RE.search(text) or PC_HEADER_HI_RE.search(text)
    pc_no, pc_name, state = ("", "", "")
    if m:
        pc_no = int(m.group(1))
        # сегмент заголовка до начала таблицы (маркеры "S.N."/"क्रम"/комментарий)
        seg = text[m.end(): m.end() + 160]
        seg = re.split(r"S\.?\s?N\.?|क्रम|&nbsp;|-->", seg)[0]
        parens = re.findall(r"\(([^()]+)\)", seg)
        if parens:
            state = parens[-1].strip()  # штат — последняя скобка (имя может содержать "(ST)")
            pc_name = seg[: seg.find("(")].strip().rstrip("-– ").strip()
        else:
            pc_name = seg.strip()
    st_code = PC_RE.search(url).group(1)
    return {"state_code": st_code, "state": state, "pc_no": pc_no, "pc_name": pc_name, "table": df}


def main() -> None:
    lang = sys.argv[1] if len(sys.argv) > 1 else "en"
    raw_dir = DATA / "wayback" / ("pages_hi" if lang == "hi" else "pages_en")
    raw_dir.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pages = load_cdx(lang)
    print(f"страниц в CDX со статусом 200 ({lang}): {len(pages)}", flush=True)

    rows: list[pd.DataFrame] = []
    meta: list[dict] = []
    failures: list[str] = []
    for i, (url, (ts, _)) in enumerate(sorted(pages.items()), 1):
        fname = url.rsplit("/", 1)[-1]
        cached = raw_dir / fname
        is_cached = cached.exists() and cached.stat().st_size > 0
        raw = cached.read_bytes() if is_cached else fetch((url, ts))
        if raw is None:
            failures.append(f"{url} {ts} FETCH_FAIL")
            print(f"[{i}/{len(pages)}] FAIL {fname}", flush=True)
            time.sleep(DELAY)
            continue
        if not cached.exists():
            cached.write_bytes(raw)
        parsed = parse_html(raw, url)
        if parsed is None:
            failures.append(f"{url} {ts} PARSE_FAIL")
            print(f"[{i}/{len(pages)}] PARSE_FAIL {fname}", flush=True)
        else:
            t = parsed.pop("table")
            t.columns = [str(c).strip() for c in t.columns]
            t.insert(0, "pc_no", parsed["pc_no"])
            t.insert(0, "pc_name", parsed["pc_name"])
            t.insert(0, "state", parsed["state"])
            t.insert(0, "state_code", parsed["state_code"])
            t.insert(0, "src_url", url)
            rows.append(t)
            meta.append(parsed)
            print(f"[{i}/{len(pages)}] OK {fname} {parsed['state']} PC{parsed['pc_no']} {parsed['pc_name']} rows={len(t)}", flush=True)
        if not is_cached:
            time.sleep(DELAY)

    if rows:
        all_df = pd.concat(rows, ignore_index=True)
        out_csv = OUT_DIR / ("eci2024_pc_results_hi.csv" if lang == "hi" else "eci2024_pc_results.csv")
        all_df.to_csv(out_csv, index=False)
        print(f"итог: {all_df.shape} -> {out_csv.name}")
    with open(OUT_DIR / f"coverage_report_{lang}.txt", "w") as f:
        f.write(f"pages expected: {len(pages)}\nfailures: {len(failures)}\n")
        f.write("\n".join(failures))
    print(f"failures: {len(failures)} (см. coverage_report_{lang}.txt)")


if __name__ == "__main__":
    sys.exit(main())
