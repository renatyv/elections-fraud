#!/usr/bin/env python3
"""Build summary CSVs from the MAI portal download (see fetch_mai_results.py).

Reads data/<election>_mai/territory-tree.json + territory-results/*.json
and builds:
  results_all.csv        — all levels (country, districts, municipalities,
                           parishes, abroad)
  results_freguesias.csv — parishes (freguesias) only
  results_concelhos.csv  — municipalities (concelhos) only
  results_circulos.csv   — electoral constituencies (círculos) only

The format is "wide": base fields plus one column per party (votes).
The portal JSON also carries previousResults (the previous election) —
written to results_all_previous.csv.
"""
import argparse
import csv
import json
import os


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data_dir", help="download directory, e.g. data/legislativas2025_mai")
    ap.add_argument("--results-subdir", default="territory-results")
    args = ap.parse_args()

    tree = json.load(open(os.path.join(args.data_dir, "territory-tree.json"), encoding="utf-8"))
    # the new portal version (v2) uses numeric territory ids; after a JSON
    # round-trip the keys are strings while the inner parent is an int.
    # Normalize everything to strings.
    tree = {str(k): {**v, "parent": (str(v["parent"]) if v.get("parent") is not None else None)}
            for k, v in tree.items()}
    res_dir = os.path.join(args.data_dir, args.results_subdir)

    def name_of(k):
        return tree.get(k, {}).get("name") or str(k)

    def path_of(k):
        parts = []
        cur = k
        while cur:
            parts.append(name_of(cur))
            cur = tree.get(cur, {}).get("parent")
        return " > ".join(reversed(parts))

    rows, prev_rows = [], []
    party_totals = {}
    for k, info in tree.items():
        p = os.path.join(res_dir, f"{k}-AR.json") if False else None
        # the suffix may differ; look for any <KEY>-*.json file
        d = os.path.join(res_dir, k + "-AR.json")
        if not os.path.exists(d):
            cands = [f for f in os.listdir(res_dir) if f.startswith(k + "-") and f.endswith(".json")]
            if not cands:
                continue
            d = os.path.join(res_dir, cands[0])
        try:
            data = json.load(open(d, encoding="utf-8"))
        except Exception:
            continue
        # the new portal version (2025+) wraps the result in {"data": {...}}
        if isinstance(data.get("data"), dict):
            data = data["data"]
        cur = data.get("currentResults")
        if not cur:
            continue

        def base_row(cr):
            return {
                "key": k,
                "level": info.get("level"),
                "name": name_of(k),
                "path": path_of(k),
                "parent_key": info.get("parent") or "",
                "registered_voters": cr.get("subscribedVoters"),
                "voted": cr.get("numberVoters") or cr.get("totalVoters"),
                "turnout_pct": cr.get("percentageVoters"),
                "blank_votes": cr.get("blankVotes"),
                "null_votes": cr.get("nullVotes"),
            }

        r = base_row(cur)
        for pr in cur.get("resultsParty") or []:
            a = pr.get("acronym")
            if not a:
                continue
            col = "votes:" + a
            r[col] = pr.get("votes")
            party_totals[a] = party_totals.get(a, 0) + (pr.get("votes") or 0)
        r["mandates"] = next((pr.get("mandates") for pr in cur.get("resultsParty") or [] if pr.get("mandates")), None)
        rows.append(r)

        prev = data.get("previousResults")
        if prev:
            pr_row = base_row(prev)
            for pr in prev.get("resultsParty") or []:
                a = pr.get("acronym")
                if a:
                    pr_row["votes:" + a] = pr.get("votes")
            prev_rows.append(pr_row)

    parties = [a for a, _ in sorted(party_totals.items(), key=lambda kv: -kv[1])]

    def write_csv(fname, rs):
        cols = ["key", "level", "name", "path", "parent_key", "registered_voters", "voted",
                "turnout_pct", "blank_votes", "null_votes"] + ["votes:" + a for a in parties] + ["mandates"]
        with open(os.path.join(args.data_dir, fname), "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(sorted(rs, key=lambda r: r["path"]))

    write_csv("results_all.csv", rows)
    write_csv("results_all_previous.csv", prev_rows)

    # levels: 0 — roots (country/global), 1 — districts, 2 — municipalities, 3+ — parishes/consulates
    write_csv("results_circulos.csv", [r for r in rows if r["level"] == 1])
    write_csv("results_concelhos.csv", [r for r in rows if r["level"] == 2])
    write_csv("results_freguesias.csv", [r for r in rows if (r["level"] or 0) >= 3])
    print(f"rows: all={len(rows)} circulos={sum(1 for r in rows if r['level']==1)} "
          f"concelhos={sum(1 for r in rows if r['level']==2)} "
          f"freguesias+={sum(1 for r in rows if (r['level'] or 0)>=3)} previous={len(prev_rows)}")


if __name__ == "__main__":
    main()
