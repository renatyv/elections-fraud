#!/usr/bin/env python3
"""Control run for the BR-2026 runoff: the same sections across rounds and years.

1. Turnout distributions of 2022-R1/R2 (honest control), 2026-R1 and 2026-R2 on
   one plot; the Shpilkin q99.5 boundaries; 2026-R2 tails against the 2022
   control boundary and its own.
2. Jumps 2026-R1 → 2026-R2 (the same election, three weeks apart): Δturnout,
   Δshares on matched sections, robust |z|>4 outliers, deciles of Δturnout vs
   runoff shares (a stuffing signature would skew the top deciles).
3. Jumps 2022-R2 → 2026-R2 (the same stage of the honest election four years
   earlier).
4. Klimek fingerprints on 2026-R2 (both candidates).

Run: cd analysis-tool && uv run python ../brazil-oct-2026-round-1/scripts/control_forensics_T2.py
--lang {ru,en,pt,es}; --fig-out DIR writes figures (+tables) into DIR instead of
analysis_T2/figures — used for the per-language site copies
(site/brazil-oct-2026-round-2/img/details/<lang>/; metrics always stay in analysis_T2/).
Output: brazil-oct-2026-round-1/analysis_T2/{figures/control_*.png, tables/control_*.csv,
       metrics_control_T2.json}
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

from election_forensics import plots  # noqa: E402  (style/rcParams)
from election_forensics.correlations import weighted_pearson  # noqa: E402
from election_forensics.data import ElectionData  # noqa: E402
from election_forensics.fingerprints import fingerprint_mixture  # noqa: E402
from election_forensics.i18n import label  # noqa: E402
from election_forensics.shpilkin import shpilkin_estimate, suggest_t_cut, votes_by_turnout  # noqa: E402

OUT = BR / "analysis_T2"
FIG = OUT / "figures"
TAB = OUT / "tables"

LULA = "votes:LULA"
BOLSONARO = "votes:BOLSONARO"

TR: dict[str, dict[str, str]] = {
    "ru": {
        "t22_1": "2022, 1-й тур", "t22_2": "2022, 2-й тур",
        "t26_1": "2026, 1-й тур", "t26_2": "2026, 2-й тур",
        "cut_ctrl": "граница по контролю-2022: {t}%",
        "cut_own": "собственный q99,5-2026 (2-й тур): {t}%",
        "share_voted_y": "Доля проголосовавших",
        "tt_title": "Распределения явки: 2022 и 2026, оба тура",
        "tA_x": "Явка 1-й тур, %", "tB_x": "Явка 2-й тур, %",
        "same_sections": "Те же секции (n={n}); диагональ — без изменений",
        "median_line": "медиана {v} п.п.",
        "mad_line": "медиана ± 4·MAD ({v})",
        "dturnout_x": "Δявка 2-й−1-й тур, п.п. (обрезано ±30)",
        "sections_y": "Секций",
        "jumps_ttl": "Скачки явки между турами",
        "dL": "Δдоля Лулы", "dB": "Δдоля Болсонару",
        "dshare_x": "Δдоля (доля от проголосовавших), п.п. (обрезано ±40)",
        "shares_ttl": "Изменение долей: {a} → {b}",
        "fp_title": "{e} — {p}: 2-я компонента {w} ({x}%; {y}%)",
        "cand_share_y": "Доля кандидата, %",
        "fp_suptitle": "2-й тур 2026: «отпечатки» без кластера у правого верхнего угла",
    },
    "en": {
        "t22_1": "2022, 1st round", "t22_2": "2022, 2nd round",
        "t26_1": "2026, 1st round", "t26_2": "2026, 2nd round",
        "cut_ctrl": "boundary from the 2022 control: {t}%",
        "cut_own": "runoff 2026's own q99.5: {t}%",
        "share_voted_y": "Share of voters",
        "tt_title": "Turnout distributions: 2022 and 2026, both rounds",
        "tA_x": "Turnout 1st round, %", "tB_x": "Turnout 2nd round, %",
        "same_sections": "Same sections (n={n}); diagonal — no change",
        "median_line": "median {v} p.p.",
        "mad_line": "median ± 4·MAD ({v})",
        "dturnout_x": "Δturnout R2−R1, p.p. (clipped at ±30)",
        "sections_y": "Sections",
        "jumps_ttl": "Turnout jumps between the rounds",
        "dL": "Δ Lula share", "dB": "Δ Bolsonaro share",
        "dshare_x": "Δ share (of votes cast), p.p. (clipped at ±40)",
        "shares_ttl": "Change in candidate shares: {a} → {b}",
        "fp_title": "{e} — {p}: 2nd component {w} ({x}%; {y}%)",
        "cand_share_y": "Candidate share, %",
        "fp_suptitle": "2026 runoff: fingerprints without a cluster in the top-right corner",
    },
    "pt": {
        "t22_1": "2022, 1.º turno", "t22_2": "2022, 2.º turno",
        "t26_1": "2026, 1.º turno", "t26_2": "2026, 2.º turno",
        "cut_ctrl": "fronteira pelo controlo de 2022: {t}%",
        "cut_own": "q99,5 próprio do 2.º turno de 2026: {t}%",
        "share_voted_y": "Fração dos votantes",
        "tt_title": "Distribuições de afluência: 2022 e 2026, os dois turnos",
        "tA_x": "Afluência 1.º turno, %", "tB_x": "Afluência 2.º turno, %",
        "same_sections": "As mesmas seções (n={n}); diagonal — sem mudança",
        "median_line": "mediana {v} p.p.",
        "mad_line": "mediana ± 4·MAD ({v})",
        "dturnout_x": "Δafluência 2.º−1.º turno, p.p. (cortado a ±30)",
        "sections_y": "Seções",
        "jumps_ttl": "Saltos de afluência entre turnos",
        "dL": "Δquota de Lula", "dB": "Δquota de Bolsonaro",
        "dshare_x": "Δquota (fração dos votos), p.p. (cortado a ±40)",
        "shares_ttl": "Mudança das quotas: {a} → {b}",
        "fp_title": "{e} — {p}: 2.ª componente {w} ({x}%; {y}%)",
        "cand_share_y": "Quota do candidato, %",
        "fp_suptitle": "2.º turno de 2026: impressões digitais sem clúster no canto superior direito",
    },
    "es": {
        "t22_1": "2022, 1.ª vuelta", "t22_2": "2022, 2.ª vuelta",
        "t26_1": "2026, 1.ª vuelta", "t26_2": "2026, 2.ª vuelta",
        "cut_ctrl": "frontera por el control de 2022: {t}%",
        "cut_own": "q99,5 propio de la 2.ª vuelta de 2026: {t}%",
        "share_voted_y": "Fracción de votantes",
        "tt_title": "Distribuciones de participación: 2022 y 2026, ambas vueltas",
        "tA_x": "Participación 1.ª vuelta, %", "tB_x": "Participación 2.ª vuelta, %",
        "same_sections": "Las mismas secciones (n={n}); diagonal — sin cambios",
        "median_line": "mediana {v} p.p.",
        "mad_line": "mediana ± 4·MAD ({v})",
        "dturnout_x": "Δparticipación 2.ª−1.ª vuelta, p.p. (recortado a ±30)",
        "sections_y": "Secciones",
        "jumps_ttl": "Saltos de participación entre vueltas",
        "dL": "Δporcentaje de Lula", "dB": "Δporcentaje de Bolsonaro",
        "dshare_x": "Δporcentaje (fracción de los votos), p.p. (recortado a ±40)",
        "shares_ttl": "Cambio de los porcentajes: {a} → {b}",
        "fp_title": "{e} — {p}: 2.ª componente {w} ({x}%; {y}%)",
        "cand_share_y": "Porcentaje del candidato, %",
        "fp_suptitle": "2.ª vuelta de 2026: huellas sin clúster en la esquina superior derecha",
    },
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load(csv_name: str, turno: int | None = None) -> ElectionData:
    df = pd.read_csv(BR / "data" / csv_name, dtype={"key": str})
    if turno is not None:
        df = df[df["turno"] == turno]
    df = df[df["voted"] > 0].copy()
    party_cols = [c for c in df.columns if c.startswith("votes:")]
    return ElectionData(name=csv_name, df=df, party_cols=party_cols)


def plot_turnout_dists(datas: dict[str, ElectionData], t_cut_control: float,
                       t_cut_own: float, lang: str, fig_dir: Path) -> None:
    tr = TR[lang]
    colors = {tr["t22_1"]: "#7f7f7f", tr["t22_2"]: "#9467bd",
              tr["t26_1"]: "#8ab4d9", tr["t26_2"]: "#c0392b"}
    fig, ax = plots.plt.subplots(figsize=(8.6, 3.8))
    for key in ("t22_1", "t22_2", "t26_1", "t26_2"):
        d = datas[key]
        centers, h = votes_by_turnout(d, None, 0.5)
        ax.plot(centers, h / h.sum(), drawstyle="steps-mid", lw=1.3,
                color=colors[tr[key]], label=tr[key])
    ax.axvline(t_cut_control, color="#d62728", lw=1.6,
               label=tr["cut_ctrl"].format(t=f"{t_cut_control:.1f}"))
    ax.axvline(t_cut_own, color="k", ls="--", lw=1.0,
               label=tr["cut_own"].format(t=f"{t_cut_own:.1f}"))
    ax.set_xlabel(label(lang, "turnout_x"))
    ax.set_ylabel(tr["share_voted_y"])
    ax.set_yscale("log")
    ax.set_ylim(1e-6, None)
    ax.set_xlim(10, 100)
    ax.legend(fontsize=7.5)
    ax.set_title(tr["tt_title"], fontsize=9)
    fig.tight_layout()
    fig.savefig(fig_dir / "control_turnout.png", bbox_inches="tight")
    plots.plt.close(fig)


def plot_jumps(m: pd.DataFrame, med: float, mad: float, lang: str, fig_dir: Path,
               name: str, ttl_a: str, ttl_b: str) -> None:
    tr = TR[lang]
    fig, axes = plots.plt.subplots(1, 3, figsize=(11.2, 3.5))

    ax = axes[0]
    ok = m.turnout_A.between(10, 100) & m.turnout_B.between(10, 100)
    ax.hist2d(m.turnout_A[ok], m.turnout_B[ok], bins=90,
              weights=m.registered_voters_B[ok], cmap="viridis",
              cmin=1e-9, norm=plots.matplotlib.colors.LogNorm())
    ax.plot([10, 100], [10, 100], "w--", lw=0.8, alpha=0.8)
    ax.set_xlabel(tr["tA_x"])
    ax.set_ylabel(tr["tB_x"])
    ax.set_title(tr["same_sections"].format(n=f"{len(m):,}"), fontsize=9)
    ax.grid(False)

    ax = axes[1]
    dT = m.d_turnout.clip(-30, 30)
    ax.hist(dT, bins=120, color="#1f77b4", alpha=0.8)
    ax.axvline(med, color="k", lw=1.0, label=tr["median_line"].format(v=f"{med:+.2f}"))
    for k in (-4, 4):
        x = med + k * 1.4826 * mad
        ax.axvline(x, color="#d62728", ls="--", lw=1.0,
                   label=tr["mad_line"].format(v=f"{x:+.1f}") if k > 0 else None)
    ax.set_xlabel(tr["dturnout_x"])
    ax.set_ylabel(tr["sections_y"])
    ax.set_title(tr["jumps_ttl"], fontsize=9)
    ax.legend(fontsize=7.5)

    ax = axes[2]
    bins = np.linspace(-40, 40, 130)
    ax.hist(m.d_share_lula.clip(-40, 40), bins=bins, color="#d62728",
            alpha=0.65, label=tr["dL"])
    ax.hist(m.d_share_bolsonaro.clip(-40, 40), bins=bins, color="#1f77b4",
            alpha=0.65, label=tr["dB"])
    ax.set_xlabel(tr["dshare_x"])
    ax.set_ylabel(tr["sections_y"])
    ax.set_title(tr["shares_ttl"].format(a=ttl_a, b=ttl_b), fontsize=9)
    ax.legend(fontsize=7.5)

    fig.tight_layout()
    fig.savefig(fig_dir / name, bbox_inches="tight")
    plots.plt.close(fig)


def matched_jumps(dA: ElectionData, dB: ElectionData, label_a: str, label_b: str,
                  lang: str, fig_dir: Path, fig_name: str) -> dict:
    """Δturnout / Δshares on matched sections of two elections."""
    cols = ["key", "uf", "name", "registered_voters", "voted", LULA, BOLSONARO]
    a = dA.df[cols].rename(columns={"registered_voters": "registered_voters_A",
                                    "voted": "voted_A", "name": "name_A"})
    b = dB.df[cols].rename(columns={"registered_voters": "registered_voters_B",
                                    "voted": "voted_B"})
    m = a.merge(b.drop(columns="uf"), on="key", how="inner")
    m["turnout_A"] = 100.0 * m.voted_A / m.registered_voters_A
    m["turnout_B"] = 100.0 * m.voted_B / m.registered_voters_B
    m["d_turnout"] = m.turnout_B - m.turnout_A
    m["d_share_lula"] = (100.0 * m[LULA + "_y"] / m.voted_B
                         - 100.0 * m[LULA + "_x"] / m.voted_A)
    m["d_share_bolsonaro"] = (100.0 * m[BOLSONARO + "_y"] / m.voted_B
                              - 100.0 * m[BOLSONARO + "_x"] / m.voted_A)
    med = float(m.d_turnout.median())
    mad = float((m.d_turnout - med).abs().median())
    m["z_jump"] = (m.d_turnout - med) / (1.4826 * mad)
    flagged = m[m.z_jump.abs() > 4]

    r_stab = weighted_pearson(m.turnout_A.to_numpy(), m.turnout_B.to_numpy(),
                              m.registered_voters_B.to_numpy(dtype=float))
    # deciles of the turnout gain vs the B-round shares (stuffing signature)
    m["dT_decile"] = pd.qcut(m.d_turnout, 10, labels=False, duplicates="drop") + 1
    dec = m.groupby("dT_decile").apply(lambda g: pd.Series({
        "d_turnout_median": g.d_turnout.median(),
        "sections": len(g),
        "shareB_lula": 100.0 * g[LULA + "_y"].sum() / g.voted_B.sum(),
        "shareB_bolsonaro": 100.0 * g[BOLSONARO + "_y"].sum() / g.voted_B.sum(),
    }), include_groups=False).reset_index()
    dec.to_csv(TAB / f"{fig_name.replace('.png', '')}_deciles.csv", index=False)

    out = {
        "match": {"A": label_a, "B": label_b, "sections_A": dA.n, "sections_B": dB.n,
                  "matched": len(m),
                  "matched_pct_of_B": round(100.0 * len(m) / dB.n, 2),
                  "matched_voters_B_pct": round(100.0 * m.voted_B.sum() / dB.df.voted.sum(), 2)},
        "d_turnout": {"median": round(med, 2), "mad": round(mad, 2),
                      "q01": round(m.d_turnout.quantile(0.01), 2),
                      "q99": round(m.d_turnout.quantile(0.99), 2),
                      "flagged_z4": len(flagged),
                      "flagged_pct": round(100.0 * len(flagged) / len(m), 3),
                      "up": int((m.z_jump > 4).sum()), "down": int((m.z_jump < -4).sum())},
        "d_share_lula": {"median": round(m.d_share_lula.median(), 2),
                         "q01": round(m.d_share_lula.quantile(0.01), 2),
                         "q99": round(m.d_share_lula.quantile(0.99), 2)},
        "d_share_bolsonaro": {"median": round(m.d_share_bolsonaro.median(), 2),
                              "q01": round(m.d_share_bolsonaro.quantile(0.01), 2),
                              "q99": round(m.d_share_bolsonaro.quantile(0.99), 2)},
        "r_turnoutA_turnoutB": round(r_stab, 4),
        "flagged_shareB_lula": round(100.0 * flagged[LULA + "_y"].sum() / flagged.voted_B.sum(), 2),
        "flagged_shareB_bolsonaro": round(
            100.0 * flagged[BOLSONARO + "_y"].sum() / flagged.voted_B.sum(), 2),
        "top_decile_shareB_lula": round(float(dec.iloc[-1].shareB_lula), 2),
        "top_decile_shareB_bolsonaro": round(float(dec.iloc[-1].shareB_bolsonaro), 2),
    }
    plot_jumps(m, med, mad, lang, fig_dir, fig_name, label_a, label_b)
    flagged.assign(absz=flagged.z_jump.abs()).nlargest(200, "absz")[
        ["key", "uf", "name_A", "registered_voters_A", "registered_voters_B",
         "turnout_A", "turnout_B", "d_turnout", "z_jump",
         "d_share_lula", "d_share_bolsonaro"]].to_csv(
        TAB / f"{fig_name.replace('.png', '')}_jumps_extreme.csv", index=False)
    return out


def main() -> None:
    global FIG, TAB
    ap = argparse.ArgumentParser(description="control runs for the BR-2026 runoff")
    ap.add_argument("--lang", default="en", choices=["ru", "en", "pt", "es"])
    ap.add_argument("--fig-out", type=Path, default=None,
                    help="directory for figures/tables instead of analysis_T2/ "
                         "(metrics still go to analysis_T2/metrics_control_T2.json)")
    args = ap.parse_args()
    lang = args.lang
    if args.fig_out is not None:
        FIG = args.fig_out
        TAB = FIG / "tables"
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)

    d26_2 = load("secoes_presidente_2026_T2.csv")
    d26_1 = load("secoes_presidente_2026.csv")
    d22_1 = load("secoes_presidente_2022.csv", turno=1)
    d22_2 = load("secoes_presidente_2022.csv", turno=2)
    log(f"2026-R2: {d26_2.n}; 2026-R1: {d26_1.n}; 2022-R1: {d22_1.n}; 2022-R2: {d22_2.n}")

    metrics: dict = {"title": "BR-2026 runoff vs controls (the same sections)"}

    # --- 1. Shpilkin: boundaries and tails -------------------------------------
    t_cut_22 = suggest_t_cut([d22_1, d22_2], 99.5)
    t_own_26r2 = float(np.percentile(
        np.repeat(d26_2.turnout.to_numpy(),
                  np.round(d26_2.registered.to_numpy()).astype(int)), 99.5))
    log(f"q99.5: control-2022 {t_cut_22:.2f}%; 2026-R2 own {t_own_26r2:.2f}%")

    rows = []
    for lab, d, party in (("2026-R2", d26_2, LULA), ("2026-R2", d26_2, BOLSONARO),
                          ("2022-R2", d22_2, LULA), ("2022-R2", d22_2, BOLSONARO)):
        ctrl = [d22_1, d22_2] if lab == "2026-R2" else None
        res_c = shpilkin_estimate(d, party, controls=ctrl)
        res_o = shpilkin_estimate(d, party)
        rows.append({
            "election": lab, "party": party.removeprefix("votes:"), "n": d.n,
            "t_cut_control": round(res_c.t_cut, 2) if ctrl else None,
            "tail_votes_party_control": res_c.tail_votes_party if ctrl else None,
            "tail_share_party_control_pct": round(res_c.tail_share_of_party, 3) if ctrl else None,
            "honest_share_control": round(res_c.honest_share_pct, 2) if ctrl else None,
            "observed_share": round(res_o.observed_share_pct, 2),
            "t_cut_own_q995": round(res_o.t_cut, 2),
            "tail_voters_own_pct": round(100.0 * res_o.tail_voters / d.voted.sum(), 3),
            "tail_share_party_own_pct": round(res_o.tail_share_of_party, 3),
            "mode": round(res_o.mode, 2), "sigma": round(res_o.sigma, 2),
        })
        log(f"{lab} {party.removeprefix('votes:')}: tail by control "
            f"{res_c.tail_share_of_party:.2f}% / own {res_o.tail_share_of_party:.2f}%")
    pd.DataFrame(rows).to_csv(TAB / "control_shpilkin.csv", index=False)
    metrics["shpilkin"] = rows
    metrics["t_cut"] = {"control_2022_max": round(t_cut_22, 2),
                        "own_2026_r2": round(t_own_26r2, 2)}
    plot_turnout_dists({"t22_1": d22_1, "t22_2": d22_2, "t26_1": d26_1, "t26_2": d26_2},
                       t_cut_22, t_own_26r2, lang, FIG)

    # --- 2. jumps 2026-R1 → 2026-R2 ---------------------------------------------
    metrics["jumps_2026_r1_r2"] = matched_jumps(
        d26_1, d26_2, "2026-R1", "2026-R2", lang, FIG, "control_jumps_2026.png")
    log(f"jumps 2026 R1→R2: {json.dumps(metrics['jumps_2026_r1_r2']['d_turnout'])}")

    # --- 3. jumps 2022-R2 → 2026-R2 ---------------------------------------------
    metrics["jumps_2022r2_2026r2"] = matched_jumps(
        d22_2, d26_2, "2022-R2", "2026-R2", lang, FIG, "control_jumps_2022r2.png")
    log(f"jumps 2022R2→2026R2: {json.dumps(metrics['jumps_2022r2_2026r2']['d_turnout'])}")

    # --- 4. fingerprints on 2026-R2 ----------------------------------------------
    fp_rows, fps = [], {}
    for party in (LULA, BOLSONARO):
        fp = fingerprint_mixture(d26_2, party)
        fps[party] = fp
        fp_rows.append({
            "election": "2026-R2", "party": party.removeprefix("votes:"),
            "weight_anom": round(fp.weight_anom, 4),
            "mean_main": f"({fp.mean_main[0]:.1f}; {fp.mean_main[1]:.1f})",
            "mean_anom": f"({fp.mean_anom[0]:.1f}; {fp.mean_anom[1]:.1f})",
            "separated": fp.separated,
            "anom_voters": fp.anom_cluster_voters,
        })
    pd.DataFrame(fp_rows).to_csv(TAB / "control_fingerprints_2026r2.csv", index=False)
    metrics["fingerprints_2026_r2"] = fp_rows

    tr = TR[lang]
    fig, axes = plots.plt.subplots(1, 2, figsize=(9.2, 3.8), sharex=True, sharey=True)
    for ax, party, color in ((axes[0], LULA, "#d62728"), (axes[1], BOLSONARO, "#1f77b4")):
        t = d26_2.turnout.to_numpy()
        s = d26_2.share(party).to_numpy()
        w = d26_2.registered.to_numpy(dtype=float)
        fp = fps[party]
        ax.hist2d(t, s, bins=[70, 70], weights=w, cmap="viridis",
                  cmin=1e-9, norm=plots.matplotlib.colors.LogNorm())
        ax.plot(*fp.mean_main, "o", ms=9, mfc="none", mec="white", mew=1.6)
        ax.plot(*fp.mean_anom, "s", ms=9, mfc="none", mec="#ff7f0e", mew=1.6)
        ax.set_title(tr["fp_title"].format(
            e=tr["t26_2"], p=party.removeprefix("votes:"), w=f"{fp.weight_anom:.2f}",
            x=f"{fp.mean_anom[0]:.0f}", y=f"{fp.mean_anom[1]:.0f}"), fontsize=8.5)
        ax.set_xlim(20, 100)
        ax.grid(False)
        ax.set_xlabel(label(lang, "turnout_x"))
    axes[0].set_ylabel(tr["cand_share_y"])
    fig.suptitle(tr["fp_suptitle"], fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "control_fingerprint_2026r2.png", bbox_inches="tight")
    plots.plt.close(fig)
    log(f"2026-R2 fingerprints: {fp_rows}")

    with open(OUT / "metrics_control_T2.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2, default=float)
    log(f"done: {OUT / 'metrics_control_T2.json'}")


if __name__ == "__main__":
    main()
