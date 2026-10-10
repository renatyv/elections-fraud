#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрейпер промежуточных результатов выборов в Болгарии
(президентские выборы 25.10.2026, возможен II тур 08.11.2026).

Источник: официальный портал ЦИК https://results.cik.bg/
Механика портала: страницы результатов — статический HTML, который
перегенерируется по мере обработки протоколов СИК; у каждой страницы есть
хэш VERSION ('?v=...'), меняющийся при каждом обновлении данных.

Скрипт:
  1. Автоматически находит портал выборов в индексе https://results.cik.bg/
     (ищет блок «президент … 2026»); можно задать вручную через --base.
  2. Опрашивает страницы tur1/tur2 (rezultati + aktivnost) и индексы
     machine/data.js, protokoli/data.js (счётчик обработанных машинных
     протоколов — обновляется чаще HTML).
  3. Сохраняет сырые снапшоты в data/raw/<метка_времени>/ и дополняет
     CSV-таймлайны в data/ (results/turnout/stats/machine).

Запуск:
  разовый:   ./scrape_cik.py --once
  цикл 15мин: ./scrape_cik.py --loop              (по умолчанию interval=900 c)
  цикл с иным интервалом: ./scrape_cik.py --loop --interval 300
  вручную указать портал (напр. для теста на выборах 2021):
  ./scrape_cik.py --once --base https://results.cik.bg/pvrns2021/

Cloudflare: сайты ЦИК периодически отдают managed challenge. Применяется
каскад: requests -> curl_cffi (impersonate chrome) -> cloudscraper,
с повторами. Файлы *.js (data.js) отдаются обычно без challenge.
"""

import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

RESULTS_INDEX = "https://results.cik.bg/"
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

CHALLENGE_MARKERS = ("Just a moment", "cf-chl", "challenge-platform",
                     "Enable JS and cookies", "_cf_chl_opt")


# ---------------------------------------------------------------- fetcher --

class Fetcher:
    """Каскадный HTTP-клиент: requests -> curl_cffi -> cloudscraper."""

    def __init__(self, timeout=30, retries=3):
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT,
                                     "Accept-Language": "bg,en;q=0.9,ru;q=0.8"})
        self._curl_cffi = None      # ленивые импорты опциональных бэкендов
        self._cloudscraper = None
        self._backend = "requests"  # последний успешный бэкенд

    # -- отдельные бэкенды ---------------------------------------------
    def _get_requests(self, url):
        r = self.session.get(url, timeout=self.timeout)
        return r.status_code, r.content

    def _get_curl_cffi(self, url):
        if self._curl_cffi is None:
            from curl_cffi import requests as cffi_requests
            self._curl_cffi = cffi_requests
        r = self._curl_cffi.get(url, impersonate="chrome", timeout=self.timeout,
                                headers={"User-Agent": USER_AGENT})
        return r.status_code, r.content

    def _get_cloudscraper(self, url):
        if self._cloudscraper is None:
            import cloudscraper
            self._cloudscraper = cloudscraper.create_scraper(
                browser={"browser": "chrome", "platform": "darwin", "desktop": True})
        r = self._cloudscraper.get(url, timeout=self.timeout + 10)
        return r.status_code, r.content

    def _looks_like_challenge(self, body):
        if len(body) < 6000:
            head = body[:3000]
            return any(m.encode() in head for m in CHALLENGE_MARKERS)
        return False

    # -- публичный метод -------------------------------------------------
    def get(self, url):
        """Возвращает (status, bytes). Бросает RuntimeError после всех ретраев."""
        backends = [self._get_requests]
        # опциональные бэкенды подключаются, если пакет установлен
        try:
            import curl_cffi  # noqa: F401
            backends.append(self._get_curl_cffi)
        except ImportError:
            pass
        try:
            import cloudscraper  # noqa: F401
            backends.append(self._get_cloudscraper)
        except ImportError:
            pass

        # начинаем с последнего успешного бэкенда
        order = ([self._backend] +
                 [b for b in ("requests", "curl_cffi", "cloudscraper") if b != self._backend])
        by_name = {"requests": self._get_requests,
                   "curl_cffi": self._get_curl_cffi,
                   "cloudscraper": self._get_cloudscraper}

        last_err = None
        for attempt in range(self.retries):
            for name in order:
                fn = by_name.get(name)
                if fn is None or fn not in backends:
                    continue
                try:
                    status, body = fn(url)
                except Exception as e:            # сетевая ошибка — следующий бэкенд
                    last_err = f"{name}: {e}"
                    continue
                if status == 200 and not self._looks_like_challenge(body):
                    self._backend = name
                    return status, body
                last_err = f"{name}: HTTP {status}" + (
                    " (cloudflare challenge)" if self._looks_like_challenge(body) else "")
                if status == 404:
                    return status, body           # 404 — это валидный ответ
            time.sleep(2 * (attempt + 1))          # пауза перед повторной попыткой
        raise RuntimeError(f"не удалось получить {url}: {last_err}")


# --------------------------------------------------------------- discovery --

def discover_portal(fetcher, log):
    """Ищет в индексе results.cik.bg блок президентских выборов 2026.

    Возвращает базовый URL портала (напр. https://results.cik.bg/pvr202610/)
    или None, если портал ещё не опубликован.
    """
    status, body = fetcher.get(RESULTS_INDEX)
    if status != 200:
        log(f"индекс {RESULTS_INDEX}: HTTP {status}")
        return None
    soup = BeautifulSoup(body, "lxml")

    # блок выбора = заголовок h2 («25 октомври 2026 Избори за президент…»)
    # + ссылки до следующего заголовка
    for h in soup.find_all(["h2", "h3"]):
        text = h.get_text(" ", strip=True).lower()
        if "президент" in text and "2026" in text:
            links = []
            for el in h.next_elements:
                if getattr(el, "name", None) in ("h2", "h3"):
                    break
                if getattr(el, "name", None == None):  # noqa: E711
                    continue
                if el.name == "a" and el.get("href"):
                    links.append(el["href"])
                elif el.name in ("p", "div") and links and el.name == "p":
                    break
            # ссылка «Резултати от гласуването» -> базовый URL портала
            for href in links:
                if "rezultati" in href:
                    base = href.split("rezultati")[0]
                    if base.startswith("/"):
                        base = RESULTS_INDEX.rstrip("/") + base
                    return base.rstrip("/") + "/"
    return None


# ----------------------------------------------------------------- parsing --

STATUS_RE = re.compile(
    r"Данни\s+към\s+(\d{1,2}:\d{2})\s+на\s+(\d{2}\.\d{2}\.\d{4})"
    r"(?:\s+г\.?)?\s+при\s+обработени\s+([\d.,]+)\s*%", re.U)
VERSION_RE = re.compile(r"VERSION\s*=\s*'(\?v=[0-9a-f]+)'")


def _num(text):
    """"1 322 385" (с \xa0) -> 1322385; "49.42%" -> 49.42."""
    text = text.replace("\xa0", "").replace(" ", "").strip()
    m = re.search(r"-?\d+(?:[.,]\d+)?", text)
    if not m:
        return None
    val = m.group(0).replace(",", ".")
    try:
        return int(val) if "." not in val else float(val)
    except ValueError:
        return None


def _header_cells(table):
    first = table.find("tr")
    if first is None:
        return []
    return _header_cells_row(first)


def _header_cells_row(tr):
    return [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]


def parse_results_page(html):
    """Парсит страницу rezultati/index.html.

    Возвращает dict: version, asof, processed_pct, candidates[], parties[],
    stats{} (метрики протокола: избиратели, гласували, действителни…).
    """
    soup = BeautifulSoup(html, "lxml")
    out = {"version": None, "asof": None, "processed_pct": None,
           "candidates": [], "parties": [], "stats": {}}

    m = VERSION_RE.search(html)
    out["version"] = m.group(1) if m else None
    m = STATUS_RE.search(html)
    if m:
        out["asof"] = f"{m.group(2)} {m.group(1)}"
        out["processed_pct"] = _num(m.group(3))

    for table in soup.find_all("table", class_="table-results"):
        header = " | ".join(_header_cells(table))
        is_presidential = "Кандидатска двойка" in header
        is_party = "Партия, Коалиция" in header
        if not (is_presidential or is_party):
            continue
        for tr in table.find_all("tr"):
            if "graph-row" in (tr.get("class") or []):
                continue
            cells = tr.find_all("td")
            if len(cells) < 4:
                continue
            no = _num(cells[0].get_text())
            # имя в <strong>, выдвинувшая организация после <br/>
            strong = cells[1].find("strong")
            name = strong.get_text(" ", strip=True) if strong else cells[1].get_text(" ", strip=True)
            nominator = ""
            if strong:
                rest = cells[1].get_text(" ", strip=True).replace(name, "", 1).strip(" -–—")
                nominator = re.sub(r"^(ИК за|ИК)\s*", "", rest).strip()
            votes = cells[2].get("data-sort") or _num(cells[2].get_text())
            pct = cells[3].get("data-sort") or _num(cells[3].get_text())
            row = {"no": no, "name": name, "nominator": nominator,
                   "votes": int(votes) if votes not in (None, "") else None,
                   "pct": float(pct) if pct not in (None, "") else None}
            (out["candidates"] if is_presidential else out["parties"]).append(row)

    # таблицы метрик протокола: «ПРИ СЪСТАВЯНЕ НА ПРОТОКОЛА…»
    for table in soup.find_all("table"):
        if "table-results" in (table.get("class") or []):
            continue
        txt = table.get_text(" ", strip=True)
        if "ПРИ СЪСТАВЯНЕ НА ПРОТОКОЛА" not in txt:
            continue
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) >= 2:
                label = cells[0].get_text(" ", strip=True)
                label = re.sub(r"\s+", " ", label).strip()
                if label and not label.startswith("ПРИ СЪСТАВЯНЕ"):
                    val = _num(cells[-1].get_text())
                    if val is not None:
                        out["stats"][label] = val
    return out


def parse_aktivnost_page(html):
    """Явка по часам: таблица Час / Избиратели / Гласували / Процент.

    Заголовки могут быть как в первой строке таблицы (pe202604),
    так и во второй — под строкой с названием выборов (pvrns2021).
    """
    soup = BeautifulSoup(html, "lxml")
    rows = []
    time_re = re.compile(r"^\d{1,2}:\d{2}")
    for table in soup.find_all("table"):
        trs = table.find_all("tr")
        head = " ".join(
            " ".join(_header_cells_row(tr)) for tr in trs[:2])
        if "Час" not in head or "Гласували" not in head:
            continue
        for tr in trs:
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if len(cells) >= 4 and time_re.match(cells[0]):
                rows.append({"hour": cells[0], "voters": _num(cells[1]),
                             "voted": _num(cells[2]), "pct": _num(cells[3])})
    return rows


def count_machine_protocols(data_js_text):
    """Считает число секций с машинными протоколами из machine/data.js."""
    m = re.search(r"HAS_MACHINE\s*=\s*(\{.*?\})\s*;", data_js_text, re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(1))
        return sum(len(v) for v in obj.values())
    except (json.JSONDecodeError, AttributeError, TypeError):
        # HAS_MACHINE бывает массивом
        try:
            obj = json.loads(m.group(1))
            return len(obj) if isinstance(obj, list) else None
        except Exception:
            return None


# ------------------------------------------------------------------ output --

class Storage:
    def __init__(self, data_dir):
        self.dir = Path(data_dir)
        self.raw_dir = self.dir / "raw"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.dir / "state.json"
        self.state = {}
        if self.state_path.exists():
            try:
                self.state = json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                self.state = {}

    def save_state(self):
        self.state_path.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")

    def append_csv(self, name, fieldnames, rows):
        if not rows:
            return
        path = self.dir / name
        new = not path.exists()
        with path.open("a", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            if new:
                w.writeheader()
            w.writerows(rows)

    def save_raw(self, ts_label, name, body):
        d = self.raw_dir / ts_label
        d.mkdir(parents=True, exist_ok=True)
        (d / name).write_bytes(body)


# ------------------------------------------------------------------ scraping --

def candidate_urls(base, page):
    """Возможные URL страницы page ('rezultati/index.html', 'aktivnost/index.html',
    'machine/data.js') для тура round с учётом обоих известных макетов портала."""
    flat = [f"{base}{page}"]
    for rnd in ("tur1", "tur2"):
        flat.append(f"{base}{rnd}/{page}")
    # dedupe с сохранением порядка
    return list(dict.fromkeys(flat))


def fetch_first(fetcher, urls, log, optional=True):
    for url in urls:
        try:
            status, body = fetcher.get(url)
        except RuntimeError as e:
            log(f"  ! {url}: {e}")
            continue
        if status == 200:
            return url, body
        log(f"  - {url}: HTTP {status}")
    if not optional:
        raise RuntimeError(f"ни один из URL не доступен: {urls}")
    return None, None


def scrape_cycle(fetcher, storage, args, log):
    ts = datetime.now()
    ts_label = ts.strftime("%Y-%m-%d_%H%M%S")
    log(f"=== цикл {ts_label} ===")

    base = args.base
    if base:
        base = base.rstrip("/") + "/"
    else:
        base = storage.state.get("portal_base")
        if not base or args.redetect:
            found = discover_portal(fetcher, log)
            if found:
                log(f"портал выборов найден: {found}")
                storage.state["portal_base"] = found
                storage.state["portal_found_at"] = ts_label
                base = found
            elif base:
                log(f"портал 2026 в индексе ещё нет, использую последний: {base}")
            else:
                log("портал президентских выборов 2026 ещё не опубликован "
                    "в индексе results.cik.bg; повторю проверку в следующем цикле")
                return

    results_rows, turnout_rows, stats_rows, machine_rows = [], [], [], []
    rounds = args.rounds.split(",") if args.rounds else ["tur1", "tur2"]
    summary_lines = []
    seen_urls = set()          # чтобы не качать один файл дважды за цикл
                                              # (плоские порталы без tur1/tur2)

    for rnd in rounds:
        # --- результаты ------------------------------------------------
        rurls = ([f"{base}{rnd}/rezultati/index.html"] +
                 ([f"{base}rezultati/index.html"] if rnd == "tur1" else []))
        rurls = [u for u in rurls if u not in seen_urls]
        rurl, rbody = fetch_first(fetcher, rurls, log)
        if rurl and rbody:
            seen_urls.add(rurl)
            parsed = parse_results_page(rbody.decode("utf-8", "replace"))
            version = parsed["version"] or ""
            storage.save_raw(ts_label, f"{rnd}_rezultati.html", rbody)
            changed = storage.state.get(f"version_{rurl}") != version
            storage.state[f"version_{rurl}"] = version
            tag = "" if changed else " (без изменений)"
            log(f"  {rnd} результаты: {parsed['asof'] or 'финал'}, "
                f"обработено {parsed['processed_pct'] if parsed['processed_pct'] is not None else '?'}%"
                f"{tag}")
            if parsed["candidates"]:
                top = sorted(parsed["candidates"], key=lambda c: -(c["pct"] or 0))[:5]
                for c in top:
                    summary_lines.append(
                        f"  {rnd}: {c['pct'] if c['pct'] is not None else '?':>6}%  "
                        f"{c['votes'] or 0:>10}  {c['name']}")
                for c in parsed["candidates"]:
                    results_rows.append({
                        "fetch_ts": ts_label, "round": rnd,
                        "data_asof": parsed["asof"] or "",
                        "processed_pct": parsed["processed_pct"] or "",
                        "version": version, "cand_no": c["no"] or "",
                        "candidate": c["name"], "nominator": c["nominator"],
                        "votes": c["votes"] or "", "pct": c["pct"] or ""})
            for c in parsed["parties"]:
                results_rows.append({
                    "fetch_ts": ts_label, "round": rnd + "_party",
                    "data_asof": parsed["asof"] or "",
                    "processed_pct": parsed["processed_pct"] or "",
                    "version": version, "cand_no": c["no"] or "",
                    "candidate": c["name"], "nominator": c["nominator"],
                    "votes": c["votes"] or "", "pct": c["pct"] or ""})
            for label, val in parsed["stats"].items():
                stats_rows.append({"fetch_ts": ts_label, "round": rnd,
                                   "label": label, "value": val})
        else:
            log(f"  {rnd}: страница результатов недоступна")

        # --- явка --------------------------------------------------------
        aurls = ([f"{base}{rnd}/aktivnost/index.html"] +
                 ([f"{base}aktivnost/index.html"] if rnd == "tur1" else []))
        aurls = [u for u in aurls if u not in seen_urls]
        aurl, abody = fetch_first(fetcher, aurls, log)
        if aurl and abody:
            seen_urls.add(aurl)
            rows = parse_aktivnost_page(abody.decode("utf-8", "replace"))
            storage.save_raw(ts_label, f"{rnd}_aktivnost.html", abody)
            if rows:
                last = rows[-1]
                log(f"  {rnd} явка: {last['hour']} -> {last['pct']}%")
            for r in rows:
                turnout_rows.append({"fetch_ts": ts_label, "round": rnd,
                                     "hour": r["hour"], "voters": r["voters"] or "",
                                     "voted": r["voted"] or "", "pct": r["pct"] or ""})

        # --- машинные протоколы (обновляются чаще HTML) -------------------
        murls = [u for u in (f"{base}{rnd}/machine/data.js", f"{base}machine/data.js")
                 if u not in seen_urls]
        murl, mbody = fetch_first(fetcher, murls, log)
        if murl and mbody:
            seen_urls.add(murl)
            n = count_machine_protocols(mbody.decode("utf-8", "replace"))
            storage.save_raw(ts_label, f"{rnd}_machine_data.js", mbody)
            if n is not None:
                prev = storage.state.get("machine_sections")
                storage.state["machine_sections"] = n
                log(f"  {rnd} машинных протоколов по секциям: {n}"
                    + (f" (+{n - prev})" if isinstance(prev, int) and n >= prev else ""))
                machine_rows.append({"fetch_ts": ts_label, "round": rnd,
                                     "sections": n})

    storage.append_csv("results_timeline.csv",
                       ["fetch_ts", "round", "data_asof", "processed_pct", "version",
                        "cand_no", "candidate", "nominator", "votes", "pct"],
                       results_rows)
    storage.append_csv("turnout_timeline.csv",
                       ["fetch_ts", "round", "hour", "voters", "voted", "pct"],
                       turnout_rows)
    storage.append_csv("stats_timeline.csv",
                       ["fetch_ts", "round", "label", "value"], stats_rows)
    storage.append_csv("machine_sections_timeline.csv",
                       ["fetch_ts", "round", "sections"], machine_rows)
    storage.state["last_cycle"] = ts_label
    storage.save_state()

    if summary_lines:
        log("текущий топ (первые 5):")
        for line in summary_lines[:10]:
            log(line)


def main():
    ap = argparse.ArgumentParser(
        description="Скрейпер промежуточных результатов выборов ЦИК Болгарии")
    ap.add_argument("--base", help="базовый URL портала выборов "
                    "(по умолчанию — автоопределение из индекса results.cik.bg)")
    ap.add_argument("--rounds", default="tur1,tur2",
                    help="туры через запятую (по умолчанию tur1,tur2)")
    ap.add_argument("--loop", action="store_true", help="режим цикла")
    ap.add_argument("--interval", type=int, default=900,
                    help="интервал опроса в секундах (по умолчанию 900 = 15 мин)")
    ap.add_argument("--once", action="store_true", help="один цикл и выход")
    ap.add_argument("--redetect", action="store_true",
                    help="заново выполнить автоопределение портала")
    ap.add_argument("--data-dir", default="data", help="каталог данных (по умолчанию data/)")
    ap.add_argument("--timeout", type=int, default=30, help="HTTP-таймаут, с")
    args = ap.parse_args()
    if not (args.loop or args.once):
        args.loop = True  # по умолчанию — цикл

    log_path = Path("scrape.log")

    def log(msg):
        line = f"{datetime.now().strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    fetcher = Fetcher(timeout=args.timeout)
    storage = Storage(args.data_dir)
    log(f"старт: loop={args.loop} interval={args.interval}s data={args.data_dir}")

    while True:
        try:
            scrape_cycle(fetcher, storage, args, log)
        except KeyboardInterrupt:
            log("остановлено пользователем")
            sys.exit(0)
        except Exception as e:
            log(f"! ошибка цикла: {e} (продолжаю)")
        if not args.loop:
            break
        log(f"сон {args.interval} c …")
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            log("остановлено пользователем")
            sys.exit(0)


if __name__ == "__main__":
    main()
