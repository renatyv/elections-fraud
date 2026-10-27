"""Cross-round station reconciliation and incumbent-focused forensic checks."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from election_forensics.data import load_mai_csv
from election_forensics.fingerprints import fingerprint_mixture
from election_forensics.integer_peaks import integer_peaks
from election_forensics.shpilkin import shpilkin_estimate

BASE = Path(__file__).resolve().parents[1]


def main() -> None:
    out = BASE / "analysis" / "diagnostics"
    out.mkdir(parents=True, exist_ok=True)
    current = pd.read_csv(BASE / "data/timeline/680072/stations.csv")
    previous = pd.read_csv(BASE / "data/timeline/341140/stations_complete.csv")
    for frame in (current, previous):
        assert frame.key.is_unique
        assert (frame.filter(regex=r"^votes:").sum(axis=1) == frame.valid).all()
        assert (frame.valid + frame.invalid <= frame.voted).all()
        assert (frame.voted <= frame.registered).all()
    gaps = current.assign(unaccounted=current.voted - current.valid - current.invalid)
    gaps[gaps.unaccounted != 0].to_csv(out / "ballot_accounting_gaps.csv", index=False)
    territorial = current[~current.region_code.isin([100, 101])]
    control = previous[~previous.region_code.isin([100, 101])]
    joined = territorial.merge(control, on="key", suffixes=("_2026", "_2023"), validate="one_to_one")
    for year in (2023, 2026):
        joined[f"turnout_{year}"] = 100 * joined[f"voted_{year}"] / joined[f"registered_{year}"]
        joined[f"incumbent_valid_share_{year}"] = 100 * joined[f"votes:1_{year}"] / joined[f"valid_{year}"]
    joined.to_csv(out / "matched_stations.csv", index=False)
    data = load_mai_csv(BASE / "data/ef/serbia2026_stn/results_freguesias.csv")
    old = load_mai_csv(BASE / "data/ef/serbia2023_stn/results_freguesias.csv")
    peaks = integer_peaks(data, "share:votes:Vučić")
    source = sorted((BASE / "data/raw/680072").glob("*/national_0.json"))[-1]
    raw = json.loads(source.read_text())
    assert current.valid.sum() == sum(int(str(row["won_number"]).replace(".", ""))
                                      for row in raw["table_data"])
    full_register = int(str(raw["stat_sum_numbers"]["total_voters"]).replace(".", ""))
    remaining = int(full_register - current.registered.sum())
    margin = int(current["votes:3"].sum() - current["votes:1"].sum())
    summary = {
        "forensic_snapshot": raw["stat_sum_numbers"]["datetime"],
        "stations_2023_all": len(previous), "stations_2026_all": len(current),
        "matched_territorial_stations": len(joined),
        "unmatched_2026_territorial_stations": len(territorial) - len(joined),
        "cast_minus_valid_minus_invalid_2026": int(gaps.unaccounted.sum()),
        "stations_with_ballot_gap_2026": int((gaps.unaccounted != 0).sum()),
        "matched_turnout_pct": {
            str(year): float(100 * joined[f"voted_{year}"].sum() / joined[f"registered_{year}"].sum())
            for year in (2023, 2026)},
        "matched_incumbent_valid_share_pct": {
            str(year): float(100 * joined[f"votes:1_{year}"].sum() / joined[f"valid_{year}"].sum())
            for year in (2023, 2026)},
        "uncounted_registered_voters": remaining,
        "students_vote_lead": margin,
        "students_minimum_valid_share_pct": float(100 * current["votes:3"].sum() /
            (current.valid.sum() + remaining + gaps.unaccounted.sum())),
        "bound_assumption": "unchanged register and counted votes; remaining voters and ballot gaps all vote against Students",
        "incumbent_shpilkin": shpilkin_estimate(data, "votes:Vučić", controls=[old]).to_dict(),
        "incumbent_fingerprint": fingerprint_mixture(data, "votes:Vučić").to_dict(),
        "incumbent_integer_share_z": float(peaks.z_score),
    }
    (out / "metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
