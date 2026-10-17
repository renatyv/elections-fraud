#!/usr/bin/env python3
"""Voting-paradox analyses for the BR-2026 1st round (from the repo's paradoxes.md).

Which paradoxes of single-choice (plurality / plurality-with-runoff) voting can be
measured with per-section aggregate counts, and what they show on the 4.10.2026
presidential round (+ the 2022 both-rounds control):

  cloning     — precinct-share correlation clustering of the 13 candidates,
                vote-splitting bloc arithmetic (who are "clones", did a bloc
                jointly hold a majority its members individually lacked);
  transfers   — the 2022 runoff as a natural experiment: a row-stochastic
                R1→R2 transfer matrix fitted on 470k sections (NNLS),
                out-of-sample validated, bootstrap CIs;
  predict     — 2026 candidates mapped to 2022 origin profiles by geographic
                correlation, the 2022 transfer model applied to the 2026 round 1:
                pairwise (Condorcet) preference for the two finalists, the
                frustrated-majority verdict, and per-candidate spoiler
                counterfactuals for the round-1 result;
  desertion   — same-section presidential vote vs the party's federal-deputy
                vote (lesser-evil / strategic desertion signature).

Tables -> analysis/paradox/*.csv, headline numbers -> analysis/paradox/paradox_results.json.
Run from analysis-tool/: uv run python ../brazil-oct-2026-round-1/scripts/run_paradox_analysis.py
                         [--only cloning,transfers,predict,desertion] [--bootstrap 200]
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.optimize import nnls
from scipy.spatial.distance import squareform
from scipy.stats import spearmanr

BR = Path(__file__).resolve().parents[1]
DATA = BR / "data"
OUT = BR / "analysis" / "paradox"

FINALISTS = ("LULA", "BOLSONARO")
CLUSTER_MIN_VOTES = 200_000  # candidates below this are dropped from the clustering
MIN_VALID_FOR_SHARES = 50  # sections with fewer valid votes -> no shares

PARTY_OF_2026 = {  # presidential ballot number -> party code (2-digit, as in deputy data)
    "LULA": "13", "BOLSONARO": "22", "CURY": "70", "FERREIRA": "14",
    "CAIADO": "55", "ZEMA": "30", "SAMARA": "80", "HERTZ": "16",
    "CLARIANA": "27", "EDMILSON": "21", "GRASSI": "35", "RUI": "29",
    "LEONARDO": "28",
}


@dataclass
class RoundData:
    """Per-section counts for one round: candidate votes + BRANCO/NULO + VOTED."""

    df: pd.DataFrame  # index = section key
    candidates: list[str]

    def votes(self, name: str) -> pd.Series:
        return self.df[f"votes:{name}"]

    @property
    def valid(self) -> pd.Series:
        return self.df[[f"votes:{c}" for c in self.candidates]].sum(axis=1)


def load_2026() -> RoundData:
    df = pd.read_csv(DATA / "secoes_presidente_2026.csv", dtype={"key": str})
    df = df.set_index("key")
    cands = [c.split(":", 1)[1] for c in df.columns if c.startswith("votes:")]
    df["votes:BRANCO"] = df.blank_votes.astype("int64")
    df["votes:NULO"] = df.null_votes.astype("int64")
    df["votes:VOTED"] = df.voted.astype("int64")
    return RoundData(df=df, candidates=cands)


def load_2022(turno: int) -> RoundData:
    df = pd.read_csv(DATA / "secoes_presidente_2022.csv", dtype={"key": str})
    df = df[df.turno == turno].set_index("key")
    cands = [c.split(":", 1)[1] for c in df.columns if c.startswith("votes:")]
    # round 2: only the finalists have rows; zero the rest for a common frame
    for c in df.columns:
        if c.startswith("votes:"):
            df[c] = df[c].fillna(0).astype("int64")
    df["votes:BRANCO"] = df.blank_votes.astype("int64")
    df["votes:NULO"] = df.null_votes.astype("int64")
    df["votes:VOTED"] = df.voted.astype("int64")
    return RoundData(df=df, candidates=cands)


# ── 1. cloning ───────────────────────────────────────────────────────────────


@dataclass
class ClusteringResult:
    corr: pd.DataFrame
    labels: dict[str, int]
    blocs: dict[str, dict]  # bloc name -> {members, votes, pct_valid}
    total_valid: int


def analyse_cloning(r26: RoundData) -> ClusteringResult:
    cands = [c for c in r26.candidates if r26.votes(c).sum() >= CLUSTER_MIN_VOTES]
    shares = pd.DataFrame(
        {c: r26.votes(c) / r26.valid for c in cands},
        index=r26.df.index,
    )
    shares = shares[r26.valid >= MIN_VALID_FOR_SHARES]
    corr = shares.corr(method="spearman")

    dist = 1.0 - corr.values
    np.fill_diagonal(dist, 0.0)
    dist = np.clip((dist + dist.T) / 2.0, 0.0, None)
    link = linkage(squareform(dist, checks=False), method="average")
    labels = dict(zip(cands, fcluster(link, t=1.0, criterion="distance").tolist()))

    order = sorted(cands, key=lambda c: -r26.votes(c).sum())
    blocs: dict[str, dict] = {}
    for lbl in sorted(set(labels.values())):
        members = [c for c in order if labels[c] == lbl]
        votes = int(sum(r26.votes(c).sum() for c in members))
        blocs[f"bloc_{lbl}"] = {
            "members": members,
            "votes": votes,
            "pct_valid": round(100.0 * votes / r26.valid.sum(), 2),
        }
    corr.to_csv(OUT / "cloning_corr_spearman.csv")
    pd.DataFrame(
        [{"candidate": c, "cluster": labels[c], "votes": int(r26.votes(c).sum())} for c in order]
    ).to_csv(OUT / "cloning_clusters.csv", index=False)
    return ClusteringResult(corr=corr, labels=labels, blocs=blocs,
                            total_valid=int(r26.valid.sum()))


# ── 2. transfers 2022 ────────────────────────────────────────────────────────


@dataclass
class TransferModel:
    origins: list[str]          # R1 vote types + "NEW"
    destinations: list[str]     # R2 vote types + "NOTV2"
    matrix: pd.DataFrame        # origins × destinations, rows sum to 1


@dataclass
class TransferFit:
    model: TransferModel
    cv: dict[str, float] = field(default_factory=dict)
    boot_share_ci: tuple[float, float] = 0.0, 0.0   # bootstrap CI of Lula's two-way share
    boot_matrix_ci: pd.DataFrame | None = None       # per (origin, dest) 2.5/97.5


def build_origins_dest(r1: RoundData, r2: RoundData, keys: pd.Index) -> tuple[pd.DataFrame, pd.DataFrame]:
    a, b = r1.df.loc[keys], r2.df.loc[keys]
    origin_cols = [f"votes:{c}" for c in r1.candidates] + ["votes:BRANCO", "votes:NULO"]
    X = a[origin_cols].copy()
    X["votes:NEW"] = (b["votes:VOTED"] - a["votes:VOTED"]).clip(lower=0)
    dest_cols = [f"votes:{c}" for c in FINALISTS] + ["votes:BRANCO", "votes:NULO"]
    Y = b[dest_cols].copy()
    Y["votes:NOTV2"] = (a["votes:VOTED"] - b["votes:VOTED"]).clip(lower=0)
    X.columns = [c.split(":", 1)[1] for c in X.columns]
    Y.columns = [c.split(":", 1)[1] for c in Y.columns]
    return X.astype("int64"), Y.astype("int64")


def fit_transfers(X: pd.DataFrame, Y: pd.DataFrame) -> TransferModel:
    """Row-stochastic origin→destination matrix via per-destination NNLS + row normalisation."""
    mat = np.zeros((len(X.columns), len(Y.columns)))
    for j, dest in enumerate(Y.columns):
        beta, _ = nnls(X.values, Y[dest].values)
        mat[:, j] = beta
    # a NEW voter by definition voted in R2 -> cannot end in NOTV2
    new_i = list(X.columns).index("NEW")
    mat[new_i, list(Y.columns).index("NOTV2")] = 0.0
    mat = np.clip(mat, 0.0, None)
    mat = mat / mat.sum(axis=1, keepdims=True)
    return TransferModel(
        origins=list(X.columns), destinations=list(Y.columns),
        matrix=pd.DataFrame(mat, index=X.columns, columns=Y.columns),
    )


def predicted_lula_share(m: TransferModel, X: pd.DataFrame) -> float:
    """Model-predicted national Lula share of the two-way valid vote, given origins X."""
    P = X.values @ m.matrix.values
    i, j = m.destinations.index("LULA"), m.destinations.index("BOLSONARO")
    den = P[:, i].sum() + P[:, j].sum()
    return float(P[:, i].sum() / den) if den > 0 else float("nan")


def validate_transfers(X: pd.DataFrame, Y: pd.DataFrame, m: TransferModel, rng: np.random.Generator) -> dict[str, float]:
    """Fit on 80% of sections, predict the held-out 20%: national-share error + section MAE."""
    idx = rng.permutation(len(X))
    cut = int(0.8 * len(idx))
    train, test = idx[:cut], idx[cut:]
    m_tr = fit_transfers(X.iloc[train], Y.iloc[train])
    P = X.iloc[test].values @ m_tr.matrix.values
    obs = Y.iloc[test].values
    i, j = list(Y.columns).index("LULA"), list(Y.columns).index("BOLSONARO")
    pred_share = P[:, i].sum() / (P[:, i].sum() + P[:, j].sum())
    obs_share = obs[:, i].sum() / (obs[:, i].sum() + obs[:, j].sum())
    lula_err = 100.0 * (pred_share - obs_share) / obs_share
    mae = float(np.abs(P - obs).mean())
    r2 = 1.0 - float(((P - obs) ** 2).sum() / ((obs - obs.mean(axis=0)) ** 2).sum())
    return {"cv_lula_twoway_share_rel_err_pct": round(lula_err, 3),
            "cv_pred_share_pct": round(100.0 * pred_share, 3),
            "cv_obs_share_pct": round(100.0 * obs_share, 3),
            "cv_section_mae_votes": round(mae, 2), "cv_r2": round(r2, 4)}


def analyse_transfers(r1: RoundData, r2: RoundData, n_boot: int, seed: int = 42) -> TransferFit:
    keys = r1.df.index.intersection(r2.df.index)
    X, Y = build_origins_dest(r1, r2, keys)
    model = fit_transfers(X, Y)
    model.matrix.to_csv(OUT / "transfers_2022_matrix.csv")

    rng = np.random.default_rng(seed)
    cv = validate_transfers(X, Y, model, rng)

    shares = np.empty(n_boot)
    mats = np.empty((n_boot, len(model.origins), len(model.destinations)))
    n = len(X)
    for b in range(n_boot):
        sample = rng.integers(0, n, n)
        m_b = fit_transfers(X.iloc[sample], Y.iloc[sample])
        shares[b] = predicted_lula_share(m_b, X)
        mats[b] = m_b.matrix.values
    ci = pd.DataFrame(
        {f"{o}->{d}": [np.percentile(mats[:, i, j], 2.5), np.percentile(mats[:, i, j], 97.5)]
         for i, o in enumerate(model.origins) for j, d in enumerate(model.destinations)},
        index=["lo95", "hi95"],
    ).T
    ci.to_csv(OUT / "transfers_2022_bootstrap_ci.csv")
    fit = TransferFit(model=model, cv=cv,
                      boot_share_ci=(float(np.percentile(shares, 2.5)),
                                     float(np.percentile(shares, 97.5))))
    fit.boot_matrix_ci = ci
    return fit


# ── 3. predict 2026 ──────────────────────────────────────────────────────────


@dataclass
class Prediction:
    mapping: dict[str, dict]                    # 2026 candidate -> {origin_2022, spearman}
    pairwise_lula_share: float                  # P(Lula | two-way valid), point
    pairwise_ci: tuple[float, float]
    runoff_lula_pct: float                      # predicted R2 Lula % of valid (full model)
    runoff_ci: tuple[float, float]
    spoilers: dict[str, dict]                   # minor candidate -> counterfactual round-1


def map_candidates(r26: RoundData, r1_22: RoundData) -> dict[str, dict]:
    """Match every 2026 candidate to the 2022 origin with the most similar precinct profile."""
    keys = r26.df.index.intersection(r1_22.df.index)
    a, b = r26.df.loc[keys], r1_22.df.loc[keys]
    valid26 = r26.valid.loc[keys]
    valid22 = r1_22.valid.loc[keys]
    keep = (valid26 >= MIN_VALID_FOR_SHARES) & (valid22 >= MIN_VALID_FOR_SHARES)
    mapping: dict[str, dict] = {}
    origins22 = r1_22.candidates + ["BRANCO", "NULO"]
    for c in r26.candidates:
        s26 = (a[f"votes:{c}"] / valid26)[keep]
        best, best_r = None, -2.0
        for o in origins22:
            s22 = (b[f"votes:{o}"] / valid22)[keep]
            r = spearmanr(s26, s22).statistic
            if np.isnan(r):
                continue
            if float(r) > best_r:
                best, best_r = o, float(r)
        if best is None:  # tiny candidates with no usable profile -> null-vote origin
            best, best_r = "NULO", 0.0
        forced = c if c in ("LULA", "BOLSONARO") else best
        mapping[c] = {"origin_2022": forced, "spearman": round(best_r, 3),
                      "best_match": best}
    # non-candidate origins used by origin_totals(): transfer to themselves
    for extra in ("BRANCO", "NULO"):
        mapping[extra] = {"origin_2022": extra, "spearman": None, "best_match": extra}
    return mapping


def analyse_predict(r26: RoundData, r1_22: RoundData, fit22: TransferFit,
                    n_boot: int, seed: int = 7) -> Prediction:
    mapping = map_candidates(r26, r1_22)
    t = fit22.model.matrix
    keys = r26.df.index.intersection(r1_22.df.index)

    # origins for every 2026 section (unmatched sections use national vote totals)
    V = pd.DataFrame({c: r26.votes(c) for c in r26.candidates})
    V["BRANCO"] = r26.votes("BRANCO")
    V["NULO"] = r26.votes("NULO")

    def origin_totals(V: pd.DataFrame, mapping: dict[str, dict]) -> pd.Series:
        o = pd.Series(0.0, index=t.index)
        for c in V.columns:
            o[mapping[c]["origin_2022"]] += V[c].sum()
        return o

    o_nat = origin_totals(V, mapping)

    def pairwise_share(origin_votes: pd.Series) -> float:
        num = sum(origin_votes[o] * t.loc[o, "LULA"] for o in t.index)
        den = sum(origin_votes[o] * (t.loc[o, "LULA"] + t.loc[o, "BOLSONARO"]) for o in t.index)
        return float(num / den)

    point = pairwise_share(o_nat)

    # bootstrap: resample the transfer model over the 2022 sections
    rng = np.random.default_rng(seed)
    r2_22 = load_2022(2)
    keys22 = r1_22.df.index.intersection(r2_22.df.index)
    X22, Y22 = build_origins_dest(r1_22, r2_22, keys22)
    shares = np.empty(n_boot)
    n = len(X22)
    for b in range(n_boot):
        s = rng.integers(0, n, n)
        m_b = fit_transfers(X22.iloc[s], Y22.iloc[s])
        t_b = m_b.matrix
        num = sum(o_nat[o] * t_b.loc[o, "LULA"] for o in t_b.index)
        den = sum(o_nat[o] * (t_b.loc[o, "LULA"] + t_b.loc[o, "BOLSONARO"]) for o in t_b.index)
        shares[b] = num / den
    ci = (float(np.percentile(shares, 2.5)), float(np.percentile(shares, 97.5)))

    # full-runoff prediction (all origins incl. blank/null/dropout dynamics)
    num_r = sum(o_nat[o] * t.loc[o, "LULA"] for o in t.index)
    den_r = sum(o_nat[o] * (t.loc[o, "LULA"] + t.loc[o, "BOLSONARO"]) for o in t.index)
    # spoiler counterfactuals: candidate c absent from round 1, voters per transfer row
    spoilers: dict[str, dict] = {}
    v_lula, v_bolso = V["LULA"].sum(), V["BOLSONARO"].sum()
    for c in r26.candidates:
        if c in FINALISTS or V[c].sum() < 100_000:
            continue
        o = mapping[c]["origin_2022"]
        to_l = t.loc[o, "LULA"]
        to_b = t.loc[o, "BOLSONARO"]
        l, b = v_lula + V[c].sum() * to_l, v_bolso + V[c].sum() * to_b
        spoilers[c] = {
            "votes_2026": int(V[c].sum()),
            "to_lula": round(float(to_l), 3),
            "to_bolsonaro": round(float(to_b), 3),
            "round1_twoway_lula_if_out": round(100.0 * l / (l + b), 2),
        }
    pd.DataFrame(mapping).T.to_csv(OUT / "mapping_2026_to_2022.csv")
    return Prediction(
        mapping=mapping, pairwise_lula_share=point, pairwise_ci=ci,
        runoff_lula_pct=100.0 * num_r / den_r, runoff_ci=ci,  # two-way valid ≈ runoff valid
        spoilers=spoilers,
    )


# ── 4. desertion ─────────────────────────────────────────────────────────────


@dataclass
class DesertionResult:
    parties: dict[str, dict]  # party code -> metrics


def analyse_desertion(r26: RoundData) -> DesertionResult:
    dep = pd.read_csv(DATA / "secoes_deputado_2026_parties.csv", dtype={"key": str}).set_index("key")
    common = r26.df.index.intersection(dep.index)
    res: dict[str, dict] = {}
    for cand, party in PARTY_OF_2026.items():
        col = f"votes_p{party}"
        if col not in dep.columns:
            continue
        pres = r26.votes(cand).loc[common]
        depv = dep[col].loc[common].astype("int64")
        both = (pres + depv) > 0
        ratio = (pres / depv.replace(0, np.nan))[both & (depv > 0)]
        res[party] = {
            "candidate": cand,
            "pres_votes": int(pres.sum()),
            "dep_votes": int(depv.sum()),
            "pres_over_dep": round(float(pres.sum() / max(depv.sum(), 1)), 3),
            "median_section_ratio": round(float(ratio.median()), 3) if len(ratio) else None,
            "sections_dep_gt_pres": round(
                100.0 * float((depv > pres).sum() / max(int(both.sum()), 1)), 1),
        }
    pd.DataFrame(res).T.to_csv(OUT / "desertion_parties.csv")
    return DesertionResult(parties=res)


# ── main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    args = [a for a in sys.argv[1:]]
    only = "all"
    n_boot = 200
    if "--only" in args:
        only = args[args.index("--only") + 1]
    if "--bootstrap" in args:
        n_boot = int(args[args.index("--bootstrap") + 1])
    OUT.mkdir(parents=True, exist_ok=True)

    results: dict = {"n_bootstrap": n_boot}

    r26 = load_2026()
    print(f"2026: {len(r26.df):,} sections, {r26.valid.sum():,} valid votes", flush=True)
    totals = {c: int(r26.votes(c).sum()) for c in r26.candidates}
    print("2026 votes:", dict(sorted(totals.items(), key=lambda kv: -kv[1])), flush=True)
    results["totals_2026"] = totals

    if only in ("all", "cloning"):
        cl = analyse_cloning(r26)
        results["cloning"] = {
            "n_candidates": len(cl.corr),
            "clusters": cl.labels,
            "blocs": cl.blocs,
            "lula_vs_bloc": None,
        }
        print("cloning blocs:", json.dumps(cl.blocs, ensure_ascii=False), flush=True)

    fit22 = None
    if only in ("all", "transfers", "predict"):
        r1_22, r2_22 = load_2022(1), load_2022(2)
        print(f"2022: R1 {len(r1_22.df):,} / R2 {len(r2_22.df):,} sections", flush=True)
        fit22 = analyse_transfers(r1_22, r2_22, n_boot=n_boot)
        print("2022 transfer matrix:\n", fit22.model.matrix.round(3), flush=True)
        print("cv:", fit22.cv, flush=True)
        print("Lula two-way share 2022 bootstrap CI:", fit22.boot_share_ci, flush=True)
        results["transfers_2022"] = {
            "matrix": fit22.model.matrix.round(4).to_dict(),
            "cv": fit22.cv,
            "observed_lula_r2_pct_valid": round(
                100.0 * r2_22.votes("LULA").sum()
                / (r2_22.votes("LULA").sum() + r2_22.votes("BOLSONARO").sum()), 2),
            "boot_lula_twoway_ci": fit22.boot_share_ci,
        }

    if only in ("all", "predict") and fit22 is not None:
        r1_22 = load_2022(1)
        pred = analyse_predict(r26, r1_22, fit22, n_boot=n_boot)
        print("mapping:", json.dumps(pred.mapping, ensure_ascii=False, indent=1), flush=True)
        print(f"2026 pairwise Lula share: {pred.pairwise_lula_share:.2%} "
              f"CI {pred.pairwise_ci[0]:.2%}–{pred.pairwise_ci[1]:.2%}", flush=True)
        print("spoilers:", json.dumps(pred.spoilers, ensure_ascii=False, indent=1), flush=True)
        results["predict_2026"] = {
            "mapping": pred.mapping,
            "pairwise_lula_share_pct": round(100 * pred.pairwise_lula_share, 2),
            "pairwise_ci_pct": [round(100 * pred.pairwise_ci[0], 2),
                                round(100 * pred.pairwise_ci[1], 2)],
            "spoilers": pred.spoilers,
        }

    if only in ("all", "desertion"):
        if (DATA / "secoes_deputado_2026_parties.csv").exists():
            des = analyse_desertion(r26)
            results["desertion"] = des.parties
            print("desertion:", json.dumps(des.parties, ensure_ascii=False, indent=1), flush=True)
        else:
            print("deputy-party CSV missing — skipping desertion", flush=True)

    (OUT / "paradox_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"written: {OUT / 'paradox_results.json'}")


if __name__ == "__main__":
    sys.exit(main())
