# -*- coding: utf-8 -*-
"""
Dump the municipality index of a RIK round: for every region, the municipality
<option> list with the official unit code (data-id), the API value and the name.

The index is the provenance for the stable join keys of the forensics CSVs
(unit_id is the official municipality code, stable across elections) — kept as
a file so build_ef_csv.py never needs the live API.

Usage:
  python3 scripts/dump_municipality_index.py            # 2026 round (auto)
  python3 scripts/dump_municipality_index.py --round 341140
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rik_api  # noqa: E402
from capture_stations import resolve_round  # noqa: E402


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, default=None)
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--data-dir", default=None)
    args = ap.parse_args()

    rd = args.round or resolve_round(args.year)
    data_dir = args.data_dir or os.path.normpath(os.path.join(here, "..", "data"))
    et = rik_api.ELECTION_TYPE_PARLIAMENTARY
    index = {}
    for reg_code, reg_name in sorted(rik_api.get_regions(et, rd).get("regions", {}).items(),
                                     key=lambda kv: int(kv[0])):
        muns = rik_api.get_municipalities(et, rd, int(reg_code))
        index[reg_code] = {"name": reg_name,
                           "municipalities": [
                               {"value": m["value"], "unit_id": m["unit_id"], "name": m["name"]}
                               for m in muns]}
        print(f"region {reg_code} {reg_name}: {len(muns)} municipalities")
    out = os.path.join(data_dir, f"municipality_index_{rd}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"round": rd, "regions": index}, f, ensure_ascii=False, indent=1)
    print(f"-> {out}")


if __name__ == "__main__":
    main()
