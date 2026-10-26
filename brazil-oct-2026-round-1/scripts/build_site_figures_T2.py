# Figures for the public site page of the BR-2026 runoff — one set per language
# (pt, en, es, ru). Inputs:
#   data/secoes_presidente_2026_T2.csv + data/secoes_presidente_2022.csv
#   data/trends/*.csv (election-night captures), analysis/trends/trends_summary.json
#   analysis_T2/metrics_T2.json (forensics run), analysis/paradox/{transfers_2026_matrix,
#   prediction_vs_actual.json}.json (paradox run).
# Run from the repo root:
#   cd analysis-tool && uv run python ../brazil-oct-2026-round-1/scripts/build_site_figures_T2.py
# Output: <repo>/site/brazil-oct-2026-round-2/img/<lang>/{result,counting,prediction,
#          transfers_2026,turnout,comet,control,selftest,swing}.png
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas", "matplotlib"]
# ///
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT.parent / "site" / "brazil-oct-2026-round-2" / "img"

BLUE = "#3b82c4"       # Bolsonaro
BLUE_SOFT = "#8ab4d9"
DARK = "#16324f"
RED = "#c0392b"        # Lula
GREY = "#8a97a5"
PURPLE = "#9b59b6"
AMBER = "#8a6116"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.edgecolor": GREY,
        "axes.labelcolor": DARK,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "xtick.color": DARK,
        "ytick.color": DARK,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)

# ── inputs ────────────────────────────────────────────────────────────────────
print("loading inputs ...")
trends = pd.read_csv(ROOT / "data" / "trends" / "results.csv")
trends_nat = pd.read_csv(ROOT / "data" / "trends" / "national.csv")
swing_dec = pd.read_csv(ROOT / "analysis" / "trends" / "swing_decomposition.csv")
import json  # noqa: E402

metrics = json.loads((ROOT / "analysis_T2" / "metrics_T2.json").read_text())
pva = json.loads((ROOT / "analysis" / "paradox" / "prediction_vs_actual.json").read_text())
t26 = pd.read_csv(ROOT / "data" / "secoes_presidente_2026_T2.csv",
                  usecols=["voted", "turnout_pct", "votes:LULA", "votes:BOLSONARO"])
t26 = t26[t26["voted"] > 0]
t22 = pd.read_csv(ROOT / "data" / "secoes_presidente_2022.csv",
                  usecols=["turno", "voted", "turnout_pct"])
t22 = t22[t22["voted"] > 0]
t26r1 = pd.read_csv(ROOT / "data" / "secoes_presidente_2026.csv",
                    usecols=["voted", "turnout_pct"])
t26r1 = t26r1[t26r1["voted"] > 0]

mat = pd.read_csv(ROOT / "analysis" / "paradox" / "transfers_2026_matrix.csv", index_col=0)

LULA_PCT = pva["actual_2026_runoff"]["lula_twoway_pct"]           # 51.79
BOLSO_PCT = round(100.0 - LULA_PCT, 2)                            # 48.21
PRED_LULA = pva["prediction_vs_actual"]["predicted_lula_twoway_pct"]  # 47.43
PRED_CI = pva["prediction_vs_actual"]["predicted_ci_pct"]         # [47.39, 47.45]
TURNOUT = pva["actual_2026_runoff"]["turnout_pct"]                # 80.78

SHP = metrics["shpilkin_leader"]
CUT = round(SHP["t_cut"], 1)
TAIL_PCT = round(100.0 * SHP["tail_voters"] / metrics["national"]["voted"], 2)
TAIL_LULA = round(100.0 * SHP["tail_share_of_party"], 2)
SHP_B = metrics["shpilkin_runner_up"]
TAIL_BOLSO = round(100.0 * SHP_B["tail_share_of_party"], 2)
corr_by_party = {r["party"]: r["pearson_w"] for r in metrics["correlations_national"]}
CORR_L = round(corr_by_party.get("LULA", 0.0), 2)
CORR_B = round(corr_by_party.get("BOLSONARO", 0.0), 2)
SELF_CLEAN = int(metrics["selftest"]["clean_tail_party"])
SELF_INJ = int(metrics["selftest"]["injected_tail_party"])
Z_CLEAN = round(float(metrics["selftest"]["peaks_z_clean"]), 2)
Z_PAINTED = round(float(metrics["selftest"]["peaks_z_rounded"]), 2)

tsum = json.loads((ROOT / "analysis" / "trends" / "trends_summary.json").read_text())
SWING = tsum["swing_decomposed"]
SWING_ANCHOR = SWING["anchor_lula_tw"]          # Lula two-way at the 1.56% anchor
SWING_NET = SWING["swing_pp"]                   # anchor → final, pp


def dec(lang: str) -> str:
    return "," if lang in ("pt", "es", "ru") else "."


def num(lang: str, v: float, nd: int = 2) -> str:
    return f"{v:.{nd}f}".replace(".", dec(lang))


# ── election-night counting trajectory ────────────────────────────────────────
pres_nat = trends_nat[trends_nat.race == "president"].copy()
pres = trends[(trends.race == "president") & (trends.area_level == "country")].copy()
pres = pres.merge(pres_nat[["fetch_ts_utc", "pct_counted"]], on="fetch_ts_utc",
                  suffixes=("", "_x"))
_ts = pd.to_datetime(pres.source_ts.str.replace(" BRT", "", regex=False),
                     format="%d/%m/%Y %H:%M:%S")
pres["brt_h"] = _ts.dt.hour + _ts.dt.minute / 60 + _ts.dt.second / 3600
traj = pres.drop_duplicates(subset=["source_ts", "candidate"])


def pct_lab(lang: str, v: float) -> str:
    return num(lang, v, 1).rstrip("0").rstrip(dec(lang)) + "%"


def fig_counting(lang: str, tr: dict) -> None:
    fig, ax = plt.subplots(figsize=(9.6, 4.6), dpi=150)
    piv = traj.pivot_table(index="brt_h", columns="candidate", values="pct").sort_index()
    x = piv.index.to_numpy()
    ax.plot(x, piv["LULA"], color=RED, lw=2.6, marker="o", ms=5, label="Lula")
    ax.plot(x, piv["FLAVIO BOLSONARO"], color=BLUE, lw=2.6, marker="o", ms=5,
            label="Flávio Bolsonaro")
    ax.axhline(50, color=DARK, ls="--", lw=1.2)
    ax.text(17.03, 50.4, "50%", color=DARK, fontsize=9)
    ax.set_xlim(16.98, 24.35)
    ax.set_ylim(40, 60)
    hours = list(range(17, 24))
    ax.set_xticks(hours, [f"{h}:00" for h in hours])
    ax.set_xlabel(tr["x_lab"])
    ax.set_ylabel(tr["y_lab"])
    ax.set_title(tr["title"])
    # top axis: share of sections counted, at the observed snapshot times only
    snap = (traj[["brt_h", "pct_counted"]].drop_duplicates("pct_counted")
            .sort_values("brt_h").reset_index(drop=True))
    ticks: list[float] = []
    labels: list[str] = []
    chosen: set[int] = set()
    for target in (1.5, 30, 95, 100):
        cand = snap[~snap.index.isin(chosen)]
        i = int((cand.pct_counted - target).abs().idxmin())
        chosen.add(i)
        ticks.append(float(snap.at[i, "brt_h"]))
        labels.append(pct_lab(lang, float(snap.at[i, "pct_counted"])))
    sec = ax.secondary_xaxis("top")
    sec.set_xticks(ticks, labels, fontsize=8.5, color=GREY)
    sec.set_xlabel(tr["x2_lab"], fontsize=9.5, color=GREY)
    for spine in sec.spines.values():
        spine.set_color(GREY)
    # annotate final
    t_last = float(x[-1])
    ax.annotate(f"{num(lang, LULA_PCT, 1)}%", xy=(t_last, LULA_PCT),
                xytext=(t_last + 0.3, LULA_PCT + 1.3),
                color=RED, fontsize=10.5, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.2))
    ax.annotate(f"{num(lang, BOLSO_PCT, 1)}%", xy=(t_last, BOLSO_PCT),
                xytext=(t_last + 0.3, BOLSO_PCT - 2.2),
                color=BLUE, fontsize=10.5, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.2))
    ax.text(
        0.5, 0.05, tr["box"], transform=ax.transAxes, fontsize=9.5,
        ha="center", va="bottom", color=DARK,
        bbox=dict(boxstyle="round,pad=0.45", fc="#f4f7fa", ec=GREY, lw=0.8))
    ax.legend(loc="upper right", fontsize=9.5, framealpha=0.9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(SITE / lang / "counting.png")
    plt.close(fig)


# ── swing decomposition by state batch ────────────────────────────────────────
def fig_swing(lang: str, tr: dict) -> None:
    d = swing_dec[swing_dec.swing_contribution_pp.abs() >= 0.05].sort_values(
        "swing_contribution_pp")
    y = np.arange(len(d))
    colors = [BLUE if v < 0 else RED for v in d.swing_contribution_pp]
    fig, ax = plt.subplots(figsize=(9.6, 7.4), dpi=150)
    ax.barh(y, d.swing_contribution_pp, color=colors, alpha=0.88, height=0.68, zorder=3)
    for yi, v in zip(y, d.swing_contribution_pp):
        ax.text(v + (0.06 if v >= 0 else -0.06), yi, f"{v:+.2f}",
                va="center", ha="left" if v >= 0 else "right",
                fontsize=8.6, color=DARK)
    ax.set_yticks(y, [c.upper() for c in d.area_code], fontsize=9)
    ax.axvline(0, color=DARK, lw=1.2)
    xmin, xmax = d.swing_contribution_pp.min(), d.swing_contribution_pp.max()
    ax.set_xlim(xmin - 0.75, xmax + 0.75)
    ax.set_xlabel(tr["x_lab"])
    ax.set_title(tr["title"])
    ax.text(0.985, 0.03, tr["box"].format(a=num(lang, SWING_ANCHOR, 2),
                                          f=num(lang, LULA_PCT, 1),
                                          n=num(lang, abs(SWING_NET), 2)),
            transform=ax.transAxes, fontsize=9.5, ha="right", va="bottom", color=DARK,
            bbox=dict(boxstyle="round,pad=0.45", fc="#f4f7fa", ec=GREY, lw=0.8))
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(SITE / lang / "swing.png")
    plt.close(fig)


# ── prediction vs actual ──────────────────────────────────────────────────────
def fig_prediction(lang: str, tr: dict) -> None:
    fig, ax = plt.subplots(figsize=(9.6, 4.8), dpi=150)
    xs = np.arange(2)
    w = 0.36
    pred = [100.0 - PRED_LULA, PRED_LULA]
    act = [BOLSO_PCT, LULA_PCT]
    b1 = ax.bar(xs - w / 2, pred, w, color=[BLUE_SOFT, "#e5a8a0"], zorder=3,
                label=tr["legend_pred"])
    b2 = ax.bar(xs + w / 2, act, w, color=[BLUE, RED], zorder=3, label=tr["legend_act"])
    err = PRED_LULA - PRED_CI[0]
    ax.errorbar([1 - w / 2], [PRED_LULA], yerr=[[err], [err]], fmt="none", ecolor=DARK,
                elinewidth=1.4, capsize=5, zorder=5)
    for bars, vals in ((b1, pred), (b2, act)):
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.6, f"{num(lang, v, 1)}%",
                    ha="center", va="bottom", fontsize=10.5, fontweight="bold", color=DARK,
                    zorder=6, bbox=dict(boxstyle="square,pad=0.3", fc="white", ec="none"))
    ax.set_xticks(xs, [tr["x_bolsonaro"], tr["x_lula"]], fontsize=10.5)
    ax.axhline(50, color=DARK, ls="--", lw=1.3, zorder=4)
    ax.set_ylim(0, 66)
    ax.set_ylabel(tr["y_lab"])
    ax.set_title(tr["title"])
    ax.text(
        0.5, 0.66, tr["box"].format(err=num(lang, abs(PRED_LULA - LULA_PCT), 2),
                                    lo=num(lang, PRED_CI[0], 2), hi=num(lang, PRED_CI[1], 2)),
        transform=ax.transAxes, fontsize=9.5, ha="center", va="top", color=DARK,
        bbox=dict(boxstyle="round,pad=0.45", fc="#f4f7fa", ec=GREY, lw=0.8))
    ax.legend(fontsize=9.5, framealpha=0.9, loc="upper center")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(SITE / lang / "prediction.png")
    plt.close(fig)


# ── actual 2026 R1→R2 transfer matrix ─────────────────────────────────────────
MICRO = ["SAMARA", "HERTZ", "CLARIANA", "EDMILSON", "GRASSI", "RUI", "LEONARDO"]
DESTS = ["LULA", "BOLSONARO", "BRANCO", "NULO", "NOTV2"]


def micro_row() -> tuple[str, np.ndarray]:
    votes_r1 = {c: pd.read_csv(ROOT / "data" / "secoes_presidente_2026.csv",
                               usecols=[f"votes:{c}"])[f"votes:{c}"].sum() for c in MICRO}
    tot = sum(votes_r1.values())
    row = np.zeros(len(DESTS))
    for c, v in votes_r1.items():
        if c in mat.index:
            row += (v / tot) * mat.loc[c, DESTS].to_numpy(dtype=float)
    return tot, row


def fig_transfers(lang: str, tr: dict) -> None:
    rows = ["LULA", "BOLSONARO", "CURY", "FERREIRA", "CAIADO", "ZEMA", "BRANCO", "NULO", "NEW"]
    m = mat.loc[rows, DESTS].to_numpy(dtype=float)
    tot_micro, row_micro = micro_row()
    rows_tr = rows + ["MICRO"]
    M = np.vstack([m, row_micro])
    dest_colors = [RED, BLUE, GREY, AMBER, DARK]
    y = np.arange(len(rows_tr))[::-1]
    fig, ax = plt.subplots(figsize=(10.4, 6.0), dpi=150)
    for j in range(M.shape[1]):
        ax.barh(y, M[:, j], left=M[:, :j].sum(axis=1),
                color=dest_colors[j], alpha=0.88, height=0.66, zorder=3,
                label=tr["dests"][j])
    for i in range(M.shape[0]):
        cum = 0.0
        for j in range(M.shape[1]):
            v = M[i, j]
            if v >= 0.05:
                ax.text(cum + v / 2, y[i], f"{100 * v:.0f}", ha="center", va="center",
                        fontsize=8.6, color="white", fontweight="bold", zorder=4)
            cum += v
    ax.set_yticks(y, [tr["rows"][r] for r in rows_tr], fontsize=10)
    ax.set_xlim(0, 1.0)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0], ["0%", "25%", "50%", "75%", "100%"])
    ax.set_xlabel(tr["x_lab"])
    ax.set_title(tr["title"])
    ax.legend(fontsize=9.5, framealpha=0.95, loc="upper center", ncol=5,
              bbox_to_anchor=(0.5, -0.10), columnspacing=1.1)
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(SITE / lang / "transfers_2026.png", bbox_inches="tight")
    plt.close(fig)


# ── turnout histogram ─────────────────────────────────────────────────────────
def fig_turnout(lang: str, tr: dict) -> None:
    fig, ax = plt.subplots(figsize=(9.6, 4.2), dpi=150)
    ax.hist(t26["turnout_pct"], bins=100, range=(0, 100), color=RED, alpha=0.8,
            edgecolor="white", linewidth=0.2)
    ax.axvline(CUT, color=DARK, linestyle="--", linewidth=1.6)
    ax.text(CUT - 1.2, ax.get_ylim()[1] * 0.92,
            tr["cut_lab"].format(t=num(lang, CUT, 1)), color=DARK, fontsize=10, ha="right")
    ax.text(0.975, 0.72, tr["box"].format(tail=num(lang, TAIL_PCT, 2),
                                          tl=num(lang, TAIL_LULA, 2),
                                          tb=num(lang, TAIL_BOLSO, 2)),
            transform=ax.transAxes, fontsize=9.5, ha="right", va="top", color=DARK,
            bbox=dict(boxstyle="round,pad=0.45", fc="#f4f7fa", ec=GREY, lw=0.8))
    ax.set_xlim(0, 100)
    ax.set_xlabel(tr["x_lab"])
    ax.set_ylabel(tr["y_lab"])
    ax.set_title(tr["title"])
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(SITE / lang / "turnout.png")
    plt.close(fig)


# ── comet scatter ─────────────────────────────────────────────────────────────
def fig_comet(lang: str, tr: dict) -> None:
    t = t26["turnout_pct"]
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.8), dpi=150, sharex=True, sharey=True)
    bins = list(range(20, 105, 5))
    for ax, col, name, color in (
        (axes[0], "votes:LULA", tr["lula"], RED),
        (axes[1], "votes:BOLSONARO", tr["bolsonaro"], BLUE),
    ):
        share = t26[col] / t26["voted"] * 100
        ax.scatter(t, share, s=1.2, color=color, alpha=0.10, linewidths=0, rasterized=True)
        grp = pd.cut(t, bins)
        mser = pd.DataFrame({"g": grp, "t": t, "s": share, "w": t26["voted"]}).groupby(
            "g", observed=True).apply(
            lambda g: pd.Series(
                {"x": (g["t"] * g["w"]).sum() / g["w"].sum(),
                 "y": (g["s"] * g["w"]).sum() / g["w"].sum()}
            ), include_groups=False)
        ax.plot(mser["x"], mser["y"], color=DARK, linewidth=2.6, marker="o", markersize=5,
                zorder=5, label=tr["legend"])
        ax.set_title(name, fontsize=11.5)
        ax.set_xlim(20, 100)
        ax.set_ylim(-2, 102)
        ax.set_xlabel(tr["x_lab"])
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel(tr["y_lab"])
    axes[0].legend(loc="upper left", fontsize=9, framealpha=0.9)
    axes[1].text(0.03, 0.95, tr["box"].format(cl=num(lang, CORR_L, 2), cb=num(lang, CORR_B, 2)),
                 transform=axes[1].transAxes, fontsize=9.5, va="top", color=DARK,
                 bbox=dict(boxstyle="round,pad=0.45", fc="#f4f7fa", ec=GREY, lw=0.8))
    fig.suptitle(tr["title"], fontsize=13, fontweight="bold", y=1.0)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(SITE / lang / "comet.png")
    plt.close(fig)


# ── control: four turnout curves ──────────────────────────────────────────────
def fig_control(lang: str, tr: dict) -> None:
    fig, ax = plt.subplots(figsize=(9.6, 4.4), dpi=150)
    series = [
        (t22.loc[t22.turno == 1, "turnout_pct"], GREY, tr["l22_1"]),
        (t22.loc[t22.turno == 2, "turnout_pct"], PURPLE, tr["l22_2"]),
        (t26r1["turnout_pct"], BLUE_SOFT, tr["l26_1"]),
        (t26["turnout_pct"], RED, tr["l26_2"]),
    ]
    for s, color, label in series:
        ax.hist(s, bins=180, range=(0, 100), density=True, histtype="step",
                color=color, linewidth=1.4, label=label)
    ax.set_yscale("log")
    ax.set_xlim(10, 100)
    ax.set_xlabel(tr["x_lab"])
    ax.set_ylabel(tr["y_lab"])
    ax.set_title(tr["title"])
    ax.legend(loc="upper left", fontsize=9.5, framealpha=0.9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(SITE / lang / "control.png")
    plt.close(fig)


# ── self-test ─────────────────────────────────────────────────────────────────
def fig_selftest(lang: str, tr: dict) -> None:
    growth = SELF_INJ / max(SELF_CLEAN, 1)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.6, 4.2), dpi=150)
    bars1 = ax1.bar([tr["clean"], tr["injected"]], [SELF_CLEAN, SELF_INJ],
                    color=[RED, BLUE], width=0.55)
    ax1.set_yscale("log")
    for b, v in zip(bars1, (SELF_CLEAN, SELF_INJ)):
        ax1.text(b.get_x() + b.get_width() / 2, v * 1.25,
                 f"{v:,}".replace(",", " "), ha="center", fontsize=10.5,
                 fontweight="bold", color=DARK)
    ax1.annotate(f"×{growth:,.0f}", xy=(1, SELF_INJ * 0.35),
                 xytext=(0.42, SELF_INJ * 0.5), fontsize=15, fontweight="bold",
                 color=BLUE, arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.8))
    ax1.set_ylabel(tr["x1_lab"])
    ax1.set_title(tr["t1"], fontsize=11.5)
    ax1.spines[["top", "right"]].set_visible(False)

    bars2 = ax2.bar([tr["clean2"], tr["painted"]], [Z_CLEAN, Z_PAINTED],
                    color=[RED, BLUE], width=0.55)
    ax2.axhline(2, color=GREY, linestyle=":", linewidth=1.4)
    ax2.text(1.42, 2.35, "z = 2", color=GREY, fontsize=9.5, ha="right")
    for b, v in zip(bars2, (Z_CLEAN, Z_PAINTED)):
        ax2.text(b.get_x() + b.get_width() / 2, v + 0.25, f"z = {v:.2f}",
                 ha="center", fontsize=10.5, fontweight="bold", color=DARK)
    ax2.set_ylim(0, max(11.5, Z_PAINTED + 1.5))
    ax2.set_title(tr["t2"], fontsize=11.5)
    ax2.spines[["top", "right"]].set_visible(False)
    for lbl in list(ax1.get_xticklabels()) + list(ax2.get_xticklabels()):
        lbl.set_fontsize(9.5)

    fig.suptitle(tr["suptitle"], fontsize=13, fontweight="bold", y=1.0)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(SITE / lang / "selftest.png")
    plt.close(fig)


T_COUNT = {
"en": {
    "title": "Election night: the lead flipped as counting progressed",
    "x_lab": "Brasília time, 25 Oct 2026",
    "x2_lab": "% of sections counted",
    "y_lab": "% of valid votes counted so far",
    "box": ("Early-reporting states lean Bolsonaro (mean Lula two-way\n"
            "46.7% in the 11 states that crossed 50% counted first,\n"
            "vs 54.0% in the other 17). The counting order, not the\n"
            "count itself, moved the lines."),
},
"pt": {
    "title": "Noite eleitoral: a liderança mudou conforme a apuração avançava",
    "x_lab": "horário de Brasília, 25 out 2026",
    "x2_lab": "% das seções apuradas",
    "y_lab": "% dos votos válidos apurados até o momento",
    "box": ("Os estados que apuraram primeiro puxam para Bolsonaro\n"
            "(média de Lula no confronto direto: 46,7% nos 11 estados\n"
            "que passaram de 50% apurado antes; 54,0% nos outros 17).\n"
            "A ordem da apuração, não a contagem, movia as linhas."),
},
"es": {
    "title": "Noche electoral: el liderazgo cambió según avanzó el escrutinio",
    "x_lab": "hora de Brasilia, 25 oct 2026",
    "x2_lab": "% de secciones escrutadas",
    "y_lab": "% de votos válidos escrutados hasta el momento",
    "box": ("Los estados que escrutaron primero se inclinan por Bolsonaro\n"
            "(media de Lula cara a cara: 46,7% en los 11 estados que\n"
            "pasaron el 50% escrutado primero; 54,0% en los otros 17).\n"
            "El orden del escrutinio, no el recuento, movía las líneas."),
},
"ru": {
    "title": "Вечер выборов: лидер менялся по мере подсчёта",
    "x_lab": "время в Бразилиа, 25 окт 2026",
    "x2_lab": "% обработанных секций",
    "y_lab": "% действительных голосов на момент",
    "box": ("Первыми отчитываются штаты Болсонару (средняя доля Лулы\n"
            "при очной ставке: 46,7% в 11 штатах, первыми прошедших 50%,\n"
            "против 54,0% в остальных 17). Линии двигал порядок\n"
            "подсчёта, а не сам подсчёт."),
},
}

T_SWING = {
"en": {
    "title": "Which states' batches moved the national line",
    "x_lab": "contribution to Lula's two-way share, percentage points",
    "box": ("From the anchor point (1.6% counted, Lula {a}%) to the final {f}%:\n"
            "net {n} pp. Blue: South/Southeast batches that reported early;\n"
            "red: Northeast batches that dominated after ~30% counted."),
},
"pt": {
    "title": "Quais estados moveram a linha nacional",
    "x_lab": "contribuição para a fração de Lula no confronto direto, pontos",
    "box": ("Do ponto de ancoragem (1,6% apurado, Lula {a}%) ao final {f}%:\n"
            "líquido de {n} p.p. Azul: lotes do Sul/Sudeste que apuraram cedo;\n"
            "vermelho: lotes do Nordeste que dominaram após ~30% apurado."),
},
"es": {
    "title": "Qué estados movieron la línea nacional",
    "x_lab": "contribución a la fracción de Lula cara a cara, puntos",
    "box": ("Del punto de anclaje (1,6% escrutado, Lula {a}%) al final {f}%:\n"
            "neto {n} puntos. Azul: lotes del Sur/Sudeste que escrutaron pronto;\n"
            "rojo: lotes del Nordeste que dominaron tras ~30% escrutado."),
},
"ru": {
    "title": "Чьи партии голосов двигали общенациональную линию",
    "x_lab": "вклад в долю Лулы при очной ставке, п.п.",
    "box": ("От точки отсчёта (1,6% обработано, Лула {a}%) до итоговых {f}%:\n"
            "нетто {n} п.п. Синие — партии Юга/Юго-Востока, отчитавшиеся рано;\n"
            "красные — партии Северо-Востока, доминировавшие после ~30%."),
},
}

T_PRED = {
"en": {
    "title": "The round-1 conditional scenario vs the actual runoff",
    "legend_pred": "scenario from 2022 transfer rates",
    "legend_act": "actual runoff, 25 Oct 2026",
    "x_bolsonaro": "Flávio Bolsonaro", "x_lula": "Lula",
    "y_lab": "% of the two-candidate valid vote",
    "box": ("Actual Lula share exceeded the scenario by {err} pp.\n"
            "The whisker is the scenario's bootstrap CI ({lo}–{hi}):\n"
            "model resampling only — mapping and behaviour-change\n"
            "uncertainty were excluded by construction."),
},
"pt": {
    "title": "O cenário condicional do 1.º turno contra o 2.º turno real",
    "legend_pred": "cenário com taxas de transferência de 2022",
    "legend_act": "2.º turno real, 25 out 2026",
    "x_bolsonaro": "Flávio Bolsonaro", "x_lula": "Lula",
    "y_lab": "% dos votos válidos dos dois candidatos",
    "box": ("A parcela real de Lula superou o cenário em {err} p.p.\n"
            "A barra de erro é o intervalo bootstrap do cenário ({lo}–{hi}):\n"
            "apenas reamostragem do modelo — a incerteza do mapeamento\n"
            "e da mudança de comportamento ficou fora por construção."),
},
"es": {
    "title": "El escenario condicional de la 1.ª vuelta frente a la 2.ª vuelta real",
    "legend_pred": "escenario con tasas de transferencia de 2022",
    "legend_act": "2.ª vuelta real, 25 oct 2026",
    "x_bolsonaro": "Flávio Bolsonaro", "x_lula": "Lula",
    "y_lab": "% de los votos válidos de dos candidatos",
    "box": ("La porción real de Lula superó el escenario en {err} puntos.\n"
            "La barra de error es el intervalo bootstrap del escenario\n"
            "({lo}–{hi}): solo remuestreo del modelo — la incertidumbre\n"
            "del mapeo y del cambio de comportamiento quedó fuera."),
},
"ru": {
    "title": "Условный сценарий 1-го тура против фактического 2-го",
    "legend_pred": "сценарий по коэффициентам перетоков 2022",
    "legend_act": "фактический 2-й тур, 25 окт 2026",
    "x_bolsonaro": "Флавиу Болсонару", "x_lula": "Лула",
    "y_lab": "% действительных голосов двоих",
    "box": ("Фактическая доля Лулы превысила сценарий на {err} п.п.\n"
            "Ус — бутстреп-интервал сценария ({lo}–{hi}): только\n"
            "повторные выборки модели; неопределённость сопоставления\n"
            "и изменения поведения исключена по построению."),
},
}

T_TRANSFERS = {
"en": {
    "title": "Actual 2026 transfers between the rounds — ecological estimates from section totals,\nnot observed individual transitions",
    "dests": ("→ Lula", "→ Flávio Bolsonaro", "→ blank", "→ null", "→ stayed home"),
    "rows": {"LULA": "Lula voters", "BOLSONARO": "Bolsonaro voters", "CURY": "Cury",
             "FERREIRA": "Ferreira", "CAIADO": "Caiado", "ZEMA": "Zema",
             "BRANCO": "blank R1", "NULO": "null R1", "NEW": "runoff-only voters",
             "MICRO": "7 micro-candidates"},
    "x_lab": "round-1 vote, 2026",
},
"pt": {
    "title": "Transferências reais de 2026 entre os turnos — estimativas ecológicas dos totais por seção,\nnão trajetórias individuais observadas",
    "dests": ("→ Lula", "→ Flávio Bolsonaro", "→ branco", "→ nulo", "→ ficou em casa"),
    "rows": {"LULA": "eleitores de Lula", "BOLSONARO": "eleitores de Bolsonaro",
             "CURY": "Cury", "FERREIRA": "Ferreira", "CAIADO": "Caiado", "ZEMA": "Zema",
             "BRANCO": "branco 1.º turno", "NULO": "nulo 1.º turno",
             "NEW": "eleitores só do 2.º turno", "MICRO": "7 microcandidatos"},
    "x_lab": "voto no 1.º turno, 2026",
},
"es": {
    "title": "Transferencias reales de 2026 entre las vueltas — estimaciones ecológicas de los totales por sección,\nno trayectorias individuales observadas",
    "dests": ("→ Lula", "→ Flávio Bolsonaro", "→ blanco", "→ nulo", "→ se quedó en casa"),
    "rows": {"LULA": "votantes de Lula", "BOLSONARO": "votantes de Bolsonaro",
             "CURY": "Cury", "FERREIRA": "Ferreira", "CAIADO": "Caiado", "ZEMA": "Zema",
             "BRANCO": "blanco 1.ª vuelta", "NULO": "nulo 1.ª vuelta",
             "NEW": "votantes solo de la 2.ª vuelta", "MICRO": "7 microcandidatos"},
    "x_lab": "voto en la 1.ª vuelta, 2026",
},
"ru": {
    "title": "Фактические перетоки 2026 года между турами — экологические оценки по итогам секций,\nне наблюдаемые индивидуальные переходы",
    "dests": ("→ Лула", "→ Флавиу Болсонару", "→ белый", "→ недействительный", "→ остался дома"),
    "rows": {"LULA": "избиратели Лулы", "BOLSONARO": "избиратели Болсонару",
             "CURY": "Кури", "FERREIRA": "Феррейра", "CAIADO": "Кайаду", "ZEMA": "Зема",
             "BRANCO": "белый 1-й тур", "NULO": "недействительный 1-й тур",
             "NEW": "голосовавшие только во 2-м туре", "MICRO": "7 микрокандидатов"},
    "x_lab": "голос в 1-м туре, 2026",
},
}

T_TURNOUT = {
"en": {
    "title": "Runoff turnout distribution across sections",
    "x_lab": "Turnout, % of registered voters",
    "y_lab": "Number of sections",
    "cut_lab": "sample percentile q99.5 ({t}%)",
    "box": ("Above {t}% turnout: {tail}% of ballots.\nCandidate shares in this tail:\n"
            "Lula {tl}%; Bolsonaro {tb}%.\nDescriptive counts, not identified fraudulent votes."),
},
"pt": {
    "title": "Distribuição do comparecimento no 2.º turno por seção",
    "x_lab": "Comparecimento, % dos eleitores aptos",
    "y_lab": "Número de seções",
    "cut_lab": "percentil amostral q99,5 ({t}%)",
    "box": ("Acima de {t}%: {tail}% dos votos.\nParcela de cada candidato na cauda:\n"
            "Lula {tl}%; Bolsonaro {tb}%.\nContagens descritivas, não votos fraudulentos identificados."),
},
"es": {
    "title": "Distribución de participación del 2.ª vuelta por sección",
    "x_lab": "Participación, % de los electores inscritos",
    "y_lab": "Número de secciones",
    "cut_lab": "percentil muestral q99,5 ({t}%)",
    "box": ("Por encima de {t}%: {tail}% de los votos.\nPorción de cada candidato en la cola:\n"
            "Lula {tl}%; Bolsonaro {tb}%.\nRecuentos descriptivos, no fraude identificado."),
},
"ru": {
    "title": "Распределение явки 2-го тура по секциям",
    "x_lab": "Явка, % от зарегистрированных",
    "y_lab": "Число секций",
    "cut_lab": "перцентиль выборки q99,5 ({t}%)",
    "box": ("Выше {t}% явки: {tail}% голосов.\nДоля кандидата в этом хвосте:\n"
            "Лула {tl}%; Болсонару {tb}%.\nОписательные числа, а не выявленные вбросы."),
},
}

T_COMET = {
"en": {
    "title": "Turnout × result — horizontal clouds, no “comet tail”",
    "x_lab": "Turnout, %", "y_lab": "Share of ballots cast, %",
    "legend": "average by turnout group",
    "lula": "Lula — 51.8% of valid votes",
    "bolsonaro": "Flávio Bolsonaro — 48.2% of valid votes",
    "box": "Weighted national correlations:\nLula {cl}; Bolsonaro {cb}.",
},
"pt": {
    "title": "Comparecimento × resultado — nuvens horizontais, sem “cauda de cometa”",
    "x_lab": "Comparecimento, %", "y_lab": "% dos votos apurados",
    "legend": "média por faixa de comparecimento",
    "lula": "Lula — 51,8% dos votos válidos",
    "bolsonaro": "Flávio Bolsonaro — 48,2% dos votos válidos",
    "box": "Correlações nacionais ponderadas:\nLula {cl}; Bolsonaro {cb}.",
},
"es": {
    "title": "Participación × resultado — nubes horizontales, sin «cola de cometa»",
    "x_lab": "Participación, %", "y_lab": "% de los votos emitidos",
    "legend": "promedio por grupo de participación",
    "lula": "Lula — 51,8% de votos válidos",
    "bolsonaro": "Flávio Bolsonaro — 48,2% de votos válidos",
    "box": "Correlaciones nacionales ponderadas:\nLula {cl}; Bolsonaro {cb}.",
},
"ru": {
    "title": "Явка × результат — горизонтальные облака, без «хвоста кометы»",
    "x_lab": "Явка, %", "y_lab": "% от проголосовавших",
    "legend": "среднее по группам явки",
    "lula": "Лула — 51,8% действительных",
    "bolsonaro": "Флавиу Болсонару — 48,2% действительных",
    "box": "Взвешенные корреляции по стране:\nЛула {cl}; Болсонару {cb}.",
},
}

T_CONTROL = {
"en": {
    "title": "Turnout distributions: 2022 and 2026, both rounds",
    "x_lab": "Turnout, %", "y_lab": "Share of voters (log scale)",
    "l22_1": "2022, 1st round", "l22_2": "2022, 2nd round",
    "l26_1": "2026, 1st round", "l26_2": "2026, runoff",
},
"pt": {
    "title": "Distribuições de comparecimento: 2022 e 2026, os dois turnos",
    "x_lab": "Comparecimento, %", "y_lab": "Parcela dos eleitores (escala log)",
    "l22_1": "2022, 1.º turno", "l22_2": "2022, 2.º turno",
    "l26_1": "2026, 1.º turno", "l26_2": "2026, 2.º turno",
},
"es": {
    "title": "Distribuciones de participación: 2022 y 2026, ambas vueltas",
    "x_lab": "Participación, %", "y_lab": "Proporción de electores (escala log)",
    "l22_1": "2022, 1.ª vuelta", "l22_2": "2022, 2.ª vuelta",
    "l26_1": "2026, 1.ª vuelta", "l26_2": "2026, 2.ª vuelta",
},
"ru": {
    "title": "Распределения явки: 2022 и 2026, оба тура",
    "x_lab": "Явка, %", "y_lab": "Доля проголосовавших (лог. шкала)",
    "l22_1": "2022, 1-й тур", "l22_2": "2022, 2-й тур",
    "l26_1": "2026, 1-й тур", "l26_2": "2026, 2-й тур",
},
}

T_SELFTEST = {
"en": {
    "suptitle": "Sensitivity to two specified synthetic perturbations",
    "t1": "Votes above the turnout threshold",
    "t2": "Round-number peaks statistic (z)",
    "clean": "original data",
    "injected": "+2M synthetic ballots\ninjected (10% of sections)",
    "clean2": "original data",
    "painted": "turnout “painted” to whole %\n(5% of sections)",
    "x1_lab": "votes in the selected tail",
},
"pt": {
    "suptitle": "Sensibilidade a duas perturbações sintéticas específicas",
    "t1": "Votos acima do limiar de comparecimento",
    "t2": "Estatística de picos em números redondos (z)",
    "clean": "dados originais",
    "injected": "+2 mi de votos sintéticos\ninjetados (10% das seções)",
    "clean2": "dados originais",
    "painted": "comparecimento “ajustado” a % inteiro\n(5% das seções)",
    "x1_lab": "votos na cauda selecionada",
},
"es": {
    "suptitle": "Sensibilidad a dos perturbaciones sintéticas específicas",
    "t1": "Votos sobre el umbral de participación",
    "t2": "Estadística de picos en números redondos (z)",
    "clean": "datos originales",
    "injected": "+2 millones de votos sintéticos\ninyectados (10% de las secciones)",
    "clean2": "datos originales",
    "painted": "participación «ajustada» a % entero\n(5% de las secciones)",
    "x1_lab": "votos en la cola seleccionada",
},
"ru": {
    "suptitle": "Чувствительность к двум заданным синтетическим вмешательствам",
    "t1": "Голоса выше порога явки",
    "t2": "Статистика пиков на круглых числах (z)",
    "clean": "исходные данные",
    "injected": "+2 млн синтетических голосов\nвброшено (10% секций)",
    "clean2": "исходные данные",
    "painted": "явка «подогнана» под целый %\n(5% секций)",
    "x1_lab": "голоса в выделенном хвосте",
},
}


def fig_result(lang: str, tr: dict) -> None:
    fig, ax = plt.subplots(figsize=(9.6, 3.4), dpi=150)
    y = [1, 0]
    vals = [LULA_PCT, BOLSO_PCT]
    bars = ax.barh(y, vals, color=[RED, BLUE], alpha=0.9, height=0.58, zorder=3)
    for b, v in zip(bars, vals):
        ax.text(v + 0.7, b.get_y() + b.get_height() / 2, f"{num(lang, v, 2)}%",
                va="center", fontsize=12, fontweight="bold", color=DARK)
    ax.set_yticks(y, ["Lula (PT)", "Flávio Bolsonaro (PL)"], fontsize=11)
    ax.set_xlim(0, 62)
    ax.axvline(50, color=DARK, ls="--", lw=1.3, zorder=4)
    ax.text(50.5, 1.38, "50%", color=DARK, fontsize=9)
    ax.set_xlabel(tr["x_lab"])
    ax.set_title(tr["title"])
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(SITE / lang / "result.png")
    plt.close(fig)


T_RESULT = {
"en": {"title": "Runoff result, 25 October 2026",
       "x_lab": "% of valid votes"},
"pt": {"title": "Resultado do 2.º turno, 25 de outubro de 2026",
       "x_lab": "% dos votos válidos"},
"es": {"title": "Resultado de la 2.ª vuelta, 25 de octubre de 2026",
       "x_lab": "% de votos válidos"},
"ru": {"title": "Итог 2-го тура, 25 октября 2026",
       "x_lab": "% действительных голосов"},
}

ALL = {"result": (fig_result, T_RESULT), "counting": (fig_counting, T_COUNT),
       "swing": (fig_swing, T_SWING),
       "prediction": (fig_prediction, T_PRED), "transfers_2026": (fig_transfers, T_TRANSFERS),
       "turnout": (fig_turnout, T_TURNOUT), "comet": (fig_comet, T_COMET),
       "control": (fig_control, T_CONTROL), "selftest": (fig_selftest, T_SELFTEST)}

for lang in ("en", "pt", "es", "ru"):
    (SITE / lang).mkdir(parents=True, exist_ok=True)
    for name, (fn, tr) in ALL.items():
        fn(lang, tr[lang])
    print(f"{lang}: {len(ALL)} figures -> site/brazil-oct-2026-round-2/img/{lang}/")
