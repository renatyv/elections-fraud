#!/usr/bin/env python3
"""Stratified run: Shpilkin and Klimek fingerprints by macro-regions.

Checks the robustness of the conclusions of sections 2-3 of the REPORT against
regional heterogeneity (Lula's Northeast vs Bolsonaro's South; §13.2): the honest-core
boundary and the 2D-Gaussian mixtures are computed WITHIN each macro-region,
the region's distribution serves as its own control (before the 2022 control
elections were added; the control is now scripts/control_forensics.py,
section 12 of the REPORT). Additionally — a breakdown of the "corner"
(turnout ≥90% AND share ≥75%) against the regional boundary: how normal the
high-turnout NE sections are for their region.

Run: cd analysis-tool && uv run python ../brazil-oct-2026/scripts/stratified_forensics.py
Output: brazil-oct-2026/analysis/{figures/shpilkin_regions.png, fingerprint_*_regions.png,
       tables/{shpilkin_by_region,fingerprints_by_region,corners_by_region}.csv,
       metrics_stratified.json}

Flags: --lang ru|en|pt|es — figure label language (default en);
--fig-out DIR — write the figures (plus tables and metrics_stratified.json)
into DIR without touching brazil-oct-2026/analysis/.
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
from election_forensics.data import ElectionData  # noqa: E402
from election_forensics.fingerprints import fingerprint_mixture  # noqa: E402
from election_forensics.i18n import label  # noqa: E402
from election_forensics.shpilkin import shpilkin_estimate, votes_by_turnout  # noqa: E402

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
REG_NAMES = {"N": "North", "NE": "Northeast", "CW": "Centre-West",
             "SE": "Southeast", "S": "South", "ZZ": "Abroad"}
# macro-region names on the figures (metrics/log always use REG_NAMES); --lang ru keeps Russian
REG_NAMES_I18N: dict[str, dict[str, str]] = {
    "ru": {"N": "Север", "NE": "Северо-Восток", "CW": "Центр.-Запад",
           "SE": "Юго-Восток", "S": "Юг", "ZZ": "Заграница"},
    "en": {"N": "North", "NE": "Northeast", "CW": "Centre-West",
           "SE": "Southeast", "S": "South", "ZZ": "Abroad"},
    "pt": {"N": "Norte", "NE": "Nordeste", "CW": "Centro-Oeste",
           "SE": "Sudeste", "S": "Sul", "ZZ": "Exterior"},
    "es": {"N": "Norte", "NE": "Noreste", "CW": "Centro-Oeste",
           "SE": "Sudeste", "S": "Sur", "ZZ": "Exterior"},
}
CAND_NAMES: dict[str, dict[str, str]] = {
    "ru": {"BOLSONARO": "Болсонару", "LULA": "Лула"},
    "en": {"BOLSONARO": "Bolsonaro", "LULA": "Lula"},
    "pt": {"BOLSONARO": "Bolsonaro", "LULA": "Lula"},
    "es": {"BOLSONARO": "Bolsonaro", "LULA": "Lula"},
}
# --- custom figure labels (ru|en|pt|es) ---------------------------------------
TR: dict[str, dict[str, str]] = {
    "ru": {
        "reg_cut": "{reg}: граница {t}%",
        "share_voted_reg_y": "Доля проголосовавших региона",
        "shp_reg_title": "Распределения явки по макрорегионам\n"
                         "(свои границы честного спада, q99,5 региона)",
        "nat_ref": "нац. прогон: 0,62%",
        "tail_party_y": "Хвост партии, % её голосов",
        "tails_ttl": "Голоса выше региональной границы",
        "fp_reg_title": "{reg}: 2-я компонента {w} ({x}%; {y}%)",
        "fp_reg_suptitle": "«Отпечатки пальцев» внутри макрорегионов: сигнатура Klimek — "
                           "кластер у правого верхнего угла (90–100% × 80–100%)",
    },
    "en": {
        "reg_cut": "{reg}: boundary {t}%",
        "share_voted_reg_y": "Share of the region's voters",
        "shp_reg_title": "Turnout distributions by macro-region\n"
                         "(each region's own honest-decline boundary, regional q99.5)",
        "nat_ref": "national run: 0.62%",
        "tail_party_y": "Party tail, % of its votes",
        "tails_ttl": "Votes above the regional boundary",
        "fp_reg_title": "{reg}: 2nd component {w} ({x}%; {y}%)",
        "fp_reg_suptitle": "Election fingerprints within macro-regions: the Klimek signature "
                           "would be a cluster in the top-right corner (90–100% × 80–100%)",
    },
    "pt": {
        "reg_cut": "{reg}: fronteira {t}%",
        "share_voted_reg_y": "Fração dos votantes da região",
        "shp_reg_title": "Distribuições de afluência por macrorregião\n"
                         "(fronteiras de declínio honesto próprias, q99,5 da região)",
        "nat_ref": "estimativa nacional: 0,62%",
        "tail_party_y": "Cauda do partido, % dos seus votos",
        "tails_ttl": "Votos acima da fronteira regional",
        "fp_reg_title": "{reg}: 2.ª componente {w} ({x}%; {y}%)",
        "fp_reg_suptitle": "Impressões digitais dentro das macrorregiões: a assinatura de "
                           "Klimek seria um agrupamento no canto superior direito "
                           "(90–100% × 80–100%)",
    },
    "es": {
        "reg_cut": "{reg}: frontera {t}%",
        "share_voted_reg_y": "Fracción de los votantes de la región",
        "shp_reg_title": "Distribuciones de participación por macrorregión\n"
                         "(fronteras de descenso honesto propias, q99,5 de la región)",
        "nat_ref": "estimación nacional: 0,62%",
        "tail_party_y": "Cola del partido, % de sus votos",
        "tails_ttl": "Votos por encima de la frontera regional",
        "fp_reg_title": "{reg}: 2.ª componente {w} ({x}%; {y}%)",
        "fp_reg_suptitle": "Huellas electorales dentro de las macrorregiones: la firma de "
                           "Klimek sería un clúster en la esquina superior derecha "
                           "(90–100% × 80–100%)",
    },
}

REG_ORDER = ["N", "NE", "CW", "SE", "S", "ZZ"]
# ZZ (1,309 sections): the quantile and mixture are unstable at this n — computed
# for completeness, with a separate caveat in the report's conclusions
REG_STABLE = ["N", "NE", "CW", "SE", "S"]
REG_COLORS = {"N": "#8c564b", "NE": "#d62728", "CW": "#e6960c",
              "SE": "#1f77b4", "S": "#2ca02c", "ZZ": "#7f7f7f"}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def corner_stats(data: ElectionData, party: str, t_cut: float) -> dict:
    """The "corner" (turnout ≥90% AND party share ≥75%) and its position relative
    to the region's honest-decline boundary."""
    t = data.turnout.to_numpy()
    s = data.share(party).to_numpy()
    m = (t >= 90) & (s >= 75)
    return {
        "corner_sections": int(m.sum()),
        "corner_voters": int(data.df["registered_voters"].to_numpy()[m].sum()),
        "corner_votes_party": int(data.df[party].to_numpy()[m].sum()),
        "corner_below_tcut": int((m & (t < t_cut)).sum()),
    }


def plot_shpilkin_regions(rows: list[dict], datas: dict[str, ElectionData],
                          lang: str, fig_dir: Path) -> None:
    tr = TR[lang]
    reg_names = REG_NAMES_I18N[lang]
    fig, axes = plots.plt.subplots(1, 2, figsize=(9.2, 3.6))

    ax = axes[0]
    for reg in REG_ORDER:
        d = datas[reg]
        centers, h = votes_by_turnout(d, None, 0.5)
        dens = h / h.sum()  # share of the region's voters — shapes are comparable
        r = next(x for x in rows if x["reg"] == reg)
        ax.plot(centers, dens, drawstyle="steps-mid", lw=1.2, color=REG_COLORS[reg],
                label=tr["reg_cut"].format(reg=reg_names[reg], t=f"{r['t_cut']:.1f}"))
        ax.axvline(r["t_cut"], color=REG_COLORS[reg], ls="--", lw=0.8, alpha=0.7)
    ax.set_xlabel(label(lang, "turnout_x"))
    ax.set_ylabel(tr["share_voted_reg_y"])
    ax.set_yscale("log")
    ax.set_ylim(1e-6, None)
    ax.set_title(tr["shp_reg_title"], fontsize=9)
    ax.legend(fontsize=6.5)

    ax = axes[1]
    x = np.arange(len(REG_ORDER))
    w = 0.38
    vals_l = [next(r for r in rows if r["reg"] == reg)["leader_tail_pct"] for reg in REG_ORDER]
    vals_r = [next(r for r in rows if r["reg"] == reg)["runner_tail_pct"] for reg in REG_ORDER]
    ax.bar(x - w / 2, vals_l, w, color="#1f77b4", label=CAND_NAMES[lang]["BOLSONARO"])
    ax.bar(x + w / 2, vals_r, w, color="#d62728", label=CAND_NAMES[lang]["LULA"])
    for xi, v in zip(x - w / 2, vals_l):
        ax.text(xi, v + 0.015, f"{v:.2f}", ha="center", fontsize=6.5, color="#1f77b4")
    for xi, v in zip(x + w / 2, vals_r):
        ax.text(xi, v + 0.015, f"{v:.2f}", ha="center", fontsize=6.5, color="#d62728")
    ax.set_ylim(0, max(vals_l + vals_r) * 1.3)
    ax.axhline(0.62, color="k", lw=0.8, ls=":", label=tr["nat_ref"])
    ax.set_xticks(x, REG_ORDER, fontsize=8)
    ax.set_ylabel(tr["tail_party_y"])
    ax.set_title(tr["tails_ttl"], fontsize=9)
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(fig_dir / "shpilkin_regions.png", bbox_inches="tight")
    plots.plt.close(fig)


def plot_fingerprint_regions(datas: dict[str, ElectionData], fps: dict[tuple[str, str], object],
                             party: str, fname: str, lang: str, fig_dir: Path) -> None:
    tr = TR[lang]
    reg_names = REG_NAMES_I18N[lang]
    fig, axes = plots.plt.subplots(2, 3, figsize=(9.6, 6.2), sharex=True, sharey=True)
    for ax, reg in zip(axes.flat, REG_ORDER):
        d = datas[reg]
        t = d.turnout.to_numpy()
        s = d.share(party).to_numpy()
        w = d.registered.to_numpy(dtype=float)
        ok = np.isfinite(s) & (d.df["voted"].to_numpy() > 0)
        fp = fps[(reg, party)]
        ax.hist2d(t[ok], s[ok], bins=[70, 70], weights=w[ok], cmap="viridis",
                  cmin=1e-9, norm=plots.matplotlib.colors.LogNorm())
        ax.plot(*fp.mean_main, "o", ms=8, mfc="none", mec="white", mew=1.5)
        ax.plot(*fp.mean_anom, "s", ms=8, mfc="none", mec="#ff7f0e", mew=1.5)
        ax.set_title(tr["fp_reg_title"].format(
            reg=reg_names[reg], w=f"{fp.weight_anom:.2f}",
            x=f"{fp.mean_anom[0]:.0f}", y=f"{fp.mean_anom[1]:.0f}"), fontsize=8)
        ax.set_xlim(20, 100)
        ax.grid(False)
    for ax in axes[1]:
        ax.set_xlabel(label(lang, "turnout_x"), fontsize=8)
    for ax in axes[:, 0]:
        ax.set_ylabel(label(lang, "leader_share_y", p=party.removeprefix("votes:")), fontsize=8)
    fig.suptitle(tr["fp_reg_suptitle"], fontsize=9)
    fig.tight_layout()
    fig.savefig(fig_dir / fname, bbox_inches="tight")
    plots.plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description="Brazil-2026 stratification by macro-regions")
    ap.add_argument("--lang", default="en", choices=["ru", "en", "pt", "es"],
                    help="figure label language (default en)")
    ap.add_argument("--fig-out", type=Path, default=None,
                    help="directory for figures/tables/metrics instead of brazil-oct-2026/analysis/")
    args = ap.parse_args()
    lang = args.lang
    if args.fig_out is not None:
        fig_dir = args.fig_out
        tab_dir = fig_dir / "tables"
        metrics_path = fig_dir / "metrics_stratified.json"
    else:
        fig_dir, tab_dir, metrics_path = FIG, TAB, OUT / "metrics_stratified.json"
    fig_dir.mkdir(parents=True, exist_ok=True)
    tab_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(BR / "data" / "secoes_presidente_2026.csv")
    df = df[df["voted"] > 0].copy()
    party_cols = [c for c in df.columns if c.startswith("votes:")]
    uf2macro = {uf: m for m, ufs in MACRO.items() for uf in ufs}
    df["reg"] = df["uf"].map(uf2macro)
    assert df["reg"].notna().all(), "UF without a macro-region mapping"

    datas: dict[str, ElectionData] = {}
    rows: list[dict] = []
    fp_rows: list[dict] = []
    corner_rows: list[dict] = []
    fps: dict[tuple[str, str], object] = {}

    for reg in REG_ORDER:
        d = ElectionData(name=REG_NAMES[reg], df=df[df["reg"] == reg].copy(),
                         party_cols=party_cols)
        datas[reg] = d
        shp_l = shpilkin_estimate(d, LEADER)
        shp_r = shpilkin_estimate(d, RUNNER_UP)
        c_l = corner_stats(d, LEADER, shp_l.t_cut)
        c_r = corner_stats(d, RUNNER_UP, shp_r.t_cut)
        rows.append({
            "reg": reg, "reg_name": REG_NAMES[reg],
            "sections": d.n, "registered": int(d.registered.sum()),
            "voted": int(d.voted.sum()),
            "mode": round(shp_l.mode, 2), "sigma": round(shp_l.sigma, 2),
            "t_cut": round(shp_l.t_cut, 2),
            "tail_voters": shp_l.tail_voters,
            "tail_voters_pct": round(100 * shp_l.tail_voters / d.voted.sum(), 3),
            "leader_tail_votes": shp_l.tail_votes_party,
            "leader_tail_pct": round(shp_l.tail_share_of_party, 3),
            "leader_obs_share": round(shp_l.observed_share_pct, 2),
            "leader_honest_share": round(shp_l.honest_share_pct, 2),
            "runner_tail_votes": shp_r.tail_votes_party,
            "runner_tail_pct": round(shp_r.tail_share_of_party, 3),
            "runner_obs_share": round(shp_r.observed_share_pct, 2),
            "runner_honest_share": round(shp_r.honest_share_pct, 2),
        })
        for party, corner in ((LEADER, c_l), (RUNNER_UP, c_r)):
            fp = fingerprint_mixture(d, party)
            fps[(reg, party)] = fp
            fp_rows.append({
                "reg": reg, "reg_name": REG_NAMES[reg],
                "party": party.removeprefix("votes:"),
                "weight_anom": round(fp.weight_anom, 4),
                "mean_anom": f"({fp.mean_anom[0]:.1f}; {fp.mean_anom[1]:.1f})",
                "mean_main": f"({fp.mean_main[0]:.1f}; {fp.mean_main[1]:.1f})",
                "separated": fp.separated,
                "anom_voters": fp.anom_cluster_voters,
                "anom_votes_party": fp.anom_cluster_votes_party,
            })
            corner_rows.append({
                "reg": reg, "reg_name": REG_NAMES[reg],
                "party": party.removeprefix("votes:"),
                **corner,
                "corner_share_pct_of_party": round(
                    100 * corner["corner_votes_party"] / d.df[party].sum(), 3),
            })
        log(f"{REG_NAMES[reg]}: boundary {shp_l.t_cut:.1f}%; Bolsonaro tail "
            f"{shp_l.tail_share_of_party:.2f}% of his votes, Lula {shp_r.tail_share_of_party:.2f}%; "
            f"2nd component {fp_rows[-2]['weight_anom']}/{fp_rows[-1]['weight_anom']}")

    shp_tab = pd.DataFrame(rows)
    fp_tab = pd.DataFrame(fp_rows)
    corner_tab = pd.DataFrame(corner_rows)
    shp_tab.to_csv(tab_dir / "shpilkin_by_region.csv", index=False)
    fp_tab.to_csv(tab_dir / "fingerprints_by_region.csv", index=False)
    corner_tab.to_csv(tab_dir / "corners_by_region.csv", index=False)

    plot_shpilkin_regions(rows, datas, lang, fig_dir)
    plot_fingerprint_regions(datas, fps, LEADER, "fingerprint_bolsonaro_regions.png", lang, fig_dir)
    plot_fingerprint_regions(datas, fps, RUNNER_UP, "fingerprint_lula_regions.png", lang, fig_dir)

    # cross-check: sum of regional tails against the national run (§2)
    national = {"t_cut": 91.6, "tail_voters": 779_412, "leader_tail": 272_315,
                "runner_tail": 430_824}
    metrics = {
        "title": "Brazil 1st round 2026: stratification by macro-regions (Shpilkin, fingerprints)",
        "regions": REG_ORDER, "stable_regions": REG_STABLE,
        "shpilkin_by_region": rows,
        "fingerprints_by_region": fp_rows,
        "corners_by_region": corner_rows,
        "sum_of_regional_tails": {
            "voters": int(shp_tab["tail_voters"].sum()),
            "leader": int(shp_tab["leader_tail_votes"].sum()),
            "runner": int(shp_tab["runner_tail_votes"].sum()),
        },
        "national_run_for_reference": national,
        "note": "each region's boundary is its own q99.5 (no control election); "
                "ZZ: n=1309, quantile/mixture unstable, reference only",
    }
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2, default=float)

    log(f"sum of regional tails: {metrics['sum_of_regional_tails']['leader']:,} "
        f"(Bolsonaro) / {metrics['sum_of_regional_tails']['runner']:,} (Lula) "
        f"against the national run {national['leader_tail']:,}/{national['runner_tail']:,}")
    log(f"done: {OUT}")


if __name__ == "__main__":
    main()
