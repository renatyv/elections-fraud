#!/usr/bin/env python3
"""Validate the clean UP Form 20 tables against the official ECI results.

Reads data/form20/parsed/up_ac_clean.csv (built by form20_clean.py),
groups ACs into PCs, and compares every PC whose mapping ACs are all
present against the official results
(data/results_pc/in-rolls_2024_constituencywise_detailed_result.csv):

  - sum of AC electors (Form 20 headers)  vs  PC total electors
  - valid votes incl. NOTA (votes:cK + votes:NOTA)
      vs sum of official candidate totals
  - NOTA total vs the official NOTA row
  - sorted per-candidate vector (multiset test) vs official totals
    (Form 20 lists the PC's candidates in one order, so candidate
    index k is the same candidate in every AC of the PC)

Writes parsed/validation_form20.txt.

Run:  cd india-2024 && uv run python scripts/form20_validate.py
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from form20_clean import load_pools

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PARSED = ROOT / "data" / "form20" / "parsed"
OFFICIAL_CSV = (ROOT / "data" / "results_pc" /
                "in-rolls_2024_constituencywise_detailed_result.csv")

# in-rolls keeps four historical PC names; the mapping uses current ones
PC_NAME_FIX = {"Allahabad": "Prayagraj", "Faizabad": "Ayodhya",
               "Baharaich": "Bahraich", "Baghpat": "Bagpat"}
CLOSE_PCT = 0.5  # % tolerance for the "close" verdict


@dataclass
class PCRef:
    """Official reference numbers of one parliamentary constituency."""
    pc: str
    electors: int
    valid_nota: int
    nota: int
    totals: list[int]


def load_official() -> dict[str, PCRef]:
    ir = pd.read_csv(OFFICIAL_CSV)
    ir = ir[ir["State Name"].str.strip() == "Uttar Pradesh"].copy()
    ir["pc"] = ir["PC Name"].str.strip().replace(PC_NAME_FIX)
    ir["Total"] = ir["Total"].astype("Int64")
    out: dict[str, PCRef] = {}
    for pc, g in ir.groupby("pc"):
        nota_mask = g["Candidate Name"].str.strip().str.upper() == "NOTA"
        out[str(pc)] = PCRef(
            pc=str(pc),
            electors=int(g["Total Electors"].iloc[0]),
            valid_nota=int(g["Total"].sum()),
            nota=int(g.loc[nota_mask, "Total"].sum()),
            totals=sorted(int(v) for v in g["Total"]),
        )
    return out


def main() -> None:
    ac = pd.read_csv(PARSED / "up_ac_clean.csv")
    pools = load_pools()
    official = load_official()
    vcols = [c for c in ac.columns if c.startswith("votes:c")]

    rows: list[dict] = []
    for pc, ref in official.items():
        want = {a for a, r in pools.by_no.items() if r.pc_name == pc}
        got = ac[ac.pc_name == pc]
        if got.empty:
            rows.append({"pc": pc, "coverage": "missing"})
            continue
        if not want <= set(got.ac_no):
            rows.append({"pc": pc, "coverage": "partial",
                         "acs_have": len(got), "acs_want": len(want)})
            continue
        # the Form 20 electors header is often blank: only compare the
        # sum when every AC of the PC has one
        complete_el = bool(got.registered_voters.notna().all())
        electors = got.registered_voters.sum() if complete_el else None
        el_delta = None if electors is None else int(electors - ref.electors)
        valid_nota = int(got[vcols].to_numpy().sum() + got["votes:NOTA"].sum())
        v_delta = valid_nota - ref.valid_nota
        nota_delta = int(got["votes:NOTA"].sum() - ref.nota)
        mine = sorted(int(x) for c in vcols for x in got[c] if x > 0)
        mine.append(int(got["votes:NOTA"].sum()))
        multiset_ok = sorted(mine) == sorted(v for v in ref.totals if v > 0)
        close = abs(v_delta) <= CLOSE_PCT / 100 * ref.valid_nota \
            and abs(nota_delta) <= CLOSE_PCT / 100 * max(ref.nota, 1) \
            and (el_delta is None
                 or abs(el_delta) <= CLOSE_PCT / 100 * ref.electors)
        rows.append({
            "pc": pc, "coverage": "full", "acs": len(want),
            "stations": int(got.n_stations.sum()),
            "electors_form20": None if el_delta is None else int(electors),
            "electors_official": ref.electors, "electors_delta": el_delta,
            "valid_form20": valid_nota, "valid_official": ref.valid_nota,
            "valid_delta": v_delta,
            "valid_delta_pct": round(100.0 * v_delta / ref.valid_nota, 2),
            "nota_delta": nota_delta, "multiset_ok": multiset_ok,
            "ok_close": close,
        })

    det = pd.DataFrame([r for r in rows if r["coverage"] == "full"])
    cov = pd.Series([r["coverage"] for r in rows]).value_counts()
    n_exact = int((det.valid_delta == 0).sum()) if len(det) else 0
    n_close = int(det.ok_close.sum()) if len(det) else 0

    report = [
        "UP Form 20 clean-data validation vs official ECI results",
        "(in-rolls constituencywise detailed result, state=Uttar Pradesh)",
        "",
        f"clean data: {len(ac)} ACs, {int(ac.n_stations.sum())} stations; "
        f"{int(ac.registered_voters.isna().sum())} ACs without electors",
        f"PC coverage: {dict(cov)}",
        f"full PCs: {len(det)} | exact match: {n_exact} | "
        f"within ±{CLOSE_PCT}% + multiset: {n_close}",
        "",
    ]
    if len(det):
        cols = ["pc", "acs", "stations", "valid_delta", "valid_delta_pct",
                "nota_delta", "electors_delta", "multiset_ok", "ok_close"]
        with pd.option_context("display.max_rows", None):
            report.append(det[cols].sort_values("valid_delta_pct")
                          .to_string(index=False))
        bad = det[~det.ok_close]
        if len(bad):
            report += ["", "full PCs outside tolerance (detail):"]
            report.append(bad.drop(columns=["coverage"]).to_string(index=False))

    no_electors = ac[ac.registered_voters.isna()]
    if len(no_electors):
        report += [
            "",
            f"ACs without electors ({len(no_electors)}) by PC: "
            + ", ".join(f"{pc}:{n}" for pc, n in
                        no_electors.pc_name.value_counts().items()),
        ]

    text = "\n".join(report)
    (PARSED / "validation_form20.txt").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
