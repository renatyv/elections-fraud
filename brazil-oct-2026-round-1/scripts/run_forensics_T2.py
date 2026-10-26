#!/usr/bin/env python3
"""Election forensics: Brazil, president, 2nd round (runoff) 25.10.2026 (seção level).

The same method set as run_forensics.py (1st round), on data/secoes_presidente_2026_T2.csv:
Shpilkin, Klimek fingerprints, Kobak integer peaks, 2D correlations, Benford/last
digit, outliers vs neighbors, Isolation Forest, self-test, Brazilian checks.
The runoff has two candidates — Lula (leader, 51.79%) and Flávio Bolsonaro (48.21%).

Run: cd analysis-tool && uv run python ../brazil-oct-2026-round-1/scripts/run_forensics_T2.py
Output: brazil-oct-2026-round-1/analysis_T2/{figures,tables,metrics_T2.json}

Flags: --lang ru|en|pt|es — figure label language (default en);
--fig-out DIR — write outputs into DIR instead of brazil-oct-2026-round-1/analysis_T2/.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

BR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "analysis-tool" / "src"))

from election_forensics import plots  # noqa: E402
from election_forensics.anomaly_ml import isolation_forest_anomalies  # noqa: E402
from election_forensics.correlations import turnout_result_correlations, weighted_pearson  # noqa: E402
from election_forensics.data import ElectionData, major_parties, national_totals  # noqa: E402
from election_forensics.digit_tests import BENFORD_2ND, digit_freqs, digit_null_band, digit_test  # noqa: E402
from election_forensics import digit_tests as dt  # noqa: E402
from election_forensics.fingerprints import fingerprint_mixture  # noqa: E402
from election_forensics.integer_peaks import integer_peaks  # noqa: E402
from election_forensics.selftest import inject_additive_fraud, run_selftest  # noqa: E402
from election_forensics.shpilkin import shpilkin_estimate  # noqa: E402

OUT = BR / "analysis_T2"
FIG = OUT / "figures"
TAB = OUT / "tables"

LEADER = "votes:LULA"        # 51.79% of valid
RUNNER_UP = "votes:BOLSONARO"

DATA_TITLES = {
    "ru": "Бразилия, президент 2-й тур 25.10.2026 (seções)",
    "en": "Brazil, presidential runoff 25.10.2026 (seções)",
    "pt": "Brasil, presidencial 2.º turno 25.10.2026 (seções)",
    "es": "Brasil, presidencial 2.ª vuelta 25.10.2026 (secciones)",
}
DIGITS_POOL_LABEL = {
    "ru": "Лула + Болсонару, пул",
    "en": "Lula + Bolsonaro, pooled",
    "pt": "Lula + Bolsonaro, agregado",
    "es": "Lula + Bolsonaro, agrupado",
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _digits_fast(counts: np.ndarray, test: str) -> np.ndarray:
    """Vectorized equivalent of digit_tests._digits (numbers < 10 filtered out by MIN_COUNT)."""
    counts = np.asarray(counts, dtype=np.int64)
    if test == "last":
        return counts % 10
    d = np.floor(np.log10(np.maximum(counts, 1))).astype(np.int64)
    return (counts // np.power(10, np.maximum(d - 1, 0), dtype=np.int64)) % 10


def robust_z_outliers_fast(data: ElectionData, party: str, threshold: float = 4.0) -> pd.DataFrame:
    """Same test as neighbors.robust_z_outliers, but vectorized (~500k rows)."""
    df = data.df[["key", "name", "path", "parent_key", "registered_voters", "voted"]].copy()
    df["turnout"] = data.turnout.to_numpy()
    df["share"] = data.share(party).to_numpy()
    g = df.groupby("parent_key", group_keys=False)
    for col in ("turnout", "share"):
        med = g[col].transform("median")
        mad = (df[col] - med).abs().groupby(df["parent_key"]).transform("median")
        z = (df[col] - med) / (1.4826 * mad)
        df[f"z_{col}"] = z.where(mad > 0, 0.0)
    df["n_concelho"] = g["key"].transform("count")
    df["concelho"] = df["path"].str.split(" > ").str[-2]
    df.loc[df["n_concelho"] < 4, ["z_turnout", "z_share"]] = np.nan
    df["flag"] = df[["z_turnout", "z_share"]].abs().max(axis=1) > threshold
    return df.sort_values("z_share", key=lambda s: s.abs(), ascending=False)


def uf_correlations(data: ElectionData, parties: list[str]) -> pd.DataFrame:
    """Turnout × share correlations by state."""
    df = data.df.copy()
    df["turnout"] = data.turnout.to_numpy()
    rows = []
    for uf, g in df.groupby("uf"):
        if len(g) < 30:
            continue
        w = g["registered_voters"].to_numpy(dtype=float)
        row = {"uf": uf, "n": len(g)}
        for p in parties:
            s = 100.0 * g[p].to_numpy() / g["voted"].to_numpy()
            row[p.removeprefix("votes:")] = weighted_pearson(g["turnout"].to_numpy(), s, w)
        rows.append(row)
    return pd.DataFrame(rows).sort_values("uf").reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Election forensics: Brazil-2026 runoff (seções)")
    ap.add_argument("--lang", default="en", choices=["ru", "en", "pt", "es"],
                    help="figure label language (default en)")
    ap.add_argument("--fig-out", type=Path, default=None,
                    help="directory for figures/tables/metrics instead of brazil-oct-2026-round-1/analysis_T2/")
    args = ap.parse_args()
    lang = args.lang
    if args.fig_out is not None:
        fig_dir = args.fig_out
        tab_dir = fig_dir / "tables"
        metrics_path = fig_dir / "metrics_T2.json"
    else:
        fig_dir, tab_dir, metrics_path = FIG, TAB, OUT / "metrics_T2.json"
    fig_dir.mkdir(parents=True, exist_ok=True)
    tab_dir.mkdir(parents=True, exist_ok=True)
    dt._digits = _digits_fast  # ~500k×N numbers: a per-row python loop is too slow

    df = pd.read_csv(BR / "data" / "secoes_presidente_2026_T2.csv")
    dropped = int((df["voted"] == 0).sum())
    df = df[df["voted"] > 0].copy()
    party_cols = [c for c in df.columns if c.startswith("votes:")]
    title = DATA_TITLES[lang]
    data = ElectionData(name=title, df=df, party_cols=party_cols)
    leader, runner_up = LEADER, RUNNER_UP
    assert data.leader_party == leader, f"leader expected LULA, got {data.leader_party}"
    top = major_parties(data, top=6)
    metrics: dict = {
        "title": title,
        "national": national_totals(data),
        "leader": leader.removeprefix("votes:"),
        "n_units": data.n,
        "dropped_zero_voted": dropped,
        "checks_file": "data/secoes_presidente_2026_T2_checks.json",
    }
    log(f"data: {data.n} sections (dropped voted=0: {dropped}), leader {leader}")

    # --- 1. Shpilkin method: leader + runner-up -----------------------------
    shp_l = shpilkin_estimate(data, leader)
    shp_r = shpilkin_estimate(data, runner_up)
    metrics["shpilkin_leader"] = shp_l.to_dict()
    metrics["shpilkin_runner_up"] = shp_r.to_dict()
    plots.plot_shpilkin(data, leader, shp_l, fig_dir, lang=lang)
    (fig_dir / "shpilkin_core.png").replace(fig_dir / "shpilkin_lula.png")
    plots.plot_shpilkin(data, runner_up, shp_r, fig_dir, lang=lang)
    (fig_dir / "shpilkin_core.png").replace(fig_dir / "shpilkin_bolsonaro.png")
    log(f"Shpilkin: boundary {shp_l.t_cut:.1f}%; leader tail {shp_l.tail_votes_party:,} "
        f"({shp_l.tail_share_of_party:.2f}%), Bolsonaro {shp_r.tail_votes_party:,} "
        f"({shp_r.tail_share_of_party:.2f}%)")

    # --- 2. comet tail -------------------------------------------------------
    plots.plot_comet(data, top[:2], fig_dir, lang=lang)
    log("comet: ok")

    # --- 3. fingerprints (Klimek) --------------------------------------------
    fp_l = fingerprint_mixture(data, leader)
    fp_r = fingerprint_mixture(data, runner_up)
    metrics["fingerprint_leader"] = fp_l.to_dict()
    metrics["fingerprint_runner_up"] = fp_r.to_dict()
    plots.plot_fingerprint(data, leader, fp_l, fig_dir, lang=lang)
    (fig_dir / "fingerprint_2d.png").replace(fig_dir / "fingerprint_lula.png")
    plots.plot_fingerprint(data, runner_up, fp_r, fig_dir, lang=lang)
    (fig_dir / "fingerprint_2d.png").replace(fig_dir / "fingerprint_bolsonaro.png")
    log(f"fingerprints: 2nd component weight leader {fp_l.weight_anom:.4f} "
        f"(separated: {fp_l.separated}), Bolsonaro {fp_r.weight_anom:.4f} ({fp_r.separated})")

    # --- 4. integer peaks (Kobak) --------------------------------------------
    peaks_t = integer_peaks(data, "turnout")
    peaks_l = integer_peaks(data, f"share:{leader}")
    metrics["integer_peaks_turnout"] = {
        "observed_pct": peaks_t.observed_integer_pct, "null_pct": peaks_t.null_mean_pct,
        "z": peaks_t.z_score, "z_mult5": peaks_t.z_mult5}
    metrics["integer_peaks_leader_share"] = {
        "observed_pct": peaks_l.observed_integer_pct, "null_pct": peaks_l.null_mean_pct,
        "z": peaks_l.z_score, "z_mult5": peaks_l.z_mult5}
    plots.plot_integer_peaks(data, peaks_t, fig_dir, lang=lang)
    log(f"integer turnout percents: {peaks_t.observed_integer_pct:.2f}% vs "
        f"{peaks_t.null_mean_pct:.2f}% (z={peaks_t.z_score:.1f}); leader share z={peaks_l.z_score:.1f}")

    # --- 5. digit tests: Benford-2 + last digit -------------------------------
    benford_parties = [p for p in top if int((data.df[p] >= 10).sum()) >= 1000]
    last_parties = [p for p in top if int((data.df[p] >= 100).sum()) >= 1000]
    metrics["digit_tests_eligible"] = {
        "benford2": [p.removeprefix("votes:") for p in benford_parties],
        "last": [p.removeprefix("votes:") for p in last_parties],
    }
    benford_rows, last_rows = [], []
    for pv in benford_parties:
        benford_rows.append(digit_test(data, pv, "benford2").to_dict())
    for pv in last_parties:
        row = digit_test(data, pv, "last").to_dict()
        c = data.df[pv].to_numpy()
        digs = c[c >= 100] % 10        # same filter as the test itself
        row["excess_05"] = round(100.0 * (float(np.mean(digs == 0)) + float(np.mean(digs == 5))) - 20.0, 3)
        last_rows.append(row)
    metrics["benford2"] = benford_rows
    metrics["last_digit"] = last_rows
    pd.DataFrame(benford_rows).to_csv(tab_dir / "benford2.csv", index=False)
    pd.DataFrame(last_rows).to_csv(tab_dir / "last_digit.csv", index=False)
    pooled = np.concatenate([data.df[pv].to_numpy() for pv in last_parties])
    pool_label = DIGITS_POOL_LABEL[lang]
    plots.plot_digit_test(digit_freqs(pooled, "benford2"), BENFORD_2ND,
                          digit_null_band(pooled, "benford2"), "benford2",
                          pool_label, fig_dir, lang=lang)
    plots.plot_digit_test(digit_freqs(pooled, "last"), np.full(10, 0.1),
                          digit_null_band(pooled, "last"), "last",
                          pool_label, fig_dir, lang=lang)
    log(f"digit tests: Benford {len(benford_rows)} candidates, last digit "
        f"{len(last_rows)}; max Benford deviation "
        f"{max(r['max_dev'] for r in benford_rows):.2f} pp, last digit "
        f"{max(r['max_dev'] for r in last_rows):.2f} pp")

    # --- 6. 2D correlations: national + by states -----------------------------
    corr_nat = turnout_result_correlations(data, top)
    corr_nat.to_csv(tab_dir / "corr_national.csv", index=False)
    corr_uf = uf_correlations(data, top[:2])
    corr_uf.to_csv(tab_dir / "corr_uf.csv", index=False)
    plots.plot_correlations(corr_nat, corr_uf.rename(columns={"uf": "district"}), leader, fig_dir, lang=lang)
    metrics["correlations_national"] = corr_nat.to_dict(orient="records")
    metrics["corr_uf_leader_range"] = [float(corr_uf[leader.removeprefix("votes:")].min()),
                                       float(corr_uf[leader.removeprefix("votes:")].max())]
    log(f"correlations: national leader {corr_nat.loc[0, 'pearson_w']:.3f}, "
        f"by state from {metrics['corr_uf_leader_range'][0]:.2f} to {metrics['corr_uf_leader_range'][1]:.2f}")

    # --- 7. outliers vs neighbors (within municipality) -----------------------
    neigh = robust_z_outliers_fast(data, leader)
    flagged = neigh[neigh["flag"]]
    flagged.to_csv(tab_dir / "neighbors_flagged.csv", index=False)
    plots.plot_neighbors(neigh, fig_dir, lang=lang)
    metrics["neighbors_flagged"] = int(neigh["flag"].sum())
    metrics["neighbors_flagged_pct"] = 100.0 * float(neigh["flag"].sum()) / len(neigh)
    log(f"neighbors: |z|>4 outliers — {metrics['neighbors_flagged']} "
        f"({metrics['neighbors_flagged_pct']:.3f}% of sections)")

    # --- 8. Isolation Forest ---------------------------------------------------
    anom = isolation_forest_anomalies(data, leader)
    anom.nlargest(2000, "anomaly_score").to_csv(tab_dir / "ml_anomalies_top2000.csv", index=False)
    plots.plot_ml_anomalies(anom, fig_dir, lang=lang)
    metrics["ml_flagged"] = int(anom["is_anomaly"].sum())
    log(f"ML: anomalous sections — {metrics['ml_flagged']} (contamination=1%)")

    # --- 9. self-test -----------------------------------------------------------
    report = run_selftest(data, leader)
    injected, _ = inject_additive_fraud(data, leader)
    plots.plot_selftest(data, injected, leader, report, fig_dir, lang=lang)
    metrics["selftest"] = report.to_dict()
    log(f"self-test: signal ×{report.signal_growth:,.0f}; peaks z {report.peaks_z_clean:.1f} → "
        f"{report.peaks_z_rounded:.1f}")

    # --- 10. Brazilian checks ----------------------------------------------
    d = data.df.copy()
    d["turnout"] = data.turnout.to_numpy()
    d["share_lider"] = data.share(leader).to_numpy()
    d["share_bolsonaro"] = data.share(runner_up).to_numpy()
    g = d.groupby("urna_model")
    urna = pd.DataFrame({
        "sections": g.size(),
        "registered": g["registered_voters"].sum(),
        "turnout_pct": 100.0 * g["voted"].sum() / g["registered_voters"].sum(),
        "leader_pct": 100.0 * g[leader].sum() / g["voted"].sum(),
        "bolsonaro_pct": 100.0 * g[runner_up].sum() / g["voted"].sum(),
        "blank_pct": 100.0 * g["blank_votes"].sum() / g["voted"].sum(),
        "null_pct": 100.0 * g["null_votes"].sum() / g["voted"].sum(),
    })
    urna.to_csv(tab_dir / "urna_models.csv")
    metrics["urna_models"] = urna.reset_index().to_dict(orient="records")

    vec_cols = ["registered_voters", "voted", "blank_votes", "null_votes"] + party_cols
    dups = d.duplicated(subset=vec_cols, keep=False)
    dup_groups = d[dups].groupby(vec_cols, dropna=False).size()
    metrics["duplicate_protocols"] = {
        "rows_in_dup_groups": int(dups.sum()),
        "groups": int((dup_groups > 1).sum()),
        "max_group": int(dup_groups.max()) if len(dup_groups) else 0,
        "note": "groups with an identical electorate (including section size)",
    }
    log(f"machines: {len(urna)} models; duplicate protocols: "
        f"{metrics['duplicate_protocols']['rows_in_dup_groups']} rows in "
        f"{metrics['duplicate_protocols']['groups']} groups")

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2, default=float)
    log(f"done: {metrics_path.parent}")


if __name__ == "__main__":
    main()
