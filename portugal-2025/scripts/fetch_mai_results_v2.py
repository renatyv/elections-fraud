#!/usr/bin/env python3
"""Download election results from the NEW version of the MAI/SGMAI portal (2025+).

The new portal version (elections since late 2025: autarquicas2025,
presidenciais2026_*) serves static files differently and uses numeric ids for
territories and "organs":

  <election>/app-settings.json                                        -> electionId
  <election>/assets/static/election/data-electionId=<E>.json          -> tree roots
  <election>/assets/static/territory/children-electionId=<E>-territoryId=<ID>.json
  <election>/assets/static/result/territory-electionId=<E>-territoryId=<ID>-organId=<O>.json

organId is the race type (the list for a given election is in
election/data-electionId under the organs key): PR=3 (presidential);
autarquicas2025: CM=4, AM=5, AF=6.
Inside the result file the structure is the same as before
(currentResults/previousResults/resultsParty) under the data key.

Usage:
  python3 fetch_mai_results_v2.py <slug> [--organs 3] [--out DIR]

Examples:
  python3 fetch_mai_results_v2.py presidenciais2026_1S --organs 3
  python3 fetch_mai_results_v2.py autarquicas2025 --organs 4
"""
import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

REQ_DELAY = 0.4
BLOCKED = {"flag": False}


def fetch(url, tries=3):
    """As in v1: curl + pause; on Access Denied — 90s pause and retry."""
    for i in range(tries):
        while BLOCKED["flag"]:
            time.sleep(15)
        try:
            r = subprocess.run(
                ["curl", "-sL", "--max-time", "30", "--connect-timeout", "10",
                 "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                 url],
                capture_output=True, timeout=40)
            out = r.stdout or b""
            if b"Access Denied" in out[:200] or b"<HTML>" in out[:32]:
                BLOCKED["flag"] = True
                print(f"  [blocked] {url} — pausing 90s", file=sys.stderr)
                time.sleep(90)
                BLOCKED["flag"] = False
                continue
            if r.returncode == 0 and out:
                time.sleep(REQ_DELAY)
                return out
        except Exception:
            pass
        if i < tries - 1:
            time.sleep(2 + 2 * i)
    return None


def get_json(url):
    data = fetch(url)
    if data is None or data.startswith(b"Not found"):
        return None
    try:
        return json.loads(data)
    except Exception:
        return None


def crawl(election, organs, out, leaf_level=None):
    origin = f"https://www.eleicoes.mai.gov.pt/{election}"
    os.makedirs(out, exist_ok=True)

    settings = get_json(f"{origin}/app-settings.json")
    if not settings or "electionId" not in settings:
        print(f"Failed to get electionId for {election} "
              f"(the slug does not exist or this is the old portal format — use fetch_mai_results.py)",
              file=sys.stderr)
        sys.exit(2)
    election_id = settings["electionId"]
    base = f"{origin}/assets/static"
    print(f"election: {election}, electionId={election_id}, organs={organs}", file=sys.stderr)

    # service files without a territory
    for rel in [f"election/data-electionId={election_id}.json",
                f"psconfiguration/configurations-electionId={election_id}.json",
                f"result/available-electionId={election_id}.json",
                f"votingOptions/votingOptions-electionId={election_id}.json",
                f"candidate/candidates-electionId={election_id}.json"]:
        p = os.path.join(out, rel.split("/")[-1])
        if os.path.exists(p):
            continue
        data = fetch(f"{base}/{rel}")
        if data and not data.startswith(b"Not found"):
            with open(p, "wb") as f:
                f.write(data)

    # tree roots — from election/data
    el_data = get_json(f"{base}/election/data-electionId={election_id}.json")
    roots = [t["id"] for t in (el_data or {}).get("data", {}).get("mainTerritories", [])]
    if not roots:
        print("No mainTerritories in election/data", file=sys.stderr)
        sys.exit(2)
    print(f"roots: {roots}", file=sys.stderr)

    raw_ch = os.path.join(out, "territory-children")
    os.makedirs(raw_ch, exist_ok=True)
    children_cache = {}

    def get_children(tid):
        if tid in children_cache:
            return children_cache[tid]
        p = os.path.join(raw_ch, f"{tid}.json")
        if not os.path.exists(p):
            data = fetch(f"{base}/territory/children-electionId={election_id}-territoryId={tid}.json")
            if data is None or data.startswith(b"Not found"):
                children_cache[tid] = None
                return None
            with open(p, "wb") as f:
                f.write(data)
        try:
            lst = json.load(open(p, encoding="utf-8")).get("data")
        except Exception:
            lst = None
        if not isinstance(lst, list):
            lst = None
        children_cache[tid] = lst
        return lst

    # BFS over the territory tree (leaf_level: levels >= N are leaves, not probed)
    tree = {}
    frontier = {t: (None, 0) for t in roots}
    while frontier:
        nxt = {}
        fetch_keys = [t for t, (_, lvl) in frontier.items()
                      if leaf_level is None or lvl < leaf_level]
        with ThreadPoolExecutor(max_workers=4) as ex:
            list(ex.map(get_children, fetch_keys))
        for tid, (parent, level) in frontier.items():
            if tid in tree:
                continue
            if leaf_level is not None and level >= leaf_level:
                kids = []
            else:
                kids = get_children(tid) or []
            tree[tid] = {"parent": parent, "level": level}
            tree[tid]["children"] = [c.get("id") for c in kids] or None
            for c in kids:
                cid = c.get("id")
                if cid and cid not in tree and cid not in nxt:
                    nxt[cid] = (tid, level + 1)
        frontier = nxt
        print(f"  level done: {len(tree)} territories", file=sys.stderr)

    # names/types — from the parent's children files
    for tid, info in tree.items():
        parent = info["parent"]
        if parent is not None and children_cache.get(parent):
            for c in children_cache[parent]:
                if c.get("id") == tid:
                    info["name"] = c.get("descriptionShort") or c.get("description")
                    info["typeId"] = c.get("typeId")

    with open(os.path.join(out, "territory-tree.json"), "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=1)
    print(f"territories: {len(tree)}", file=sys.stderr)

    jobs = []
    for organ in organs:
        res_dir = os.path.join(out, "territory-results" + ("" if len(organs) == 1 else f"-organ{organ}"))
        os.makedirs(res_dir, exist_ok=True)
        for tid in tree:
            jobs.append((tid, organ, res_dir))

    def dl(job):
        tid, organ, res_dir = job
        p = os.path.join(res_dir, f"{tid}-organ{organ}.json")
        if os.path.exists(p):
            return "cached"
        data = fetch(f"{base}/result/territory-electionId={election_id}-territoryId={tid}-organId={organ}.json")
        if data is None or data.startswith(b"Not found"):
            return "404"
        with open(p, "wb") as f:
            f.write(data)
        return "ok"

    stats = {"ok": 0, "cached": 0, "404": 0}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for fut in as_completed([ex.submit(dl, j) for j in jobs]):
            stats[fut.result()] += 1
    print(f"results: {stats}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("election", help="election slug, e.g. presidenciais2026_1S")
    ap.add_argument("--organs", default="3", help="comma-separated organId: PR=3; municipal CM=1,AM=2,AF=4 (check against the configuration)")
    ap.add_argument("--out", default=None, help="download directory (default ../data/<election>_mai)")
    ap.add_argument("--leaf-level", type=int, default=None,
                    help="treat levels >= N as leaves without probing children (3 = parishes)")
    args = ap.parse_args()
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", f"{args.election}_mai")
    crawl(args.election, [int(s.strip()) for s in args.organs.split(",")], os.path.normpath(out), args.leaf_level)


if __name__ == "__main__":
    main()
