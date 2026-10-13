# Фигуры для публичной страницы сайта репозитория — по комплекту на каждый
# язык (pt, en, es, ru), данные — data/secoes_presidente_2026.csv +
# контроль-2022 data/secoes_presidente_2022.csv. Запуск из корня репозитория:
#   cd analysis-tool && uv run python ../brazil-oct-2026/scripts/build_site_figures.py
# Выход: <репо>/site/brazil-oct-2026/img/<lang>/{turnout,comet,control,selftest}.png
# Числа для самотеста — из analysis/metrics.json прогона 12.10.2026.
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas", "matplotlib"]
# ///
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "site" / "brazil-oct-2026" / "img"
OUT.mkdir(parents=True, exist_ok=True)

BLUE = "#3b82c4"
DARK = "#16324f"
RED = "#c0392b"
GREY = "#8a97a5"
PURPLE = "#9b59b6"
CUT = 91.6  # граница честного спада (own q99.5), см. отчёт, раздел 2
CUT_CONTROL = 91.5  # граница из контроля-2022 (q99.5, максимум двух туров), §12.1

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

# числа самотеста (analysis/metrics.json, прогон 12.10.2026)
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
    print(f"{lang}: turnout, comet, control, selftest -> site/brazil-oct-2026/img/{lang}/")
