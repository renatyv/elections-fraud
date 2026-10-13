"""CLI: полный прогон методов election forensics по выгрузке MAI.

Пример:
    ef-analyze --data ../portugal-2025/data/legislativas2025_mai \
               --out ../portugal-2025/analysis \
               --title "Португалия, AR 2025" \
               --controls ../portugal-2025/data/legislativas2022_mai,../portugal-2025/data/legislativas2024_mai
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import plots
from .anomaly_ml import isolation_forest_anomalies
from .correlations import district_correlations, turnout_result_correlations
from .data import load_mai_csv, major_parties, merge_parties, national_totals
from .digit_tests import BENFORD_2ND, digit_freqs, digit_null_band, digit_test
from .fingerprints import fingerprint_mixture
from .integer_peaks import integer_peaks
from .neighbors import robust_z_outliers, swing_vs_previous
from .selftest import inject_additive_fraud, run_selftest
from .shpilkin import shpilkin_estimate


def analyze(
    data_dir: str | Path,
    out_dir: str | Path,
    title: str = "",
    controls: list[str | Path] | None = None,
    prev_party: str = "",
    merge: str = "",
    run_self_test: bool = True,
) -> dict:
    data_dir = Path(data_dir)
    out_dir = Path(out_dir)
    fig_dir = out_dir / "figures"
    tab_dir = out_dir / "tables"
    fig_dir.mkdir(parents=True, exist_ok=True)
    tab_dir.mkdir(parents=True, exist_ok=True)

    csv = data_dir / "results_freguesias.csv"
    data = load_mai_csv(csv, election_name=title or data_dir.name)
    if merge:
        data = merge_parties(data, merge)
    leader = data.leader_party
    top = major_parties(data, top=6)
    control_sets = [load_mai_csv(Path(c) / "results_freguesias.csv") for c in controls or []]
    metrics: dict = {"title": title or data_dir.name, "national": national_totals(data),
                     "leader": leader.removeprefix("votes:"), "n_units": data.n}

    print(f"[1/9] данные: {data.n} территорий, лидер {leader}, контролов: {len(control_sets)}")

    # --- метод Шпилькина -------------------------------------------------
    shp = shpilkin_estimate(data, leader, controls=control_sets)
    metrics["shpilkin"] = shp.to_dict()
    plots.plot_shpilkin(data, leader, shp, fig_dir)
    print(f"[2/9] Шпилькин: граница {shp.t_cut:.1f}% ({shp.t_cut_source}); аномальных голосов "
          f"за лидера {shp.tail_votes_party:,} ({shp.tail_share_of_party:.2f}% голосов лидера); "
          f"результат без аномалии: {shp.honest_share_pct:.2f}% против {shp.observed_share_pct:.2f}%")

    # --- хвост кометы + отпечатки ----------------------------------------
    plots.plot_comet(data, top[:3], fig_dir)
    fp = fingerprint_mixture(data, leader)
    metrics["fingerprint"] = fp.to_dict()
    plots.plot_fingerprint(data, leader, fp, fig_dir)
    print(f"[3/9] отпечатки: вес 2-й компоненты {fp.weight_anom:.4f}, "
          f"разделение {'есть' if fp.separated else 'нет'}")

    # --- целочисленные пики ----------------------------------------------
    peaks_t = integer_peaks(data, "turnout")
    peaks_l = integer_peaks(data, f"share:{leader}")
    metrics["integer_peaks_turnout"] = {
        "observed_pct": peaks_t.observed_integer_pct, "null_pct": peaks_t.null_mean_pct,
        "z": peaks_t.z_score, "z_mult5": peaks_t.z_mult5}
    metrics["integer_peaks_leader_share"] = {
        "observed_pct": peaks_l.observed_integer_pct, "null_pct": peaks_l.null_mean_pct,
        "z": peaks_l.z_score, "z_mult5": peaks_l.z_mult5}
    plots.plot_integer_peaks(data, peaks_t, fig_dir)
    print(f"[4/9] целые проценты явки: {peaks_t.observed_integer_pct:.2f}% против "
          f"{peaks_t.null_mean_pct:.2f}% (z={peaks_t.z_score:.1f})")

    # --- цифровые тесты (Бенфорд, последняя цифра) ------------------------
    benford_rows, last_rows = [], []
    pooled_b, pooled_l = [], []
    for p in top:
        benford_rows.append(digit_test(data, p, "benford2").to_dict())
        last_rows.append(digit_test(data, p, "last").to_dict())
        pooled_b.append(data.df[p].to_numpy())
        pooled_l.append(data.df[p].to_numpy())
    metrics["benford2"] = benford_rows
    metrics["last_digit"] = last_rows

    counts_b = np.concatenate(pooled_b)
    plots.plot_digit_test(digit_freqs(counts_b, "benford2"), BENFORD_2ND,
                          digit_null_band(counts_b, "benford2"), "benford2",
                          "топ-6 партий, пул", fig_dir)
    counts_l = np.concatenate(pooled_l)
    plots.plot_digit_test(digit_freqs(counts_l, "last"), np.full(10, 0.1),
                          digit_null_band(counts_l, "last"), "last",
                          "топ-6 партий, пул", fig_dir)
    pd.DataFrame(benford_rows).to_csv(tab_dir / "benford2.csv", index=False)
    pd.DataFrame(last_rows).to_csv(tab_dir / "last_digit.csv", index=False)
    print(f"[5/9] цифровые тесты: {len(benford_rows)} партий, см. tables/")

    # --- корреляции --------------------------------------------------------
    corr_nat = turnout_result_correlations(data, top)
    corr_dist = district_correlations(data, top[:4])
    corr_nat.to_csv(tab_dir / "corr_national.csv", index=False)
    corr_dist.to_csv(tab_dir / "corr_districts.csv", index=False)
    plots.plot_correlations(corr_nat, corr_dist, leader, fig_dir)
    metrics["correlations_national"] = corr_nat.to_dict(orient="records")
    print(f"[6/9] корреляция явка×лидер (взвеш. Пирсон): "
          f"{corr_nat.loc[corr_nat.party == leader.removeprefix('votes:'), 'pearson_w'].iloc[0]:.3f}")

    # --- соседи и прошлые выборы ------------------------------------------
    neigh = robust_z_outliers(data, leader)
    neigh.to_csv(tab_dir / "neighbors_z.csv", index=False)
    plots.plot_neighbors(neigh, fig_dir)
    metrics["neighbors_flagged"] = int(neigh["flag"].sum())

    prev_csv = data_dir / "results_all_previous.csv"
    if prev_csv.exists():
        prev = load_mai_csv(prev_csv, election_name=f"{title or data_dir.name}: предыдущие выборы")
        if merge:
            prev = merge_parties(prev, merge)
        prev_party = prev_party or (leader if leader in prev.df.columns else prev.leader_party)
        swing = swing_vs_previous(data, prev, prev_party)
        swing.to_csv(tab_dir / "swing_vs_previous.csv", index=False)
        plots.plot_swing(swing, fig_dir)
        metrics["swing"] = {
            "prev_party": prev_party.removeprefix("votes:"),
            "flagged_both": int(swing["flag"].sum()),
            "flagged_turnout": int(swing["flag_turnout_only"].sum()),
            "n": int(len(swing)),
        }
    print(f"[7/9] соседи: выбросов |z|>4 — {int(neigh['flag'].sum())}; "
          f"скачков к прошлым выборам — {metrics.get('swing', {}).get('flagged_both', 'н/д')}")

    # --- ML -----------------------------------------------------------------
    anom = isolation_forest_anomalies(data, leader)
    anom.to_csv(tab_dir / "ml_anomalies.csv", index=False)
    plots.plot_ml_anomalies(anom, fig_dir)
    metrics["ml_flagged"] = int(anom["is_anomaly"].sum())
    print(f"[8/9] ML (Isolation Forest): аномальных территорий — {int(anom['is_anomaly'].sum())}")

    # --- самотест + контрольные выборы ---------------------------------------
    if run_self_test:
        report = run_selftest(data, leader)
        injected, _ = inject_additive_fraud(data, leader)
        plots.plot_selftest(data, injected, leader, report, fig_dir)
        metrics["selftest"] = report.to_dict()
        print(f"[9/9] самотест: сигнал аномалии ×{report.signal_growth:,.0f} "
              f"({report.clean_tail_party:,} → {report.injected_tail_party:,} голосов); "
              f"целые пики: z {report.peaks_z_clean:.1f} → {report.peaks_z_rounded:.1f}")
    if control_sets:
        series = [(cd.name, cd.turnout.to_numpy()) for cd in control_sets]
        series.insert(0, (data.name, data.turnout.to_numpy()))
        plots.plot_controls(series, fig_dir)

    with open(out_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2, default=float)
    print(f"готово: {out_dir}")
    return metrics


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Election forensics по выгрузке MAI")
    ap.add_argument("--data", required=True, help="каталог выгрузки MAI (с results_freguesias.csv)")
    ap.add_argument("--out", required=True, help="каталог для результатов")
    ap.add_argument("--title", default="", help="название выборов для подписей")
    ap.add_argument("--controls", default="", help="каталоги контрольных выборов через запятую")
    ap.add_argument("--prev-party", default="", help="партия прошлых выборов для сравнения скачков")
    ap.add_argument("--merge", default="", help="объединение колонок коалиций: 'votes:A<-votes:B,votes:C'")
    ap.add_argument("--no-selftest", action="store_true", help="не запускать синтетическую валидацию")
    args = ap.parse_args(argv)
    controls = [c for c in args.controls.split(",") if c.strip()]
    analyze(args.data, args.out, args.title, controls, args.prev_party, args.merge, not args.no_selftest)


if __name__ == "__main__":
    main()
