"""Figures for the public site page — one set per language (en, hi).

Data: data/mai_pc_2024 + mai_pc_2014 (constituencies), form20 booths
(via booth_digit_tests helpers), analysis_up_booth_2014 (honest booth control).
Run from the india-2024 project:  uv run python scripts/build_site_figures.py
Output: <repo>/site/india-2024/img/<lang>/{turnout,comet,booths}.png
"""
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas", "matplotlib", "numpy"]
# ///
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "site" / "india-2024" / "img"
DATA = ROOT / "data"

BLUE = "#3b82c4"
DARK = "#16324f"
RED = "#c0392b"
GREY = "#8a97a5"
GREEN = "#1e8e5a"
CUT = 87.6  # Shpilkin boundary from the 2014 control (q99.5)

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
        "turnout_title": "Constituency turnout: one bell curve, no tail",
        "turnout_xlabel": "Turnout, % of registered voters",
        "turnout_ylabel": "Constituencies",
        "turnout_2024": "2024",
        "turnout_2014": "2014 (control)",
        "turnout_cut": "anomaly boundary 87.6% (from 2014)",
        "turnout_box": "zero constituencies to the right of the boundary —\nthe 88–100% zone, where ballot stuffing lands, is empty",
        "comet_title": "The leader's result does not grow with turnout",
        "comet_xlabel": "Turnout, %",
        "comet_ylabel": "Vote share, % of ballots",
        "comet_r": "weighted r = {r}",
        "booths_title": "110,000 recovered polling stations: digits behave",
        "booths_xlabel": "Last digit of BJP vote counts",
        "booths_ylabel": "Frequency, %",
        "booths_uniform": "uniform expectation (±95% band)",
        "booths_2024": "UP 2024 (81,652 counts ≥ 100)",
        "booths_2014": "UP 2014 control (107,722 counts ≥ 100)",
        "peaks_xlabel": "Stations with exactly integer BJP share, %",
        "peaks_ylabel": "Observed vs Monte-Carlo expectation",
        "peaks_obs": "observed",
        "peaks_null": "binomial null",
        "legend_loc": "best",
    },
    "hi": {
        "font": "Devanagari Sangam MN",
        "turnout_title": "लोकसभा क्षेत्रों में मतदान: एक साफ़ घंटी-वक्र, कोई पूँछ नहीं",
        "turnout_xlabel": "मतदान, पंजीकृत मतदाताओं का %",
        "turnout_ylabel": "लोकसभा क्षेत्र",
        "turnout_2024": "2024",
        "turnout_2014": "2014 (नियंत्रण)",
        "turnout_cut": "विसंगति सीमा 87.6% (2014 से)",
        "turnout_box": "सीमा के दाईन ओर एक भी क्षेत्र नहीं —\nबैलट-भराई का 88–100% क्षेत्र खाली है",
        "comet_title": "नेता का परिणाम मतदान के साथ नहीं बढ़ता",
        "comet_xlabel": "मतदान, %",
        "comet_ylabel": "वोट हिस्सा, मतपत्रों का %",
        "comet_r": "भारित r = {r}",
        "booths_title": "बहाल किए गए 1.1 लाख बूथ: अंकों का व्यवहार सामान्य",
        "booths_xlabel": "भाजपा के वोट-आंकड़ों का अंतिम अंक",
        "booths_ylabel": "बारंबारता, %",
        "booths_uniform": "समान प्रत्याशा (95% पट्टी)",
        "booths_2024": "यूपी 2024 (81,652 गिनतियाँ ≥ 100)",
        "booths_2014": "यूपी 2014 नियंत्रण (1,07,722 गिनतियाँ ≥ 100)",
        "peaks_xlabel": "पूर्ण-प्रतिशत भाजपा हिस्से वाले बूथ, %",
        "peaks_ylabel": "देखा गया बनाम मोंटे-कार्लो प्रत्याशा",
        "peaks_obs": "देखा गया",
        "peaks_null": "द्विपद शून्य",
        "legend_loc": "best",
    },
}


def _load() -> tuple[pd.DataFrame, pd.DataFrame]:
    n24 = pd.read_csv(DATA / "mai_pc_2024" / "results_freguesias.csv")
    n14 = pd.read_csv(DATA / "mai_pc_2014" / "results_freguesias.csv")
    return n24, n14


def fig_turnout(n24: pd.DataFrame, n14: pd.DataFrame, lang: str, t: dict) -> None:
    plt.rcParams["font.family"] = t["font"]
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    bins = np.arange(35, 100, 2.5)
    ax.hist(100 * n14.voted / n14.registered_voters, bins=bins, color=GREY, alpha=0.55,
            label=t["turnout_2014"], edgecolor="white")
    ax.hist(100 * n24.voted / n24.registered_voters, bins=bins, color=BLUE, alpha=0.75,
            label=t["turnout_2024"], edgecolor="white")
    ax.axvline(CUT, color=RED, lw=2, ls="--")
    ax.text(CUT + 0.7, ax.get_ylim()[1] * 0.72, t["turnout_cut"], color=RED, fontsize=10)
    ax.text(45, ax.get_ylim()[1] * 0.86, t["turnout_box"], fontsize=11.5, color=DARK,
            bbox=dict(facecolor="#eef4fa", edgecolor="#c6d6e6", boxstyle="round,pad=0.5"))
    ax.set_xlabel(t["turnout_xlabel"])
    ax.set_ylabel(t["turnout_ylabel"])
    ax.set_title(t["turnout_title"])
    ax.legend(loc="upper right", frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    (OUT / lang).mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / lang / "turnout.png", dpi=150)
    plt.close(fig)


def _wcorr(x: pd.Series, y: pd.Series, w: pd.Series) -> float:
    x, y, w = x.to_numpy(float), y.to_numpy(float), w.to_numpy(float)
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    cov = np.average((x - mx) * (y - my), weights=w)
    return cov / np.sqrt(np.average((x - mx) ** 2, weights=w) * np.average((y - my) ** 2, weights=w))


def fig_comet(n24: pd.DataFrame, lang: str, t: dict) -> None:
    plt.rcParams["font.family"] = t["font"]
    fig, axes = plt.subplots(1, 3, figsize=(11.4, 4.0), sharey=True)
    for ax, party, color in zip(axes, ["BJP", "INC", "SP"], [BLUE, GREEN, "#b57edc"]):
        d = n24
        x = 100 * d.voted / d.registered_voters
        y = 100 * d[f"votes:{party}"] / d.voted
        w = d.registered_voters
        if party == "SP":
            m = d[f"votes:SP"] > 0
            x, y, w = x[m], y[m], w[m]
        s = 18 + 62 * (w / w.max())
        ax.scatter(x, y, s=s, alpha=0.45, color=color, edgecolors="none")
        r = _wcorr(x, y, w)
        ax.set_title(f"{party} — {t['comet_r'].format(r=f'{r:+.2f}')}", fontsize=12)
        ax.set_xlabel(t["comet_xlabel"])
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_ylim(0, 80)
    axes[0].set_ylabel(t["comet_ylabel"])
    fig.suptitle(t["comet_title"], fontweight="bold", fontsize=13)
    fig.tight_layout()
    (OUT / lang).mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / lang / "comet.png", dpi=150)
    plt.close(fig)


def _booth_counts() -> tuple[np.ndarray, np.ndarray]:
    """Last digits of BJP booth counts: 2024 (form20), 2014 (control)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from booth_digit_tests import build_booth_parties

    w24 = build_booth_parties()
    c24 = w24["votes:BJP"].to_numpy()
    c24 = c24[c24 >= 100].astype(int)

    b14 = pd.read_csv(DATA / "mai_up_booth_2014" / "results_freguesias.csv")
    c14 = b14["votes:BJP"].to_numpy()
    c14 = c14[c14 >= 100].astype(int)
    return c24, c14


def fig_booths(lang: str, t: dict) -> None:
    plt.rcParams["font.family"] = t["font"]
    c24, c14 = _booth_counts()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.4, 4.2))
    d24 = np.bincount([int(str(x)[-1]) for x in c24], minlength=10) / len(c24) * 100
    d14 = np.bincount([int(str(x)[-1]) for x in c14], minlength=10) / len(c14) * 100
    band = 196 * np.sqrt(0.1 * 0.9 / len(c24))
    x = np.arange(10)
    ax1.fill_between(x, (10 - band) * np.ones(10), (10 + band) * np.ones(10),
                     color=GREY, alpha=0.3, label=t["booths_uniform"])
    ax1.plot(x, d14, "o-", color=GREY, lw=1.6, label=t["booths_2014"])
    ax1.plot(x, d24, "o-", color=BLUE, lw=2.2, label=t["booths_2024"])
    ax1.axhline(10, color=DARK, lw=0.8)
    ax1.set_xticks(x)
    ax1.set_xlabel(t["booths_xlabel"])
    ax1.set_ylabel(t["booths_ylabel"])
    ax1.legend(loc="upper right", frameon=False, fontsize=10)
    ax1.spines[["top", "right"]].set_visible(False)

    # integer-share peaks: observed vs binomial null, 2024 booths vs 2014
    # control — take the pipeline's own numbers so figure == report
    import json

    pk24 = pd.read_csv(ROOT / "analysis_booth" / "tables" / "booth_integer_share_peaks.csv")
    obs24 = float(pk24["observed_integer_pct"].iloc[0])
    null24 = float(pk24["null_mean_pct"].iloc[0])
    m14 = json.load(open(ROOT / "analysis_up_booth_2014" / "metrics.json"))
    obs14 = m14["integer_peaks_leader_share"]["observed_pct"]
    null14 = m14["integer_peaks_leader_share"]["null_pct"]
    labels = ["UP 2024", "UP 2014"]
    obs = [obs24, obs14]
    nulls = [null24, null14]
    xx = np.arange(2)
    ax2.bar(xx - 0.18, obs, width=0.36, color=BLUE, label=t["peaks_obs"])
    ax2.bar(xx + 0.18, nulls, width=0.36, color=GREY, alpha=0.7, label=t["peaks_null"])
    for i, (o, nn) in enumerate(zip(obs, nulls)):
        ax2.text(i - 0.18, o + 0.12, f"{o:.1f}", ha="center", fontsize=10.5, fontweight="bold")
        ax2.text(i + 0.18, nn + 0.12, f"{nn:.1f}", ha="center", fontsize=10.5, color="#5b6b7b")
    ax2.set_xticks(xx)
    ax2.set_xticklabels(labels)
    ax2.set_xlabel(t["peaks_xlabel"])
    ax2.set_ylabel(t["peaks_ylabel"])
    ax2.set_ylim(0, max(obs + nulls) + 1.2)
    ax2.legend(loc="upper right", frameon=False, fontsize=10)
    ax2.spines[["top", "right"]].set_visible(False)
    fig.suptitle(t["booths_title"], fontweight="bold", fontsize=13)
    fig.tight_layout()
    (OUT / lang).mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / lang / "booths.png", dpi=150)
    plt.close(fig)
    print(f"booth digits: 2024 n={len(c24):,}, 2014 n={len(c14):,}; "
          f"integer shares 2014: {obs14:.2f}% vs null {null14:.2f}%")


if __name__ == "__main__":
    n24, n14 = _load()
    for lang, t in T.items():
        fig_turnout(n24, n14, lang, t)
        fig_comet(n24, lang, t)
        fig_booths(lang, t)
        print(f"{lang}: done")
    print(f"output: {OUT}")
