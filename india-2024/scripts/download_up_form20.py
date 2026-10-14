#!/usr/bin/env python3
"""Сбор побоотлевых итогов GE-2024 Уттар-Прадеш (Form 20, PDF со сканов).

Цепочка: индекс ceouttarpradesh.nic.in/Form20_2024.aspx (архив Wayback) ->
страницы районов (40/68 сохранены в Wayback) -> PDF на cdn.s3waas.gov.in,
который доступен НАПРЯМУЮ (geo-бана нет, в отличие от *.nic.in).

Скрипт:
  1. берёт сохранённые страницы районов из Wayback (id_, последний снапшот);
  2. находит ссылки-якоря "NN-ACNAME" на PDF (uploads/2024/0X/...pdf);
  3. докапливает страницы "part-2/part-3", если на них есть ссылки;
  4. качает PDF напрямую с cdn.s3waas.gov.in (тайп-аут, рэтраи);
  5. складывает в data/form20/up/<district>/<ac_label>.pdf + manifest.csv.

Запуск:  cd india-2024 && uv run python scripts/download_up_form20.py
Выход:   data/form20/up/*.pdf, data/form20/up_manifest.csv
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
DISTRICTS_JSON = FORM20 / "up_form20_districts_cdx.json"

UA = {"User-Agent": "Mozilla/5.0 (election-forensics-research)"}
WB = "https://web.archive.org/web/{ts}id_/{url}"
DELAY_WB = 3.0   # Wayback
DELAY_CDN = 0.7  # s3waas CDN

# якорь вида "01-BEHAT" / "43 Siwalkhas (सिवालखास)" -> PDF; метка с вложенными тегами
AC_LINK_RE = re.compile(
    r"<a[^>]+href=[\"']([^\"']+\.pdf)[\"'][^>]*>(.*?)</a>",
    re.I | re.S,
)
NUM_START_RE = re.compile(r"^\d{1,3}\s*[-–.]\s*\S|^\d{1,3}\s+\S")
FORM20_RE = re.compile(r"form\s*-?\s*20", re.I)
VIEW_WORDS = ("view", "download", "pdf", "click")
NAME_RE = re.compile(r"^[A-Za-z\u0900-\u097F][A-Za-z\u0900-\u097F .()]{1,39}$")
STOP_WORDS = re.compile(r"gazette|holiday|guide|tender|budget|calendar|list of", re.I)
TAG_RE = re.compile(r"<[^>]+>")

# страницы-продолжения/альтернативные страницы Form 20, найденные в кэше part-1
EXTRA_PAGES: dict[str, str] = {
    "Jaunpur": "https://jaunpur.nic.in/lok-sabha-general-election-2024-praroop-20part-2",
    "Mau": "https://mau.nic.in/en/format-20-lok-sabha-general-election-2024/",
    "Fatehpur": "https://fatehpur.nic.in/lok-sabha-general-election-2024-election-result-form-20/",
    "Maharajganj": "https://maharajganj.nic.in/lok-sabha-general-election-2024-form-20-part-1/",
    "Unnao": "https://unnao.nic.in/general-lok-sabha-election-2024-33-unnao-form-20/",
    "Rae Bareli": "https://raebareli.nic.in/lok-sabha-general-election-2024-praroop-20-part-1/",
    "Hapur": "https://hapur.nic.in/lok-sabha-general-election-2024-format-20-part-1/",
}
# страницы-продолжения того же района: part-2/3, слаги с "-2"/"prarup" на том же хосте
PART_RE = re.compile(
    r"href=[\"'](https?://[^\"']*\.nic\.in/[^\"']*(?:part-[2-9]|prarup[^\"']*-[2-9]|format-20[^\"']*))/?[\"']",
    re.I,
)


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
    """Ближайший снапшот со статусом 200 через availability API."""
    api = "http://archive.org/wayback/available?url=" + urllib.parse.quote(url, safe="")
    try:
        r = requests.get(api, headers=UA, timeout=30).json()
        s = r.get("archived_snapshots", {}).get("closest", {})
        if s.get("available") and str(s.get("status")) == "200":
            return s["timestamp"]
    except requests.RequestException:
        pass
    return None


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pages_dir = FORM20 / "up_pages"
    pages_dir.mkdir(exist_ok=True)
    districts = json.load(open(DISTRICTS_JSON))
    have = [d for d in districts if d["captures"]]
    print(f"районов с архивными страницами: {len(have)}/{len(districts)}")

    jobs: list[tuple[str, str, str]] = []  # district, ts, page_url
    for d in have:
        jobs.append((d["district"], d["captures"][-1]["ts"], d["captures"][-1]["url"]))
    for district, page_url in EXTRA_PAGES.items():
        ts = get_snap(page_url)
        if ts:
            jobs.append((district, ts, page_url))
            print(f"extra: {district} -> {ts}")
        else:
            print(f"extra: {district} — снапшота нет")
        time.sleep(1.0)
    print(f"страниц к обработке: {len(jobs)}")

    rows: list[dict] = []
    seen_pdfs: set[str] = set()
    for i, (district, ts, page_url) in enumerate(jobs, 1):
        snap = {"ts": ts, "url": page_url}
        safe = re.sub(r"[^A-Za-z0-9]+", "_", district).lower()
        cache = pages_dir / f"{safe}.htm"
        if cache.exists():
            html = cache.read_text(encoding="utf-8", errors="replace")
        else:
            raw = fetch(WB.format(ts=snap["ts"], url=snap["url"]), DELAY_WB)
            time.sleep(DELAY_WB)
            if raw is None:
                print(f"[{i}/{len(have)}] PAGE FAIL {district}", flush=True)
                continue
            cache.write_bytes(raw)
            html = raw.decode("utf-8", errors="replace")
        n_found = 0
        for m in AC_LINK_RE.finditer(html):
            href, inner = m.group(1), m.group(2)
            label = re.sub(r"\s+", " ", TAG_RE.sub(" ", inner)).strip(" \xa0-–.")
            low = label.lower()
            if NUM_START_RE.match(label) or FORM20_RE.search(label):
                pass
            elif low.startswith(VIEW_WORDS) and "form" not in low:
                # метки "View"/"Download File": имя АС из окружающей строки таблицы
                tr0 = html.rfind("<tr", 0, m.start())
                tr1 = html.find("</tr>", m.start())
                if tr0 != -1 and tr1 != -1:
                    row_txt = re.sub(r"\s+", " ", TAG_RE.sub(" ", html[tr0:tr1])).strip()
                    row_txt = re.sub(r"^(?:tr|tbody|thead)?[^A-Za-z0-9\u0900-\u097F]*", "", row_txt, flags=re.I)
                    label = f"row[{row_txt[:60]}]" if row_txt else "row[?]"
                else:
                    label = "view"
            elif NAME_RE.match(label) and "/uploads/2024/09/" in href and not STOP_WORDS.search(label):
                pass  # голое имя АС, напр. "Bangermau" (Unnao); 09 = месяц выкладки Form 20
            else:
                continue
            href = urllib.parse.urljoin(snap["url"], href)
            if "/uploads/" not in href:
                continue
            if href in seen_pdfs:
                continue
            seen_pdfs.add(href)
            rows.append({"district": district, "ac_label": label, "pdf_url": href})
            n_found += 1
        # страницы-продолжения (part-2 и т.п.) — для будущего расширения
        extra = [u for u in PART_RE.findall(html) if not u.rstrip("/").endswith(("-1", "part-1"))]
        if extra:
            print(f"[{i}/{len(jobs)}] {district}: {n_found} PDF, part-pages: {extra[:3]}", flush=True)
        else:
            print(f"[{i}/{len(jobs)}] {district}: {n_found} PDF", flush=True)

    man = pd.DataFrame(rows)
    man.to_csv(FORM20 / "up_manifest_raw.csv", index=False)
    print(f"всего PDF-ссылок: {len(man)} (уникальных)")

    # скачивание напрямую с CDN
    ok = fail = 0
    for i, r in man.iterrows():
        safe_ac = re.sub(r"[^A-Za-z0-9()-]+", "_", r["ac_label"])[:60]
        dest = OUT / f"{r['district']}__{safe_ac}.pdf"
        if dest.exists() and dest.stat().st_size > 10000:
            ok += 1
            continue
        raw = fetch(r["pdf_url"], DELAY_CDN)
        if raw and raw[:5] == b"%PDF-":
            dest.write_bytes(raw)
            ok += 1
            print(f"PDF [{i+1}/{len(man)}] OK {dest.name} ({len(raw)//1024} КБ)", flush=True)
        else:
            fail += 1
            print(f"PDF [{i+1}/{len(man)}] FAIL {r['ac_label']}", flush=True)
        time.sleep(DELAY_CDN)

    man.to_csv(FORM20 / "up_manifest.csv", index=False)
    print(f"готово: ok={ok}, fail={fail}; manifest -> up_manifest.csv")


if __name__ == "__main__":
    main()
