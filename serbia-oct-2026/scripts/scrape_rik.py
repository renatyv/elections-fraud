# -*- coding: utf-8 -*-
"""
Scraper of interim results of the National Assembly election in Serbia (25 Oct 2026).

Polls the RIK JSON API (the same one that powers the official results portal),
stores raw responses (raw JSON) and appends to a CSV timeline.

Usage:
  single pass:       python3 scripts/scrape_rik.py
  15-minute loop:    python3 scripts/scrape_rik.py --loop --interval 900
  another round:     python3 scripts/scrape_rik.py --round 341140          # 2023 election
  detailed:          python3 scripts/scrape_rik.py --levels national,regions,municipalities

Standard library only. Directories are created automatically:
  data/raw/<round>/<YYYYMMDD_HHMMSS>/...        — raw JSON
  data/timeline/<round>/snapshots_national.csv  — national summary timeline
  data/timeline/<round>/results_long.csv        — long format across all levels
  data/state.json                               — RIK update stamps (deduplication)
  data/poll.log                                 — log of every poll
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


# ---------- infrastructure ----------

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
    """Finds the election round by year; returns (round_id, name)."""
    rounds = rik_api.get_elections()
    for rid, name in rounds.items():
        if str(year) in name:
            return int(rid), name
    # fallback: the largest id (the most recent campaign)
    rid = max(int(k) for k in rounds)
    return rid, rounds[str(rid)]


# ---------- snapshot and timeline writing ----------

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
    """Writes raw JSON + rows into the timelines. Returns the snapshot path."""
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


# ---------- a single pass ----------

def fetch_level(round_id: int, level: str, regions_filter: str) -> list:
    """
    Returns [(norm, raw_results)] for the requested levels.
    The national level yields one record, regions — one per region,
    municipalities — one per municipality (in the regions from regions_filter).
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
            time.sleep(0.5)  # polite pause between requests

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
        log(data_dir, f"Round auto-detected: {round_id} ({round_name})")

    levels = [l.strip() for l in args.levels.split(",") if l.strip() in LEVEL_CHOICES]
    regions_filter = set(args.regions.split(",")) if args.regions else set()

    any_data = False
    changed_keys = []
    for level in levels:
        try:
            fetched = fetch_level(round_id, level, regions_filter)
        except Exception as e:  # noqa: BLE001 — logging and continuing matter more than crashing
            log(data_dir, f"ERROR level {level}: {e!r}")
            continue

        for norm, raw in fetched:
            key = f"{round_id}:{norm['level_type']}:{norm['level_id']}"
            # write a snapshot only when RIK has refreshed the data (datetime changed)
            if norm["rik_datetime"] is None:
                log(data_dir, f"{key}: no data yet (datetime='-')")
                continue
            any_data = True
            if state["rik_datetimes"].get(key) == norm["rik_datetime"]:
                continue
            state["rik_datetimes"][key] = norm["rik_datetime"]
            changed_keys.append(key)
            fname = f"{norm['level_type']}_{norm['level_id'].replace('/', '_')}.json"
            snap_dir = save_normalized(data_dir, round_id, norm, {fname: raw})
            summary = (f"{key}: updated to {norm['rik_datetime']} | "
                       f"{norm['processed_stations']}/{norm['total_stations']} "
                       f"stations processed ({norm['processed_pct']}%) | turnout "
                       f"{norm['turnout_pct']}% | lists: {len(norm['lists'])}")
            log(data_dir, summary + f" | snapshot: {os.path.relpath(snap_dir, data_dir)}")

    if any_data:
        save_state(data_dir, state)
    if not any_data:
        log(data_dir, "RIK has not published results for this round yet.")
    if changed_keys:
        log(data_dir, f"Pass finished, levels updated: {len(changed_keys)}.")
    else:
        log(data_dir, "Pass finished, no changes.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--round", type=int, default=None,
                    help="RIK round id (default: auto-detected from --year)")
    ap.add_argument("--year", type=int, default=DEFAULT_YEAR,
                    help=f"campaign year for round auto-detection (default {DEFAULT_YEAR})")
    ap.add_argument("--levels", default="national,regions",
                    help="comma-separated levels: national,regions,municipalities")
    ap.add_argument("--regions", default="",
                    help="restrict municipalities to regions, e.g. '1,2'")
    ap.add_argument("--data-dir", default=None, help="data directory (default ../data)")
    ap.add_argument("--loop", action="store_true", help="run in a loop")
    ap.add_argument("--interval", type=int, default=900,
                    help="loop interval in seconds (default 900 = 15 minutes)")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    if args.data_dir is None:
        args.data_dir = os.path.normpath(os.path.join(here, "..", "data"))
    os.makedirs(args.data_dir, exist_ok=True)

    log(args.data_dir, f"Start: levels={args.levels}, interval={args.interval}s, data={args.data_dir}")
    while True:
        state = load_state(args.data_dir)
        try:
            run_once(args, state)
        except KeyboardInterrupt:
            raise
        except Exception as e:  # noqa: BLE001
            log(args.data_dir, f"UNEXPECTED PASS ERROR: {e!r}")
        if not args.loop:
            break
        # sleep aligned to the interval grid measured from the start time
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
