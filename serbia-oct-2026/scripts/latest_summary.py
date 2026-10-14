# -*- coding: utf-8 -*-
"""
Summary of the collected data: current standings of the lists, dynamics between
the last two snapshots, polling-station processing progress.

  python3 scripts/latest_summary.py                 # latest round in data/
  python3 scripts/latest_summary.py --round 341140  # a specific round
  python3 scripts/latest_summary.py --html          # also writes data/latest_summary.md
"""

import argparse
import csv
import glob
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA = os.path.normpath(os.path.join(HERE, "..", "data"))


def read_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def latest_round(data_dir):
    rounds = sorted(
        (os.path.basename(p) for p in glob.glob(os.path.join(data_dir, "timeline", "*"))),
        key=int, reverse=True)
    if not rounds:
        raise SystemExit("No data. Run scrape_rik.py first.")
    return rounds[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=DEFAULT_DATA)
    ap.add_argument("--round", default=None)
    ap.add_argument("--html", action="store_true", help="also write data/latest_summary.md")
    args = ap.parse_args()

    round_id = args.round or latest_round(args.data_dir)
    tl = os.path.join(args.data_dir, "timeline", round_id)
    nat_path = os.path.join(tl, "snapshots_national.csv")
    long_path = os.path.join(tl, "results_long.csv")
    if not os.path.exists(long_path):
        raise SystemExit(f"No timeline for round {round_id}: {long_path}")

    lines = []
    add = lines.append
    add(f"# Summary for RIK round {round_id}\n")

    if os.path.exists(nat_path):
        snaps = read_csv(nat_path)
        if snaps:
            last = snaps[-1]
            first = snaps[0]
            add(f"* Snapshots: {len(snaps)} "
                f"({first['snapshot_ts']} … {last['snapshot_ts']})")
            add(f"* RIK data as of: {last['rik_datetime']}")
            add(f"* Turnout: {last['turnout_voters']} of {last['registered_voters']} "
                f"({last['turnout_pct']}%)")
            add(f"* Stations processed: {last['processed_stations']} of "
                f"{last['total_stations']} ({last['processed_pct']}%)")
            add(f"* Ballots: {last['valid_ballots']} valid, "
                f"{last['invalid_ballots']} invalid\n")

    rows = read_csv(long_path)
    national_rows = [r for r in rows if r["level_type"] == "national"]
    snaps_ts = sorted({r["snapshot_ts"] for r in national_rows})
    if not snaps_ts:
        raise SystemExit("No national-level records in the timeline.")

    latest = {r["list_name"]: r for r in national_rows if r["snapshot_ts"] == snaps_ts[-1]}
    prev = ({r["list_name"]: r for r in national_rows if r["snapshot_ts"] == snaps_ts[-2]}
            if len(snaps_ts) >= 2 else {})

    add("| # | List | Votes | % | Δ votes since previous snapshot |")
    add("|---|------|-------|---|--------------------------------|")
    for name in sorted(latest, key=lambda n: int(latest[n]["list_no"] or 0)):
        r = latest[name]
        d = ""
        if name in prev:
            delta = int(r["votes"]) - int(prev[name]["votes"])
            if delta:
                d = f"{'+' if delta > 0 else ''}{delta:,}".replace(",", " ")
        add(f"| {r['list_no']} | {name} | {int(r['votes']):,}".replace(",", " ") +
            f" | {r['percent']} | {d} |")

    text = "\n".join(lines)
    print(text)
    if args.html:
        out = os.path.join(args.data_dir, "latest_summary.md")
        with open(out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"\nWritten: {out}")


if __name__ == "__main__":
    main()
