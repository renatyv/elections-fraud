# Фигуры для публичной страницы сайта репозитория — по комплекту на каждый
# язык (pt, en), данные — data/legislativas2025_mai/results_all.csv (freguesias,
# level=3). Запуск из каталога проекта:
#   uv run python scripts/build_site_figures.py
# Выход: <репо>/site/portugal-2025/img/<lang>/{turnout,comet,selftest}.png
# Числа в подписях сверены с analysis/metrics.json (shpilkin, selftest).
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
OUT = ROOT.parent / "site" / "portugal-2025" / "img"
OUT.mkdir(parents=True, exist_ok=True)

BLUE = "#3b82c4"
DARK = "#16324f"
RED = "#c0392b"
GREEN = "#1e8e5a"
GREY = "#8a97a5"
# Граница честного спада — q99.5 контрольных выборов (см. ОТЧЁТ_стат_анализ, раздел 1
# и analysis/metrics.json → shpilkin.t_cut).
CUT = 78.6424600948544

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
    "turnout_title": "Turnout, parish by parish: one bell curve — and nothing above ~79%",
    "turnout_xlabel": "Turnout, % of registered voters",
    "turnout_ylabel": "Voters",
    "cut_label": "honest-decline boundary (78.6%, set by control elections)",
    "box": ("above the line: 7,779 voters = 0.13% of ballots cast.\n"
            "The 80–100% zone — exactly where ballot-stuffing lands — is empty."),
    "comet_title": "Turnout vs leading-party (AD) share — no “comet tail”",
    "comet_xlabel": "Turnout, %",
    "comet_ylabel": "AD share, % of votes cast",
    "comet_legend": "average by turnout group",
    "comet_box": ("The AD share stays flat across the whole turnout range\n"
                  "(weighted correlation −0.09); there is no separate cloud\n"
                  "of high-turnout, high-share parishes."),
    "selftest_title": "Self-test: inject synthetic stuffing — every alarm fires (signal ×18)",
    "selftest_ylabel": "estimated AD votes in the anomalous zone",
    "clean_label": "clean data\n14,589",
    "injected_label": "after injection\n255,496",
    "added_label": "ballots injected: 131,629",
},
"pt": {
    "turnout_title": "Afluência, freguesia a freguesia: uma curva em sino — e nada acima de ~79%",
    "turnout_xlabel": "Afluência, % dos eleitores inscritos",
    "turnout_ylabel": "Votantes",
    "cut_label": "fronteira do declínio honesto (78,6%, fixada pelas eleições de controlo)",
    "box": ("acima da linha: 7 779 votantes = 0,13% dos boletins.\n"
            "A faixa de 80–100% — precisamente onde cai a inflação de votos — está vazia."),
    "comet_title": "Afluência vs. percentagem do AD (líder) — sem «cauda de cometa»",
    "comet_xlabel": "Afluência, %",
    "comet_ylabel": "Percentagem do AD, % dos boletins",
    "comet_legend": "média por grupos de afluência",
    "comet_box": ("A percentagem do AD mantém-se estável em toda a gama de afluência\n"
                  "(correlação ponderada −0,09); não há nuvem separada\n"
                  "de afluência alta com percentagem alta."),
    "selftest_title": "Auto-teste: injeção de fraude sintética — todos os alarmes disparam (sinal ×18)",
    "selftest_ylabel": "votos estimados do AD na zona anómala",
    "clean_label": "dados limpos\n14 589",
    "injected_label": "após injeção\n255 496",
    "added_label": "boletins injetados: 131 629",
},
}

df = pd.read_csv(ROOT / "data" / "legislativas2025_mai" / "results_all.csv", encoding="utf-8-sig")
df = df[df["level"] == 3].copy()  # freguesias (континент + Мадейра + Азорские о-ва)
party_cols = [c for c in df.columns if c.startswith("votes:")]
df["valid"] = df[party_cols].sum(axis=1)
# Коалиция AD: на материке PPD/PSD.CDS-PP, на Азорах добавляется PPM (cf. AGENTS.md).
df["ad"] = df["votes:PPD/PSD.CDS-PP"].fillna(0) + df["votes:PPD/PSD.CDS-PP.PPM"].fillna(0)
df["turnout"] = 100.0 * df["voted"] / df["registered_voters"]
df["ad_share"] = 100.0 * df["ad"] / df["voted"]

# Контрольные суммы против analysis/metrics.json. Хвост Шпилькина считается
# по корзинам 0,5 п.п. (bin centers > t_cut) — как в analysis-tool.
edges = np.arange(0.0, 100.0 + 0.5, 0.5)
centers = 0.5 * (edges[:-1] + edges[1:])
h_voted, _ = np.histogram(df["turnout"], bins=edges, weights=df["voted"])
h_ad, _ = np.histogram(df["turnout"], bins=edges, weights=df["ad"])
mask = centers > CUT
assert len(df) == 3092, len(df)
assert int(df["registered_voters"].sum()) == 9_265_493
assert int(df["voted"].sum()) == 5_965_446
assert int(h_voted[mask].sum()) == 7_779, int(h_voted[mask].sum())
assert int(h_ad[mask].sum()) == 2_980, int(h_ad[mask].sum())
print(f"checks ok: 3 092 parishes; tail zone: {int(h_voted[mask].sum()):,} voters "
      f"({h_voted[mask].sum()/df['voted'].sum()*100:.2f}%), AD {int(h_ad[mask].sum()):,}")


def fig_turnout(lang: str, tr: dict) -> None:
    fig, ax = plt.subplots(figsize=(9.6, 4.0), dpi=150)
    ax.hist(df["turnout"], bins=np.arange(0, 100.75, 0.75), weights=df["voted"],
            color=BLUE, alpha=0.85, edgecolor="white", linewidth=0.3)
    ax.axvline(CUT, color=RED, linestyle="--", linewidth=1.6)
    ax.text(CUT - 1.2, ax.get_ylim()[1] * 0.94, tr["cut_label"], color=RED,
            fontsize=10, ha="right")
    ax.text(
        0.865,
        0.58,
        tr["box"],
        transform=ax.transAxes,
        color=DARK,
        fontsize=10,
        ha="center",
        bbox=dict(boxstyle="round,pad=0.4", fc="#f4f7fa", ec=GREY, lw=0.8),
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
    fig, ax = plt.subplots(figsize=(9.6, 4.8), dpi=150)
    ax.scatter(df["turnout"], df["ad_share"], s=df["registered_voters"] / 450,
               color=BLUE, alpha=0.18, linewidths=0)
    bins = list(range(30, 85, 3))
    d = df[(df["turnout"] >= bins[0]) & (df["turnout"] < bins[-1])].copy()
    d["bin"] = pd.cut(d["turnout"], bins)
    m = d.groupby("bin", observed=True).apply(
        lambda g: pd.Series(
            {
                "x": (g["turnout"] * g["registered_voters"]).sum() / g["registered_voters"].sum(),
                "y": (g["ad_share"] * g["voted"]).sum() / g["voted"].sum(),
                "n": len(g),
            }
        ),
        include_groups=False,
    )
    m = m[m["n"] >= 20]
    ax.plot(m["x"], m["y"], color=DARK, linewidth=2.6, marker="o", markersize=5, zorder=5,
            label=tr["comet_legend"])
    ax.text(
        0.03,
        0.95,
        tr["comet_box"],
        transform=ax.transAxes,
        fontsize=10,
        va="top",
        color=DARK,
        bbox=dict(boxstyle="round,pad=0.45", fc="#f4f7fa", ec=GREY, lw=0.8),
    )
    ax.legend(loc="upper right", fontsize=10, framealpha=0.9)
    ax.set_xlim(25, 85)
    ax.set_ylim(0, 80)
    ax.set_xlabel(tr["comet_xlabel"])
    ax.set_ylabel(tr["comet_ylabel"])
    ax.set_title(tr["comet_title"])
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / lang / "comet.png")
    plt.close(fig)


def fig_selftest(lang: str, tr: dict) -> None:
    # Числа — analysis/metrics.json → selftest (инъекция: +10% приходов,
    # явка +5–35 п.п., 60–95% добавленных бюллетеней за AD).
    clean, added, injected = 14_589, 131_629, 255_496
    fig, ax = plt.subplots(figsize=(9.6, 4.0), dpi=150)
    ax.bar([0], [clean], width=0.55, color=GREEN, zorder=3)
    ax.bar([1], [injected], width=0.55, color=RED, zorder=3)
    ax.bar([1], [added], width=0.55, facecolor="none", edgecolor=BLUE,
           hatch="///", linewidth=1.4, zorder=4, label=tr["added_label"])
    ax.text(0, clean + 6000, tr["clean_label"], ha="center", fontsize=11, color=DARK)
    ax.text(1, injected + 6000, tr["injected_label"], ha="center", fontsize=11, color=DARK)
    ax.set_xticks([0, 1], ["", ""])
    ax.set_xlim(-0.6, 1.6)
    ax.set_ylim(0, 300_000)
    ax.set_ylabel(tr["selftest_ylabel"])
    ax.set_title(tr["selftest_title"])
    ax.legend(loc="upper left", fontsize=10, framealpha=0.9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / lang / "selftest.png")
    plt.close(fig)


for lang, tr in T.items():
    (OUT / lang).mkdir(parents=True, exist_ok=True)
    fig_turnout(lang, tr)
    fig_comet(lang, tr)
    fig_selftest(lang, tr)
    print(f"{lang}: turnout, comet, selftest -> site/portugal-2025/img/{lang}/")
