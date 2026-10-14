#!/usr/bin/env python3
"""Summarize UP Form 20 coverage: files per district and AC numbers covered.

Run:     cd india-2024 && uv run python scripts/form20_up_coverage.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
FORM20 = HERE.parent / "data" / "form20"

AC_NUM_RE = re.compile(r"\d{1,3}")


def main() -> None:
    m = pd.read_csv(FORM20 / "up_manifest.csv")
    files = {p.name for p in (FORM20 / "up").glob("*.pdf")}

    def dest(row: pd.Series) -> str:
        safe = re.sub(r"[^A-Za-z0-9()-]+", "_", row.ac_label)[:60].strip("_-")
        return f"{row.district}__{safe}.pdf" if safe else f"{row.district}__.pdf"

    m = m[[dest(r) in files for r in m.itertuples()]]
    m["ac_no"] = [int(n.group()) if (n := AC_NUM_RE.search(r.ac_label)) else -1
                  for r in m.itertuples()]

    print(f"files: {len(files)}, manifest rows w/ file: {len(m)}, districts: {m.district.nunique()}")
    acs = sorted({int(a) for a in m.ac_no if 0 < a <= 403})
    print(f"distinct AC numbers (1-403): {len(acs)}")

    by_dist = m.groupby("district").size().sort_values(ascending=False)
    print("\nfiles per district:")
    print(by_dist.to_string())

    d = json.load(open(FORM20 / "up_form20_districts_cdx.json"))
    probed = {x["district"] for x in d}
    print(f"\ndistricts in round-1 json: {len(probed)}; covered now: {len(probed & set(m.district))}")
    print("uncovered (probed):", sorted(probed - set(m.district)))


if __name__ == "__main__":
    main()
