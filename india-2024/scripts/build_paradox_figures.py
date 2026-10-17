"""Paradox figures for the public site page — one set per language (en, hi).

Data: analysis_paradoxes outputs written by scripts/paradox_analysis.py.
Run from the india-2024 project:  uv run python scripts/build_paradox_figures.py
Output: <repo>/site/india-2024/img/<lang>/{spoilers,transfer}.png
"""
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas", "matplotlib", "numpy"]
# ///
from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "site" / "india-2024" / "img"
DATA = ROOT / "analysis_paradoxes"

BLUE = "#3b82c4"
DARK = "#16324f"
RED = "#c0392b"
GREY = "#8a97a5"
GREEN = "#1e8e5a"
AMBER = "#c98a2b"

plt.rcParams.update(
    {
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
        "font": "DejaVu Sans",
        "share_title": "Nearly half of all winners lack a majority",
        "share_xlabel": "Winner's vote share, % (candidates' votes, excl. NOTA)",
        "share_ylabel": "Constituencies",
        "share_50": "50%",
        "share_box": "left of the line the frustrated-majority\nparadox is possible; right of it — impossible",
        "sp_title": "One seat in three decided by vote splitting",
        "sp_ylabel": "Seats where a third candidate's votes\nexceeded the whole winning margin, %",
        "sp_note": "BSP alone was the largest spoiler in 54 of them (2024)",
        "tr_title": "Uttar Pradesh: whose turf do the spoiler votes sit on?",
        "tr_xlabel": "Correlation asymmetry:  r(spoiler, runner-up) − r(spoiler, winner)",
        "tr_legend_pos": "runner-up's turf (p < 0.05)",
        "tr_legend_neg": "winner's turf (p < 0.05)",
        "tr_legend_ns": "not significant",
        "tr_note": "46 spoiler cases · Form 20 booths · permutation test, 2,000 shuffles",
    },
    "hi": {
        "font": "Devanagari Sangam MN",
        "share_title": "लगभग आधे विजेताओं के पास बहुमत नहीं",
        "share_xlabel": "विजेता का वोट हिस्सा, % (प्रत्याशियों के मत, नोटा छोड़कर)",
        "share_ylabel": "लोकसभा क्षेत्र",
        "share_50": "50%",
        "share_box": "रेखा के बाएँ निराश-बहुमत विरोधाभास संभव है;\nदाएँ — असंभव",
        "sp_title": "हर तीसरी सीट वोट-विभाजन से तय हुई",
        "sp_ylabel": "ऐसी सीटें जहाँ तीसरे प्रत्याशी के मत\nपूरे जीत-अंतर से बड़े थे, %",
        "sp_note": "अकेली बसपा उनमें 54 सीटों की सबसे बड़ी स्पॉइलर रही (2024)",
        "tr_title": "उत्तर प्रदेश: वोट-काट किसकी ज़मीन पर बैठी है?",
        "tr_xlabel": "सहसंबंध असममिति:  r(स्पॉइलर, उपविजेता) - r(स्पॉइलर, विजेता)",
        "tr_legend_pos": "उपविजेता की ज़मीन (p < 0.05)",
        "tr_legend_neg": "विजेता की ज़मीन (p < 0.05)",
        "tr_legend_ns": "असार्थक",
        "tr_note": "46 स्पॉइलर मामले, फॉर्म 20 बूथ, क्रमचय-परीक्षण (2,000 फेरबदल)",
    },
}

YEARS = [(2024, BLUE, "2024"), (2019, GREY, "2019"), (2014, AMBER, "2014")]


def make(lang: str) -> None:
    t = T[lang]
    plt.rcParams["font.family"] = t["font"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.4, 4.2))

    # ── left: winner-share distributions, three elections, 50% line
    bins = np.arange(20, 90, 2.5)
    for year, color, label in YEARS:
        d = pd.read_csv(DATA / f"pc_paradoxes_{year}.csv")
        ax1.hist(d["winner_share"] * 100, bins=bins, histtype="stepfilled",
                 alpha=0.55 if year == 2024 else 0.30, color=color,
                 edgecolor=color, linewidth=1.6 if year == 2024 else 1.0,
                 label=f"{label} ({len(d)})")
    ax1.axvline(50, color=DARK, linewidth=1.6, linestyle="--")
    ax1.text(50.8, ax1.get_ylim()[1] * 0.97, t["share_50"], color=DARK,
             fontsize=11, va="top", fontweight="bold")
    ax1.set_title(t["share_title"])
    ax1.set_xlabel(t["share_xlabel"])
    ax1.set_ylabel(t["share_ylabel"])
    ax1.legend(loc="upper left", frameon=False, fontsize=10)
    ax1.text(0.02, 0.60, t["share_box"], transform=ax1.transAxes, fontsize=10,
             color=DARK, bbox=dict(boxstyle="round,pad=0.45", fc="#f4f7fa",
                                   ec=GREY, lw=0.8))

    # ── right: spoiler-decided share of seats per election
    s = pd.read_csv(DATA / "summary_by_year.csv").set_index("year")
    order = [2014, 2019, 2024]
    colors = {"2014": AMBER, "2019": GREY, "2024": BLUE}
    vals = [s.loc[y, "spoiler_seat_share"] * 100 for y in order]
    bars = ax2.bar([str(y) for y in order], vals, width=0.62,
                   color=[colors[str(y)] for y in order])
    for b, y in zip(bars, order):
        ax2.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.2,
                 f"{s.loc[y, 'spoiler_seats']}/{s.loc[y, 'seats']}",
                 ha="center", color=DARK, fontweight="bold", fontsize=10.5)
    ax2.set_ylim(0, max(vals) * 1.22)
    ax2.set_title(t["sp_title"])
    ax2.set_ylabel(t["sp_ylabel"], fontsize=10)
    ax2.set_yticks([0, 10, 20, 30, 40, 50])
    ax2.set_yticklabels(["0", "10", "20", "30", "40", "50%"])
    ax2.text(0.5, -0.24, t["sp_note"], transform=ax2.transAxes, ha="center",
             fontsize=10, color=DARK)

    fig.tight_layout()
    (OUT / lang).mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / lang / "spoilers.png", dpi=150)
    plt.close(fig)


def make_transfer(lang: str) -> None:
    """UP booth-transfer asymmetry: r(spoiler, runner) − r(spoiler, winner)
    for every spoiler case, coloured by permutation significance."""
    t = T[lang]
    plt.rcParams["font.family"] = t["font"]
    plt.rcParams["axes.unicode_minus"] = False  # Devanagari font lacks U+2212
    d = pd.read_csv(DATA / "up_booth_transfer_2024.csv").sort_values("diff").reset_index(drop=True)
    labels = [pc if sp == "BSP" else f"{pc} ({sp})" for pc, sp in zip(d["pc"], d["spoiler"])]
    sig = d["perm_p_two_sided"] < 0.05
    colors = [BLUE if s and v > 0 else RED if s else GREY for s, v in zip(sig, d["diff"])]

    fig, ax = plt.subplots(figsize=(7.6, 8.8))
    ax.barh(range(len(d)), d["diff"], color=colors, height=0.72)
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.axvline(0, color=DARK, lw=1.2)
    ax.set_xlabel(t["tr_xlabel"], fontsize=10)
    ax.set_title(t["tr_title"])
    ax.spines[["top", "right"]].set_visible(False)

    from matplotlib.patches import Patch

    ax.legend(
        handles=[
            Patch(color=BLUE, label=t["tr_legend_pos"]),
            Patch(color=RED, label=t["tr_legend_neg"]),
            Patch(color=GREY, label=t["tr_legend_ns"]),
        ],
        loc="lower right", frameon=False, fontsize=10,
    )
    ax.text(0.01, -0.095, t["tr_note"], transform=ax.transAxes, fontsize=9.5, color="#5b6b7b")

    fig.tight_layout()
    fig.savefig(OUT / lang / "transfer.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    for lang in ("en", "hi"):
        make(lang)
        make_transfer(lang)
        print(f"img/{lang}/spoilers.png + transfer.png done")
