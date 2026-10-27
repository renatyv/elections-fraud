# -*- coding: utf-8 -*-
"""
Capture polling-station level results of a RIK round into a wide CSV.

One row per polling station: registered voters, votes cast, valid/invalid
ballots and votes per electoral list — the grain the forensics pipeline
(analysis-tool) needs. Resume-safe: stations already present in the output
CSV are skipped; stations RIK has not processed yet (datetime '-') are
retried on the next pass, so run the script again (or with --passes) after
the count completes.

The stable join key across rounds is <municipality unit_id>_<station
number> — the unit_id is the official municipality code (data-id in the
municipality <option> list), the station number is the prefix of the
station name ("12 - ОШ ..."), both stable between elections.

Usage:
  python3 scripts/capture_stations.py                      # round 2026 -> data/timeline/<round>/stations.csv
  python3 scripts/capture_stations.py --round 341140       # 2023 control
  python3 scripts/capture_stations.py --regions 1,100      # subset of regions
  python3 scripts/capture_stations.py --passes 3           # retry pending stations N times

Standard library only.
"""

import argparse
import csv
import datetime as dt
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rik_api  # noqa: E402

STATION_NO_RE = re.compile(r"^\s*(\d+)\s*[-–]")


def log(message: str) -> None:
    print(f"{dt.datetime.now().replace(microsecond=0).isoformat()} {message}", flush=True)


def station_no(name: str) -> str:
    """'12 - ОШ "АРНАЈЕВО"' -> '12'; falls back to the raw name hash-free suffix."""
    m = STATION_NO_RE.match(name)
    return m.group(1) if m else name.strip()


def list_numbers(round_id: int) -> list[int]:
    """All list numbers of the round, from the national table_data."""
    raw = rik_api.get_results(rik_api.ELECTION_TYPE_PARLIAMENTARY, round_id, 0, 0, 0)
    nums = sorted(int(row["count_number"]) for row in raw.get("table_data", []))
    return nums


def load_done(path: str) -> set:
    """Station join keys already present in the output CSV."""
    done = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                done.add(row["key"])
    return done


def fieldnames(list_nums: list[int]) -> list:
    base = ["key", "round", "region_code", "region_name", "mun_value", "mun_unit_id",
            "mun_name", "station_id", "station_no", "station_name", "rik_datetime",
            "registered", "voted", "valid", "invalid"]
    return base + [f"votes:{n}" for n in list_nums]


def resolve_round(year: int) -> int:
    """Finds the election round by year; falls back to the largest id."""
    rounds = rik_api.get_elections()
    for rid, name in rounds.items():
        if str(year) in name:
            return int(rid)
    return max(int(k) for k in rounds)


def pass_once(args, regions_filter: set, out_path: str, list_nums: list[int],
              done: set) -> tuple[int, int]:
    """One walk over regions -> municipalities -> stations. Returns (fetched, pending)."""
    et, rd = rik_api.ELECTION_TYPE_PARLIAMENTARY, args.round
    fetched = pending = 0
    new_file = not os.path.exists(out_path)
    with open(out_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames(list_nums), extrasaction="ignore")
        if new_file:
            writer.writeheader()
        for reg_code, reg_name in sorted(rik_api.get_regions(et, rd).get("regions", {}).items(),
                                         key=lambda kv: int(kv[0])):
            if regions_filter and reg_code not in regions_filter:
                continue
            regions = None  # keep the name local; fetch inside try below
            try:
                regions = rik_api.get_municipalities(et, rd, int(reg_code))
            except RuntimeError as e:
                log(f"ERROR region {reg_code}: {e!r} — skipped this pass")
                continue
            for mun in regions:
                try:
                    stations = rik_api.get_election_stations(et, rd, int(reg_code), int(mun["value"]))
                except RuntimeError as e:
                    log(f"ERROR stations of region {reg_code} mun {mun['value']}: {e!r}")
                    continue
                log(f"region {reg_code} {reg_name} / {mun['name']}: {len(stations)} stations")
                for st in stations:
                    no = station_no(st["name"])
                    key = f"{mun['unit_id']}_{no}"
                    if key in done:
                        continue
                    try:
                        raw = rik_api.get_results(et, rd, int(reg_code), int(mun["value"]), int(st["id"]))
                    except RuntimeError as e:
                        log(f"ERROR station {key}: {e!r} — will retry next pass")
                        pending += 1
                        time.sleep(args.sleep)
                        continue
                    norm = rik_api.normalize_results(
                        raw, "station", key,
                        f"{reg_name} / {mun['name']} / {st['name']}", rd,
                        dt.datetime.now().replace(microsecond=0).isoformat())
                    if norm["rik_datetime"] is None:
                        pending += 1  # not processed by RIK yet — retry on a later pass
                        time.sleep(args.sleep)
                        continue
                    votes = {int(l["list_no"]): l["votes"] for l in norm["lists"]}
                    writer.writerow({
                        "key": key, "round": rd,
                        "region_code": reg_code, "region_name": reg_name,
                        "mun_value": mun["value"], "mun_unit_id": mun["unit_id"],
                        "mun_name": mun["name"], "station_id": st["id"],
                        "station_no": no, "station_name": st["name"],
                        "rik_datetime": norm["rik_datetime"],
                        "registered": norm["registered_voters"],
                        "voted": norm["turnout_voters"],
                        "valid": norm["valid_ballots"],
                        "invalid": norm["invalid_ballots"],
                        **{f"votes:{n}": votes.get(n, 0) for n in list_nums},
                    })
                    done.add(key)
                    fetched += 1
                    if fetched % 250 == 0:
                        f.flush()
                        log(f"... {fetched} new stations (pending so far: {pending})")
                    time.sleep(args.sleep)
        f.flush()
    return fetched, pending


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--round", type=int, default=None,
                    help="RIK round id (default: auto-detected from --year)")
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--regions", default="", help="restrict to region codes, e.g. '1,100'")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--out", default=None, help="output CSV (default <data-dir>/timeline/<round>/stations.csv)")
    ap.add_argument("--sleep", type=float, default=0.2, help="pause between requests, seconds")
    ap.add_argument("--passes", type=int, default=1, help="number of walks (retries pending stations)")
    args = ap.parse_args()

    if args.round is None:
        args.round = resolve_round(args.year)
    log(f"Round: {args.round}")

    data_dir = args.data_dir or os.path.normpath(os.path.join(here, "..", "data"))
    out_path = args.out or os.path.join(data_dir, "timeline", str(args.round), "stations.csv")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    log(f"Output: {out_path}")

    list_nums = list_numbers(args.round)
    log(f"Lists: {list_nums}")
    done = load_done(out_path)
    log(f"Already captured: {len(done)}")

    regions_filter = set(args.regions.split(",")) if args.regions else set()
    total_new = 0
    for p in range(1, args.passes + 1):
        fetched, pending = pass_once(args, regions_filter, out_path, list_nums, done)
        total_new += fetched
        log(f"Pass {p}/{args.passes} done: +{fetched} stations, {pending} pending, total {len(done)}")
        if pending == 0:
            break
        if p < args.passes:
            time.sleep(60.0)  # give RIK time to process the rest between passes
    log(f"Finished: {total_new} new stations this run, {len(done)} in the CSV")


if __name__ == "__main__":
    main()
