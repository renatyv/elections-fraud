# Preliminary site figures for the BR-2026 runoff page — the subset computable
# before TSE publishes the post-runoff section export: election-night counting
# trajectory, per-state swing decomposition, and the round-1 scenario vs the
# actual result. build_site_figures_T2.py overwrites these with the final
# versions when the full pipeline runs.
# Inputs: data/trends/{results,national}.csv, analysis/trends/{trends_summary.json,
# swing_decomposition.csv}, analysis/paradox/paradox_results.json.
# Run from the repo root:
#   cd analysis-tool && uv run python ../brazil-oct-2026-round-1/scripts/build_site_figures_T2_prelim.py
# Output: <repo>/site/brazil-oct-2026-round-2/img/<lang>/{counting,swing,prediction}.png
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas", "matplotlib"]
# ///
import json
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
tsum = json.loads((ROOT / "analysis" / "trends" / "trends_summary.json").read_text())
prev = json.loads((ROOT / "analysis" / "paradox" / "paradox_results.json").read_text())

LULA_PCT = tsum["president_final"]["lula_pct_valid"]                   # 51.79
BOLSO_PCT = round(100.0 - LULA_PCT, 2)                                 # 48.21
PRED_LULA = prev["predict_2026"]["pairwise_lula_share_pct"]            # 47.43
PRED_CI = prev["predict_2026"]["pairwise_ci_pct"]                      # [47.39, 47.45]
SWING_ANCHOR = tsum["swing_decomposed"]["anchor_lula_tw"]              # 53.05
SWING_NET = tsum["swing_decomposed"]["swing_pp"]                       # -1.26


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

ALL = {"counting": (fig_counting, T_COUNT), "swing": (fig_swing, T_SWING),
       "prediction": (fig_prediction, T_PRED)}

for lang in ("en", "pt", "es", "ru"):
    (SITE / lang).mkdir(parents=True, exist_ok=True)
    for name, (fn, tr) in ALL.items():
        fn(lang, tr[lang])
    print(f"{lang}: {len(ALL)} figures -> site/brazil-oct-2026-round-2/img/{lang}/")
