#!/usr/bin/env python3
"""Voting-paradox analyses for the BR-2026 runoff (25.10.2026).

  transfers_2026 — the 2026 R1→R2 pair as its own natural experiment: a
                row-stochastic transfer matrix fitted on matched sections
                (NNLS), out-of-sample validated, bootstrap CIs — where the
                round-1 votes of the 13 candidates (and blank/null/new voters)
                actually went in the runoff;
  validate    — the round-1 conditional scenario (PARADOXES.md §4: Lula 47.43%
                two-way, bootstrap CI 47.39–47.45) against the actual runoff
                split, with a per-origin decomposition of the miss: for every
                2026 vote type, its actual 2026 transfer rate to Lula vs the
                2022 rate the scenario borrowed for it.

Tables -> analysis/paradox/transfers_2026_*.csv,
headline numbers -> analysis/paradox/prediction_vs_actual.json.
Run from analysis-tool/: uv run python ../brazil-oct-2026-round-1/scripts/run_paradox_analysis_T2.py
                         [--bootstrap 200]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_paradox_analysis import (  # noqa: E402
    BR, DATA, OUT, RoundData, build_origins_dest, fit_transfers, load_2026,
    predicted_lula_share, validate_transfers,
)


def load_2026_t2() -> RoundData:
    df = pd.read_csv(DATA / "secoes_presidente_2026_T2.csv", dtype={"key": str})
    df = df.set_index("key")
    df["votes:BRANCO"] = df.blank_votes.astype("int64")
    df["votes:NULO"] = df.null_votes.astype("int64")
    df["votes:VOTED"] = df.voted.astype("int64")
    cands = [c.split(":", 1)[1] for c in df.columns if c.startswith("votes:")]
    return RoundData(df=df, candidates=cands)


def main() -> None:
    n_boot = 200
    if "--bootstrap" in sys.argv:
        n_boot = int(sys.argv[sys.argv.index("--bootstrap") + 1])
    OUT.mkdir(parents=True, exist_ok=True)

    r26_1 = load_2026()
    r26_2 = load_2026_t2()
    results: dict = {"n_bootstrap": n_boot}

    actual_lula_tw = 100.0 * r26_2.votes("LULA").sum() / (
        r26_2.votes("LULA").sum() + r26_2.votes("BOLSONARO").sum())
    print(f"2026 R1: {len(r26_1.df):,} sections; R2: {len(r26_2.df):,}; "
          f"actual Lula two-way {actual_lula_tw:.2f}%", flush=True)
    results["actual_2026_runoff"] = {
        "lula_votes": int(r26_2.votes("LULA").sum()),
        "bolsonaro_votes": int(r26_2.votes("BOLSONARO").sum()),
        "lula_twoway_pct": round(actual_lula_tw, 2),
        "turnout_pct": round(100.0 * r26_2.df["votes:VOTED"].sum()
                             / pd.read_csv(DATA / "secoes_presidente_2026_T2.csv",
                                           usecols=["registered_voters"])
                             .registered_voters.sum(), 2),
        "blank": int(r26_2.votes("BRANCO").sum()),
        "null": int(r26_2.votes("NULO").sum()),
    }

    # ── 1. the 2026 R1→R2 transfer matrix ───────────────────────────────────
    keys = r26_1.df.index.intersection(r26_2.df.index)
    X, Y = build_origins_dest(r26_1, r26_2, keys)
    results["match"] = {"sections_r1": len(r26_1.df), "sections_r2": len(r26_2.df),
                        "matched": len(keys)}
    model = fit_transfers(X, Y)
    model.matrix.to_csv(OUT / "transfers_2026_matrix.csv")
    rng = np.random.default_rng(42)
    cv = validate_transfers(X, Y, model, rng)
    print("cv:", cv, flush=True)
    print("2026 transfer matrix:\n", model.matrix.round(3), flush=True)

    shares = np.empty(n_boot)
    mats = np.empty((n_boot, len(model.origins), len(model.destinations)))
    n = len(X)
    for b in range(n_boot):
        s = rng.integers(0, n, n)
        m_b = fit_transfers(X.iloc[s], Y.iloc[s])
        shares[b] = predicted_lula_share(m_b, X)
        mats[b] = m_b.matrix.values
    ci = pd.DataFrame(
        {f"{o}->{d}": [np.percentile(mats[:, i, j], 2.5), np.percentile(mats[:, i, j], 97.5)]
         for i, o in enumerate(model.origins) for j, d in enumerate(model.destinations)},
        index=["lo95", "hi95"],
    ).T
    ci.to_csv(OUT / "transfers_2026_bootstrap_ci.csv")
    results["transfers_2026"] = {
        "matrix": model.matrix.round(4).to_dict(),
        "cv": cv,
        "boot_lula_twoway_ci": [round(float(np.percentile(shares, 2.5)), 4),
                                round(float(np.percentile(shares, 97.5)), 4)],
    }

    # ── 2. the round-1 scenario vs the actual runoff ──────────────────────────
    prev = json.loads((OUT / "paradox_results.json").read_text(encoding="utf-8"))
    pred_pct = prev["predict_2026"]["pairwise_lula_share_pct"]        # 47.43
    pred_ci = prev["predict_2026"]["pairwise_ci_pct"]                 # [47.39, 47.45]
    results["prediction_vs_actual"] = {
        "predicted_lula_twoway_pct": pred_pct,
        "predicted_ci_pct": pred_ci,
        "actual_lula_twoway_pct": round(actual_lula_tw, 2),
        "error_pp": round(pred_pct - actual_lula_tw, 2),
        "ci_covers_actual": bool(pred_ci[0] <= actual_lula_tw <= pred_ci[1]),
        "note": "the CI reflects model resampling only; mapping and cross-election "
                "uncertainty were excluded by construction",
    }

    # ── 3. per-origin decomposition of the miss ───────────────────────────────
    # scenario: votes of 2026 type c travel with the 2022 rates of map(c);
    # actual: the 2026 matrix above. Contribution to the two-way share.
    mapping = pd.read_csv(OUT / "mapping_2026_to_2022.csv", index_col=0)
    t22 = pd.read_csv(OUT / "transfers_2022_matrix.csv", index_col=0)
    t26 = model.matrix
    V = pd.DataFrame({c: r26_1.votes(c) for c in r26_1.candidates})
    V["BRANCO"] = r26_1.votes("BRANCO")
    V["NULO"] = r26_1.votes("NULO")
    votes_nat = {c: float(V[c].sum()) for c in V.columns}
    total_tw = float(r26_2.votes("LULA").sum() + r26_2.votes("BOLSONARO").sum())

    decomp = []
    for c in V.columns:
        origin22 = mapping.loc[c, "origin_2022"] if c in mapping.index else c
        if origin22 not in t22.index:
            continue
        v = votes_nat[c]
        r22_l = float(t22.loc[origin22, "LULA"])
        r26_l = float(t26.loc[c, "LULA"])
        r22_tw = r22_l + float(t22.loc[origin22, "BOLSONARO"])
        r26_tw = r26_l + float(t26.loc[c, "BOLSONARO"])
        decomp.append({
            "vote_type_2026": c, "origin_2022": origin22, "votes_r1_2026": int(v),
            "to_lula_2022rates": round(r22_l, 3), "to_lula_actual_2026": round(r26_l, 3),
            "twoway_stay_2022rates": round(r22_tw, 3),
            "twoway_stay_actual_2026": round(r26_tw, 3),
            # pp of the national two-way total: predicted-minus-actual Lula flow
            "contrib_error_pp": round(-v * (r26_l - r22_l) / (total_tw / 100.0) / 1e0, 3),
        })
    dd = pd.DataFrame(decomp)
    dd.to_csv(OUT / "prediction_decomposition.csv", index=False)
    print(dd.sort_values("contrib_error_pp"), flush=True)
    results["decomposition"] = {
        "rows": dd.sort_values("contrib_error_pp").to_dict(orient="records"),
        "sum_error_pp": round(float(dd.contrib_error_pp.sum()), 2),
    }

    (OUT / "prediction_vs_actual.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"written: {OUT / 'prediction_vs_actual.json'}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
