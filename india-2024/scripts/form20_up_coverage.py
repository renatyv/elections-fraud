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

    # manifest rows carry the dest filename chosen by the finalize script;
    # fall back to derived names for rows from older manifest versions
    if "dest" not in m.columns:
        def base(label: str) -> str:
            return re.sub(r"[^A-Za-z0-9()-]+", "_", label)[:60].strip("_-")

        def url_stem(url: str) -> str:
            return re.sub(r".*/", "", url).removesuffix(".pdf")

        m["base"] = [base(r.ac_label) if base(r.ac_label) else url_stem(r.pdf_url)
                     for r in m.itertuples()]
        dup = m.groupby(["district", "base"]).pdf_url.transform("size") > 1
        m["dest"] = [
            f"{d}__{b}.pdf" if not is_dup else f"{d}__{b}__{url_stem(u)}.pdf"
            for d, b, is_dup, u in zip(m.district, m.base, dup, m.pdf_url)
        ]
    m = m[[d in files for d in m.dest]]

    def ac_no(label: str) -> int:
        nums = [int(n) for n in re.findall(r"\d{1,3}", label)]
        nums = [n for n in nums if 0 < n <= 403]
        if not nums:
            return -1
        # a leading row serial (1..20) followed by a bigger number means the
        # bigger one is the AC number ("1_282-Balha", "row_10_Form20-175-…")
        if len(nums) > 1 and nums[0] <= 20:
            return nums[1]
        return nums[0]

    m["ac_no"] = [ac_no(r.ac_label) for r in m.itertuples()]

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
