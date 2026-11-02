"""Add explicit tail sensitivity and multiple-test adjustment to the toolkit run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE.parent / "analysis-tool/src"))
from election_forensics.data import load_mai_csv
from election_forensics.shpilkin import shpilkin_estimate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/ef")
    parser.add_argument("--out", default="analysis/ef")
    args = parser.parse_args()
    output = BASE / args.out
    metrics = json.loads((output / "metrics.json").read_text())
    data = load_mai_csv(BASE / args.data / "results_freguesias.csv")
    tail = []
    for quantile in (99, 99.5, 99.9):
        result = shpilkin_estimate(data, "votes:Yotova", q=quantile)
        tail.append({"percentile": quantile, **result.to_dict(), "t_cut_source": f"own_percentile_{quantile}"})
    # Chi-square approximations are not interpreted when fewer than 50 tallies survive.
    eligible = [{"test": r["test"], "party": r["party"], "n": r["n_numbers"], "p_mc": r["p_null_mc"]}
                for kind in ("benford2", "last_digit") for r in metrics[kind]
                if r["n_numbers"] >= 50 and r["p_null_mc"] is not None]
    eligible.sort(key=lambda r: r["p_mc"])
    previous = 0.0
    for i, row in enumerate(eligible):
        row["p_holm"] = min(1.0, max(previous, row["p_mc"] * (len(eligible) - i)))
        previous = row["p_holm"]
    assert eligible and all(0 <= r["p_holm"] <= 1 for r in eligible)
    summary = {"tail_sensitivity": tail, "digit_holm_mc": eligible,
               "digit_family_note": f"{len(eligible)} candidate/test combinations with at least 50 usable tallies; exploratory, not preregistered"}
    (output / "sensitivity.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
