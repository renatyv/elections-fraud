"""Election forensics на уровне секций AR-2025 (91 участок шести конселью).

Данные — data/seccoes/ar2025_seccoes.csv (scripts/parse_seccoes_ar2025.py):
Benavente 27, Alcácer do Sal 21, Vendas Novas 16, Ferreira do Alentejo 14,
Borba 8, Sousel 5 — 60 711 избирателей (0,66% электората), по всем 22 приходам
сходятся с MAI до единого голоса (ar2025_seccoes_validation.txt).

Методы — analysis-tool (election_forensics); запуск из каталога analysis-tool:

    cd analysis-tool && uv sync
    uv run python ../portugal-2025/scripts/analyze_seccoes.py

Выход: portugal-2025/analysis_seccoes/{figures/*.png, tables/*.csv, metrics.json}.

Отличия от основного прогона по приходам (ef-analyze): нет секционных данных
контрольных выборов (граница Шпилькина — q99.5 своих данных), нет прошлого
уровня секций (тест скачков неприменим), окружные корреляции пропущены (группы
конселью 5–27 секций < 30), contamination ML поднят до 5% (рейтинг кандидатов,
не сигнал). Дополнительные проверки секционного уровня: целые проценты по долям
всех топ-6 партий, дубликаты протокольных векторов (copy-paste), выбросы внутри
своей фрегезии, экстремумы бланковых/недействительных, арифметика строк.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from election_forensics import plots
from election_forensics.anomaly_ml import isolation_forest_anomalies
from election_forensics.correlations import turnout_result_correlations
from election_forensics.data import ElectionData, major_parties, national_totals
from election_forensics.digit_tests import BENFORD_2ND, digit_freqs, digit_null_band, digit_test
from election_forensics.fingerprints import fingerprint_mixture
from election_forensics.integer_peaks import integer_peaks
from election_forensics.neighbors import robust_z_outliers
from election_forensics.selftest import inject_additive_fraud, run_selftest
from election_forensics.shpilkin import shpilkin_estimate

BASE = Path(__file__).resolve().parents[1]  # portugal-2025/
CSV = BASE / "data" / "seccoes" / "ar2025_seccoes.csv"
OUT = BASE / "analysis_seccoes"
MAIN_METRICS = BASE / "analysis" / "metrics.json"
FREG_CSV = BASE / "data" / "legislativas2025_mai" / "results_freguesias.csv"


def load_sections() -> ElectionData:
    """Секции AR-2025 в формате ElectionData (аналог results_freguesias.csv).

    Единица анализа — секция; parent_key = конселью (группа для теста соседей),
    path = «AR2025 секции > конселью > фрегезия · сек. N» ([-2] = конселью).
    """
    raw = pd.read_csv(CSV, encoding="utf-8-sig")
    raw = raw[raw["nivel"] == "secao"].copy()
    raw["secao"] = raw["secao"].astype(int)
    df = pd.DataFrame(
        {
            "key": raw["mai_key"] + "-S" + raw["secao"].map("{:02d}".format),
            "level": 3,
            "name": raw["freguesia"] + " · S" + raw["secao"].astype(str),
            "path": "AR2025 секции > " + raw["concelho"] + " > "
                    + raw["freguesia"] + " · S" + raw["secao"].astype(str),
            "parent_key": raw["dico"].astype(str),
            "registered_voters": raw["eleitores"].astype(int),
            "voted": raw["votantes"].astype(int),
            "turnout_pct": 100.0 * raw["votantes"] / raw["eleitores"],
            "blank_votes": raw["brancos"].astype(int),
            "null_votes": raw["nulos"].astype(int),
        }
    )
    for c in raw.columns:
        if c.startswith("votes:"):
            df[c] = pd.to_numeric(raw[c], errors="coerce").fillna(0).astype(int)
    return ElectionData(name="AR 2025, секции (6 конселью)", df=df,
                        party_cols=[c for c in df.columns if c.startswith("votes:")],)


def freguesia_comparison(data: ElectionData) -> dict:
    """Явка тех же 22 приходов на уровне MAI — против разброса секций внутри них."""
    out: dict = {}
    t = data.turnout.to_numpy()
    out["section_turnout_min_median_max"] = [float(t.min()), float(np.median(t)), float(t.max())]
    if FREG_CSV.exists():
        keys = data.df["key"].str.extract(r"^(LOCAL-\d{6})-", expand=False).unique()
        fr = pd.read_csv(FREG_CSV, encoding="utf-8-sig")
        fr = fr[fr["key"].isin(keys)]
        tf = (100.0 * fr["voted"] / fr["registered_voters"]).to_numpy()
        out["freguesia_n"] = int(len(fr))
        out["freguesia_turnout_min_median_max"] = [float(tf.min()), float(np.median(tf)), float(tf.max())]
        out["sections_outside_freguesia_range"] = int(((t < tf.min()) | (t > tf.max())).sum())
    if MAIN_METRICS.exists():
        with open(MAIN_METRICS, encoding="utf-8") as f:
            out["national_t_cut"] = json.load(f)["shpilkin"]["t_cut"]
        out["sections_above_national_cut"] = int((t > out["national_t_cut"]).sum())
    return out


def main() -> None:
    fig_dir = OUT / "figures"
    tab_dir = OUT / "tables"
    fig_dir.mkdir(parents=True, exist_ok=True)
    tab_dir.mkdir(parents=True, exist_ok=True)

    data = load_sections()
    leader = data.leader_party
    top = major_parties(data, top=6, min_total=800)
    metrics: dict = {"title": data.name, "national": national_totals(data),
                     "leader": leader.removeprefix("votes:"), "n_units": data.n}
    print(f"[1/8] данные: {data.n} секций, лидер {leader}")

    # --- Шпилькин: распределение явки секций (без контролов — q99.5 своих) ---
    shp = shpilkin_estimate(data, leader)
    metrics["shpilkin"] = shp.to_dict()
    plots.plot_shpilkin(data, leader, shp, fig_dir)
    print(f"[2/8] Шпилькин: граница {shp.t_cut:.1f}% ({shp.t_cut_source}); мода {shp.mode:.1f}%, "
          f"σ {shp.sigma:.1f} п.п.; аномальных голосов лидера {shp.tail_votes_party}")

    # --- хвост кометы + отпечатки ---
    plots.plot_comet(data, top[:3], fig_dir)
    fp = fingerprint_mixture(data, leader)
    metrics["fingerprint"] = fp.to_dict()
    plots.plot_fingerprint(data, leader, fp, fig_dir)
    print(f"[3/8] отпечатки: вес 2-й компоненты {fp.weight_anom:.3f}, "
          f"разделение {'есть' if fp.separated else 'нет'}")

    # --- целочисленные пики (низкая мощность при n=91 — см. самотест) ---
    peaks_t = integer_peaks(data, "turnout")
    peaks_l = integer_peaks(data, f"share:{leader}")
    metrics["integer_peaks_turnout"] = {
        "observed_pct": peaks_t.observed_integer_pct, "null_pct": peaks_t.null_mean_pct,
        "z": peaks_t.z_score, "z_mult5": peaks_t.z_mult5}
    metrics["integer_peaks_leader_share"] = {
        "observed_pct": peaks_l.observed_integer_pct, "null_pct": peaks_l.null_mean_pct,
        "z": peaks_l.z_score, "z_mult5": peaks_l.z_mult5}
    plots.plot_integer_peaks(data, peaks_t, fig_dir)
    print(f"[4/8] целые проценты явки: {peaks_t.observed_integer_pct:.2f}% против "
          f"{peaks_t.null_mean_pct:.2f}% (z={peaks_t.z_score:.1f})")

    # --- цифровые тесты: только партии с достаточным числом пригодных чисел ---
    # (последняя цифра — счётчики >=100: у мелких партий таких секций нет;
    # порог 30 чисел — минимум, при котором chi2 с df=9 ещё осмыслен)
    from election_forensics.digit_tests import MIN_COUNT
    benford_rows, last_rows, pooled_b, pooled_l = [], [], [], []
    for p in top:
        for test, rows, pool in (("benford2", benford_rows, pooled_b), ("last", last_rows, pooled_l)):
            n_ok = int((data.df[p] >= MIN_COUNT[test]).sum())
            if n_ok >= 30:
                rows.append(digit_test(data, p, test).to_dict())
                pool.append(data.df[p].to_numpy())
            else:
                rows.append({"test": test, "party": p.removeprefix("votes:"),
                             "n_numbers": n_ok, "p_value": None,
                             "note": f"мало чисел >= {MIN_COUNT[test]} — тест не проводился"})
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
    print(f"[5/8] цифровые тесты: {len(benford_rows)} партий, см. tables/")

    # --- корреляции и соседи: секция против медианы своего конселью ---
    corr_nat = turnout_result_correlations(data, top)
    corr_nat.to_csv(tab_dir / "corr_national.csv", index=False)
    metrics["correlations_national"] = corr_nat.to_dict(orient="records")
    neigh = robust_z_outliers(data, leader)
    neigh.to_csv(tab_dir / "neighbors_z.csv", index=False)
    plots.plot_neighbors(neigh, fig_dir)
    metrics["neighbors_flagged"] = int(neigh["flag"].sum())
    print(f"[6/8] соседи (по конселью): выбросов |z|>4 — {int(neigh['flag'].sum())}; "
          f"корреляция явка×лидер (взвеш. Пирсон): "
          f"{corr_nat.loc[corr_nat.party == leader.removeprefix('votes:'), 'pearson_w'].iloc[0]:.3f}")

    # --- дополнительные проверки секционного уровня ------------------------
    # целые проценты по долям ВСЕХ топ-6 партий (в основном прогоне — только лидер)
    peaks_parties = [
        {"party": p.removeprefix("votes:"), "observed_pct": (r := integer_peaks(data, f"share:{p}")).observed_integer_pct,
         "null_pct": r.null_mean_pct, "z": r.z_score, "z_mult5": r.z_mult5}
        for p in top
    ]
    metrics["integer_peaks_party_shares"] = peaks_parties

    # ML: contamination 5% — рейтинг кандидатов на ручную проверку, не сигнал
    anom = isolation_forest_anomalies(data, leader, contamination=0.05)
    anom.to_csv(tab_dir / "ml_anomalies.csv", index=False)
    plots.plot_ml_anomalies(anom, fig_dir)
    metrics["ml_flagged"] = int(anom["is_anomaly"].sum())
    metrics["ml_candidates"] = anom.loc[anom["is_anomaly"], "name"].tolist()

    # дубликаты протокольных векторов: полный copy-paste строки голосов
    vote_cols = [c for c in data.df.columns if c.startswith("votes:")] + ["blank_votes", "null_votes"]
    vec = data.df[vote_cols].astype(str).agg("|".join, axis=1)
    metrics["duplicate_protocol_rows"] = int(vec.duplicated().sum())

    # выбросы внутри своей фрегезии (группы >= 4 секций; внутри фрегезии секции
    # максимально сопоставимы — один приход, одна местная администрация)
    def _rz(g: pd.DataFrame, col: str) -> pd.Series:
        med = g[col].median()
        mad = (g[col] - med).abs().median()
        return (g[col] - med) / (1.4826 * mad) if mad > 0 else g[col] * 0

    dfw = data.df.copy()
    dfw["mai_key"] = dfw["key"].str.extract(r"^(LOCAL-\d{6})-", expand=False)
    dfw["turnout"] = data.turnout.to_numpy()
    dfw["share"] = data.share(leader).to_numpy()
    parts = []
    for _, g in dfw.groupby("mai_key"):
        if len(g) < 4:
            continue
        gg = g[["key", "name", "parent_key", "registered_voters", "turnout", "share"]].copy()
        gg["z_turnout"] = _rz(g, "turnout").to_numpy()
        gg["z_share"] = _rz(g, "share").to_numpy()
        gg["flag"] = (gg["z_turnout"].abs() > 4) | (gg["z_share"].abs() > 4)
        parts.append(gg)
    fr_z = pd.concat(parts, ignore_index=True)
    fr_z.to_csv(tab_dir / "within_freguesia_z.csv", index=False)
    metrics["within_freguesia"] = {
        "n_groups": len(parts),
        "n_units": int(len(fr_z)),
        "flagged": int(fr_z["flag"].sum()),
        "flagged_names": fr_z.loc[fr_z["flag"], "name"].tolist(),
    }

    # бланковые/недействительные: медианы и экстремумы секций
    blank_pct = 100.0 * data.df["blank_votes"] / data.df["voted"]
    null_pct = 100.0 * data.df["null_votes"] / data.df["voted"]
    metrics["ballot_shares"] = {
        "blank_median": float(blank_pct.median()), "blank_max": float(blank_pct.max()),
        "blank_max_name": str(data.df.loc[blank_pct.idxmax(), "name"]),
        "null_median": float(null_pct.median()), "null_max": float(null_pct.max()),
        "null_max_name": str(data.df.loc[null_pct.idxmax(), "name"]),
    }

    # арифметика строк исходного CSV: суммы должны сходиться до единого бюллетеня
    raw = pd.read_csv(CSV, encoding="utf-8-sig")
    raw = raw[raw["nivel"] == "secao"]
    raw_votes = raw[[c for c in raw.columns if c.startswith("votes:")]].fillna(0)
    d_votes = (raw_votes.sum(axis=1) + raw["brancos"] + raw["nulos"] - raw["votantes"]).abs()
    d_elec = (raw["votantes"] + raw["abst"] - raw["eleitores"]).abs()
    metrics["internal_consistency"] = {
        "max_diff_ballots": float(d_votes.max()), "max_diff_electorate": float(d_elec.max()),
        "n_mismatch_rows": int((d_votes > 0).sum() + (d_elec > 0).sum()),
    }
    print(f"[7/8] доп. проверки: пики долей топ-6 z∈[{min(p['z'] for p in peaks_parties):+.1f}; "
          f"{max(p['z'] for p in peaks_parties):+.1f}]; дубликатов {metrics['duplicate_protocol_rows']}; "
          f"ML-кандидатов {metrics['ml_flagged']}; внутрифрегезионных выбросов "
          f"{metrics['within_freguesia']['flagged']}; арифметика: расхождений "
          f"{metrics['internal_consistency']['n_mismatch_rows']}")

    # --- самотест: видны ли инъекции при n=91 ---
    report = run_selftest(data, leader)
    injected, _ = inject_additive_fraud(data, leader)
    plots.plot_selftest(data, injected, leader, report, fig_dir)
    metrics["selftest"] = report.to_dict()
    print(f"[8/8] самотест: сигнал ×{report.signal_growth:,.0f} "
          f"({report.clean_tail_party} → {report.injected_tail_party} голосов); "
          f"целые пики z {report.peaks_z_clean:.1f} → {report.peaks_z_rounded:.1f}")

    metrics["turnout_comparison"] = freguesia_comparison(data)
    with open(OUT / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2, default=float)
    print(f"готово: {OUT}")


if __name__ == "__main__":
    main()
