#!/usr/bin/env python3
"""Контрольный прогон: выборы-2022 как контроль для BR-2026 (те же секции).

Закрывает главное ограничение ОТЧЁТа (§«Ограничения», п. 1): граница честного
спада Шпилькина теперь берётся из КОНТРОЛЬНЫХ выборов 2022 (оба тура, те же
территории), а не из собственного q99,5; плюс выполняется №8-б обзора —
«скачки к прошлым выборам» (изменение явки и долей на тех же секциях 2022→2026):

1. Граница q99,5 (взвешенно по электорату) контрольных 2022-1Т/2Т → пересчёт
   хвостов BR-2026 по ней; собственные хвосты 2022 как базовый уровень шума.
2. Распределения явки 2022-1Т/2Т и 2026-1Т на одном поле с границами.
3. Матч секций по ключу (UF-município-zona-seção) 2022↔2026; Δявка, Δдоли
   Болсонару/Лулы; робастные выбросы |z|>4; децили Δявки против долей-2026
   (сигнатура вброса: прирост явки смещён в пользу одного кандидата).
4. Отпечатки Klimek на контрольных 2022 (обa тура) — где лежат компоненты.

Запуск: cd analysis-tool && uv run python ../brazil-oct-2026/scripts/control_forensics.py
Выход: brazil-oct-2026/analysis/{figures/control_*.png, tables/control_*.csv,
       metrics_control_2022.json}
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

BR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "analysis-tool" / "src"))

from election_forensics import plots  # noqa: E402  (стиль/rcParams)
from election_forensics.correlations import weighted_pearson  # noqa: E402
from election_forensics.data import ElectionData  # noqa: E402
from election_forensics.fingerprints import fingerprint_mixture  # noqa: E402
from election_forensics.shpilkin import shpilkin_estimate, suggest_t_cut, votes_by_turnout  # noqa: E402

OUT = BR / "analysis"
FIG = OUT / "figures"
TAB = OUT / "tables"

LEADER = "votes:BOLSONARO"
RUNNER_UP = "votes:LULA"

MACRO = {
    "N": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
    "NE": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "CW": ["DF", "GO", "MT", "MS"],
    "SE": ["ES", "MG", "RJ", "SP"],
    "S": ["PR", "RS", "SC"],
    "ZZ": ["ZZ"],
}
REG_NAMES = {"N": "Север", "NE": "Северо-Восток", "CW": "Центр.-Запад",
             "SE": "Юго-Восток", "S": "Юг", "ZZ": "Заграница"}
REG_ORDER = ["N", "NE", "CW", "SE", "S", "ZZ"]
REG_COLORS = {"N": "#8c564b", "NE": "#d62728", "CW": "#e6960c",
              "SE": "#1f77b4", "S": "#2ca02c", "ZZ": "#7f7f7f"}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load(csv_name: str, turno: int | None = None) -> ElectionData:
    df = pd.read_csv(BR / "data" / csv_name)
    if turno is not None:
        df = df[df["turno"] == turno]
    df = df[df["voted"] > 0].copy()
    party_cols = [c for c in df.columns if c.startswith("votes:")]
    return ElectionData(name=csv_name, df=df, party_cols=party_cols)


def plot_turnout_dists(datas: dict[str, ElectionData], t_cut_control: float,
                        t_cut_own26: float, q22: dict[str, float]) -> None:
    fig, ax = plots.plt.subplots(figsize=(8.6, 3.8))
    colors = {"2022, 1-й тур": "#7f7f7f", "2022, 2-й тур": "#9467bd",
              "2026, 1-й тур": "#1f77b4"}
    for label, d in datas.items():
        centers, h = votes_by_turnout(d, None, 0.5)
        ax.plot(centers, h / h.sum(), drawstyle="steps-mid", lw=1.3,
                color=colors[label], label=label)
    ax.axvline(t_cut_control, color="#d62728", lw=1.6,
               label=f"граница по контролю-2022: {t_cut_control:.1f}%")
    ax.axvline(t_cut_own26, color="k", ls="--", lw=1.0,
               label=f"собственный q99,5-2026: {t_cut_own26:.1f}%")
    for label, q in q22.items():
        ax.axvline(q, color=colors[label], ls=":", lw=0.9, alpha=0.8)
    ax.set_xlabel("Явка, %")
    ax.set_ylabel("Доля проголосовавших")
    ax.set_yscale("log")
    ax.set_ylim(1e-6, None)
    ax.set_xlim(10, 100)
    ax.legend(fontsize=7.5)
    ax.set_title("Распределения явки: контроль-2022 против 2026 (точечные линии — "
                 "собственные q99,5 туров 2022)", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "control_turnout.png", bbox_inches="tight")
    plots.plt.close(fig)


def plot_jumps(m: pd.DataFrame, med: float, mad: float) -> None:
    fig, axes = plots.plt.subplots(1, 3, figsize=(11.2, 3.5))

    ax = axes[0]
    ok = m.turnout_22.between(10, 100) & m.turnout_26.between(10, 100)
    ax.hist2d(m.turnout_22[ok], m.turnout_26[ok], bins=90,
              weights=m.registered_voters_26[ok], cmap="viridis",
              cmin=1e-9, norm=plots.matplotlib.colors.LogNorm())
    ax.plot([10, 100], [10, 100], "w--", lw=0.8, alpha=0.8)
    ax.set_xlabel("Явка 2022-1Т, %")
    ax.set_ylabel("Явка 2026-1Т, %")
    ax.set_title(f"Те же секции (n={len(m):,}); диагональ — без изменений", fontsize=9)
    ax.grid(False)

    ax = axes[1]
    dT = m.d_turnout.clip(-30, 30)
    ax.hist(dT, bins=120, color="#1f77b4", alpha=0.8)
    ax.axvline(med, color="k", lw=1.0, label=f"медиана {med:+.2f} п.п.")
    for k in (-4, 4):
        x = med + k * 1.4826 * mad
        ax.axvline(x, color="#d62728", ls="--", lw=1.0,
                   label=f"медиана ± 4·MAD ({x:+.1f})" if k > 0 else None)
    ax.set_xlabel("Δявка 2026−2022, п.п. (обрезано ±30)")
    ax.set_ylabel("Секций")
    ax.set_title("Скачки явки на тех же секциях", fontsize=9)
    ax.legend(fontsize=7.5)

    ax = axes[2]
    bins = np.linspace(-40, 40, 130)
    ax.hist(m.d_share_bolsonaro.clip(-40, 40), bins=bins, color="#1f77b4",
            alpha=0.65, label="Δдоля Болсонару")
    ax.hist(m.d_share_lula.clip(-40, 40), bins=bins, color="#d62728",
            alpha=0.65, label="Δдоля Лулы")
    ax.set_xlabel("Δдоля (доля от проголосовавших), п.п. (обрезано ±40)")
    ax.set_ylabel("Секций")
    ax.set_title("Изменение долей кандидатов, 2022-1Т → 2026-1Т", fontsize=9)
    ax.legend(fontsize=7.5)

    fig.tight_layout()
    fig.savefig(FIG / "control_jumps.png", bbox_inches="tight")
    plots.plt.close(fig)


def plot_fingerprint_2022(d: ElectionData, fps: dict[str, object]) -> None:
    fig, axes = plots.plt.subplots(1, 2, figsize=(9.2, 3.8), sharex=True, sharey=True)
    for ax, party, color in ((axes[0], LEADER, "#1f77b4"), (axes[1], RUNNER_UP, "#d62728")):
        t = d.turnout.to_numpy()
        s = d.share(party).to_numpy()
        w = d.registered.to_numpy(dtype=float)
        fp = fps[party]
        ax.hist2d(t, s, bins=[70, 70], weights=w, cmap="viridis",
                  cmin=1e-9, norm=plots.matplotlib.colors.LogNorm())
        ax.plot(*fp.mean_main, "o", ms=9, mfc="none", mec="white", mew=1.6)
        ax.plot(*fp.mean_anom, "s", ms=9, mfc="none", mec="#ff7f0e", mew=1.6)
        ax.set_title(f"2022, 2-й тур — {party.removeprefix('votes:')}: "
                     f"2-я компонента {fp.weight_anom:.2f} ({fp.mean_anom[0]:.0f}%; "
                     f"{fp.mean_anom[1]:.0f}%)", fontsize=8.5)
        ax.set_xlim(20, 100)
        ax.grid(False)
        ax.set_xlabel("Явка, %")
    axes[0].set_ylabel("Доля кандидата, %")
    fig.suptitle("Контрольные выборы-2022 (2-й тур): «отпечатки» без кластера "
                 "у правого верхнего угла", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "control_fingerprint_2022.png", bbox_inches="tight")
    plots.plt.close(fig)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)

    d26 = load("secoes_presidente_2026.csv")
    d22_1 = load("secoes_presidente_2022.csv", turno=1)
    d22_2 = load("secoes_presidente_2022.csv", turno=2)
    log(f"2026: {d26.n} секций; 2022-1Т: {d22_1.n}; 2022-2Т: {d22_2.n}")

    metrics: dict = {"title": "Контрольные выборы-2022 против BR-2026 (те же секции)"}

    # --- 1. граница Шпилькина из контроля --------------------------------
    t_cut_1 = suggest_t_cut([d22_1], 99.5)
    t_cut_2 = suggest_t_cut([d22_2], 99.5)
    t_cut = suggest_t_cut([d22_1, d22_2], 99.5)
    t_own26 = float(np.percentile(np.repeat(d26.turnout.to_numpy(),
                                            np.round(d26.registered.to_numpy()).astype(int)), 99.5))
    log(f"границы q99,5: 2022-1Т {t_cut_1:.2f}%, 2022-2Т {t_cut_2:.2f}%, "
        f"макс (контроль) {t_cut:.2f}%; собственная 2026 {t_own26:.2f}%")

    rows = []
    for label, d, party in (("2026-1Т", d26, LEADER), ("2026-1Т", d26, RUNNER_UP),
                            ("2022-1Т", d22_1, LEADER), ("2022-1Т", d22_1, RUNNER_UP),
                            ("2022-2Т", d22_2, LEADER), ("2022-2Т", d22_2, RUNNER_UP)):
        ctrl = [d22_1, d22_2] if label == "2026-1Т" else None
        res_c = shpilkin_estimate(d, party, controls=ctrl)
        res_o = shpilkin_estimate(d, party)  # собственный q99,5
        rows.append({
            "election": label, "party": party.removeprefix("votes:"),
            "n": d.n,
            "t_cut_control": round(res_c.t_cut, 2) if ctrl else None,
            "tail_voters_control": res_c.tail_voters if ctrl else None,
            "tail_votes_party_control": res_c.tail_votes_party if ctrl else None,
            "tail_share_party_control_pct": round(res_c.tail_share_of_party, 3) if ctrl else None,
            "honest_share_control": round(res_c.honest_share_pct, 2) if ctrl else None,
            "observed_share": round(res_c.observed_share_pct, 2),
            "t_cut_own_q995": round(res_o.t_cut, 2),
            "tail_voters_own": res_o.tail_voters,
            "tail_voters_own_pct": round(100.0 * res_o.tail_voters / d.voted.sum(), 3),
            "tail_share_party_own_pct": round(res_o.tail_share_of_party, 3),
            "mode": round(res_o.mode, 2), "sigma": round(res_o.sigma, 2),
        })
        log(f"{label} {party.removeprefix('votes:')}: хвост по контролю "
            f"{res_c.tail_share_of_party:.2f}% (граница {res_c.t_cut:.2f}); "
            f"по собственному q99,5 {res_o.tail_share_of_party:.2f}%")
    shp_tab = pd.DataFrame(rows)
    shp_tab.to_csv(TAB / "control_shpilkin.csv", index=False)
    metrics["shpilkin"] = rows
    metrics["t_cut"] = {"control_2022_max": round(t_cut, 2),
                        "control_2022_t1": round(t_cut_1, 2),
                        "control_2022_t2": round(t_cut_2, 2),
                        "own_2026": round(t_own26, 2)}

    plot_turnout_dists({"2022, 1-й тур": d22_1, "2022, 2-й тур": d22_2,
                        "2026, 1-й тур": d26}, t_cut, t_own26,
                       {"2022, 1-й тур": t_cut_1, "2022, 2-й тур": t_cut_2})

    # --- 2. матч секций 2022-1Т ↔ 2026-1Т --------------------------------
    cols = ["key", "uf", "name", "registered_voters", "voted", LEADER, RUNNER_UP]
    a = d26.df[cols].rename(columns={"registered_voters": "registered_voters_26",
                                    "voted": "voted_26", "name": "name_26"})
    b = d22_1.df[cols].rename(columns={"registered_voters": "registered_voters_22",
                                      "voted": "voted_22"})
    m = a.merge(b.drop(columns="uf"), on="key", how="inner")
    uf2macro = {uf: rg for rg, ufs in MACRO.items() for uf in ufs}
    m["reg"] = m.uf.map(uf2macro)
    match = {
        "sections_2026": d26.n, "sections_2022_t1": d22_1.n,
        "matched": len(m),
        "matched_pct_of_2026": round(100.0 * len(m) / d26.n, 2),
        "matched_voters_2026_pct": round(
            100.0 * m.voted_26.sum() / d26.df.voted.sum(), 2),
        "matched_registered_2026_pct": round(
            100.0 * m.registered_voters_26.sum() / d26.df.registered_voters.sum(), 2),
    }
    by_region = []
    for rg in REG_ORDER:
        g26 = d26.df[d26.df.uf.isin(MACRO[rg])]
        gm = m[m.reg == rg]
        by_region.append({
            "reg": rg, "reg_name": REG_NAMES[rg],
            "sections_2026": len(g26), "matched": len(gm),
            "matched_pct": round(100.0 * len(gm) / max(len(g26), 1), 2),
        })
    metrics["match"] = match
    metrics["match_by_region"] = by_region
    log(f"матч: {match['matched']:,} из {d26.n:,} секций-2026 "
        f"({match['matched_pct_of_2026']}%), покрывает "
        f"{match['matched_voters_2026_pct']}% проголосовавших-2026")

    # --- 3. скачки явки/долей на тех же секциях ---------------------------
    m["turnout_22"] = 100.0 * m.voted_22 / m.registered_voters_22
    m["turnout_26"] = 100.0 * m.voted_26 / m.registered_voters_26
    m["d_turnout"] = m.turnout_26 - m.turnout_22
    m["d_share_bolsonaro"] = (100.0 * m[LEADER + "_x"] / m.voted_26
                              - 100.0 * m[LEADER + "_y"] / m.voted_22)
    m["d_share_lula"] = (100.0 * m[RUNNER_UP + "_x"] / m.voted_26
                         - 100.0 * m[RUNNER_UP + "_y"] / m.voted_22)
    med = float(m.d_turnout.median())
    mad = float((m.d_turnout - med).abs().median())
    m["z_jump"] = (m.d_turnout - med) / (1.4826 * mad)
    flagged = m[m.z_jump.abs() > 4]
    up = int((m.z_jump > 4).sum())
    down = int((m.z_jump < -4).sum())

    r_stab = weighted_pearson(m.turnout_22.to_numpy(), m.turnout_26.to_numpy(),
                              m.registered_voters_26.to_numpy(dtype=float))
    r_dT_share_b = weighted_pearson(m.d_turnout.to_numpy(), m.d_share_bolsonaro.to_numpy(),
                                    m.registered_voters_26.to_numpy(dtype=float))
    r_dT_share_l = weighted_pearson(m.d_turnout.to_numpy(), m.d_share_lula.to_numpy(),
                                    m.registered_voters_26.to_numpy(dtype=float))

    # децили прироста явки против средних долей-2026 (сигнатура вброса:
    # верхние децили смещены в пользу бенефициара)
    m["dT_decile"] = pd.qcut(m.d_turnout, 10, labels=False, duplicates="drop") + 1
    dec = m.groupby("dT_decile").apply(lambda g: pd.Series({
        "d_turnout_median": g.d_turnout.median(),
        "sections": len(g),
        "share26_bolsonaro": 100.0 * g[LEADER + "_x"].sum() / g.voted_26.sum(),
        "share26_lula": 100.0 * g[RUNNER_UP + "_x"].sum() / g.voted_26.sum(),
        "share22_bolsonaro": 100.0 * g[LEADER + "_y"].sum() / g.voted_22.sum(),
        "share22_lula": 100.0 * g[RUNNER_UP + "_y"].sum() / g.voted_22.sum(),
    }), include_groups=False).reset_index()
    dec.to_csv(TAB / "control_deciles.csv", index=False)

    jumps = {
        "d_turnout": {"median": round(med, 2), "mad": round(mad, 2),
                      "q01": round(m.d_turnout.quantile(0.01), 2),
                      "q99": round(m.d_turnout.quantile(0.99), 2),
                      "flagged_z4": len(flagged), "flagged_pct": round(100.0 * len(flagged) / len(m), 3),
                      "up": up, "down": down},
        "d_share_bolsonaro": {"median": round(m.d_share_bolsonaro.median(), 2),
                              "q01": round(m.d_share_bolsonaro.quantile(0.01), 2),
                              "q99": round(m.d_share_bolsonaro.quantile(0.99), 2)},
        "d_share_lula": {"median": round(m.d_share_lula.median(), 2),
                         "q01": round(m.d_share_lula.quantile(0.01), 2),
                         "q99": round(m.d_share_lula.quantile(0.99), 2)},
        "r_turnout22_turnout26": round(r_stab, 4),
        "r_dT_share_bolsonaro": round(r_dT_share_b, 4),
        "r_dT_share_lula": round(r_dT_share_l, 4),
        "flagged_share26_bolsonaro": round(100.0 * flagged[LEADER + "_x"].sum() / flagged.voted_26.sum(), 2),
        "flagged_share26_lula": round(100.0 * flagged[RUNNER_UP + "_x"].sum() / flagged.voted_26.sum(), 2),
        "all_share26_bolsonaro": round(100.0 * m[LEADER + "_x"].sum() / m.voted_26.sum(), 2),
        "all_share26_lula": round(100.0 * m[RUNNER_UP + "_x"].sum() / m.voted_26.sum(), 2),
    }
    metrics["jumps"] = jumps
    log(f"Δявка: медиана {med:+.2f} п.п., MAD {mad:.2f}; |z|>4 — {len(flagged)} "
        f"({jumps['d_turnout']['flagged_pct']}%): вверх {up} / вниз {down}; "
        f"r(Δявка, Δдоля Болсонару)={r_dT_share_b:+.3f}, Лулы={r_dT_share_l:+.3f}")

    jrows = []
    for rg in REG_ORDER:
        g = m[m.reg == rg]
        if not len(g):
            continue
        jrows.append({
            "reg": rg, "reg_name": REG_NAMES[rg], "sections": len(g),
            "d_turnout_median": round(g.d_turnout.median(), 2),
            "d_turnout_mad": round((g.d_turnout - g.d_turnout.median()).abs().median(), 2),
            "flagged_z4": int(g.z_jump.abs().gt(4).sum()),
            "flagged_pct": round(100.0 * g.z_jump.abs().gt(4).sum() / len(g), 3),
            "up": int(g.z_jump.gt(4).sum()), "down": int(g.z_jump.lt(-4).sum()),
        })
    pd.DataFrame(jrows).to_csv(TAB / "control_jumps_by_region.csv", index=False)
    metrics["jumps_by_region"] = jrows

    ext = flagged.assign(absz=flagged.z_jump.abs()).nlargest(200, "absz")
    ext[["key", "uf", "name_26", "registered_voters_26", "turnout_22", "turnout_26",
         "d_turnout", "z_jump", "d_share_bolsonaro", "d_share_lula"]].to_csv(
        TAB / "control_jumps_extreme.csv", index=False)

    plot_jumps(m, med, mad)

    # --- 4. отпечатки на контроле-2022 ------------------------------------
    fp_rows = []
    fps2: dict[str, object] = {}
    for label, d in (("2022-1Т", d22_1), ("2022-2Т", d22_2)):
        for party in (LEADER, RUNNER_UP):
            fp = fingerprint_mixture(d, party)
            if label == "2022-2Т":
                fps2[party] = fp
            fp_rows.append({
                "election": label, "party": party.removeprefix("votes:"),
                "weight_anom": round(fp.weight_anom, 4),
                "mean_main": f"({fp.mean_main[0]:.1f}; {fp.mean_main[1]:.1f})",
                "mean_anom": f"({fp.mean_anom[0]:.1f}; {fp.mean_anom[1]:.1f})",
                "separated": fp.separated,
                "anom_voters": fp.anom_cluster_voters,
            })
    pd.DataFrame(fp_rows).to_csv(TAB / "control_fingerprints_2022.csv", index=False)
    metrics["fingerprints_2022"] = fp_rows
    plot_fingerprint_2022(d22_2, fps2)
    log("отпечатки-2022: " + "; ".join(
        f"{r['election']} {r['party']}: w={r['weight_anom']} @ {r['mean_anom']}" for r in fp_rows))

    metrics["files"] = {
        "data_2022": "data/secoes_presidente_2022.csv (построен build_sections_csv_2022.py)",
        "tables": ["control_shpilkin.csv", "control_deciles.csv",
                   "control_jumps_by_region.csv", "control_jumps_extreme.csv",
                   "control_fingerprints_2022.csv"],
        "figures": ["control_turnout.png", "control_jumps.png",
                    "control_fingerprint_2022.png"],
    }
    with open(OUT / "metrics_control_2022.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2, default=float)
    log(f"готово: {OUT/'metrics_control_2022.json'}")


if __name__ == "__main__":
    main()
