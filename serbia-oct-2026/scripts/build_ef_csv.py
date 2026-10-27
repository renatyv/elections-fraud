# -*- coding: utf-8 -*-
"""
Build the forensics (MAI-format) CSVs for the Serbia 2026 parliamentary
election and its 2023 control, at municipality or polling-station grain.

Sources (no live API needed):
  grain=municipalities  data/raw/<round>/<stamp>/municipality_<r>_<v>.json
                        (scrape_rik.py passes; newest stamp wins) +
                        data/municipality_index_<round>.json (official unit
                        codes and names, dump_municipality_index.py)
  grain=stations        data/timeline/<round>/stations.csv
                        (capture_stations.py; key = unit_id + station number)

Output: data/ef/<out>/
  results_freguesias.csv      — the 2026 election (level=3 units)
  results_all_previous.csv    — the 2023 election, same keys (municipality
                                grain only; for stations the control is a
                                separate directory used via --controls)
  VALIDATION.txt              — reconciliation against the national totals

Units of the special registers (region 100 prisons, 101 abroad) are excluded
from both grains and analysed separately.

List short names are entity-stable across the two rounds (the same party keeps
the same column), so the swing/jump analysis can compare them directly.

Run (from the repository root):
  analysis-tool/.venv/bin/python serbia-oct-2026/scripts/build_ef_csv.py                 # municipalities
  analysis-tool/.venv/bin/python serbia-oct-2026/scripts/build_ef_csv.py --grain stations
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

EXCLUDE_REGIONS = {"100", "101"}  # prisons, abroad — special registers

# candidate_id -> short, entity-stable name (RIK list numbers of each round)
SHORT_NAMES: dict[int, dict[int, str]] = {
    680072: {
        1: "Vučić", 2: "Dacić (SPS)", 3: "Students", 4: "Ljajić", 5: "VMSZ",
        6: "Zukorlić (SPP)", 7: "Russ. party", 8: "Jovanović (NDSS)", 9: "Tepić (ES)",
        10: "SDA Sandžaka", 11: "Karić", 12: "LZS", 13: "Biram pravdu",
        14: "Rus.-srb. jedinstvo", 15: "Đurić (Ćale)", 16: "Gajić (Alternativa)",
        17: "Alb. coalition", 18: "Majka Srbija",
    },
    341140: {
        1: "Vučić", 2: "Dacić (SPS)", 3: "Šešelj (SRS)", 4: "NOS—Zavetnici—Dveri",
        5: "Jovanović (NDSS)", 6: "VMSZ", 7: "SPN", 8: "Zukorlić (SPP)",
        9: "SDA Sandžaka", 10: "Zajedno za razvoj", 11: "Narodna (Jeremić)",
        12: "DJB—Tadić", 13: "Alb. Kamberi", 14: "MI-Glas (Nestorović)",
        15: "Srbija na Zapadu", 16: "Russ. party", 17: "Č. Jovanović (Moramo)",
        18: "Alb. ADA",
    },
}


@dataclass
class Unit:
    """One territory's result (municipality or polling station)."""

    key: str            # stable join key across rounds
    parent: str         # region name
    name: str
    registered: int
    valid: int
    voted: int
    invalid: int
    votes: dict[int, int] = field(default_factory=dict)


# ---------- municipality grain ----------

def load_municipality_units(round_id: int) -> tuple[list[Unit], dict]:
    """All municipality raws of a round (newest stamp wins) with index metadata."""
    index = json.loads((DATA / f"municipality_index_{round_id}.json").read_text(encoding="utf-8"))
    meta: dict[str, dict] = {}
    for reg_code, reg in index["regions"].items():
        for m in reg["municipalities"]:
            meta[f"{reg_code}_{m['value']}"] = {
                "unit_id": m["unit_id"], "name": m["name"], "region": reg["name"],
                "region_code": reg_code}
    raws: dict[str, Path] = {}
    for snap_dir in sorted((DATA / "raw" / str(round_id)).iterdir()):
        for f in snap_dir.glob("municipality_*.json"):
            raws[f.stem.removeprefix("municipality_")] = f  # later stamps overwrite
    units, national = [], {}
    for lv, path in sorted(raws.items()):
        if lv not in meta or meta[lv]["region_code"] in EXCLUDE_REGIONS:
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        votes = {int(r["count_number"]): int(str(r["won_number"]).replace(".", "") or 0)
                 for r in raw.get("table_data", [])}
        valid, invalid = _ballots(raw)
        ssn = raw.get("stat_sum_numbers", {})
        m = meta[lv]
        units.append(Unit(key=f"RS-{m['unit_id']}", parent=m["region"], name=m["name"],
                          registered=_num(ssn.get("total_voters")),
                          valid=valid, voted=_num(ssn.get("available")), invalid=invalid, votes=votes))
    nat_file = _newest_raw(round_id, "national_0.json")
    if nat_file:
        raw = json.loads(nat_file.read_text(encoding="utf-8"))
        national = {"valid": _ballots(raw)[0], "invalid": _ballots(raw)[1],
                    "registered": _num(raw["stat_sum_numbers"].get("total_voters")),
                    "votes": {int(r["count_number"]): int(str(r["won_number"]).replace(".", "") or 0)
                              for r in raw.get("table_data", [])}}
    return units, national


# ---------- station grain ----------

def load_station_units(round_id: int) -> tuple[list[Unit], dict]:
    csv_path = DATA / "timeline" / str(round_id) / "stations.csv"
    complete = csv_path.with_name("stations_complete.csv")
    if complete.exists():
        csv_path = complete
    import csv as _csv
    units = []
    with open(csv_path, encoding="utf-8") as f:
        for row in _csv.DictReader(f):
            if row["region_code"] in EXCLUDE_REGIONS:
                continue
            votes = {int(k.removeprefix("votes:")): int(v or 0)
                     for k, v in row.items() if k.startswith("votes:")}
            units.append(Unit(key=f"RS-{row['key']}", parent=f"{row['region_name']} > {row['mun_name']}",
                              name=f"{row['mun_name']}, st. {row['station_no']}",
                              registered=int(row["registered"]), valid=int(row["valid"]), voted=int(row["voted"]),
                              invalid=int(row["invalid"]), votes=votes))
    national = {}
    nat_file = _newest_raw(round_id, "national_0.json")
    if nat_file:
        raw = json.loads(nat_file.read_text(encoding="utf-8"))
        national = {"valid": _ballots(raw)[0], "invalid": _ballots(raw)[1],
                    "registered": _num(raw["stat_sum_numbers"].get("total_voters")),
                    "votes": {int(r["count_number"]): int(str(r["won_number"]).replace(".", "") or 0)
                              for r in raw.get("table_data", [])}}
    return units, national


# ---------- MAI writing ----------

def mai_rows(units: list[Unit], round_id: int, year: int) -> tuple[list[dict], list[str]]:
    names = SHORT_NAMES[round_id]
    party_cols = [f"votes:{names[n]}" for n in sorted({k for u in units for k in u.votes})]
    rows = []
    for u in sorted(units, key=lambda x: x.key):
        turnout = round(100 * u.voted / u.registered, 2) if u.registered else 0.0
        rows.append({"key": u.key, "level": 3, "name": u.name,
                     "path": f"RS {year} > {u.parent} > {u.name}",
                     "parent_key": u.parent, "registered_voters": u.registered,
                     "voted": u.voted, "turnout_pct": turnout, "blank_votes": 0,
                     "null_votes": u.invalid,
                     **{c: u.votes.get(_no_of(c, names), 0) for c in party_cols},
                     "mandates": ""})
    return rows, party_cols


def _no_of(col: str, names: dict[int, str]) -> int:
    want = col.removeprefix("votes:")
    for no, nm in names.items():
        if nm == want:
            return no
    return -1


def _ballots(raw: dict) -> tuple[int, int]:
    try:
        data = raw["sum_config"]["data"]["datasets"][0]["data"]
        return int(str(data[0]).replace(".", "") or 0), int(str(data[1]).replace(".", "") or 0)
    except (KeyError, IndexError, TypeError):
        return 0, 0


def _num(value) -> int:
    return int(str(value).replace(".", "") or 0) if value else 0


def _newest_raw(round_id: int, fname: str) -> Path | None:
    for snap_dir in sorted((DATA / "raw" / str(round_id)).iterdir(), reverse=True):
        f = snap_dir / fname
        if f.exists():
            return f
    return None


def _special_votes(round_id: int) -> dict[int, int]:
    """Votes per list summed over the excluded special registers (regions 100, 101)."""
    out: dict[int, int] = {}
    for code in EXCLUDE_REGIONS:
        f = _newest_raw(round_id, f"region_{code}.json")
        if f is None:
            continue
        raw = json.loads(f.read_text(encoding="utf-8"))
        for r in raw.get("table_data", []):
            n = int(r["count_number"])
            out[n] = out.get(n, 0) + _num(r["won_number"])
    return out


def write_ef_dir(units: list[Unit], round_id: int, year: int, out: Path,
                 national: dict, control_units: list[Unit] | None = None,
                 grain: str = "municipalities") -> None:
    out.mkdir(parents=True, exist_ok=True)
    assert len({u.key for u in units}) == len(units), "duplicate territory keys"
    assert all(sum(u.votes.values()) == u.valid for u in units), "list totals differ from valid ballots"
    assert all(0 <= u.valid + u.invalid <= u.voted <= u.registered for u in units), "invalid ballot accounting"
    rows, party_cols = mai_rows(units, round_id, year)
    fields = ["key", "level", "name", "path", "parent_key", "registered_voters",
              "voted", "turnout_pct", "blank_votes", "null_votes", *party_cols, "mandates"]
    import csv as _csv
    with open(out / "results_freguesias.csv", "w", newline="", encoding="utf-8") as f:
        w = _csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    if control_units is not None:
        crows, ccols = mai_rows(control_units, 341140, 2023)
        cfields = ["key", "level", "name", "path", "parent_key", "registered_voters",
                   "voted", "turnout_pct", "blank_votes", "null_votes",
                   *sorted(set(party_cols) | set(ccols)), "mandates"]
        with open(out / "results_all_previous.csv", "w", newline="", encoding="utf-8") as f:
            w = _csv.DictWriter(f, fieldnames=cfields)
            w.writeheader()
            w.writerows(crows)

    # validation
    sum_valid = sum(u.valid for u in units)
    sum_reg = sum(u.registered for u in units)
    lines = [f"unit = {'polling station (biralište)' if grain == 'stations' else 'municipality (opština/gradska opština)'}, territorial Serbia only",
             f"round {round_id} ({year}): {len(units)} units, registered {sum_reg:,},",
             f"valid {sum_valid:,}, invalid {sum(u.invalid for u in units):,}"]
    if national:
        lines.append(f"national JSON: registered {national['registered']:,}, "
                     f"valid {national['valid']:,} -> "
                     f"Δvalid {sum_valid - national['valid']:+,} (special registers and incomplete coverage "
                     f"may account for the difference), Δregistered "
                     f"{sum_reg - national['registered']:+,}")
        per_list = {n: sum(u.votes.get(n, 0) for u in units) for n in sorted({k for u in units for k in u.votes})}
        specials = _special_votes(round_id)
        bad = {n: (v, national["votes"].get(n, 0) - specials.get(n, 0))
               for n, v in per_list.items()
               if national["votes"].get(n, 0) - specials.get(n, 0) != v}
        lines.append(f"per-list sums vs national minus special registers: "
                     f"{'ALL MATCH' if not bad else bad}")
    if control_units is not None:
        matched = len({u.key for u in units} & {u.key for u in control_units})
        lines.append(f"keys matched to 2023: {matched} of {len(units)} "
                     f"(2023 units: {len(control_units)})")
    (out / "VALIDATION.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--grain", choices=["municipalities", "stations"], default="municipalities")
    ap.add_argument("--round", type=int, default=680072)
    ap.add_argument("--control-round", type=int, default=341140)
    args = ap.parse_args()

    loader = load_municipality_units if args.grain == "municipalities" else load_station_units
    tag = "mun" if args.grain == "municipalities" else "stn"
    units, national = loader(args.round)
    control_units, control_national = loader(args.control_round)
    suffix = f"serbia2026_{tag}"
    print(f"{args.grain}: 2026 units {len(units)}, 2023 control units "
          f"{len(control_units)}")
    write_ef_dir(units, args.round, 2026, DATA / "ef" / suffix, national,
                 control_units if args.grain == "municipalities" else None, grain=args.grain)
    write_ef_dir(control_units, args.control_round, 2023, DATA / "ef" / f"serbia2023_{tag}",
                 national=control_national, grain=args.grain)


if __name__ == "__main__":
    main()
