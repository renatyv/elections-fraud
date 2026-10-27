"""Adapt reconciled CIK numeric protocols for ef-analyze; preserve exclusions."""
from __future__ import annotations

import csv
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


def main() -> None:
    source = BASE / "data/official_20261027"
    summary = json.loads((source / "summary.json").read_text())
    sections = json.loads((source / "sections.json").read_text())
    if not summary["sections_reconcile"] or len(sections) != summary["indexed_sections"]:
        raise ValueError("All indexed sections must reconcile candidate by candidate before analysis")
    output = BASE / "data/ef"
    output.mkdir(parents=True, exist_ok=True)
    excluded, rows = [], []
    names = {"25": "Yotova", "4": "Gyurov", "11": "Kostadinov", "17": "Vasilev", "19": "Mihaylov"}
    for p in sections:
        registered = p["registered"] + p["added"]
        valid = sum(p["votes"].values()) + p["nobody"]
        reason = ("abroad" if p["district"] == "32" else
                  "protocol_balance" if valid > p["voted"] or p["voted"] > registered else
                  "register_under_100" if registered < 100 else
                  "no_voters" if p["voted"] <= 0 else "")
        if reason:
            excluded.append({"section": p["section"], "reason": reason})
            continue
        row = {"key": f'BG-{p["section"]}', "level": 3, "name": p["section"],
               "path": f'Bulgaria > {p["district"]} > {p["section"][:4]} > {p["section"]}', "parent_key": f'BG-{p["section"][:4]}',
               "registered_voters": registered, "voted": p["voted"],
               "turnout_pct": 100 * p["voted"] / registered,
               "blank_votes": p["nobody"], "null_votes": p["voted"] - valid}
        row.update({f"votes:{names.get(cid, cid)}": n for cid, n in p["votes"].items()})
        rows.append(row)
    if not rows or len({r["key"] for r in rows}) != len(rows):
        raise ValueError("Empty or duplicate analysis units")
    assert len(rows) + len(excluded) == len(sections)
    assert all(sum(r[c] for c in r if c.startswith("votes:")) + r["blank_votes"] + r["null_votes"] == r["voted"] for r in rows)
    for filename, values in [("results_freguesias.csv", rows), ("exclusions.csv", excluded)]:
        with (output / filename).open("w") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(values[0]))
            writer.writeheader()
            writer.writerows(values)
    audit = {"indexed": len(sections), "eligible": len(rows), "excluded": len(excluded),
             "exclusion_counts": {reason: sum(r["reason"] == reason for r in excluded) for reason in sorted({r["reason"] for r in excluded})},
             "registered": sum(r["registered_voters"] for r in rows), "voted": sum(r["voted"] for r in rows),
             "denominator": "opening register plus election-day additions", "controls": [],
             "eligible_leader_votes": sum(r["votes:Yotova"] for r in rows)}
    (output / "audit.json").write_text(json.dumps(audit, indent=2))
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
