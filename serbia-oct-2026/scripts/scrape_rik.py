# -*- coding: utf-8 -*-
"""
Скрейпер промежуточных результатов выборов в Народную скупщину Сербии (25.10.2026).

Опрашивает JSON-API РИК (тот же, что питает официальный портал результатов),
сохраняет исходные ответы (raw JSON) и наращивает CSV-таймлайн.

Запуск:
  один проход:      python3 scripts/scrape_rik.py
  цикл 15 минут:    python3 scripts/scrape_rik.py --loop --interval 900
  другой тур:       python3 scripts/scrape_rik.py --round 341140          # выборы-2023
  детально:         python3 scripts/scrape_rik.py --levels national,regions,municipalities

Только стандартная библиотека. Каталоги создаются автоматически:
  data/raw/<round>/<ГГГГММДД_ЧЧММСС>/...      — исходные JSON
  data/timeline/<round>/snapshots_national.csv — сводный таймлайн (страна)
  data/timeline/<round>/results_long.csv       — длинный формат по всем уровням
  data/state.json                               — метки обновлений РИК (дедупликация)
  data/poll.log                                 — журнал каждого опроса
"""

import argparse
import csv
import datetime as dt
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rik_api  # noqa: E402

DEFAULT_YEAR = 2026
LEVEL_CHOICES = ("national", "regions", "municipalities")


# ---------- инфраструктура ----------

def now_iso() -> str:
    return dt.datetime.now().replace(microsecond=0).isoformat()


def log(data_dir: str, message: str) -> None:
    line = f"{now_iso()} {message}"
    print(line, flush=True)
    with open(os.path.join(data_dir, "poll.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_state(data_dir: str) -> dict:
    path = os.path.join(data_dir, "state.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"rik_datetimes": {}}


def save_state(data_dir: str, state: dict) -> None:
    path = os.path.join(data_dir, "state.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def resolve_round(year: int) -> tuple:
    """Находит тур выборов по году; возвращает (round_id, название)."""
    rounds = rik_api.get_elections()
    for rid, name in rounds.items():
        if str(year) in name:
            return int(rid), name
    # fallback: наибольший id (самая свежая кампания)
    rid = max(int(k) for k in rounds)
    return rid, rounds[str(rid)]


# ---------- запись снапшотов и таймлайна ----------

def append_csv(path: str, fieldnames: list, row: dict) -> None:
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if new:
            writer.writeheader()
        writer.writerow(row)


NATIONAL_FIELDS = [
    "snapshot_ts", "rik_datetime", "election_round", "election_title",
    "registered_voters", "turnout_voters", "turnout_pct",
    "total_stations", "processed_stations", "processed_pct",
    "valid_ballots", "invalid_ballots",
]
LONG_FIELDS = [
    "snapshot_ts", "rik_datetime", "election_round", "level_type", "level_id",
    "level_name", "list_no", "list_name", "votes", "percent",
    "processed_stations", "total_stations", "processed_pct", "turnout_pct",
]


def save_normalized(data_dir: str, round_id: int, norm: dict, raw_responses: dict) -> str:
    """Пишет raw JSON + строки в таймлайны. Возвращает путь снапшота."""
    stamp = norm["snapshot_ts"].replace("-", "").replace(":", "").replace("T", "_")
    snap_dir = os.path.join(data_dir, "raw", str(round_id), stamp)
    os.makedirs(snap_dir, exist_ok=True)

    for fname, payload in raw_responses.items():
        with open(os.path.join(snap_dir, fname), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
    with open(os.path.join(snap_dir, "normalized.json"), "w", encoding="utf-8") as f:
        json.dump(norm, f, ensure_ascii=False, indent=1)

    tl_dir = os.path.join(data_dir, "timeline", str(round_id))
    os.makedirs(tl_dir, exist_ok=True)

    if norm["level_type"] == "national":
        row = {k: norm[k] for k in NATIONAL_FIELDS}
        append_csv(os.path.join(tl_dir, "snapshots_national.csv"), NATIONAL_FIELDS, row)

    long_rows = []
    for lst in norm["lists"]:
        long_rows.append({
            "snapshot_ts": norm["snapshot_ts"],
            "rik_datetime": norm["rik_datetime"],
            "election_round": norm["election_round"],
            "level_type": norm["level_type"],
            "level_id": norm["level_id"],
            "level_name": norm["level_name"],
            "list_no": lst["list_no"],
            "list_name": lst["list_name"],
            "votes": lst["votes"],
            "percent": lst["percent"],
            "processed_stations": norm["processed_stations"],
            "total_stations": norm["total_stations"],
            "processed_pct": norm["processed_pct"],
            "turnout_pct": norm["turnout_pct"],
        })
    if long_rows:
        long_path = os.path.join(tl_dir, "results_long.csv")
        for r in long_rows:
            append_csv(long_path, LONG_FIELDS, r)

    return snap_dir


# ---------- один проход ----------

def fetch_level(round_id: int, level: str, regions_filter: str) -> list:
    """
    Возвращает [(norm, raw_results)] для затребованных уровней.
    Уровень national даёт одну запись, regions — по записи на регион,
    municipalities — по записи на муниципалитет (в регионах из regions_filter).
    """
    snapshot_ts = now_iso()
    out = []

    if level == "national":
        raw = rik_api.get_results(
            rik_api.ELECTION_TYPE_PARLIAMENTARY, round_id, 0, 0, 0)
        out.append((rik_api.normalize_results(
            raw, "national", "0", "Република Србија (укупно)", round_id, snapshot_ts), raw))

    elif level == "regions":
        regions = rik_api.get_regions(
            rik_api.ELECTION_TYPE_PARLIAMENTARY, round_id).get("regions", {})
        for rid, rname in sorted(regions.items(), key=lambda kv: int(kv[0])):
            raw = rik_api.get_results(
                rik_api.ELECTION_TYPE_PARLIAMENTARY, round_id, int(rid), 0, 0)
            out.append((rik_api.normalize_results(
                raw, "region", str(rid), rname, round_id, snapshot_ts), raw))
            time.sleep(0.5)  # вежливая пауза между запросами

    elif level == "municipalities":
        regions = rik_api.get_regions(
            rik_api.ELECTION_TYPE_PARLIAMENTARY, round_id).get("regions", {})
        for rid, rname in sorted(regions.items(), key=lambda kv: int(kv[0])):
            if regions_filter and rid not in regions_filter:
                continue
            for mun in rik_api.get_municipalities(
                    rik_api.ELECTION_TYPE_PARLIAMENTARY, round_id, int(rid)):
                raw = rik_api.get_results(
                    rik_api.ELECTION_TYPE_PARLIAMENTARY, round_id,
                    int(rid), int(mun["value"]), 0)
                out.append((rik_api.normalize_results(
                    raw, "municipality", f"{rid}_{mun['value']}",
                    f"{rname} / {mun['name']}", round_id, snapshot_ts), raw))
                time.sleep(0.4)
    return out


def run_once(args, state: dict) -> None:
    data_dir = args.data_dir
    round_id, round_name = args.round, ""
    if round_id is None:
        round_id, round_name = resolve_round(args.year)
        log(data_dir, f"Тур определён автоматически: {round_id} ({round_name})")

    levels = [l.strip() for l in args.levels.split(",") if l.strip() in LEVEL_CHOICES]
    regions_filter = set(args.regions.split(",")) if args.regions else set()

    any_data = False
    changed_keys = []
    for level in levels:
        try:
            fetched = fetch_level(round_id, level, regions_filter)
        except Exception as e:  # noqa: BLE001 — журнал и продолжение важнее падения
            log(data_dir, f"ОШИБКА уровень {level}: {e!r}")
            continue

        for norm, raw in fetched:
            key = f"{round_id}:{norm['level_type']}:{norm['level_id']}"
            # снапшот пишем только когда РИК обновил данные (datetime изменился)
            if norm["rik_datetime"] is None:
                log(data_dir, f"{key}: данных ещё нет (datetime='-')")
                continue
            any_data = True
            if state["rik_datetimes"].get(key) == norm["rik_datetime"]:
                continue
            state["rik_datetimes"][key] = norm["rik_datetime"]
            changed_keys.append(key)
            fname = f"{norm['level_type']}_{norm['level_id'].replace('/', '_')}.json"
            snap_dir = save_normalized(data_dir, round_id, norm, {fname: raw})
            summary = (f"{key}: обновлено до {norm['rik_datetime']} | "
                       f"обработано {norm['processed_stations']}/{norm['total_stations']} "
                       f"участков ({norm['processed_pct']}%) | явка {norm['turnout_pct']}% | "
                       f"списков {len(norm['lists'])}")
            log(data_dir, summary + f" | снапшот: {os.path.relpath(snap_dir, data_dir)}")

    if any_data:
        save_state(data_dir, state)
    if not any_data:
        log(data_dir, "РИК ещё не опубликовал результаты по этому туру.")
    if changed_keys:
        log(data_dir, f"Проход завершён, обновлённых уровней: {len(changed_keys)}.")
    else:
        log(data_dir, "Проход завершён, изменений нет.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--round", type=int, default=None,
                    help="id тура РИК (по умолчанию автоопределение по --year)")
    ap.add_argument("--year", type=int, default=DEFAULT_YEAR,
                    help=f"год кампании для автоопределения тура (по умолчанию {DEFAULT_YEAR})")
    ap.add_argument("--levels", default="national,regions",
                    help="уровни через запятую: national,regions,municipalities")
    ap.add_argument("--regions", default="",
                    help="ограничить муниципалитеты регионами, напр. '1,2'")
    ap.add_argument("--data-dir", default=None, help="каталог данных (по умолчанию ../data)")
    ap.add_argument("--loop", action="store_true", help="работать циклически")
    ap.add_argument("--interval", type=int, default=900,
                    help="интервал цикла в секундах (по умолчанию 900 = 15 минут)")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    if args.data_dir is None:
        args.data_dir = os.path.normpath(os.path.join(here, "..", "data"))
    os.makedirs(args.data_dir, exist_ok=True)

    log(args.data_dir, f"Старт: levels={args.levels}, interval={args.interval}s, data={args.data_dir}")
    while True:
        state = load_state(args.data_dir)
        try:
            run_once(args, state)
        except KeyboardInterrupt:
            raise
        except Exception as e:  # noqa: BLE001
            log(args.data_dir, f"НЕОЖИДАННАЯ ОШИБКА прохода: {e!r}")
        if not args.loop:
            break
        # выравнивание на сетку интервала от момента старта
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
