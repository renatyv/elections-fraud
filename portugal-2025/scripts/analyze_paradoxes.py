# Electoral-system paradoxes checkable on official Portuguese results.
#
# Covers the paradoxes of paradoxes.md that are testable with categorical
# ballots (no ranked data exists in Portugal):
#   1. Referendum paradox / multiple-district paradox — AR-2025: national
#      votes vs D'Hondt seats (PS vs CH inversion), FPTP simulation on the
#      same votes (freguesias / concelhos).
#   2. Spoiler & cloning effects — exact counterfactuals: merge or split
#      lists per círculo, re-run D'Hondt, compare seats.
#   3. Frustrated majority (bloc form) — autárquicas 2025 câmaras are pure
#      plurality: enumerate concelhos where the winning list trails the
#      opposing ideological bloc.
#   4. Runoff pathologies — presidential 2026: 1S→2S transfer matrix
#      (ecological regression), blank/null surge, center-squeeze bounds,
#      monotonicity/no-show margins (exact arithmetic).
#
# Run from the project directory (portugal-2025/):
#   uv run python scripts/analyze_paradoxes.py
# Output: analysis/paradoxes/{metrics.json, tables/*.csv}
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas", "numpy"]
# ///
from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "analysis" / "paradoxes"
TABLES = OUT / "tables"

TOTAL_SEATS = 230  # Assembleia da República

# Display names for the official list labels of AR-2025.
PARTY_LABELS = {
    "PPD/PSD.CDS-PP": "AD",
    "PPD/PSD.CDS-PP.PPM": "AD",
    "PS": "PS",
    "CH": "CH",
    "IL": "IL",
    "L": "L",
    "PCP-PEV": "PCP-PEV",
    "B.E.": "B.E.",
    "PAN": "PAN",
    "ADN": "ADN",
    "JPP": "JPP",
}

# Blocs used for the AR-2025 counterfactuals and the autárquicas check.
LEFT_BLOC = {"PS", "B.E.", "PCP-PEV", "PAN", "L"}
RIGHT_BLOC = {"PPD/PSD.CDS-PP", "PPD/PSD.CDS-PP.PPM", "CDS-PP", "IL", "CH"}


class Paradox(StrEnum):
    REFERENDUM = "referendum_paradox"
    MULTIPLE_DISTRICT = "multiple_district_paradox"
    SPOILER = "spoiler_effect"
    CLONING = "cloning_paradox"
    FRUSTRATED = "frustrated_majority"
    CENTER_SQUEEZE = "center_squeeze"
    LESSER_EVIL = "lesser_evil_voting"
    NO_SHOW = "no_show_margin"


@dataclass
class Circle:
    """One AR-2025 círculo: votes and official seats by official list."""

    name: str
    magnitude: int
    votes: dict[str, int] = field(default_factory=dict)
    official_seats: dict[str, int] = field(default_factory=dict)


@dataclass
class Scenario:
    """A counterfactual: merge (or drop) lists per circle, re-run D'Hondt."""

    name: str
    merges: list[set[str]]
    drop: set[str] = field(default_factory=set)


def dhondt(votes: dict[str, int], seats: int) -> dict[str, int]:
    """D'Hondt apportionment of `seats` over lists with positive votes."""
    alloc: dict[str, int] = {p: 0 for p in votes}
    for _ in range(seats):
        quotients = {p: v / (alloc[p] + 1) for p, v in votes.items() if v > 0}
        if not quotients:
            break
        alloc[max(quotients, key=quotients.get)] += 1
    return alloc


# ── CNE official map (xlsx, stdlib parse) ────────────────────────────────────

def load_cne_official() -> tuple[dict[str, dict[str, int]], list[str]]:
    """Official AR-2025 seats per círculo per list, from the CNE mapa xlsx.

    Returns ({circle: {list: seats}}, [circle names in column order]).
    """
    path = DATA / "cne" / "2025_ar_mapa_resultados.xlsx"
    z = zipfile.ZipFile(path)
    m = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    shared: list[str] = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(m + "si"):
            shared.append("".join(t.text or "" for t in si.iter(m + "t")))

    def col_idx(ref: str) -> int:
        letters = re.match(r"([A-Z]+)", ref).group(1)
        n = 0
        for ch in letters:
            n = n * 26 + ord(ch) - 64
        return n - 1

    rows: list[dict[int, str]] = []
    for row in ET.fromstring(z.read("xl/worksheets/sheet1.xml")).iter(m + "row"):
        cells: dict[int, str] = {}
        for c in row.iter(m + "c"):
            v = c.find(m + "v")
            if v is None:
                continue
            val = shared[int(v.text)] if c.get("t") == "s" else v.text
            cells[col_idx(c.get("r"))] = val
        rows.append(cells)

    circles = [rows[0][i] for i in range(1, 23)]  # 22 círculos + Total col 23
    seats: dict[str, dict[str, int]] = {c: {} for c in circles}
    party = None
    for cells in rows[1:]:
        first = cells.get(0, "")
        second = cells.get(1, "")
        if first in (None, "", "md") and second != "md":
            continue
        if second == "Número":
            party = str(first)
        elif second == "md" or first == "md":
            if party is None:
                continue
            start = 2 if first == "md" else 1
            for i, c in enumerate(circles):
                v = cells.get(start + i, "")
                if v not in ("", "-", None):
                    seats[c][party] = int(float(v))
    total = sum(s for c in seats.values() for s in c.values())
    if total != TOTAL_SEATS:
        raise ValueError(f"CNE map parsed {total} seats, expected {TOTAL_SEATS}")
    return seats, circles


# ── MAI results ──────────────────────────────────────────────────────────────

def _votes_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c.startswith("votes:")]


def load_ar2025_circles(cne_seats: dict[str, dict[str, int]]) -> list[Circle]:
    """MAI círculo-level votes reconciled with CNE official seats."""
    df = pd.read_csv(DATA / "legislativas2025_mai" / "results_circulos.csv",
                     encoding="utf-8-sig", dtype={"key": str})
    cne_names = {n.lower(): n for n in cne_seats}

    def canon(name: str, path: str) -> str | None:
        if name.lower() in cne_names:
            return cne_names[name.lower()]
        if "Europa" in path and "Fora" not in path:
            return cne_names["europa"]
        return cne_names["fora da europa"]

    circles: dict[str, Circle] = {}
    for _, r in df.iterrows():
        cname = canon(str(r["name"]), str(r["path"]))
        if cname is None:
            raise ValueError(f"unmapped circle row: {r['name']} ({r['path']})")
        c = circles.setdefault(cname, Circle(cname, 0))
        for col in _votes_cols(df):
            v = r.get(col)
            if pd.notna(v) and v != "":
                c.votes[col.removeprefix("votes:")] = (
                    c.votes.get(col.removeprefix("votes:"), 0) + int(v))

    for cname, lists in cne_seats.items():
        circles[cname].official_seats = lists
        circles[cname].magnitude = sum(lists.values())
    return list(circles.values())


def validate_dhondt(circles: list[Circle]) -> None:
    """Our D'Hondt engine must reproduce the official CNE allocation exactly."""
    for c in circles:
        got = dhondt(c.votes, c.magnitude)
        if got != c.official_seats:
            diff = {p: (c.official_seats.get(p, 0), got.get(p, 0))
                    for p in set(got) | set(c.official_seats)
                    if got.get(p, 0) != c.official_seats.get(p, 0)}
            raise ValueError(f"D'Hondt mismatch in {c.name}: {diff}")


# ── 1. Referendum paradox + FPTP simulation (AR-2025) ────────────────────────

def national_totals(circles: list[Circle]) -> dict[str, int]:
    tot: dict[str, int] = {}
    for c in circles:
        for p, v in c.votes.items():
            tot[p] = tot.get(p, 0) + v
    return tot


def referendum_paradox(circles: list[Circle]) -> dict:
    tot = national_totals(circles)
    ps, ch = tot["PS"], tot["CH"]
    seats: dict[str, int] = {}
    for c in circles:
        for p, s in c.official_seats.items():
            seats[p] = seats.get(p, 0) + s
    nat_dhondt = dhondt(tot, TOTAL_SEATS)
    return {
        "paradox": Paradox.REFERENDUM,
        "ps_votes": ps, "ch_votes": ch, "vote_margin_ps_over_ch": ps - ch,
        "ps_seats": seats.get("PS", 0), "ch_seats": seats.get("CH", 0),
        "seat_margin_ch_over_ps": seats.get("CH", 0) - seats.get("PS", 0),
        "national_single_district_dhondt": nat_dhondt,
        "inversion_present": (ps > ch) and (seats.get("CH", 0) > seats.get("PS", 0)),
    }


def fptp_simulation() -> dict:
    """Winner-take-all on the same AR-2025 votes: freguesias and concelhos."""
    out = {}
    for level, fname, unit in ((3, "results_freguesias.csv", "freguesias"),
                               (2, "results_concelhos.csv", "concelhos")):
        df = pd.read_csv(DATA / "legislativas2025_mai" / fname,
                         encoding="utf-8-sig", dtype={"key": str})
        df = df[df["level"] == level]
        cols = _votes_cols(df)
        votes = df[cols].fillna(0).astype(int)
        votes.columns = [PARTY_LABELS.get(c.removeprefix("votes:"),
                                          c.removeprefix("votes:")) for c in cols]
        votes = votes.groupby(level=0, axis=1).sum()  # merge AD variants
        winners = votes.idxmax(axis=1).map(lambda p: PARTY_LABELS.get(p, p))
        counts = winners.value_counts().to_dict()
        n = len(winners)
        leader = max(counts, key=counts.get)
        out[unit] = {
            "paradox": Paradox.MULTIPLE_DISTRICT,
            "n_districts": n, "wins": counts,
            "leader": leader, "leader_share": counts[leader] / n,
            "leader_majority": counts[leader] > n / 2,
        }
    return out


# ── 2. Spoiler / cloning counterfactuals (AR-2025) ─────────────────────────

def apply_scenario(circles: list[Circle], sc: Scenario) -> dict[str, int]:
    """Re-run D'Hondt per círculo with lists merged/dropped per the scenario."""
    seats: dict[str, int] = {}
    for c in circles:
        votes = {p: v for p, v in c.votes.items() if p not in sc.drop}
        for group in sc.merges:
            present = [p for p in group if p in votes]
            if not present:
                continue
            label = "+".join(sorted(present))
            votes[label] = sum(votes.pop(p) for p in present)
        for p, s in dhondt(votes, c.magnitude).items():
            seats[p] = seats.get(p, 0) + s
    # merge AD variants for display
    out: dict[str, int] = {}
    for p, s in seats.items():
        out[PARTY_LABELS.get(p, p)] = out.get(PARTY_LABELS.get(p, p), 0) + s
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def counterfactuals(circles: list[Circle]) -> dict[str, dict]:
    psd_cds_split = load_psd_cds_split()
    scenarios = [
        Scenario("AD+CH united right", [{"PPD/PSD.CDS-PP", "PPD/PSD.CDS-PP.PPM", "CH"}]),
        Scenario("Left united (PS+BE+PCP+PAN+L)", [{p for p in LEFT_BLOC}]),
        Scenario("IL does not run", [], drop={"IL"}),
    ]
    results = {}
    for sc in scenarios:
        results[sc.name] = apply_scenario(circles, sc)
    results["AD splits (PSD/CDS as in 2022)"] = split_ad(circles, psd_cds_split)
    return results


def load_psd_cds_split() -> dict[str, float]:
    """PSD vs CDS-PP share of the combined 2022 vote, per círculo."""
    df = pd.read_csv(DATA / "legislativas2022_mai" / "results_circulos.csv",
                     encoding="utf-8-sig", dtype={"key": str})
    split: dict[str, float] = {}
    for _, r in df.iterrows():
        psd = r.get("votes:PPD/PSD", 0) or 0
        cds = r.get("votes:CDS-PP", 0) or 0
        both = int(psd) + int(cds)
        if both > 0:
            split[str(r["name"])] = int(psd) / both
    return split


def split_ad(circles: list[Circle], split_2022: dict[str, float]) -> dict[str, int]:
    """Cloning counterfactual: AD's votes split between PSD and CDS-PP lists
    with the per-circle PSD:CDS ratio observed in 2022, then D'Hondt."""
    seats: dict[str, int] = {}
    for c in circles:
        votes = dict(c.votes)
        ad_total = (votes.pop("PPD/PSD.CDS-PP", 0)
                    + votes.pop("PPD/PSD.CDS-PP.PPM", 0))
        share = next((v for k, v in split_2022.items() if k.lower() in c.name.lower()),
                     0.85)
        votes["PPD/PSD"] = int(ad_total * share)
        votes["CDS-PP"] = ad_total - int(ad_total * share)
        for p, s in dhondt(votes, c.magnitude).items():
            seats[p] = seats.get(p, 0) + s
    out: dict[str, int] = {}
    for p, s in seats.items():
        out[PARTY_LABELS.get(p, p)] = out.get(PARTY_LABELS.get(p, p), 0) + s
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


# ── 3. Frustrated majority in autárquicas (real FPP races) ──────────────────

def autarquicas_fpp() -> dict:
    df = pd.read_csv(DATA / "autarquicas2025_mai" / "results_concelhos.csv",
                     encoding="utf-8-sig", dtype={"key": str})
    cols = _votes_cols(df)
    votes = df[cols].fillna(0).astype(int)
    votes.columns = [c.removeprefix("votes:") for c in cols]

    rows = []
    for (_, r), v in zip(df.iterrows(), votes.iterrows()):
        lists = votes.loc[v[0]]
        winner = lists.idxmax()
        w = int(lists[winner])
        fams = {name: family(name) for name in lists.index}
        blocs = {"left": 0, "right": 0}
        for name, val in lists.items():
            fam = fams[name]
            if name == winner:
                continue
            if fam in ("socialist", "communist", "left", "green"):
                blocs["left"] += int(val)
            elif fam in ("right", "far_right", "liberal"):
                blocs["right"] += int(val)
        winner_bloc = fams[winner]
        loser_bloc = "right" if winner_bloc in ("socialist", "communist",
                                                "left", "green") else "left"
        # votes of the winner's own bloc that went to other lists
        own_bloc_split = sum(int(val) for name, val in lists.items()
                             if name != winner
                             and fams[name] == winner_bloc
                             and fams[name] not in ("local", "regional"))
        valid = w + int(df.loc[v[0], "blank_votes"] or 0)
        rows.append({
            "concelho": r["name"], "registered": int(r["registered_voters"]),
            "winner": winner, "winner_votes": w,
            "winner_share": w / max(1, int(lists.sum())),
            "winner_family": winner_bloc,
            "loser_bloc": loser_bloc if winner_bloc in ("socialist", "communist",
                                                        "left", "green", "right",
                                                        "far_right", "liberal") else None,
            "loser_bloc_votes": blocs[loser_bloc] if winner_bloc in (
                "socialist", "communist", "left", "green", "right", "far_right",
                "liberal") else 0,
            "own_bloc_split_votes": own_bloc_split,
        })
    t = pd.DataFrame(rows)
    t["frustrated"] = t["loser_bloc_votes"] > t["winner_votes"]
    frustrated = t[t["frustrated"]].sort_values("registered", ascending=False)
    under50 = (t["winner_share"] < 0.5).sum()
    return {
        "paradox": Paradox.FRUSTRATED,
        "n_concelhos": len(t),
        "winners_under_50pct": int(under50),
        "frustrated_count": int(t["frustrated"].sum()),
        "frustrated_by_bloc": frustrated["winner_family"].value_counts().to_dict(),
        "biggest_frustrated": frustrated.head(12)[
            ["concelho", "winner", "winner_votes", "winner_share",
             "loser_bloc", "loser_bloc_votes"]].to_dict("records"),
        "table": t,
    }


def family(list_name: str) -> str:
    """Ideological family of an autárquicas list label (name heuristics)."""
    n = list_name.strip()
    if n.startswith("PPD/PSD") or n.startswith("CDS"):
        return "right"
    if n == "CH" or n.startswith("CH "):
        return "far_right"
    if n.startswith("PPM") or n == "ADN":
        return "right"
    if n.startswith("IL") or ".IL" in n:
        return "liberal"
    if n.startswith("PCP") or n.startswith("CDU") or n.startswith("PEV"):
        return "communist"
    if n.startswith("B.E") or n.startswith("BE") or n.startswith("MPT"):
        return "left" if not n.startswith("MPT") else "green"
    if n == "PAN" or n.startswith("PAN"):
        return "green"
    if re.fullmatch(r"L([.\- ].*)?|([A-Z0-9]+[.\- ])L$|.*[.\- ]L([.\- ].*)?", n):
        return "left"  # Livre and its local coalitions
    if n == "PS" or n.startswith("PS") and not n.startswith("PSD"):
        return "socialist"
    if re.search(r"(^|[.\- ])PS([.\- ]|$)", n):
        return "socialist"
    if n.startswith("JPP"):
        return "regional"
    return "local"


# ── 4. Presidential 2026: runoff pathologies ────────────────────────────────

CAND_SHORT = {
    "António José Seguro": "Seguro",
    "André Ventura": "Ventura",
    "João Cotrim de Figueiredo": "Cotrim",
    "Henrique Gouveia e Melo": "Gouveia",
    "Luís Marques Mendes": "Mendes",
    "Catarina Martins": "C.Martins",
    "António Filipe": "A.Filipe",
    "Manuel João Vieira": "M.J.Vieira",
    "Jorge Pinto": "J.Pinto",
    "André Pestana da Silva": "A.Pestana",
    "Humberto Correia": "H.Correia",
}


def load_presidential() -> tuple[pd.DataFrame, pd.DataFrame]:
    def load(rnd: str) -> pd.DataFrame:
        df = pd.read_csv(DATA / f"presidenciais2026_{rnd}_mai" / "results_freguesias.csv",
                         encoding="utf-8-sig", dtype={"key": str})
        df = df[~df["key"].str.startswith("FOREIGN")]
        cols = [c for c in df.columns if c.startswith("votes:")]
        out = pd.DataFrame({"key": df["key"]})
        for c in cols:
            out[CAND_SHORT.get(c.removeprefix("votes:"), c.removeprefix("votes:"))] = (
                df[c].fillna(0).astype(int))
        out["blank"] = df["blank_votes"].fillna(0).astype(int)
        out["null"] = df["null_votes"].fillna(0).astype(int)
        out["abstain"] = (df["registered_voters"] - df["voted"]).astype(int)
        return out.set_index("key")
    return load("1S"), load("2S")


def presidential_runoff() -> tuple[dict, pd.DataFrame | None]:
    d1, d2 = load_presidential()
    m: dict = {"paradox": [Paradox.CENTER_SQUEEZE, Paradox.LESSER_EVIL,
                           Paradox.NO_SHOW]}

    t1 = d1.sum()
    t2 = d2.sum()
    valid1 = t1[[c for c in d1.columns if c not in ("blank", "null", "abstain")]].sum()
    valid2 = t2["Seguro"] + t2["Ventura"]
    m["first_round"] = {c: int(v) for c, v in t1.items()}
    m["second_round"] = {c: int(v) for c, v in t2.items()}
    m["valid1"], m["valid2"] = int(valid1), int(valid2)
    m["blank_surge"] = int(t2["blank"] - t1["blank"])
    m["null_surge"] = int(t2["null"] - t1["null"])
    m["turnout_change"] = int(-(t2["abstain"] - t1["abstain"]))

    # margins: how far the runoff was from any finalist-pair change
    ordered = t1.drop(["blank", "null", "abstain"]).sort_values(ascending=False)
    m["margin_1st_over_2nd"] = int(ordered.iloc[0] - ordered.iloc[1])
    m["margin_2nd_over_3rd"] = int(ordered.iloc[1] - ordered.iloc[2])

    # center-squeeze: the three eliminated centrists combined vs each finalist
    centrists = ["Cotrim", "Gouveia", "Mendes"]
    m["centrists_combined"] = int(t1[centrists].sum())
    m["centrists_share"] = float(t1[centrists].sum() / valid1)
    m["top2_combined"] = int(t1[["Seguro", "Ventura"]].sum())
    m["top2_share"] = float(t1[["Seguro", "Ventura"]].sum() / valid1)

    # pairwise bound: Ventura's observed ceiling vs the anti-Ventura pool
    v_max = int(t2["Ventura"])
    anti_pool = int(t2["Seguro"])
    m["ventura_2s"] = v_max
    m["ventura_2s_share"] = float(v_max / valid2)
    m["anti_pool_2s"] = anti_pool
    m["defection_tolerance"] = anti_pool - v_max  # X beats V while defections < this

    # ecological transfer matrix 1S -> 2S (weighted LS, freguesia level)
    transfers, diag = ecological_transfers(d1, d2)
    m["transfers"] = transfers
    m["transfers_diag"] = diag
    return m, None


def ecological_transfers(d1: pd.DataFrame, d2: pd.DataFrame) -> tuple[dict, dict]:
    """Estimate 1S→2S transfers by freguesia-level weighted least squares.

    Sources: each ≥2% 1S candidate (others pooled), blank, null, abstain.
    Outcomes: Seguro, Ventura, blank, null, abstain in the 2S.
    Assumption (Goodman): transfer rates are homogeneous across freguesias.
    """
    t1 = d1.sum()
    cand_cols = [c for c in d1.columns if c not in ("blank", "null", "abstain")]
    big = [c for c in cand_cols if t1[c] / t1[cand_cols].sum() >= 0.02]
    small = [c for c in cand_cols if c not in big]
    d1 = d1.copy()
    d1["others"] = d1[small].sum(axis=1)
    sources = big + ["others", "blank", "null", "abstain"]
    outcomes = ["Seguro", "Ventura", "blank", "null", "abstain"]

    X = d1[sources].to_numpy(dtype=float)
    W = np.sqrt(d2["Seguro"].to_numpy(dtype=float) + d2["Ventura"] + 1)
    T = np.zeros((len(sources), len(outcomes)))
    for j, o in enumerate(outcomes):
        y = d2[o].to_numpy(dtype=float)
        beta = np.linalg.lstsq(X * W[:, None], y * W, rcond=None)[0]
        T[:, j] = np.clip(beta, 0, 1)

    transfers = {s: {o: float(T[i, j]) for j, o in enumerate(outcomes)}
                 for i, s in enumerate(sources)}
    pred = X @ T
    ss_res = float(((d2[outcomes].to_numpy(dtype=float) - pred) ** 2).sum())
    ss_tot = float(((d2[outcomes].to_numpy(dtype=float)
                     - d2[outcomes].to_numpy(dtype=float).mean(0)) ** 2).sum())
    diag = {"r2": 1 - ss_res / ss_tot,
            "pred_vs_actual_2s": {o: [float(pred[:, j].sum()),
                                      float(d2[o].sum())]
                                   for j, o in enumerate(outcomes)}}
    # renormalise rows for presentation
    for i, s in enumerate(sources):
        z = T[i].sum()
        if z > 0:
            for j in range(len(outcomes)):
                transfers[s][outcomes[j]] = float(T[i, j] / z)
    return transfers, diag


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)

    cne_seats, _ = load_cne_official()
    circles = load_ar2025_circles(cne_seats)
    validate_dhondt(circles)
    print(f"✓ D'Hondt reproduces all 22 círculos exactly "
          f"({sum(c.magnitude for c in circles)} seats)")

    metrics: dict = {}
    metrics["referendum"] = referendum_paradox(circles)
    print(f"✓ referendum paradox: PS +{metrics['referendum']['vote_margin_ps_over_ch']:,} votes, "
          f"{metrics['referendum']['seat_margin_ch_over_ps']} seats behind CH")

    metrics["fptp"] = fptp_simulation()
    for unit, r in metrics["fptp"].items():
        print(f"✓ FPTP by {unit}: leader {r['leader']} "
              f"{r['wins'].get(r['leader'], 0)}/{r['n_districts']}")

    metrics["counterfactuals"] = counterfactuals(circles)
    actual = {PARTY_LABELS.get(p, p): s for c in circles
              for p, s in c.official_seats.items()}
    actual = pd.Series(actual).groupby(level=0).sum().sort_values(ascending=False)
    metrics["counterfactuals"]["actual"] = actual.to_dict()
    print("✓ counterfactuals:", {k: max(v, key=v.get) if v else "-"
                                 for k, v in metrics["counterfactuals"].items()})

    aut = autarquicas_fpp()
    aut_table = aut.pop("table")
    metrics["autarquicas"] = aut
    aut_table.to_csv(TABLES / "autarquicas_frustrated.csv", index=False)
    print(f"✓ autárquicas: {aut['frustrated_count']}/{aut['n_concelhos']} concelhos "
          f"frustrated (winner trails opposing bloc)")

    pres, _ = presidential_runoff()
    metrics["presidential"] = pres
    print(f"✓ presidential 2026: blank surge {pres['blank_surge']:+,}; "
          f"centrists {pres['centrists_share']:.1%} eliminated")

    cf = pd.DataFrame(metrics["counterfactuals"]).fillna(0).astype(int)
    cf.to_csv(TABLES / "ar2025_counterfactual_seats.csv")
    pd.DataFrame(metrics["fptp"]).to_json(  # keep raw too
        TABLES / "fptp_raw.json", orient="index")

    def clean(o):
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, StrEnum):
            return str(o)
        return o

    (OUT / "metrics.json").write_text(
        json.dumps(clean(metrics), indent=2, ensure_ascii=False))
    print(f"\nWrote {OUT / 'metrics.json'} and {TABLES}/*.csv")


if __name__ == "__main__":
    main()
