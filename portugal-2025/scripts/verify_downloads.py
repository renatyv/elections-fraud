#!/usr/bin/env python3
"""Verify MAI portal downloads: vote sums over the lowest level (parishes/
consulates) against the national total, and completeness of result files.

Usage: python3 scripts/verify_downloads.py [data/*_mai directories ...]
With no arguments checks every data/*_mai that has territory-tree.json.
"""
import glob
import json
import os
import sys


def load_result(res_dir, key):
    key = str(key)
    for f in glob.glob(os.path.join(res_dir, key + "-*.json")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d.get("data"), dict):
            d = d["data"]
        cur = d.get("currentResults")
        if cur:
            return cur
    return None


def main():
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    dirs = sys.argv[1:] or sorted(glob.glob(os.path.join(base, "*_mai")))
    ok_all = True
    for d in dirs:
        tree_p = os.path.join(d, "territory-tree.json")
        if not os.path.exists(tree_p):
            continue
        tree = json.load(open(tree_p, encoding="utf-8"))
        tree = {str(k): v for k, v in tree.items()}
        res_dirs = glob.glob(os.path.join(d, "territory-results*"))
        name = os.path.basename(d)
        if not res_dirs:
            print(f"{name}: no territory-results — skipped")
            continue
        for res_dir in res_dirs:
            files = glob.glob(os.path.join(res_dir, "*.json"))
            # national total: the tree root (parent=None) with the maximum votes;
            # in the old format this is GLOBAL-990000, in the new one "Universo Global"
            # with a numeric id
            roots = [k for k, v in tree.items() if v.get("parent") is None]
            national = None
            for cand in roots:
                r = load_result(res_dir, cand)
                if r and (national is None or (r.get("totalVoters") or 0) > national[1].get("totalVoters", 0)):
                    national = (cand, r)
            # sums over leaves; roots (level 0) are excluded — otherwise the
            # aggregate would enter the sum twice (on the old portal
            # GLOBAL-990000 is a "leaf" with an empty children list)
            leaf_votes = 0
            leaf_voters = 0
            n_missing = 0
            for k, v in tree.items():
                if v.get("children") is not None or v.get("level", 99) == 0:
                    continue
                r = load_result(res_dir, k)
                if r is None:
                    n_missing += 1
                    continue
                leaf_votes += r.get("totalVoters") or 0
                leaf_voters += r.get("subscribedVoters") or 0
            tag = os.path.basename(res_dir)
            if national is None:
                print(f"{name} [{tag}]: {len(files)} files, {n_missing} leaves without a result, "
                      f"national total not found — check the download")
                ok_all = False
                continue
            nat_key, nat = national
            dv = nat.get("totalVoters") or 0
            ds = nat.get("subscribedVoters") or 0
            # the GLOBAL national total includes votes abroad; leaves cover the whole tree
            cover_v = leaf_votes / dv * 100 if dv else 0
            cover_s = leaf_voters / ds * 100 if ds else 0
            top = ", ".join(
                f"{p['acronym']} {p.get('percentage', 0)}%"
                for p in sorted(nat.get("resultsParty") or [],
                                key=lambda x: -(x.get("votes") or 0))[:3])
            status = "OK" if n_missing == 0 and abs(cover_v - 100) < 0.5 else "CHECK NEEDED"
            if status != "OK":
                ok_all = False
            print(f"{name} [{tag}]: {status} — leaves without a result: {n_missing}; "
                  f"leaf vote sum {cover_v:.2f}% of {nat_key}; "
                  f"voters {cover_s:.2f}%; turnout {nat.get('percentageVoters')}%; top: {top}")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
