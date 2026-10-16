"""Digit tests (Benford 2nd digit, last digit) on UP booth-level Form 20 counts.

Booth-level turnout cannot be computed (Form 20 carries no per-station
electors), so the turnout-based methods do not apply here — but the digit
tests need only vote counts. Candidate columns are labeled with parties via
the per-PC map built by build_mai_datasets.py (rank-pairing of PC column sums
against official ECI candidate totals).

Run from the analysis-tool project:
  cd analysis-tool && uv run python ../india-2024/scripts/booth_digit_tests.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "analysis-tool" / "src"))
from election_forensics.data import ElectionData  # noqa: E402
from election_forensics.digit_tests import (  # noqa: E402
    BENFORD_2ND,
    digit_freqs,
    digit_null_band,
    digit_test,
)
from election_forensics.plots import plot_digit_test  # noqa: E402

INDIA = Path(__file__).resolve().parents[1]
DATA = INDIA / "data"
OUT = INDIA / "analysis_booth"
TOP = ["BJP", "SP", "INC", "BSP"]


def build_booth_parties() -> pd.DataFrame:
    booths = pd.read_csv(
        DATA / "form20" / "parsed" / "up_booths_clean.csv",
        usecols=["pc_name", "ac_no", "ps_serial", "candidate", "votes", "total"],
    )
    party_map = pd.read_csv(DATA / "mai_up_ac_2024" / "pc_candidate_party_map.csv")
    col_party = {
        (r.pc, r.col): ABBR.get(r.party, r.party) for r in party_map.itertuples()
    }
    booths["col"] = "votes:" + booths.candidate.astype(int).map("c{}".format)
    booths["party"] = [col_party.get((pc, c), None) for pc, c in zip(booths.pc_name, booths.col)]
    booths = booths[booths.party.notna() & booths.party.isin(TOP + ["NOTA"])]
    wide = booths.pivot_table(index=["pc_name", "ac_no", "ps_serial"],
                              columns="party", values="votes", aggfunc="sum").fillna(0)
    wide.columns = [f"votes:{c}" for c in wide.columns]
    station_total = booths.drop_duplicates(["pc_name", "ac_no", "ps_serial"]) \
        .set_index(["pc_name", "ac_no", "ps_serial"])["total"]
    wide = wide.join(station_total)
    wide["registered_voters"] = wide["total"]  # proxy: only gates the >=100 filter
    wide["voted"] = wide["total"]  # ballots polled at the station (valid+rejected)
    wide["key"] = [f"{p}|{a}|{s}" for p, a, s in wide.index]
    return wide.reset_index(drop=True)


ABBR = {
    "Bharatiya Janata Party": "BJP", "Samajwadi Party": "SP",
    "Indian National Congress": "INC", "Bahujan Samaj Party": "BSP",
    "Rashtriya Lok Dal": "RLD", "Aazad Samaj Party (Kanshi Ram)": "ASPKR",
    "Apna Dal (Sonelal)": "ADAL",
}


def main() -> None:
    tab = OUT / "tables"
    fig = OUT / "figures"
    tab.mkdir(parents=True, exist_ok=True)
    fig.mkdir(parents=True, exist_ok=True)
    wide = build_booth_parties()
    data = ElectionData(name="UP 2024 booths", df=wide,
                        party_cols=[c for c in wide.columns if c.startswith("votes:")])
    print(f"booths: {data.n:,}, parties: {data.party_cols}")
    rows = []
    for p in data.party_cols:
        for test in ["benford2", "last"]:
            r = digit_test(data, p, test).to_dict()
            rows.append(r)
    t = pd.DataFrame(rows)
    t.to_csv(tab / "booth_digit_tests.csv", index=False)
    print(t.to_string(index=False))
    # pooled plots (all top parties together), as in the ef-analyze pipeline
    pooled = np.concatenate([data.df[p].to_numpy() for p in data.party_cols])
    plot_digit_test(digit_freqs(pooled, "benford2"), BENFORD_2ND,
                    digit_null_band(pooled, "benford2"), "benford2",
                    "top parties (pooled)", fig)
    plot_digit_test(digit_freqs(pooled, "last"), np.full(10, 0.1),
                    digit_null_band(pooled, "last"), "last",
                    "top parties (pooled)", fig)
    # Kobak integer peaks on the leader's vote share of station ballots
    # (turnout itself is not computable: Form 20 has no per-station electors)
    from election_forensics.integer_peaks import integer_peaks
    wide2 = wide[wide.voted > 0].copy()
    wide2["registered_voters"] = wide2["voted"]
    d2 = ElectionData(name="UP 2024 booths", df=wide2, party_cols=data.party_cols)
    peaks = integer_peaks(d2, "share:votes:BJP")
    print("integer BJP-share peaks:", peaks.observed_integer_pct, "% observed vs",
          peaks.null_mean_pct, "% null, z =", round(peaks.z_score, 2))
    pd.DataFrame([{k: getattr(peaks, k) for k in
                   ["observed_integer_pct", "null_mean_pct", "z_score", "z_mult5", "n_units"]}
                  ]).to_csv(tab / "booth_integer_share_peaks.csv", index=False)
    print(f"done: {OUT}")


if __name__ == "__main__":
    main()
