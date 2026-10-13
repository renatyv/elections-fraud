#!/usr/bin/env python3
"""Election forensics: Бразилия, президент, 1-й тур 04.10.2026 (уровень seção).

Прогоняет все применимые методы из analysis-tool по methods review
(методы_выявления_фальсификаций_выборов.md):
Шпилькин, отпечатки Klimek, целочисленные пики Kobak, 2D-корреляции,
Бенфорд/последняя цифра, выбросы против соседей, Isolation Forest,
самотест + бразильские проверки (модели урн, дубликаты протоколов).

Запуск: cd analysis-tool && uv run python ../brazil-oct-2026/scripts/run_forensics.py
Выход: brazil-oct-2026/analysis/{figures,tables,metrics.json}

Флаги: --lang ru|en|pt|es — язык подписей графиков (по умолчанию ru);
--fig-out DIR — записать фигуры (а также таблицы и metrics.json) в DIR,
не трогая brazil-oct-2026/analysis/.
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

OUT = BR / "analysis"
FIG = OUT / "figures"
TAB = OUT / "tables"

DATA_TITLES = {
    "ru": "Бразилия, президент 1-й тур 04.10.2026 (seções)",
    "en": "Brazil, presidential 1st round 04.10.2026 (seções)",
    "pt": "Brasil, presidencial 1.º turno 04.10.2026 (seções)",
    "es": "Brasil, presidencial 1.ª vuelta 04.10.2026 (secciones)",
}
DIGITS_POOL_LABEL = {
    "ru": "Болсонару + Лула, пул",
    "en": "Bolsonaro + Lula, pooled",
    "pt": "Bolsonaro + Lula, agregado",
    "es": "Bolsonaro + Lula, agrupado",
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _digits_fast(counts: np.ndarray, test: str) -> np.ndarray:
    """Векторный эквивалент digit_tests._digits (числа < 10 отфильтрованы MIN_COUNT)."""
    counts = np.asarray(counts, dtype=np.int64)
    if test == "last":
        return counts % 10
    d = np.floor(np.log10(np.maximum(counts, 1))).astype(np.int64)
    return (counts // np.power(10, np.maximum(d - 1, 0), dtype=np.int64)) % 10


def robust_z_outliers_fast(data: ElectionData, party: str, threshold: float = 4.0) -> pd.DataFrame:
    """Тот же тест, что neighbors.robust_z_outliers, но векторно (499k строк)."""
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
    """Корреляции явка × доля по штатам (замена district_correlations для Бразилии)."""
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
    ap = argparse.ArgumentParser(description="Election forensics: Бразилия-2026 (seções)")
    ap.add_argument("--lang", default="ru", choices=["ru", "en", "pt", "es"],
                    help="язык подписей графиков (по умолчанию ru)")
    ap.add_argument("--fig-out", type=Path, default=None,
                    help="каталог для фигур/таблиц/metrics вместо brazil-oct-2026/analysis/")
    args = ap.parse_args()
    lang = args.lang
    if args.fig_out is not None:
        fig_dir = args.fig_out
        tab_dir = fig_dir / "tables"
        metrics_path = fig_dir / "metrics.json"
    else:
        fig_dir, tab_dir, metrics_path = FIG, TAB, OUT / "metrics.json"
    fig_dir.mkdir(parents=True, exist_ok=True)
    tab_dir.mkdir(parents=True, exist_ok=True)
    dt._digits = _digits_fast  # 499k×N чисел: python-цикл по строкам слишком медленный

    df = pd.read_csv(BR / "data" / "secoes_presidente_2026.csv")
    dropped = int((df["voted"] == 0).sum())
    df = df[df["voted"] > 0].copy()
    party_cols = [c for c in df.columns if c.startswith("votes:")]
    title = DATA_TITLES[lang]
    data = ElectionData(name=title, df=df, party_cols=party_cols)
    leader = data.leader_party  # 22-BOLSONARO
    runner_up = "votes:LULA"
    top = major_parties(data, top=6)
    metrics: dict = {
        "title": title,
        "national": national_totals(data),
        "leader": leader.removeprefix("votes:"),
        "n_units": data.n,
        "dropped_zero_voted": dropped,
        "checks_file": "data/secoes_presidente_2026_checks.json",
    }
    log(f"данные: {data.n} секций (выброшено voted=0: {dropped}), лидер {leader}")

    # --- 1. метод Шпилькина: лидер + оппонент ------------------------------
    shp_l = shpilkin_estimate(data, leader)
    shp_r = shpilkin_estimate(data, runner_up)
    metrics["shpilkin_leader"] = shp_l.to_dict()
    metrics["shpilkin_runner_up"] = shp_r.to_dict()
    plots.plot_shpilkin(data, runner_up, shp_r, fig_dir, lang=lang)
    (fig_dir / "shpilkin_core.png").replace(fig_dir / "shpilkin_lula.png")
    plots.plot_shpilkin(data, leader, shp_l, fig_dir, lang=lang)
    log(f"Шпилькин: граница {shp_l.t_cut:.1f}%; хвост лидера {shp_l.tail_votes_party:,} "
        f"({shp_l.tail_share_of_party:.2f}%), Лулы {shp_r.tail_votes_party:,} "
        f"({shp_r.tail_share_of_party:.2f}%)")

    # --- 2. хвост кометы ----------------------------------------------------
    plots.plot_comet(data, top[:3], fig_dir, lang=lang)
    log("комета: ok")

    # --- 3. отпечатки пальцев (Klimek) --------------------------------------
    fp_l = fingerprint_mixture(data, leader)
    fp_r = fingerprint_mixture(data, runner_up)
    metrics["fingerprint_leader"] = fp_l.to_dict()
    metrics["fingerprint_runner_up"] = fp_r.to_dict()
    plots.plot_fingerprint(data, leader, fp_l, fig_dir, lang=lang)
    (fig_dir / "fingerprint_2d.png").replace(fig_dir / "fingerprint_bolsonaro.png")
    plots.plot_fingerprint(data, runner_up, fp_r, fig_dir, lang=lang)
    (fig_dir / "fingerprint_2d.png").replace(fig_dir / "fingerprint_lula.png")
    log(f"отпечатки: вес 2-й компоненты лидер {fp_l.weight_anom:.4f} "
        f"(разделение: {fp_l.separated}), Лула {fp_r.weight_anom:.4f} ({fp_r.separated})")

    # --- 4. целочисленные пики (Kobak) --------------------------------------
    peaks_t = integer_peaks(data, "turnout")
    peaks_l = integer_peaks(data, f"share:{leader}")
    metrics["integer_peaks_turnout"] = {
        "observed_pct": peaks_t.observed_integer_pct, "null_pct": peaks_t.null_mean_pct,
        "z": peaks_t.z_score, "z_mult5": peaks_t.z_mult5}
    metrics["integer_peaks_leader_share"] = {
        "observed_pct": peaks_l.observed_integer_pct, "null_pct": peaks_l.null_mean_pct,
        "z": peaks_l.z_score, "z_mult5": peaks_l.z_mult5}
    plots.plot_integer_peaks(data, peaks_t, fig_dir, lang=lang)
    log(f"целые проценты явки: {peaks_t.observed_integer_pct:.2f}% против "
        f"{peaks_t.null_mean_pct:.2f}% (z={peaks_t.z_score:.1f}); доля лидера z={peaks_l.z_score:.1f}")

    # --- 5. цифровые тесты: Бенфорд-2 + последняя цифра ----------------------
    # тест имеет смысл только при достаточном числе счётчиков нужного размера:
    # у минорных кандидатов в среднем <10 голосов на секцию
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
        last_rows.append(digit_test(data, pv, "last").to_dict())
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
    log(f"цифровые тесты: Бенфорд {len(benford_rows)} кандидатов, посл. цифра "
        f"{len(last_rows)}; макс. отклонение Бенфорд "
        f"{max(r['max_dev'] for r in benford_rows):.2f} п.п., посл. цифра "
        f"{max(r['max_dev'] for r in last_rows):.2f} п.п.")

    # --- 6. 2D-корреляции: национально + по штатам ---------------------------
    corr_nat = turnout_result_correlations(data, top)
    corr_nat.to_csv(tab_dir / "corr_national.csv", index=False)
    corr_uf = uf_correlations(data, top[:4])
    corr_uf.to_csv(tab_dir / "corr_uf.csv", index=False)
    plots.plot_correlations(corr_nat, corr_uf.rename(columns={"uf": "district"}), leader, fig_dir, lang=lang)
    metrics["correlations_national"] = corr_nat.to_dict(orient="records")
    metrics["corr_uf_leader_range"] = [float(corr_uf[leader.removeprefix("votes:")].min()),
                                       float(corr_uf[leader.removeprefix("votes:")].max())]
    log(f"корреляции: нац. лидер {corr_nat.loc[0, 'pearson_w']:.3f}, "
        f"по штатам от {metrics['corr_uf_leader_range'][0]:.2f} до {metrics['corr_uf_leader_range'][1]:.2f}")

    # --- 7. выбросы против соседей (внутри муниципалитета) -------------------
    neigh = robust_z_outliers_fast(data, leader)
    flagged = neigh[neigh["flag"]]
    flagged.to_csv(tab_dir / "neighbors_flagged.csv", index=False)
    plots.plot_neighbors(neigh, fig_dir, lang=lang)
    metrics["neighbors_flagged"] = int(neigh["flag"].sum())
    metrics["neighbors_flagged_pct"] = 100.0 * float(neigh["flag"].sum()) / len(neigh)
    log(f"соседи: выбросов |z|>4 — {metrics['neighbors_flagged']} "
        f"({metrics['neighbors_flagged_pct']:.3f}% секций)")

    # --- 8. Isolation Forest --------------------------------------------------
    anom = isolation_forest_anomalies(data, leader)
    anom.nlargest(2000, "anomaly_score").to_csv(tab_dir / "ml_anomalies_top2000.csv", index=False)
    plots.plot_ml_anomalies(anom, fig_dir, lang=lang)
    metrics["ml_flagged"] = int(anom["is_anomaly"].sum())
    log(f"ML: аномальных секций — {metrics['ml_flagged']} (contamination=1%)")

    # --- 9. самотест -----------------------------------------------------------
    report = run_selftest(data, leader)
    injected, _ = inject_additive_fraud(data, leader)
    plots.plot_selftest(data, injected, leader, report, fig_dir, lang=lang)
    metrics["selftest"] = report.to_dict()
    log(f"самотест: сигнал ×{report.signal_growth:,.0f}; пики z {report.peaks_z_clean:.1f} → "
        f"{report.peaks_z_rounded:.1f}")

    # --- 10. бразильские проверки ------------------------------------------------
    # модели урн: явка/доли не должны зависеть от поколения машины
    d = data.df.copy()
    d["turnout"] = data.turnout.to_numpy()
    d["share_lider"] = data.share(leader).to_numpy()
    d["share_lula"] = data.share(runner_up).to_numpy()
    g = d.groupby("urna_model")
    urna = pd.DataFrame({
        "sections": g.size(),
        "registered": g["registered_voters"].sum(),
        "turnout_pct": 100.0 * g["voted"].sum() / g["registered_voters"].sum(),
        "leader_pct": 100.0 * g[leader].sum() / g["voted"].sum(),
        "lula_pct": 100.0 * g[runner_up].sum() / g["voted"].sum(),
        "blank_pct": 100.0 * g["blank_votes"].sum() / g["voted"].sum(),
        "null_pct": 100.0 * g["null_votes"].sum() / g["voted"].sum(),
    })
    urna.to_csv(tab_dir / "urna_models.csv")
    metrics["urna_models"] = urna.reset_index().to_dict(orient="records")

    # дубликаты «протоколов»: одинаковый вектор (размер, явка, все голоса)
    vec_cols = ["registered_voters", "voted", "blank_votes", "null_votes"] + party_cols
    dups = d.duplicated(subset=vec_cols, keep=False)
    dup_groups = d[dups].groupby(vec_cols, dropna=False).size()
    metrics["duplicate_protocols"] = {
        "rows_in_dup_groups": int(dups.sum()),
        "groups": int((dup_groups > 1).sum()),
        "max_group": int(dup_groups.max()) if len(dup_groups) else 0,
        "note": "группы с одинаковым электоратом (включая размер секции)",
    }
    log(f"урны: {len(urna)} моделей; дубликаты протоколов: "
        f"{metrics['duplicate_protocols']['rows_in_dup_groups']} строк в "
        f"{metrics['duplicate_protocols']['groups']} группах")

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2, default=float)
    log(f"готово: {metrics_path.parent}")


if __name__ == "__main__":
    main()
