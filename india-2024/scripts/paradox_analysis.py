"""Voting-paradox analysis for the Lok Sabha elections (per paradoxes.md taxonomy).

Checks what official plurality counts can support:
  1. Frustrated-majority bound: a winner with >50% of candidate votes is the
     Condorcet winner by construction, so the paradox is impossible there;
     below 50% it remains possible but unverifiable from counts.
  2. Spoiler effect: any non-top-two candidate whose votes exceed the
     winner's margin (arithmetic, no behavioural assumption).
  3. Alliance consolidation (2024): two-bloc counterfactuals from
     data/alliances_2024.csv (NDA vs INDIA seat arithmetic).
  4. UP booth-level transfer plausibility (Form 20 recovery): booth-share
     correlations spoiler-vs-runner-up vs spoiler-vs-winner, permutation-tested.

Not checkable from any FPTP count (no ranked ballots exist): Condorcet
loser, center squeeze, best-is-worst, lesser-evil. Later-no-harm is vacuous
for plurality; no-show/perverse response/monotonicity are multi-round or
counterfactual procedures with nothing to observe in a single-round FPTP count.

Run: uv run python scripts/paradox_analysis.py
Outputs: analysis_paradoxes/ (pc_paradoxes_{year}.csv, alliance_2024.csv,
summary_by_year.csv, up_booth_transfer_2024.csv, up_party_correlations_2024.csv,
summary.json)
"""
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas", "numpy"]
# ///
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis_paradoxes"
NOTA_NAMES = {"NOTA", "None of the Above"}


class Bloc(StrEnum):
    NDA = "NDA"
    INDIA = "INDIA"
    OTHER = "OTHER"


@dataclass(frozen=True)
class Candidacy:
    party: str
    votes: int


@dataclass(frozen=True)
class SeatStats:
    year: int
    state: str
    pc: str
    n_candidates: int
    valid_votes: int
    nota_votes: int
    winner_party: str
    winner_votes: int
    winner_share: float
    runner_party: str
    runner_votes: int
    margin: int
    majority: bool
    n_spoilers: int
    spoiler1_party: str
    spoiler1_votes: int
    spoiler1_over: int
    losers_combined_over: int


# ---------------------------------------------------------------- loading

def _load_2024() -> pd.DataFrame:
    d = pd.read_csv(ROOT / "data/results_pc/in-rolls_2024_constituencywise_detailed_result.csv")
    d.columns = [c.replace("\n", " ").strip() for c in d.columns]
    junk = d["State Name"].isin(["Disclaimer"]) | d["State Name"].str.startswith(("Note -", "These statistical"))
    d = d[~junk]
    d = d[d["Total"].notna()]
    return pd.DataFrame(
        {
            "state": d["State Name"].str.strip(),
            "pc": d["PC Name"].str.strip(),
            "party": d["Party Name"].astype(str).str.strip(),
            "votes": d["Total"].astype(int),
            "year": 2024,
        }
    )


def _load_2014() -> pd.DataFrame:
    d = pd.read_csv(ROOT / "data/control_2014/eci-2014-candidate-wise.csv")
    return pd.DataFrame(
        {
            "state": d["State"].str.strip(),
            "pc": d["Constituency"].str.strip(),
            "party": d["Party"].astype(str).str.strip(),
            "votes": d["Votes"].astype(int),
            "year": 2014,
        }
    )


def _load_2019() -> pd.DataFrame:
    d = pd.read_csv(ROOT / "data/control_2019/eci-2019.csv")
    return pd.DataFrame(
        {
            "state": d["State"].str.strip(),
            "pc": d["Constituency"].str.strip(),
            "party": d["Party"].astype(str).str.strip(),
            "votes": d["Total Votes"].astype(int),
            "year": 2019,
        }
    )


def load_years() -> dict[int, pd.DataFrame]:
    return {2024: _load_2024(), 2019: _load_2019(), 2014: _load_2014()}


# ------------------------------------------------------------- seat logic

def seat_stats(year: int, state: str, pc: str, cands: pd.DataFrame) -> SeatStats:
    cand = cands[~cands["party"].isin(NOTA_NAMES)].sort_values("votes", ascending=False)
    nota = int(cands[cands["party"].isin(NOTA_NAMES)]["votes"].sum())
    valid = int(cand["votes"].sum())
    top = cand.iloc[0]
    runner = cand.iloc[1]
    margin = int(top["votes"] - runner["votes"])
    rest = cand.iloc[2:]
    spoilers = rest[rest["votes"] > margin]
    big = spoilers.iloc[0] if len(spoilers) else pd.Series(dtype=float)
    return SeatStats(
        year=year,
        state=state,
        pc=pc,
        n_candidates=len(cand),
        valid_votes=valid,
        nota_votes=nota,
        winner_party=str(top["party"]),
        winner_votes=int(top["votes"]),
        winner_share=round(float(top["votes"]) / valid, 4),
        runner_party=str(runner["party"]),
        runner_votes=int(runner["votes"]),
        margin=margin,
        majority=float(top["votes"]) / valid > 0.5,
        n_spoilers=len(spoilers),
        spoiler1_party=str(big["party"]) if len(spoilers) else "",
        spoiler1_votes=int(big["votes"]) if len(spoilers) else 0,
        spoiler1_over=int(big["votes"]) - margin if len(spoilers) else 0,
        losers_combined_over=int(rest["votes"].sum()) - margin,
    )


def analyse_national(years: dict[int, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[SeatStats] = []
    for year, d in sorted(years.items(), reverse=True):
        for (state, pc), grp in d.groupby(["state", "pc"]):
            rows.append(seat_stats(year, state, pc, grp))
    per_seat = pd.DataFrame([asdict(r) for r in rows])
    for year in years:
        per_seat[per_seat["year"] == year].to_csv(OUT / f"pc_paradoxes_{year}.csv", index=False)

    summary = []
    for year, g in per_seat.groupby("year"):
        summary.append(
            {
                "year": year,
                "seats": len(g),
                "median_winner_share": round(g["winner_share"].median(), 4),
                "seats_winner_over_50": int(g["majority"].sum()),
                "seats_winner_under_50": int((~g["majority"]).sum()),
                "spoiler_seats": int((g["n_spoilers"] > 0).sum()),
                "spoiler_seat_share": round(float((g["n_spoilers"] > 0).mean()), 4),
                "mean_spoilers_when_any": round(float(g.loc[g["n_spoilers"] > 0, "n_spoilers"].mean()), 2),
            }
        )
    s = pd.DataFrame(summary).sort_values("year", ascending=False)
    s.to_csv(OUT / "summary_by_year.csv", index=False)
    return per_seat, s


# --------------------------------------------------------- alliance logic

def analyse_alliance(d24: pd.DataFrame) -> pd.DataFrame:
    amap = pd.read_csv(ROOT / "data/alliances_2024.csv")
    bloc_of = dict(zip(amap["code"], amap["bloc"]))

    d = d24[~d24["party"].isin(NOTA_NAMES)].copy()
    d["bloc"] = d["party"].map(bloc_of).fillna(Bloc.OTHER)
    covered = d.loc[d["bloc"] != Bloc.OTHER, "votes"].sum() / d["votes"].sum()

    rows = []
    for (state, pc), grp in d.groupby(["state", "pc"]):
        nda = int(grp.loc[grp["bloc"] == Bloc.NDA, "votes"].sum())
        india = int(grp.loc[grp["bloc"] == Bloc.INDIA, "votes"].sum())
        best_other = grp.loc[grp["bloc"] == Bloc.OTHER].nlargest(1, "votes")
        other = int(best_other["votes"].iloc[0]) if len(best_other) else 0
        other_party = str(best_other["party"].iloc[0]) if len(best_other) else ""
        # one-sided consolidation: the united bloc's pooled votes against the
        # best individual candidate OUTSIDE the bloc — the rival bloc stays
        # split exactly as it actually was, third parties keep their votes
        best_non_india = int(grp.loc[grp["bloc"] != Bloc.INDIA, "votes"].max())
        best_non_nda = int(grp.loc[grp["bloc"] != Bloc.NDA, "votes"].max())
        win = grp.nlargest(1, "votes").iloc[0]
        win_bloc = str(win["bloc"])
        india_flips = india > best_non_india and win_bloc != str(Bloc.INDIA)
        nda_flips = nda > best_non_nda and win_bloc != str(Bloc.NDA)
        rows.append(
            {
                "state": state,
                "pc": pc,
                "winner_party": str(win["party"]),
                "winner_bloc": win_bloc,
                "winner_votes": int(win["votes"]),
                "nda_votes": nda,
                "india_votes": india,
                "best_other_party": other_party,
                "best_other_votes": other,
                "flip_if_india_unites": india_flips,
                "flip_if_nda_unites": nda_flips,
            }
        )
    a = pd.DataFrame(rows)
    a["year"] = 2024
    a.to_csv(OUT / "alliance_2024.csv", index=False)
    a.attrs["coverage"] = round(float(covered), 4)
    return a


# ------------------------------------------------------------ booth logic

def _wpearson(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    mx = np.average(x, weights=w)
    my = np.average(y, weights=w)
    cov = np.average((x - mx) * (y - my), weights=w)
    vx = np.average((x - mx) ** 2, weights=w)
    vy = np.average((y - my) ** 2, weights=w)
    return float(cov / np.sqrt(vx * vy)) if vx > 0 and vy > 0 else np.nan


def analyse_up_booths() -> tuple[pd.DataFrame, pd.DataFrame]:
    booths = pd.read_csv(ROOT / "release/up_booths_2024.csv.gz")
    amap = pd.read_csv(ROOT / "data/mai_up_ac_2024/pc_candidate_party_map.csv")
    amap["candidate"] = amap["col"].str.extract(r"c(\d+)").astype(int)
    pmap = dict(zip(amap["pc"], amap["party"]))
    cmap = {(pc, int(c)): p for pc, c, p in zip(amap["pc"], amap["candidate"], amap["party"])}

    booths["party"] = [cmap.get((pc, c), "IND") for pc, c in zip(booths["pc_name"], booths["candidate"])]
    booths = booths[~booths["party"].isin(NOTA_NAMES) & (booths["party"] != "IND")]
    booths = booths[booths["valid"] >= 50]

    rng = np.random.default_rng(20261016)
    n_perm = 2000
    transfer_rows, corr_rows = [], []

    for pc, grp in booths.groupby("pc_name"):
        booth_valid = grp.groupby(["ac_no", "ps_serial"])["valid"].first()
        piv = grp.pivot_table(index=["ac_no", "ps_serial"], columns="party", values="votes", aggfunc="sum").fillna(0)
        piv = piv.reindex(booth_valid.index)
        w = booth_valid.to_numpy(dtype=float)
        shares = piv.div(booth_valid, axis=0)

        totals = piv.sum().sort_values(ascending=False)
        if len(totals) < 3:
            continue
        win_p, run_p = totals.index[0], totals.index[1]
        margin = int(totals.iloc[0] - totals.iloc[1])
        rest = totals.iloc[2:]
        spoilers = rest[rest > margin]

        major = [p for p in ("BJP", "SP", "INC", "BSP", "RLD") if p in shares]
        corr_rows.append(
            {
                "pc": pc,
                "booths": len(piv),
                "valid_votes": int(booth_valid.sum()),
                **{
                    f"r_{a}_{b}": round(_wpearson(shares[a].to_numpy(), shares[b].to_numpy(), w), 3)
                    for i, a in enumerate(major)
                    for b in major[i + 1:]
                },
            }
        )

        for sp_p, sp_v in spoilers.items():
            if sp_p not in shares or sp_p in (win_p, run_p):
                continue
            s = shares[sp_p].to_numpy()
            r_sr = _wpearson(s, shares[run_p].to_numpy(), w)
            r_sw = _wpearson(s, shares[win_p].to_numpy(), w)
            obs = r_sr - r_sw
            perm = np.empty(n_perm)
            for i in range(n_perm):
                ps = rng.permutation(s)
                perm[i] = _wpearson(ps, shares[run_p].to_numpy(), w) - _wpearson(ps, shares[win_p].to_numpy(), w)
            p_val = float((1 + np.sum(np.abs(perm) >= abs(obs))) / (1 + n_perm))
            transfer_rows.append(
                {
                    "pc": pc,
                    "booths": len(piv),
                    "booth_coverage": round(float(booth_valid.sum() / totals.sum()), 3),
                    "winner": win_p,
                    "winner_votes": int(totals.iloc[0]),
                    "runner": run_p,
                    "runner_votes": int(totals.iloc[1]),
                    "margin": margin,
                    "spoiler": sp_p,
                    "spoiler_votes": int(sp_v),
                    "spoiler_over_margin": int(sp_v - margin),
                    "r_spoiler_runner": round(r_sr, 3),
                    "r_spoiler_winner": round(r_sw, 3),
                    "diff": round(obs, 3),
                    "perm_p_two_sided": round(p_val, 4),
                }
            )

    tr = pd.DataFrame(transfer_rows).sort_values("spoiler_votes", ascending=False)
    co = pd.DataFrame(corr_rows)
    tr.to_csv(OUT / "up_booth_transfer_2024.csv", index=False)
    co.to_csv(OUT / "up_party_correlations_2024.csv", index=False)
    return tr, co


# ------------------------------------------------------------------ main

def main() -> None:
    OUT.mkdir(exist_ok=True)
    years = load_years()
    per_seat, summary = analyse_national(years)
    d24 = years[2024]
    alliance = analyse_alliance(d24)
    transfer, corr = analyse_up_booths()

    nda_now = int((alliance["winner_bloc"] == Bloc.NDA).sum())
    india_now = int((alliance["winner_bloc"] == Bloc.INDIA).sum())
    other_now = len(alliance) - nda_now - india_now
    india_gain = int(alliance["flip_if_india_unites"].sum())
    nda_gain = int(alliance["flip_if_nda_unites"].sum())
    both = alliance[alliance["flip_if_india_unites"] | alliance["flip_if_nda_unites"]]

    bj = {
        "per_year": summary.to_dict(orient="records"),
        "bloc_mapped_vote_share_2024": alliance.attrs["coverage"],
        "bloc_seats_2024": {"NDA": nda_now, "INDIA": india_now, "OTHER": other_now},
        "seats_flipped_if_india_unites": india_gain,
        "seats_flipped_if_nda_unites": nda_gain,
        "seats_flipped_if_either_unites": len(both),
        "up_booth_spoiler_cases": len(transfer),
        "up_booth_significant_overlap": int((transfer["perm_p_two_sided"] < 0.05).sum()),
    }
    (OUT / "summary.json").write_text(json.dumps(bj, indent=2))

    print(summary.to_string(index=False))
    print(f"\nbloc-mapped vote share 2024: {alliance.attrs['coverage']:.1%}")
    print(f"seats now: NDA {nda_now} / INDIA {india_now} / other {other_now}")
    print(f"if INDIA unites everywhere: +{india_gain} for INDIA bloc")
    print(f"if NDA unites everywhere:  +{nda_gain} for NDA bloc")
    print(f"UP booth spoiler cases: {len(transfer)}, p<0.05: {int((transfer['perm_p_two_sided'] < 0.05).sum())}")


if __name__ == "__main__":
    main()
