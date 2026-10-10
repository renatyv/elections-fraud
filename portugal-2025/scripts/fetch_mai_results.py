#!/usr/bin/env python3
"""Скачивание официальных результатов выборов с портала MAI/SGMAI
(www.eleicoes.mai.gov.pt) — переиспользуемый скрипт.

Портал — Angular SPA, которая в режиме static-files читает JSON:
  <election>/assets/static/territory-children/territory-children-<KEY>.json
  <election>/assets/static/territory-results/territory-results-<KEY>-<SUF>.json

Скрипт обходит всё дерево территорий (GLOBAL -> округа -> муниципалитеты ->
приходы; для заграничных округов — консульства) и скачивает результаты для
каждого ключа. Существующие файлы пропускаются (можно перезапускать).

Использование:
  python3 fetch_mai_results.py <slug-выборов> [--suffix AR] [--out DIR] [--roots K1,K2]

Примеры slug (см. https://www.eleicoes.mai.gov.pt/):
  legislativas2025 legislativas2024 legislativas2022
  europeias2024 autarquicas2025 presidenciais2026_1S regionais2024 ...

Суффикс файла результатов (тип выборов):
  AR — парламентские (Assembleia da República)
  PE — европейские, PR — президентские
  CM/AM/AF — местные (камара/мун. собрание/приход. собрание; можно через запятую)
Корневые ключи территорий: GLOBAL-990000 (итог), LOCAL-500000 (страна),
FOREIGN-600000/800000/900000 (заграница/Европа/вне Европы).
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

DEFAULT_ROOTS = "GLOBAL-990000,LOCAL-500000,FOREIGN-600000,FOREIGN-800000,FOREIGN-900000"
# пауза между запросами одного потока: CDN блокирует при интенсивном опросе
REQ_DELAY = 0.4
STATIC_FILES = [
    "configurations.json",
    "affluences.json",
    "results-available.json",
    "reference-timestamp.json",
    "links.json",
    "parties/parties.json",
    "candidates/parties-candidates.json",
]


BLOCKED = {"flag": False}


def fetch(url, tries=3):
    """Скачивание через curl: надёжнее ведёт себя с CDN (Akamai), который
    начинает подвешивать соединения при частых запросах.
    При блокировке (Access Denied) — пауза и повтор."""
    import subprocess
    for i in range(tries):
        # если другой поток заметил блокировку — ждём снятия
        while BLOCKED["flag"]:
            time.sleep(15)
        try:
            r = subprocess.run(
                ["curl", "-sL", "--max-time", "30", "--connect-timeout", "10",
                 "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                 url],
                capture_output=True, timeout=40)
            out = r.stdout or b""
            if b"Access Denied" in out[:200] or b"<HTML>" in out[:32]:
                BLOCKED["flag"] = True
                print(f"  [blocked] {url} — пауза 90с", file=sys.stderr)
                time.sleep(90)
                BLOCKED["flag"] = False
                continue
            if r.returncode == 0 and out:
                time.sleep(REQ_DELAY)
                return out
        except Exception:
            pass
        if i < tries - 1:
            time.sleep(2 + 2 * i)
    return None


def crawl(election, suffixes, out, roots, leaf_level=None):
    base = f"https://www.eleicoes.mai.gov.pt/{election}/assets/static"
    os.makedirs(out, exist_ok=True)

    for rel in STATIC_FILES:
        p = os.path.join(out, os.path.basename(rel))
        if os.path.exists(p):
            continue
        data = fetch(f"{base}/{rel}")
        if data and not data.startswith(b"Not found") and not data.startswith(b"<!DOCTYPE"):
            with open(p, "wb") as f:
                f.write(data)

    raw_ch = os.path.join(out, "territory-children")
    os.makedirs(raw_ch, exist_ok=True)
    children_cache = {}

    def get_children(key):
        if key in children_cache:
            return children_cache[key]
        p = os.path.join(raw_ch, key + ".json")
        if not os.path.exists(p):
            data = fetch(f"{base}/territory-children/territory-children-{key}.json")
            if data is None or data.startswith(b"Not found"):
                children_cache[key] = None
                return None
            with open(p, "wb") as f:
                f.write(data)
        try:
            lst = json.load(open(p, encoding="utf-8"))
        except Exception:
            lst = None
        # иногда сервер отдаёт JSON-ошибку ("Não existem dados disponíveis") — считаем листом
        if not isinstance(lst, list) or any(not isinstance(c, dict) for c in lst):
            lst = None
        children_cache[key] = lst
        return lst

    # BFS по дереву территорий — по уровням, параллельно.
    # leaf_level: уровни >= N не проверять на детей (фрегезии/консульства —
    # заведомо листья, ниже уровня официальных данных нет) — экономит тысячи
    # пустых 404-запросов.
    tree = {}
    frontier = {k: (None, 0) for k in roots}
    while frontier:
        nxt = {}
        # 1) докачать children-файлы уровня параллельно
        fetch_keys = [k for k, (_, lvl) in frontier.items()
                      if leaf_level is None or lvl < leaf_level]
        with ThreadPoolExecutor(max_workers=4) as ex:
            list(ex.map(get_children, fetch_keys))
        # 2) раскрыть узлы уровня
        for key, (parent, level) in frontier.items():
            if key in tree:
                continue
            tree[key] = {"parent": parent, "level": level}
            if leaf_level is not None and level >= leaf_level:
                kids = None
            else:
                kids = get_children(key)
            if kids is None:
                tree[key]["children"] = None
            else:
                tree[key]["children"] = [c.get("territoryKey") for c in kids]
                for c in kids:
                    ck = c.get("territoryKey")
                    if ck and ck not in tree and ck not in nxt:
                        nxt[ck] = (key, level + 1)
        frontier = nxt
        print(f"  level done: {len(tree)} territories", file=sys.stderr)
    for key, info in tree.items():
        parent = info["parent"]
        if parent and parent in children_cache and children_cache[parent]:
            for c in children_cache[parent]:
                if c.get("territoryKey") == key:
                    tree[key]["name"] = c.get("name")

    with open(os.path.join(out, "territory-tree.json"), "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=1)
    print(f"territories: {len(tree)}", file=sys.stderr)

    jobs = []
    for suf in suffixes:
        res_dir = os.path.join(out, "territory-results" + ("" if len(suffixes) == 1 else "-" + suf))
        os.makedirs(res_dir, exist_ok=True)
        for key in tree:
            jobs.append((key, suf, res_dir))

    def dl(job):
        key, suf, res_dir = job
        p = os.path.join(res_dir, f"{key}-{suf}.json")
        if os.path.exists(p):
            return "cached"
        data = fetch(f"{base}/territory-results/territory-results-{key}-{suf}.json")
        if data is None or data.startswith(b"Not found"):
            return "404"
        with open(p, "wb") as f:
            f.write(data)
        return "ok"

    stats = {"ok": 0, "cached": 0, "404": 0}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for fut in as_completed([ex.submit(dl, j) for j in jobs]):
            stats[fut.result()] += 1
    print(f"results: {stats}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("election", help="slug выборов на портале, напр. legislativas2025")
    ap.add_argument("--suffix", default="AR", help="суффикс типа выборов (AR/PE/PR/CM/AM/AF), можно через запятую")
    ap.add_argument("--out", default=None, help="каталог выгрузки (по умолчанию ../data/<election>_mai)")
    ap.add_argument("--roots", default=DEFAULT_ROOTS, help="корневые ключи через запятую")
    ap.add_argument("--leaf-level", type=int, default=None,
                    help="уровни >= N считать листьями без проверки детей (3 = фрегезии)")
    args = ap.parse_args()
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", f"{args.election}_mai")
    crawl(args.election, [s.strip() for s in args.suffix.split(",")], os.path.normpath(out),
          [s.strip() for s in args.roots.split(",")], args.leaf_level)


if __name__ == "__main__":
    main()
