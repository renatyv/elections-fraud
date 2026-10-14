"""Complement to the standard ef-analyze run: what the CLI lacks.

The pipeline (ef-analyze) checks the leader of the regular precincts; in all
four referendums «ZA» leads there, whereas nationwide «PROTI» won on
preiskava and rtv_prispevek. This script adds:

1. Shpilkin, integer peaks and fingerprints for the SECOND option (PROTI) —
   including the national winners preiskava/rtv_prispevek;
2. cross-referendum simultaneity checks (same precincts, one electorate):
   turnout and ZA-share correlations between referendums, duplicate vectors
   (ZA, PROTI, invalid) between the ballots of one precinct, turnout
   discrepancies between referendums;
3. digit tests (last digit) of early-voting points (precinct numbers >= 900,
   upr = 0) — the pool of all four referendums;
4. the deviation profile of the second digit (to interpret borderline p).

Data — the adapted data/ef/<referendum>/results_freguesias.csv
(scripts/build_ef_csv.py) + data/derived/volisca_all.csv (turnout gl, early).

Run (from the analysis-tool directory):

    uv run python ../sloveniya-referendum-2026/scripts/analyze_extra.py

Output: sloveniya-referendum-2026/analysis/cross/{figures/, tables/, metrics.json}.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from election_forensics import plots  # noqa: E402
from election_forensics.correlations import weighted_pearson  # noqa: E402
from election_forensics.data import ElectionData, load_mai_csv  # noqa: E402
from election_forensics.digit_tests import (  # noqa: E402
    digit_freqs,
    digit_null_band,
    digit_test,
)
from election_forensics.fingerprints import fingerprint_mixture  # noqa: E402
from election_forensics.integer_peaks import integer_peaks  # noqa: E402
from election_forensics.shpilkin import shpilkin_estimate  # noqa: E402

BASE = Path(__file__).resolve().parents[1]  # sloveniya-referendum-2026/
EF = BASE / "data" / "ef"
SRC = BASE / "data" / "derived" / "volisca_all.csv"
OUT = BASE / "analysis" / "cross"

REFS = ["preiskava", "socialna_pomoc", "volilna_pravica", "rtv_prispevek"]
REF_TITLE = {
    "preiskava": "preiskava (ZPPre-B)",
    "socialna_pomoc": "socialna_pomoc",
    "volilna_pravica": "volilna_pravica",
    "rtv_prispevek": "rtv_prispevek",
}
PARTIES = ["votes:ZA", "votes:PROTI"]
OPT_NAME = {"votes:ZA": "ZA", "votes:PROTI": "PROTI"}


def main() -> None:
    fig_dir = OUT / "figures"
    tab_dir = OUT / "tables"
    fig_dir.mkdir(parents=True, exist_ok=True)
    tab_dir.mkdir(parents=True, exist_ok=True)

    data = {r: load_mai_csv(EF / r / "results_freguesias.csv", REF_TITLE[r])
            for r in REFS}
    metrics: dict = {"title": "Slovenia 11.10.2026: cross-checks and the second option"}

    # --- 1. second option (PROTI): Shpilkin, integer peaks, fingerprints ----
    rows = []
    for r in REFS:
        d = data[r]
        shp = shpilkin_estimate(d, "votes:PROTI")
        pk = integer_peaks(d, "share:votes:PROTI")
        fp = fingerprint_mixture(d, "votes:PROTI")
        rows.append({
            "referendum": r,
            "shpilkin_t_cut": shp.t_cut, "tail_voters": shp.tail_voters,
            "tail_votes_PROTI": shp.tail_votes_party,
            "tail_share_of_PROTI_pct": shp.tail_share_of_party,
            "honest_share_pct": shp.honest_share_pct,
            "observed_share_pct": shp.observed_share_pct,
            "peaks_share_PROTI_obs_pct": pk.observed_integer_pct,
            "peaks_share_PROTI_null_pct": pk.null_mean_pct,
            "peaks_share_PROTI_z": pk.z_score,
            "fingerprint_weight_anom": fp.weight_anom,
            "fingerprint_mean_main": str(tuple(round(x, 1) for x in fp.mean_main)),
            "fingerprint_mean_anom": str(tuple(round(x, 1) for x in fp.mean_anom)),
            "fingerprint_separated": fp.separated,
        })
        print(f"[1/3] {r}: PROTI — tail {shp.tail_votes_party} "
              f"({shp.tail_share_of_party:.2f}% of PROTI votes), "
              f"share peaks z={pk.z_score:+.1f}, fingerprints w={fp.weight_anom:.3f}")
    pd.DataFrame(rows).to_csv(tab_dir / "proti_option_tests.csv", index=False)
    metrics["proti_option"] = rows

    # --- 2. cross-referendum checks -----------------------------------------
    raw = pd.read_csv(SRC)
    raw["station"] = (raw["okraj_rpeid"].astype(str) + "_"
                      + raw["volisce_rpeid"].astype(str).str.zfill(3))
    reg = raw[raw["volisce_rpeid"] < 900]

    piv_upr = reg.pivot_table(index="station", columns="referendum", values="upr", aggfunc="first")
    piv_gl = reg.pivot_table(index="station", columns="referendum", values="gl", aggfunc="first")
    w = piv_upr.iloc[:, 0].astype(float)
    t_piv = 100.0 * piv_gl.div(piv_upr.iloc[:, 0], axis=0)
    g_piv = reg.pivot_table(index="station", columns="referendum", values="glas", aggfunc="first")
    s_piv = (reg.pivot_table(index="station", columns="referendum", values="za", aggfunc="first")
             / g_piv)

    corr_t = pd.DataFrame(index=REFS, columns=REFS, dtype=float)
    corr_s = pd.DataFrame(index=REFS, columns=REFS, dtype=float)
    for a in REFS:
        for b in REFS:
            ok = t_piv[[a, b]].notna().all(axis=1)
            corr_t.loc[a, b] = weighted_pearson(t_piv.loc[ok, a], t_piv.loc[ok, b], w[ok])
            ok = s_piv[[a, b]].notna().all(axis=1)
            corr_s.loc[a, b] = weighted_pearson(
                100.0 * s_piv.loc[ok, a], 100.0 * s_piv.loc[ok, b], w[ok])
    corr_t.to_csv(tab_dir / "cross_turnout_correlation.csv")
    corr_s.to_csv(tab_dir / "cross_share_correlation.csv")
    metrics["turnout_correlation"] = corr_t.round(4).to_dict()
    metrics["share_correlation"] = corr_s.round(4).to_dict()
    print(f"[2/3] turnout correlations between referendums: "
          f"{corr_t.values[np.triu_indices(4, 1)].min():+.4f}…"
          f"{corr_t.values[np.triu_indices(4, 1)].max():+.4f}; ZA shares: "
          f"{corr_s.values[np.triu_indices(4, 1)].min():+.3f}…"
          f"{corr_s.values[np.triu_indices(4, 1)].max():+.3f}")

    # scatterplots of the ZA share between pairs of referendums
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.5), sharey=True)
    pairs = [("preiskava", "rtv_prispevek"), ("preiskava", "socialna_pomoc"),
             ("volilna_pravica", "socialna_pomoc")]
    sizes = np.clip(w / 60, 2, 60)
    for ax, (a, b) in zip(axes, pairs, strict=False):
        ax.scatter(100 * s_piv[a], 100 * s_piv[b], s=sizes.reindex(s_piv.index).to_numpy(),
                   alpha=0.25, color="#1f77b4", edgecolors="none")
        ax.set_xlabel(f"ZA, % — {a}")
        ax.set_title(f"r(weighted) = {corr_s.loc[a, b]:+.2f}", fontsize=9)
    axes[0].set_ylabel("ZA share by precinct, %")
    fig.suptitle("ZA share: pairs of simultaneous referendums (same precincts)", y=1.04, fontsize=10)
    fig.tight_layout()
    fig.savefig(fig_dir / "cross_shares.png", bbox_inches="tight", dpi=150)
    plt.close(fig)

    # turnout discrepancies between referendums (one voter — 4 ballots)
    dmax = piv_gl.max(axis=1) - piv_gl.min(axis=1)
    metrics["turnout_diff_between_referendums"] = {
        "identical": int((dmax == 0).sum()), "d1_2": int(((dmax >= 1) & (dmax <= 2)).sum()),
        "d3_5": int(((dmax >= 3) & (dmax <= 5)).sum()), "gt5": int((dmax > 5).sum()),
        "max": int(dmax.max()),
    }
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    vals, cnts = np.unique(dmax, return_counts=True)
    ax.bar(vals, cnts, color="#1f77b4", alpha=0.85)
    for v, c in zip(vals, cnts, strict=False):
        if c and (v <= 5 or v > 8):
            ax.text(v, c, str(c), ha="center", va="bottom", fontsize=7)
    ax.set_xlabel("Max turnout gap of a precinct"
                  " across the 4 referendums, ballots")
    ax.set_ylabel("Number of precincts")
    ax.set_yscale("log")
    ax.set_title("Turnout agreement: one voter — four ballots", fontsize=9)
    fig.tight_layout()
    fig.savefig(fig_dir / "turnout_diff_hist.png", bbox_inches="tight", dpi=150)
    plt.close(fig)

    # duplicate vectors between the ballots of one precinct
    v = reg.pivot_table(index="station", columns="referendum",
                        values=["za", "proti", "nev"], aggfunc="first")
    velj = reg.pivot_table(index="station", columns="referendum", values="velj", aggfunc="first")
    dup_big = []
    for st in v.index:
        vecs = {r: f"{v.loc[st, ('za', r)]}|{v.loc[st, ('proti', r)]}|{v.loc[st, ('nev', r)]}"
                for r in REFS}
        seen: dict[str, list[str]] = {}
        for r in REFS:
            if velj.loc[st, r] >= 50:
                seen.setdefault(vecs[r], []).append(r)
        for vec, rs in seen.items():
            if len(rs) > 1:
                dup_big.append({"station": st, "vector": vec, "referendums": "+".join(rs)})
    metrics["duplicate_vectors_within_station_voted_ge_50"] = dup_big
    pd.DataFrame(dup_big).to_csv(tab_dir / "duplicate_vectors_within_station.csv", index=False)
    print(f"      duplicate vectors between a precinct's ballots (valid>=50): {len(dup_big)}")

    # copy-paste control: distribution of |ΔZA| between pairs of referendums.
    # With natural coincidence (same voters, correlated positions) Δ=0 does not
    # stand out among neighboring values; with copy-paste Δ=0 would dominate.
    import itertools
    za_ok = za = reg.pivot_table(index="station", columns="referendum",
                                 values="za", aggfunc="first")
    big = reg.pivot_table(index="station", columns="referendum",
                          values="velj", aggfunc="first").max(axis=1) >= 50
    diffs = pd.Series(0, index=range(11), dtype=float)
    for a, b in itertools.combinations(REFS, 2):
        d = (za_ok[a] - za_ok[b]).abs()[big]
        diffs = diffs.add(d.value_counts().reindex(range(11), fill_value=0), fill_value=0)
    quad = 0
    for st in v.index:
        vecs = {f"{v.loc[st, ('za', r)]}|{v.loc[st, ('proti', r)]}|{v.loc[st, ('nev', r)]}"
                for r in REFS}
        if len(vecs) == 1:
            quad += 1
    diffs.to_csv(tab_dir / "cross_za_diff_distribution.csv",
                 index_label="delta_za", header=["pair_count"])
    metrics["cross_za_diff"] = {
        "d0": int(diffs[0]), "d1": int(diffs[1]), "d2": int(diffs[2]),
        "ratio_d0_d1": float(diffs[0] / max(diffs[1], 1)),
        "all_four_vectors_equal": quad,
    }
    print(f"      |ΔZA|=0: {int(diffs[0])} vs Δ=1: {int(diffs[1])} "
          f"(ratio {diffs[0] / max(diffs[1], 1):.2f}); all 4 vectors equal: {quad}")

    # duplicate vectors within one referendum against a bootstrap null:
    # stations of similar size with similar tallies collide naturally
    rng = np.random.default_rng(42)
    dup_rows = []
    for r in REFS:
        g = reg[reg.referendum == r]
        big = g[g.velj >= 50]
        velj = big["velj"].to_numpy()
        p = big["za"].to_numpy() / velj
        nev = big["nev"].to_numpy()
        obs = pd.Series(big["za"].astype(str) + "|" + big["proti"].astype(str)
                        + "|" + big["nev"].astype(str)).duplicated().sum()
        sims = []
        for _ in range(50):
            za = rng.binomial(velj - nev, p / np.maximum(1 - nev / np.maximum(velj, 1), 1e-9))
            sims.append(int(pd.Series(za.astype(str) + "|" + (velj - nev - za).astype(str)
                                      + "|" + nev.astype(str)).duplicated().sum()))
        dup_rows.append({"referendum": r, "duplicates_observed": int(obs),
                         "duplicates_null_mean": float(np.mean(sims)),
                         "duplicates_null_sd": float(np.std(sims))})
        print(f"      {r}: duplicate vectors {obs} vs null "
              f"{np.mean(sims):.1f} ± {np.std(sims):.1f}")
    metrics["duplicates_within_referendum"] = dup_rows
    pd.DataFrame(dup_rows).to_csv(tab_dir / "duplicates_within_referendum.csv", index=False)

    # --- 3. early-voting points: last digit (pool of 4 referendums) ----------
    early = raw[raw["volisce_rpeid"] >= 900]
    ed = ElectionData(
        name="Early-voting points, pool of 4 referendums",
        df=pd.DataFrame({
            "key": early["station"] + "@" + early["referendum"],
            "registered_voters": 1, "voted": early["glas"],
            "blank_votes": 0, "null_votes": early["nev"],
            "votes:ZA": early["za"], "votes:PROTI": early["proti"],
        }),
        party_cols=list(PARTIES))
    early_rows = []
    for p in PARTIES:
        res = digit_test(ed, p, "last")
        early_rows.append(res.to_dict())
        counts = ed.df[p].to_numpy()
        plots.plot_digit_test(digit_freqs(counts, "last"), np.full(10, 0.1),
                              digit_null_band(counts, "last"), "last",
                              f"early-voting points, {OPT_NAME[p]}", fig_dir)
    metrics["early_last_digit"] = early_rows
    pd.DataFrame(early_rows).to_csv(tab_dir / "early_last_digit.csv", index=False)
    print(f"[3/3] early-voting points (pool): last digit MC p "
          f"ZA {early_rows[0]['p_null_mc']:.3f}, PROTI {early_rows[1]['p_null_mc']:.3f}")

    # --- second-digit profile of socialna_pomoc/ZA (borderline Benford) ------
    counts = data["socialna_pomoc"].df["votes:ZA"].to_numpy()
    counts = counts[counts >= 10]
    d2 = np.array([int(str(int(x))[1]) for x in counts])
    obs = np.bincount(d2, minlength=10) / len(d2)
    band = digit_null_band(counts, "benford2")
    from election_forensics.digit_tests import BENFORD_2ND
    profile = pd.DataFrame({
        "digit": range(10), "observed_pct": (100 * obs).round(2),
        "benford_pct": (100 * BENFORD_2ND).round(2),
        "null_lo_pct": (100 * band[0]).round(2), "null_hi_pct": (100 * band[1]).round(2),
    })
    profile.to_csv(tab_dir / "benford2_socialna_ZA_profile.csv", index=False)
    metrics["benford2_socialna_ZA_profile"] = profile.to_dict(orient="records")

    with open(OUT / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2, default=float)
    print(f"done: {OUT}")


if __name__ == "__main__":
    main()
