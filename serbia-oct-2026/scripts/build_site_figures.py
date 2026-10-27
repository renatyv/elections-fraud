"""Rebuild the Serbian/English public-page figures and downloadable evidence."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
SITE = BASE.parent / "site/serbia-oct-2026"
NAVY, GOLD, GRAY = "#16324f", "#d59d26", "#9aa5b1"
LABELS = {
    "en": {
        "margin_title": "From an early incumbent lead to a Students majority",
        "counted": "Polling stations processed, %", "margin": "Students − Vučić, percentage points",
        "latest": "21:15 CET: +13.54 pp", "peak": "16:55 CET: +13.62 pp",
        "seats_title": "Same votes, different seat-allocation rules · 16:55 CET snapshot",
        "students": "Students", "incumbent": "Vučić", "minorities": "Minority lists",
        "legal": "Legal D’Hondt + minority bonus", "plain": "Plain D’Hondt", "hare": "Hare remainder",
        "seats": "Seats of 250", "comparison": "The matched-station comparison · 7,935 keys",
        "turnout": "Turnout, % of registered voters", "share": "Incumbent share of valid votes, %",
        "map": "Plurality winners by municipality · 189 territorial municipalities",
        "municipalities": "Municipalities", "others": "Other lists",
    },
    "sr": {
        "margin_title": "Од раног вођства власти до већине Студентске листе",
        "counted": "Обрађена бирачка места, %", "margin": "Студентска листа − Вучић, процентни поени",
        "latest": "21:15 CET: +13,54 п.п.", "peak": "16:55 CET: +13,62 п.п.",
        "seats_title": "Исти гласови, различита расподела мандата · пресек у 16:55 CET",
        "students": "Студентска листа", "incumbent": "Вучић", "minorities": "Мањинске листе",
        "legal": "Законски Д’Онт + мањинско увећање", "plain": "Д’Онт без увећања", "hare": "Хејров највећи остатак",
        "seats": "Мандати од укупно 250", "comparison": "Поређење 7.935 упарених бирачких места",
        "turnout": "Излазност, % уписаних бирача", "share": "Удео власти у важећим гласовима, %",
        "map": "Листе са највише гласова по општинама · 189 општина",
        "municipalities": "Општине", "others": "Остале листе",
    },
}


def build_figures(lang: str) -> None:
    text = LABELS[lang]
    target = SITE / "img" / lang
    target.mkdir(parents=True, exist_ok=True)
    nat = pd.read_csv(BASE / "data/trends/national.csv")
    res = pd.read_csv(BASE / "data/trends/results.csv")
    votes = res[res.area_level == "country"].pivot(index="fetch_ts_utc", columns="candidate_id", values="pct")
    joined = nat.set_index("fetch_ts_utc").join((votes[3] - votes[1]).rename("margin"))
    assert len(joined) == 14 and joined.margin.notna().all()
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.axhline(0, color=GRAY, lw=1)
    ax.plot(joined.pct_counted, joined.margin, color=GOLD, marker="o", ms=4, lw=2)
    for idx, label, offset in [(joined.margin.idxmax(), text["peak"], (-130, 32)),
                               (joined.index[-1], text["latest"], (-130, -32))]:
        row = joined.loc[idx]
        ax.annotate(label, (row.pct_counted, row.margin), xytext=offset, textcoords="offset points",
                    fontsize=9, arrowprops={"arrowstyle": "-", "color": GRAY})
    ax.set(xlabel=text["counted"], ylabel=text["margin"], title=text["margin_title"], ylim=(-8, 18))
    ax.grid(alpha=0.18)
    fig.tight_layout()
    fig.savefig(target / "margin.png", dpi=150)
    plt.close(fig)

    seats = pd.read_csv(BASE / "analysis/paradoxes/tables/seats.csv").set_index("list_no")
    assert seats.seats_dhondt.sum() == 250
    fig, ax = plt.subplots(figsize=(9, 4.2))
    y = np.arange(3)
    for shift, column, color, label in [(-0.24, "seats_dhondt", GOLD, text["legal"]),
                                      (0, "seats_plain_dhondt", NAVY, text["plain"]),
                                      (0.24, "seats_largest_remainder", GRAY, text["hare"])]:
        values = [int(seats.loc[3, column]), int(seats.loc[1, column]),
                  int(seats.drop(index=[1, 3])[column].sum())]
        bars = ax.barh(y + shift, values, height=0.22, color=color, label=label)
        ax.bar_label(bars, padding=3, fontsize=9)
    ax.set(yticks=y, yticklabels=[text["students"], text["incumbent"], text["minorities"]],
           xlabel=text["seats"], title=text["seats_title"], xlim=(0, 160))
    ax.invert_yaxis()
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.grid(alpha=0.18, axis="x")
    fig.tight_layout()
    fig.savefig(target / "seats.png", dpi=150)
    plt.close(fig)

    metrics = json.loads((BASE / "analysis/diagnostics/metrics.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    for ax, key, title in [(axes[0], "matched_turnout_pct", text["turnout"]),
                           (axes[1], "matched_incumbent_valid_share_pct", text["share"])]:
        vals = [metrics[key][str(year)] for year in (2023, 2026)]
        bars = ax.bar(["2023", "2026"], vals, color=[GRAY, GOLD], width=0.5)
        ax.bar_label(bars, fmt="%.2f%%", padding=5)
        ax.set(ylim=(0, 82), title=title)
        ax.grid(alpha=0.18, axis="y")
    fig.suptitle(text["comparison"])
    fig.tight_layout()
    fig.savefig(target / "comparison.png", dpi=150)
    plt.close(fig)

    counts = pd.read_csv(BASE / "analysis/paradoxes/tables/municipality_winners.csv").set_index("winner").municipalities
    values = [int(counts.get("votes:Students", 0)), int(counts.get("votes:Vučić", 0)),
              int(counts.drop(index=["votes:Students", "votes:Vučić"]).sum())]
    fig, ax = plt.subplots(figsize=(9, 3.4))
    bars = ax.barh([text["students"], text["incumbent"], text["others"]], values, color=[GOLD, NAVY, GRAY])
    ax.bar_label(bars, padding=5)
    ax.set(xlim=(0, 110), xlabel=text["municipalities"], title=text["map"])
    ax.invert_yaxis()
    ax.grid(alpha=0.18, axis="x")
    fig.tight_layout()
    fig.savefig(target / "map.png", dpi=150)
    plt.close(fig)


def main() -> None:
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    for lang in LABELS:
        build_figures(lang)
        target = SITE / "img/details" / lang / "stn2026_controlled"
        target.mkdir(parents=True, exist_ok=True)
        for name in ("shpilkin_core", "comet_scatter", "fingerprint_2d", "integer_peaks",
                     "digit_benford2", "digit_last", "neighbors_outliers", "selftest"):
            source = BASE / "analysis/ef/stn2026_controlled/figures" / f"{name}.png"
            shutil.copy2(source, target / source.name)
    download = SITE / "downloads"
    download.mkdir(parents=True, exist_ok=True)
    for source in [BASE / "REPORT_statistical_fraud_analysis.md", BASE / "PARADOXES.md",
                   BASE / "analysis/trends/README.md", BASE / "analysis/trends/metrics.json",
                   BASE / "analysis/diagnostics/metrics.json",
                   BASE / "analysis/paradoxes/tables/seats.csv",
                   BASE / "analysis/paradoxes/tables/threshold.csv"]:
        name = "trends.md" if source.name == "README.md" else source.name
        if source.parent.name == "diagnostics":
            name = "diagnostics.json"
        shutil.copy2(source, download / name)
    print(f"Built Serbian/English figures and evidence downloads: {SITE}")


if __name__ == "__main__":
    main()
