# Figures for the public site pages of the repository — one set per language
# (pt, en, es, ru); data — data/secoes_presidente_2026.csv +
# the 2022 control data/secoes_presidente_2022.csv. Run from the repo root:
#   cd analysis-tool && uv run python ../brazil-oct-2026-round-1/scripts/build_site_figures.py
# Output: <repo>/site/brazil-oct-2026-round-1/img/<lang>/{turnout,comet,control,selftest,
#          clones,transfers,runoff}.png
# Self-test numbers — from analysis/metrics.json of the 12.10.2026 run.
# Paradox numbers — from analysis/paradox/paradox_results.json of the 17.10.2026 run
# (hardcoded below for a standalone script, see PARADOXES.md).
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
OUT = ROOT.parent / "site" / "brazil-oct-2026-round-1" / "img"
OUT.mkdir(parents=True, exist_ok=True)

BLUE = "#3b82c4"
BLUE_SOFT = "#8ab4d9"
DARK = "#16324f"
RED = "#c0392b"
GREY = "#8a97a5"
PURPLE = "#9b59b6"
AMBER = "#8a6116"
CUT = 91.6  # honest-decline boundary (own q99.5), see the report, section 2
CUT_CONTROL = 91.5  # boundary from the 2022 control (q99.5, max of the two rounds), §12.1

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

T = {
"en": {
    "turnout_title": "One smooth bell near 80% — and no right tail",
    "turnout_xlabel": "Turnout, % of registered voters",
    "turnout_ylabel": "Number of sections",
    "turnout_cut": "honest-decline boundary (91.6%)",
    "turnout_box": ("Above 91.6%: 0.62% of ballots (3,622 sections).\n"
                    "Tails of the rivals: Bolsonaro 0.49%, Lula 0.80% —\n"
                    "same as honest 2022 (0.47–0.62%). Removing the tail\n"
                    "would shift each candidate by ≤ 0.07 pp."),
    "comet_title": "Turnout × result — horizontal clouds, no “comet tail”",
    "comet_xlabel": "Turnout, %",
    "comet_ylabel": "Share of ballots cast, %",
    "comet_legend": "average by turnout group",
    "comet_box": ("National correlation of turnout and result:\n"
                  "Bolsonaro r = −0.03, Lula r = +0.05.\n"
                  "Ballot-stuffing gives the beneficiary\n"
                  "a rising tail with r ≈ +0.5…+0.9."),
    "bolsonaro": "Bolsonaro — 47.0% of valid votes",
    "lula": "Lula — 45.2% of valid votes",
    "control_title": "2026 (blue) is indistinguishable from the honest 2022 control",
    "control_ylabel": "Share of voters (log scale)",
    "control_xlabel": "Turnout, %",
    "control_legend_2022t1": "2022, 1st round",
    "control_legend_2022t2": "2022, 2nd round",
    "control_legend_2026": "2026, 1st round",
    "control_cut1": "boundary from 2022 control: 91.5%",
    "control_cut2": "own 2026 boundary: 91.6%",
    "selftest_suptitle": "Self-test: after injecting fraud, every alarm fires",
    "selftest_left_title": "Shpilkin anomalous-votes estimate",
    "selftest_right_title": "Round-number peaks statistic (z)",
    "selftest_clean": "clean data",
    "selftest_injected": "+2M synthetic ballots\ninjected (10% of sections)",
    "selftest_painted": "turnout “painted” to whole %\n(5% of sections)",
    "selftest_x_label": "estimated votes in the anomalous zone",
},
"pt": {
    "turnout_title": "Um único sino suave perto de 80% — sem cauda à direita",
    "turnout_xlabel": "Comparecimento, % dos eleitores aptos",
    "turnout_ylabel": "Número de seções",
    "turnout_cut": "limite do declínio honesto (91,6%)",
    "turnout_box": ("Acima de 91,6%: 0,62% dos votos (3.622 seções).\n"
                    "Caudas dos rivais: Bolsonaro 0,49%, Lula 0,80% —\n"
                    "o mesmo que nas eleições honestas de 2022 (0,47–0,62%).\n"
                    "Remover a cauda mudaria cada candidato em ≤ 0,07 p.p."),
    "comet_title": "Comparecimento × resultado — nuvens horizontais, sem “cauda de cometa”",
    "comet_xlabel": "Comparecimento, %",
    "comet_ylabel": "% dos votos apurados",
    "comet_legend": "média por faixa de comparecimento",
    "comet_box": ("Correlação nacional entre comparecimento e resultado:\n"
                  "Bolsonaro r = −0,03, Lula r = +0,05.\n"
                  "Votação fraudada dá ao beneficiário uma cauda\n"
                  "crescente com r ≈ +0,5…+0,9."),
    "bolsonaro": "Bolsonaro — 47,0% dos votos válidos",
    "lula": "Lula — 45,2% dos votos válidos",
    "control_title": "2026 (azul) é indistinguível do controle honesto de 2022",
    "control_ylabel": "Parcela dos eleitores (escala log)",
    "control_xlabel": "Comparecimento, %",
    "control_legend_2022t1": "2022, 1º turno",
    "control_legend_2022t2": "2022, 2º turno",
    "control_legend_2026": "2026, 1º turno",
    "control_cut1": "limite pelo controle de 2022: 91,5%",
    "control_cut2": "limite próprio de 2026: 91,6%",
    "selftest_suptitle": "Auto-teste: com fraude injetada, todos os alarmes disparam",
    "selftest_left_title": "Estimativa de votos anômalos (Shpilkin)",
    "selftest_right_title": "Estatística de picos em números redondos (z)",
    "selftest_clean": "dados limpos",
    "selftest_injected": "+2 mi de votos sintéticos\ninjetados (10% das seções)",
    "selftest_painted": "comparecimento “ajustado” a % inteiro\n(5% das seções)",
    "selftest_x_label": "votos estimados na zona anômala",
},
"es": {
    "turnout_title": "Una sola campana suave cerca del 80% — sin cola a la derecha",
    "turnout_xlabel": "Participación, % de los electores inscritos",
    "turnout_ylabel": "Número de secciones",
    "turnout_cut": "límite del descenso honesto (91,6%)",
    "turnout_box": ("Por encima del 91,6%: 0,62% de los votos (3.622 secciones).\n"
                    "Colas de los rivales: Bolsonaro 0,49%, Lula 0,80% —\n"
                    "lo mismo que en las honestas elecciones de 2022 (0,47–0,62%).\n"
                    "Quitar la cola movería a cada candidato ≤ 0,07 p.p."),
    "comet_title": "Participación × resultado — nubes horizontales, sin «cola de cometa»",
    "comet_xlabel": "Participación, %",
    "comet_ylabel": "% de los votos emitidos",
    "comet_legend": "promedio por grupo de participación",
    "comet_box": ("Correlación nacional entre participación y resultado:\n"
                  "Bolsonaro r = −0,03, Lula r = +0,05.\n"
                  "El fraude da al beneficiario una cola\n"
                  "creciente con r ≈ +0,5…+0,9."),
    "bolsonaro": "Bolsonaro — 47,0% de los votos válidos",
    "lula": "Lula — 45,2% de los votos válidos",
    "control_title": "2026 (azul) es indistinguible del control honesto de 2022",
    "control_ylabel": "Proporción de electores (escala log)",
    "control_xlabel": "Participación, %",
    "control_legend_2022t1": "2022, 1.ª vuelta",
    "control_legend_2022t2": "2022, 2.ª vuelta",
    "control_legend_2026": "2026, 1.ª vuelta",
    "control_cut1": "límite según el control de 2022: 91,5%",
    "control_cut2": "límite propio de 2026: 91,6%",
    "selftest_suptitle": "Autotest: al inyectar fraude, todas las alarmas saltan",
    "selftest_left_title": "Estimación de votos anómalos (Shpilkin)",
    "selftest_right_title": "Estadística de picos en números redondos (z)",
    "selftest_clean": "datos limpios",
    "selftest_injected": "+2 millones de votos sintéticos\ninyectados (10% de las secciones)",
    "selftest_painted": "participación «ajustada» a % entero\n(5% de las secciones)",
    "selftest_x_label": "votos estimados en la zona anómala",
},
"ru": {
    "turnout_title": "Один гладкий колокол у 80% — и без правого хвоста",
    "turnout_xlabel": "Явка, % от зарегистрированных",
    "turnout_ylabel": "Число секций",
    "turnout_cut": "граница честного спада (91,6%)",
    "turnout_box": ("Выше 91,6%: 0,62% голосов (3 622 секции).\n"
                    "Хвосты соперников: Болсонару 0,49%, Лула 0,80% —\n"
                    "как на честных выборах-2022 (0,47–0,62%).\n"
                    "Удаление хвоста сдвинуло бы каждого кандидата ≤ 0,07 п.п."),
    "comet_title": "Явка × результат — горизонтальные облака, без «хвоста кометы»",
    "comet_xlabel": "Явка, %",
    "comet_ylabel": "% от проголосовавших",
    "comet_legend": "среднее по группам явки",
    "comet_box": ("Общенациональная корреляция явки и результата:\n"
                  "Болсонару r = −0,03, Лула r = +0,05.\n"
                  "Вброс даёт бенефициару растущий хвост\n"
                  "с r ≈ +0,5…+0,9."),
    "bolsonaro": "Болсонару — 47,0% действительных",
    "lula": "Лула — 45,2% действительных",
    "control_title": "2026 (синий) неотличим от честного контроля-2022",
    "control_ylabel": "Доля проголосовавших (лог. шкала)",
    "control_xlabel": "Явка, %",
    "control_legend_2022t1": "2022, 1-й тур",
    "control_legend_2022t2": "2022, 2-й тур",
    "control_legend_2026": "2026, 1-й тур",
    "control_cut1": "граница по контролю-2022: 91,5%",
    "control_cut2": "собственная граница-2026: 91,6%",
    "selftest_suptitle": "Самотест: при инъекции фальши срабатывают все сигналы",
    "selftest_left_title": "Оценка аномальных голосов (Шпилькин)",
    "selftest_right_title": "Статистика пиков на круглых числах (z)",
    "selftest_clean": "чистые данные",
    "selftest_injected": "+2 млн синтетических голосов\nвброшено (10% секций)",
    "selftest_painted": "явка «подогнана» под целый %\n(5% секций)",
    "selftest_x_label": "оценка голосов в аномальной зоне",
},
}

# self-test numbers (analysis/metrics.json, run of 12.10.2026)
SELFTEST_CLEAN = 272_315
SELFTEST_INJECTED = 6_116_988
Z_CLEAN = 0.35
Z_PAINTED = 9.89

print("loading 2026 sections ...")
df26 = pd.read_csv(ROOT / "data" / "secoes_presidente_2026.csv",
                   usecols=["voted", "turnout_pct", "votes:BOLSONARO", "votes:LULA"])
df26 = df26[df26["voted"] > 0]

print("loading 2022 control ...")
df22 = pd.read_csv(ROOT / "data" / "secoes_presidente_2022.csv",
                   usecols=["turno", "voted", "turnout_pct"])
df22 = df22[df22["voted"] > 0]
t22_r1 = df22.loc[df22["turno"] == 1, "turnout_pct"]
t22_r2 = df22.loc[df22["turno"] == 2, "turnout_pct"]
t26 = df26["turnout_pct"]
del df22


def fig_turnout(lang: str, tr: dict) -> None:
    fig, ax = plt.subplots(figsize=(9.6, 4.2), dpi=150)
    ax.hist(t26, bins=100, range=(0, 100), color=BLUE, alpha=0.85, edgecolor="white", linewidth=0.2)
    ax.axvline(CUT, color=RED, linestyle="--", linewidth=1.6)
    ax.text(CUT - 1.2, ax.get_ylim()[1] * 0.92, tr["turnout_cut"], color=RED,
            fontsize=10, ha="right")
    ax.text(
        0.975, 0.72, tr["turnout_box"], transform=ax.transAxes,
        fontsize=9.5, ha="right", va="top", color=DARK,
        bbox=dict(boxstyle="round,pad=0.45", fc="#f4f7fa", ec=GREY, lw=0.8),
    )
    ax.set_xlim(0, 100)
    ax.set_xlabel(tr["turnout_xlabel"])
    ax.set_ylabel(tr["turnout_ylabel"])
    ax.set_title(tr["turnout_title"])
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / lang / "turnout.png")
    plt.close(fig)


def fig_comet(lang: str, tr: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.8), dpi=150, sharex=True, sharey=True)
    bins = list(range(20, 105, 5))
    for ax, col, name, color in (
        (axes[0], "votes:BOLSONARO", tr["bolsonaro"], BLUE),
        (axes[1], "votes:LULA", tr["lula"], RED),
    ):
        share = df26[col] / df26["voted"] * 100
        ax.scatter(t26, share, s=1.2, color=color, alpha=0.10, linewidths=0, rasterized=True)
        grp = pd.cut(t26, bins)
        m = pd.DataFrame({"g": grp, "t": t26, "s": share, "w": df26["voted"]}).groupby(
            "g", observed=True
        ).apply(
            lambda g: pd.Series(
                {"x": (g["t"] * g["w"]).sum() / g["w"].sum(),
                 "y": (g["s"] * g["w"]).sum() / g["w"].sum()}
            ),
            include_groups=False,
        )
        ax.plot(m["x"], m["y"], color=DARK, linewidth=2.6, marker="o", markersize=5,
                zorder=5, label=tr["comet_legend"])
        ax.set_title(name, fontsize=11.5)
        ax.set_xlim(20, 100)
        ax.set_ylim(-2, 102)
        ax.set_xlabel(tr["comet_xlabel"])
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel(tr["comet_ylabel"])
    axes[0].legend(loc="upper left", fontsize=9, framealpha=0.9)
    axes[1].text(
        0.03, 0.95, tr["comet_box"], transform=axes[1].transAxes,
        fontsize=9.5, va="top", color=DARK,
        bbox=dict(boxstyle="round,pad=0.45", fc="#f4f7fa", ec=GREY, lw=0.8),
    )
    fig.suptitle(tr["comet_title"], fontsize=13, fontweight="bold", y=1.0)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT / lang / "comet.png")
    plt.close(fig)


def fig_control(lang: str, tr: dict) -> None:
    fig, ax = plt.subplots(figsize=(9.6, 4.4), dpi=150)
    for series, color, label in (
        (t22_r1, GREY, tr["control_legend_2022t1"]),
        (t22_r2, PURPLE, tr["control_legend_2022t2"]),
        (t26, BLUE, tr["control_legend_2026"]),
    ):
        ax.hist(series, bins=180, range=(0, 100), density=True, histtype="step",
                color=color, linewidth=1.4, label=label)
    ax.axvline(CUT_CONTROL, color=RED, linestyle="-", linewidth=1.6)
    ax.axvline(CUT, color=DARK, linestyle="--", linewidth=1.3)
    ax.text(CUT_CONTROL - 0.8, 0.9, tr["control_cut1"], color=RED, fontsize=9.5,
            ha="right", rotation=90, va="top")
    ax.text(CUT + 0.8, 0.9, tr["control_cut2"], color=DARK, fontsize=9.5,
            ha="left", rotation=90, va="top")
    ax.set_yscale("log")
    ax.set_xlim(10, 100)
    ax.set_xlabel(tr["control_xlabel"])
    ax.set_ylabel(tr["control_ylabel"])
    ax.set_title(tr["control_title"])
    ax.legend(loc="upper left", fontsize=9.5, framealpha=0.9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / lang / "control.png")
    plt.close(fig)


def fig_selftest(lang: str, tr: dict) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.6, 4.2), dpi=150)
    bars1 = ax1.bar(
        [tr["selftest_clean"], tr["selftest_injected"]],
        [SELFTEST_CLEAN, SELFTEST_INJECTED],
        color=[BLUE, RED], width=0.55,
    )
    ax1.set_yscale("log")
    ax1.set_ylim(1e5, 1.2e7)
    for b, v in zip(bars1, (SELFTEST_CLEAN, SELFTEST_INJECTED)):
        ax1.text(b.get_x() + b.get_width() / 2, v * 1.25, f"{v:,}".replace(",", " "),
                 ha="center", fontsize=10.5, fontweight="bold", color=DARK)
    ax1.annotate("×22", xy=(1, SELFTEST_INJECTED * 0.35), xytext=(0.42, SELFTEST_INJECTED * 0.5),
                 fontsize=15, fontweight="bold", color=RED,
                 arrowprops=dict(arrowstyle="->", color=RED, lw=1.8))
    ax1.set_ylabel(tr["selftest_x_label"])
    ax1.set_title(tr["selftest_left_title"], fontsize=11.5)
    ax1.spines[["top", "right"]].set_visible(False)

    bars2 = ax2.bar(
        [tr["selftest_clean"], tr["selftest_painted"]],
        [Z_CLEAN, Z_PAINTED],
        color=[BLUE, RED], width=0.55,
    )
    ax2.axhline(2, color=GREY, linestyle=":", linewidth=1.4)
    ax2.text(1.42, 2.35, "z = 2", color=GREY, fontsize=9.5, ha="right")
    for b, v in zip(bars2, (Z_CLEAN, Z_PAINTED)):
        ax2.text(b.get_x() + b.get_width() / 2, v + 0.25, f"z = {v:.2f}",
                 ha="center", fontsize=10.5, fontweight="bold", color=DARK)
    ax2.set_ylim(0, 11.5)
    ax2.set_title(tr["selftest_right_title"], fontsize=11.5)
    ax2.spines[["top", "right"]].set_visible(False)
    for lbl in ax2.get_xticklabels():
        lbl.set_fontsize(9.5)
    for lbl in ax1.get_xticklabels():
        lbl.set_fontsize(9.5)

    fig.suptitle(tr["selftest_suptitle"], fontsize=13, fontweight="bold", y=1.0)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(OUT / lang / "selftest.png")
    plt.close(fig)


for lang, tr in T.items():
    (OUT / lang).mkdir(parents=True, exist_ok=True)
    fig_turnout(lang, tr)
    fig_comet(lang, tr)
    fig_control(lang, tr)
    fig_selftest(lang, tr)
    print(f"{lang}: turnout, comet, control, selftest -> site/brazil-oct-2026-round-1/img/{lang}/")


# ── voting-paradox figures (PARADOXES.md, run of 17.10.2026) ─────────────────

# round 1, % of valid (analysis/paradox/paradox_results.json + official totals)
R1_PCT = {"BOLSONARO": 47.03, "LULA": 45.16, "CURY": 2.89, "FERREIRA": 2.24,
          "CAIADO": 2.18, "ZEMA": 0.27, "micro": 0.22}
BLOC_PCT = 54.62          # BOLSONARO + CURY + FERREIRA + CAIADO + ZEMA
BLOC_MARGIN_VOTES = 5_507_578  # votes of the bloc above the 50%-of-valid line
# 2022 transfer matrix, rows = R1 origins (ordered as displayed), cols =
# LULA / BOLSONARO / blank / null / stayed home
TRANSFERS = [
    ("LULA",       0.968, 0.000, 0.003, 0.012, 0.016),
    ("BOLSONARO",  0.000, 0.998, 0.001, 0.000, 0.002),
    ("CIRO",       0.581, 0.300, 0.067, 0.051, 0.000),
    ("TEBET",      0.279, 0.499, 0.101, 0.121, 0.000),
    ("SORAYA",     0.000, 0.591, 0.101, 0.308, 0.000),
    ("DAVILA",     0.150, 0.785, 0.063, 0.003, 0.000),
    ("EYMAEL",     0.000, 0.612, 0.202, 0.186, 0.000),
    ("KELMON",     0.000, 0.805, 0.044, 0.054, 0.097),
    ("MANZANO",    0.842, 0.000, 0.068, 0.090, 0.000),
    ("PERICLES",   0.622, 0.210, 0.066, 0.103, 0.000),
    ("VERA",       0.694, 0.187, 0.085, 0.034, 0.000),
    ("BRANCO",     0.000, 0.461, 0.390, 0.149, 0.000),
    ("NULO",       0.267, 0.002, 0.035, 0.696, 0.000),
    ("NEW",        0.481, 0.473, 0.016, 0.030, 0.000),
]
# 2026 head-to-head prediction (transfer model on 2026 round-1 totals)
PRED_LULA = 47.43
PRED_LULA_CI = (47.39, 47.45)

PXT = {
"en": {
    "cl_title": "Round 1 — one majority, split over five names",
    "cl_xlabel": "% of valid votes",
    "cl_names": {"BOLSONARO": "Bolsonaro", "LULA": "Lula", "CURY": "Cury",
                 "FERREIRA": "Ferreira", "CAIADO": "Caiado", "ZEMA": "Zema",
                 "micro": "7 micro-candidates"},
    "cl_bloc": ("The five blue candidates fish in the same electorate\n"
                "(anti-Lula geography): together 65.2M votes = 54.6% —\n"
                "a majority. Individually nobody reaches 50% — so a runoff."),
    "cl_box": "together: 54.6% — a majority",
    "run_title": "As two blocs Bolsonaro wins outright; head-to-head he is predicted to win again",
    "run_left": "4 Oct — counted as blocs",
    "run_right": "25 Oct — predicted head-to-head",
    "run_ylabel": "% of valid votes",
    "run_bolsonaro": "Bolsonaro", "run_lula": "Lula",
    "run_bloc": "Bolsonaro + 4 bloc partners",
    "run_ci": "95% CI of the transfer model",
    "run_box": ("The runoff re-assembles the round-1 bloc:\n"
                "52.6% vs 47.4%. Backtest on 2022: the model\n"
                "errs +0.7 pp toward Lula."),
    "tr_title": "What the 2022 runoff did with each round-1 vote (measured, not assumed)",
    "tr_dests": ("→ Lula", "→ Bolsonaro", "→ blank", "→ null", "→ stayed home"),
    "tr_rows": {"BRANCO": "blank 2022", "NULO": "null 2022", "NEW": "new R2 voters",
                "DAVILA": "D'Ávila", "PERICLES": "Péricles", "MANZANO": "Manzano",
                "EYMAEL": "Eymael", "KELMON": "Kelmon", "VERA": "Vera",
                "SORAYA": "Soraya", "TEBET": "Tebet", "CIRO": "Ciro",
                "LULA": "Lula voters", "BOLSONARO": "Bolsonaro voters"},
    "tr_xlabel": "round-1 vote, 2022",
},
"pt": {
    "cl_title": "1º turno — uma maioria repartida entre cinco nomes",
    "cl_xlabel": "% dos votos válidos",
    "cl_names": {"BOLSONARO": "Bolsonaro", "LULA": "Lula", "CURY": "Cury",
                 "FERREIRA": "Ferreira", "CAIADO": "Caiado", "ZEMA": "Zema",
                 "micro": "7 microcandidatos"},
    "cl_bloc": ("Os cinco candidatos azuis pescam no mesmo eleitorado\n"
                "(geografia antilula): juntos, 65,2 mi = 54,6% — uma\n"
                "maioria. Individualmente, ninguém chega a 50% — logo, 2º turno."),
    "cl_box": "juntos: 54,6% — maioria",
    "run_title": "Em blocos, Bolsonaro vence no 1º turno; no corpo a corpo, a previsão é de vitória de novo",
    "run_left": "4 out — contado em blocos",
    "run_right": "25 out — corpo a corpo previsto",
    "run_ylabel": "% dos votos válidos",
    "run_bolsonaro": "Bolsonaro", "run_lula": "Lula",
    "run_bloc": "Bolsonaro + 4 aliados de bloco",
    "run_ci": "IC de 95% do modelo de transferência",
    "run_box": ("O 2º turno remonta o bloco do 1º turno:\n"
                "52,6% contra 47,4%. Backtest em 2022: o modelo\n"
                "erra +0,7 p.p. a favor de Lula."),
    "tr_title": "O que o 2º turno de 2022 fez com cada voto do 1º turno (medido, não suposto)",
    "tr_dests": ("→ Lula", "→ Bolsonaro", "→ branco", "→ nulo", "→ ficou em casa"),
    "tr_rows": {"BRANCO": "branco 2022", "NULO": "nulo 2022", "NEW": "eleitores novos do 2º turno",
                "DAVILA": "D'Ávila", "PERICLES": "Péricles", "MANZANO": "Manzano",
                "EYMAEL": "Eymael", "KELMON": "Kelmon", "VERA": "Vera",
                "SORAYA": "Soraya", "TEBET": "Tebet", "CIRO": "Ciro",
                "LULA": "eleitores de Lula", "BOLSONARO": "eleitores de Bolsonaro"},
    "tr_xlabel": "voto no 1º turno, 2022",
},
"es": {
    "cl_title": "1.ª vuelta — una mayoría repartida entre cinco nombres",
    "cl_xlabel": "% de votos válidos",
    "cl_names": {"BOLSONARO": "Bolsonaro", "LULA": "Lula", "CURY": "Cury",
                 "FERREIRA": "Ferreira", "CAIADO": "Caiado", "ZEMA": "Zema",
                 "micro": "7 microcandidatos"},
    "cl_bloc": ("Los cinco candidatos azules pescan en el mismo electorado\n"
                "(geografía anti-Lula): juntos, 65,2 M = 54,6% — una mayoría.\n"
                "Individualmente nadie llega al 50% — y de ahí la segunda vuelta."),
    "cl_box": "juntos: 54,6% — mayoría",
    "run_title": "En bloques, Bolsonaro gana en la 1.ª vuelta; cara a cara, la previsión es que gane de nuevo",
    "run_left": "4 oct — contado en bloques",
    "run_right": "25 oct — cara a cara previsto",
    "run_ylabel": "% de votos válidos",
    "run_bolsonaro": "Bolsonaro", "run_lula": "Lula",
    "run_bloc": "Bolsonaro + 4 socios de bloque",
    "run_ci": "IC del 95% del modelo de transferencia",
    "run_box": ("La 2.ª vuelta recompone el bloque de la 1.ª:\n"
                "52,6% contra 47,4%. Backtest en 2022: el modelo\n"
                "se equivoca +0,7 p.p. a favor de Lula."),
    "tr_title": "Qué hizo la 2.ª vuelta de 2022 con cada voto de la 1.ª (medido, no supuesto)",
    "tr_dests": ("→ Lula", "→ Bolsonaro", "→ blanco", "→ nulo", "→ se quedó en casa"),
    "tr_rows": {"BRANCO": "blanco 2022", "NULO": "nulo 2022", "NEW": "votantes nuevos de la 2.ª vuelta",
                "DAVILA": "D'Ávila", "PERICLES": "Péricles", "MANZANO": "Manzano",
                "EYMAEL": "Eymael", "KELMON": "Kelmon", "VERA": "Vera",
                "SORAYA": "Soraya", "TEBET": "Tebet", "CIRO": "Ciro",
                "LULA": "votantes de Lula", "BOLSONARO": "votantes de Bolsonaro"},
    "tr_xlabel": "voto en la 1.ª vuelta, 2022",
},
"ru": {
    "cl_title": "1-й тур — одно большинство, раздробленное на пять имён",
    "cl_xlabel": "% действительных голосов",
    "cl_names": {"BOLSONARO": "Болсонару", "LULA": "Лула", "CURY": "Кури",
                 "FERREIRA": "Феррейра", "CAIADO": "Кайаду", "ZEMA": "Зема",
                 "micro": "7 микрокандидатов"},
    "cl_bloc": ("Пять синих кандидатов ловят голоса в одном электорате\n"
                "(антилуловская география): вместе 65,2 млн = 54,6% —\n"
                "большинство. Поодиночке никто не берёт 50% — нужен 2-й тур."),
    "cl_box": "вместе: 54,6% — большинство",
    "run_title": "Блоками Болсонару побеждает уже в 1-м туре; очная ставка — прогноз тоже в его пользу",
    "run_left": "4 окт — подсчёт по блокам",
    "run_right": "25 окт — прогноз очной ставки",
    "run_ylabel": "% действительных голосов",
    "run_bolsonaro": "Болсонару", "run_lula": "Лула",
    "run_bloc": "Болсонару + 4 партнёра по блоку",
    "run_ci": "95%-й интервал модели перетеканий",
    "run_box": ("2-й тур пересобирает блок 1-го тура:\n"
                "52,6% против 47,4%. Проверка на 2022 год:\n"
                "модель завышает долю Лулы на +0,7 п.п."),
    "tr_title": "Что 2-й тур-2022 сделал с каждым голосом 1-го тура (измерено, а не предположено)",
    "tr_dests": ("→ Лула", "→ Болсонару", "→ белый", "→ недействительный", "→ остался дома"),
    "tr_rows": {"BRANCO": "белый 2022", "NULO": "недействительный 2022", "NEW": "новые избиратели 2-го тура",
                "DAVILA": "Д'Авила", "PERICLES": "Периклес", "MANZANO": "Манзано",
                "EYMAEL": "Эймаэл", "KELMON": "Келмон", "VERA": "Вера",
                "SORAYA": "Сорая", "TEBET": "Тебет", "CIRO": "Сиру",
                "LULA": "избиратели Лулы", "BOLSONARO": "избиратели Болсонару"},
    "tr_xlabel": "голос в 1-м туре, 2022",
},
}


def fig_px_clones(lang: str, tr: dict) -> None:
    t = PXT[lang]
    rows = ["BOLSONARO", "LULA", "CURY", "FERREIRA", "CAIADO", "ZEMA", "micro"]
    colors = {"BOLSONARO": BLUE, "LULA": RED, "micro": GREY}
    fig, ax = plt.subplots(figsize=(9.6, 4.6), dpi=150)
    y = list(range(len(rows)))[::-1]
    vals = [R1_PCT[r] for r in rows]
    cols = [colors.get(r, BLUE_SOFT) for r in rows]
    ax.barh(y, vals, color=cols, alpha=0.9, height=0.62, zorder=3)
    for yi, v in zip(y, vals):
        ax.text(v + 0.7, yi, f"{v:.2f}%".replace(".", "," if lang in ("pt", "es", "ru") else "."),
                va="center", fontsize=10, color=DARK, fontweight="bold")
    ax.set_yticks(y, [t["cl_names"][r] for r in rows], fontsize=10.5)
    ax.set_xlim(0, 60)
    ax.set_ylim(-0.85, len(rows) - 0.4)
    ax.axvline(50, color=DARK, linestyle="--", linewidth=1.4, zorder=4)
    ax.text(50.7, -0.62, "50%", color=DARK, fontsize=9.5, ha="left")
    ax.text(0.985, 0.06, t["cl_bloc"], transform=ax.transAxes, fontsize=9.5,
            ha="right", va="bottom", color=DARK,
            bbox=dict(boxstyle="round,pad=0.45", fc="#f4f7fa", ec=GREY, lw=0.8))
    ax.set_xlabel(t["cl_xlabel"])
    ax.set_title(t["cl_title"])
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / lang / "clones.png")
    plt.close(fig)


def fig_px_transfers(lang: str, tr: dict) -> None:
    t = PXT[lang]
    rows = [r[0] for r in TRANSFERS]
    mat = np.array([r[1:] for r in TRANSFERS])
    dest_colors = [RED, BLUE, GREY, AMBER, DARK]
    fig, ax = plt.subplots(figsize=(10.4, 6.0), dpi=150)
    for j in range(mat.shape[1]):
        ax.barh(list(range(len(rows)))[::-1], mat[:, j], left=mat[:, :j].sum(axis=1),
                color=dest_colors[j], alpha=0.88, height=0.66, zorder=3,
                label=t["tr_dests"][j])
    for i in range(mat.shape[0]):
        cum = 0.0
        for j in range(mat.shape[1]):
            v = mat[i, j]
            if v >= 0.05:
                ax.text(cum + v / 2, len(rows) - 1 - i, f"{100 * v:.0f}",
                        ha="center", va="center", fontsize=8.6, color="white",
                        fontweight="bold", zorder=4)
            cum += v
    ax.set_yticks(list(range(len(rows)))[::-1], [t["tr_rows"][r] for r in rows], fontsize=10)
    ax.set_xlim(0, 1.0)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0],
                  ["0%", "25%", "50%", "75%", "100%"])
    ax.set_xlabel(t["tr_xlabel"])
    ax.set_title(t["tr_title"])
    ax.legend(fontsize=9.5, framealpha=0.95, loc="upper center", ncol=5,
              bbox_to_anchor=(0.5, -0.10), columnspacing=1.1)
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(OUT / lang / "transfers.png", bbox_inches="tight")
    plt.close(fig)


def fig_px_runoff(lang: str, tr: dict) -> None:
    t = PXT[lang]
    dec = "," if lang in ("pt", "es", "ru") else "."

    def pct(v: float) -> str:
        return f"{v:.1f}%".replace(".", dec)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.4, 4.6), dpi=150)
    # left: round 1 counted as blocs
    labels1 = [t["run_bloc"], t["run_lula"]]
    vals1 = [BLOC_PCT, 100.0 - BLOC_PCT - R1_PCT["micro"]]
    bars1 = ax1.bar(labels1, vals1, color=[BLUE, RED], alpha=0.9, width=0.55, zorder=3)
    ax1.axhline(50, color=DARK, linestyle="--", linewidth=1.4, zorder=4)
    ax1.text(0.02, 50.9, "50%", color=DARK, fontsize=9.5)
    for b, v in zip(bars1, vals1):
        ax1.text(b.get_x() + b.get_width() / 2, v + 0.7, pct(v), ha="center",
                 fontsize=11, fontweight="bold", color=DARK)
    ax1.set_ylim(0, 62)
    ax1.set_ylabel(t["run_ylabel"])
    ax1.set_title(t["run_left"], fontsize=11.5)
    ax1.spines[["top", "right"]].set_visible(False)
    for lbl in ax1.get_xticklabels():
        lbl.set_fontsize(9.5)

    # right: predicted head-to-head with CI
    lula = PRED_LULA
    bolso = 100.0 - PRED_LULA
    err = lula - PRED_LULA_CI[0]
    bars2 = ax2.bar([t["run_bolsonaro"], t["run_lula"]], [bolso, lula],
                    color=[BLUE, RED], alpha=0.9, width=0.55, zorder=3)
    ax2.errorbar([1], [lula], yerr=[[err], [err]], fmt="none", ecolor=DARK,
                 elinewidth=1.6, capsize=6, zorder=5)
    ax2.axhline(50, color=DARK, linestyle="--", linewidth=1.4, zorder=4)
    ax2.text(0.02, 50.9, "50%", color=DARK, fontsize=9.5)
    for b, v in zip(bars2, (bolso, lula)):
        ax2.text(b.get_x() + b.get_width() / 2, v + 1.6, pct(v), ha="center",
                 fontsize=11, fontweight="bold", color=DARK)
    ax2.set_ylim(0, 62)
    ax2.set_title(t["run_right"], fontsize=11.5)
    ax2.text(0.03, 0.95, t["run_box"], transform=ax2.transAxes, fontsize=9.5,
             va="top", color=DARK,
             bbox=dict(boxstyle="round,pad=0.45", fc="#f4f7fa", ec=GREY, lw=0.8))
    ax2.spines[["top", "right"]].set_visible(False)
    for lbl in ax2.get_xticklabels():
        lbl.set_fontsize(9.5)

    fig.suptitle(t["run_title"], fontsize=13, fontweight="bold", y=1.0)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT / lang / "runoff.png")
    plt.close(fig)


for lang, tr in T.items():
    fig_px_clones(lang, tr)
    fig_px_transfers(lang, tr)
    fig_px_runoff(lang, tr)
    print(f"{lang}: clones, transfers, runoff -> site/brazil-oct-2026-round-1/img/{lang}/")
