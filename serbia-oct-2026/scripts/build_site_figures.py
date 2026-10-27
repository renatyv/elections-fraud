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

from election_forensics.data import ElectionData

BASE = Path(__file__).resolve().parents[1]
SITE = BASE.parent / "site/serbia-oct-2026"
NAVY, GOLD, GRAY = "#16324f", "#d59d26", "#9aa5b1"
LABELS = {
    "en": {
        "margin_title": "Published lead through the captured count",
        "counted": "Polling stations processed, %", "margin": "Students − Vučić, percentage points",
        "latest": "21:15 CET: +13.54 pp", "peak": "16:55 CET: +13.62 pp",
        "seats_title": "Same votes, different seat-allocation rules · 16:55 CET snapshot",
        "students": "Students", "incumbent": "Vučić", "minorities": "Minority lists",
        "legal": "Legal D’Hondt + minority bonus", "plain": "Plain D’Hondt", "hare": "Hare remainder",
        "seats": "Projected seats · 250 total", "comparison": "The matched-station comparison · 7,935 keys",
        "turnout": "Turnout, % of registered voters", "share": "Incumbent share of valid votes, %",
        "map": "Municipality plurality tally · 16:55 CET interim snapshot",
        "municipalities": "Municipalities", "others": "Other lists",
    },
    "sr": {
        "margin_title": "Објављена разлика током забележеног бројања",
        "counted": "Обрађена бирачка места, %", "margin": "Студентска листа − Вучић, процентни поени",
        "latest": "21:15 CET: +13,54 п.п.", "peak": "16:55 CET: +13,62 п.п.",
        "seats_title": "Исти гласови, различита расподела мандата · пресек у 16:55 CET",
        "students": "Студентска листа", "incumbent": "Вучић", "minorities": "Мањинске листе",
        "legal": "Законски Д’Онт + мањинско увећање", "plain": "Д’Онт без увећања", "hare": "Хејров највећи остатак",
        "seats": "Пројекција мандата · укупно 250", "comparison": "Поређење 7.935 упарених бирачких места",
        "turnout": "Излазност, % уписаних бирача", "share": "Удео власти у важећим гласовима, %",
        "map": "Број општина по водећој листи · привремени пресек у 16:55 CET",
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


def build_diagnostic_figures() -> None:
    """Render archived statistics with labels describing the observations shown."""
    from election_forensics import plots
    from election_forensics.data import load_mai_csv
    from election_forensics.integer_peaks import integer_peaks
    from election_forensics.selftest import SelftestReport, inject_additive_fraud
    from election_forensics.shpilkin import ShpilkinResult

    data = load_mai_csv(BASE / "data/ef/serbia2026_stn/results_freguesias.csv",
                        election_name="Serbia 2026 · 8,124 territorial stations · 16:55 CET")
    metrics = json.loads((BASE / "analysis/ef/stn2026_controlled/metrics.json").read_text())
    target = BASE / "analysis/ef/stn2026_controlled/figures"
    assert data.n == metrics["n_units"] == 8124
    plots.plot_shpilkin(data, "votes:Students", ShpilkinResult(**metrics["shpilkin"]), target)
    plots.plot_comet(data, ["votes:Students", "votes:Vučić", "votes:Dacić (SPS)"], target)
    plots.plot_integer_peaks(data, integer_peaks(data, "turnout"), target)
    neighbors = pd.read_csv(BASE / "analysis/ef/stn2026_controlled/tables/neighbors_z.csv")
    plots.plot_neighbors(neighbors, target)
    injected, _ = inject_additive_fraud(data, "votes:Students")
    plots.plot_selftest(data, injected, "votes:Students", SelftestReport(**metrics["selftest"]), target)
    build_fingerprint_comparison(data, metrics, target)
    build_digit_figures(data, metrics, target)


def build_fingerprint_comparison(data: ElectionData, metrics: dict, target: Path) -> None:
    from matplotlib.colors import LogNorm
    from election_forensics.data import load_mai_csv

    old = load_mai_csv(BASE / "data/ef/serbia2023_stn/results_freguesias.csv")
    old_metrics = json.loads((BASE / "analysis/ef/stn2023_control/metrics.json").read_text())
    diagnostics = json.loads((BASE / "analysis/diagnostics/metrics.json").read_text())
    panels = [(data, "Students", metrics["fingerprint"], "2026 · Students · 8,124 stations"),
              (data, "Vučić", diagnostics["incumbent_fingerprint"], "2026 · Vučić · 8,124 stations"),
              (old, "Vučić", old_metrics["fingerprint"], "2023 reference · Vučić · 8,163 stations")]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.7), sharex=True, sharey=True, layout="constrained")
    edges = np.linspace(0, 100, 81)
    for ax, (frame, party, fit, title) in zip(axes, panels):
        image = ax.hist2d(frame.turnout, frame.share(f"votes:{party}"), bins=[edges, edges],
                          weights=frame.registered, cmap="viridis", cmin=1, norm=LogNorm(vmin=1, vmax=100000))
        for key, marker, color, label in [("mean_main", "o", "white", "A: lower-turnout fitted centre"),
                                           ("mean_anom", "s", "#ff9933", "B: higher-turnout fitted centre")]:
            ax.plot(*fit[key], marker, ms=9, mfc="none", mec=color, mew=1.8)
            ax.annotate(label[0], fit[key], xytext=(7, 7), textcoords="offset points", color=color,
                        weight="bold", fontsize=10)
        ax.set(xlabel="Turnout: reported voters / registered, %", title=title, xlim=(0, 100), ylim=(0, 100))
    axes[0].set_ylabel("List votes / reported voters, %")
    fig.colorbar(image[3], ax=list(axes), label="Registered electors per cell · log scale", shrink=0.8)
    fig.suptitle("Turnout and list support: two components requested for each panel\n"
                 "A and B are fitted centres; colours show electorate density, not suspicion", fontsize=12)
    fig.savefig(target / "fingerprint_2d.png", dpi=150)
    plt.close(fig)


def build_digit_figures(data: ElectionData, metrics: dict, target: Path) -> None:
    from election_forensics.digit_tests import BENFORD_2ND, digit_freqs, digit_null_band

    for kind, key, minimum in [("benford2", "benford2", 10), ("last", "last_digit", 100)]:
        fig, axes = plt.subplots(1, 3, figsize=(11, 3.8), sharey=True)
        expected = BENFORD_2ND if kind == "benford2" else np.full(10, 0.1)
        for ax, row in zip(axes, metrics[key]):
            counts = data.df[f'votes:{row["party"]}'].to_numpy()
            observed = digit_freqs(counts, kind)
            band = digit_null_band(counts, kind)
            x = np.arange(10)
            ax.bar(x - 0.2, observed * 100, width=0.4, color=NAVY, label="Observed")
            ax.bar(x + 0.2, expected * 100, width=0.4, color=GRAY,
                   label="Benford reference" if kind == "benford2" else "Uniform reference")
            ax.fill_between(x, band[0] * 100, band[1] * 100, color=GOLD, alpha=0.25,
                            label="95% smooth-model simulation band")
            note = " · too few for chi-square inference" if row["n_numbers"] < 50 else ""
            ax.set(title=f'{row["party"]}\nn = {row["n_numbers"]:,}{note}', xlabel="Digit",
                   xticks=x)
            ax.tick_params(axis="x", labelsize=8)
        axes[0].set_ylabel("Frequency among eligible tallies, %")
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", ncols=3, fontsize=8)
        title = "Second digits" if kind == "benford2" else "Last digits"
        fig.suptitle(f"2026 territorial stations · {title} · list vote counts ≥ {minimum}\n"
                     "Each list has its own counts and fitted simulation reference", fontsize=11)
        fig.tight_layout(rect=(0, 0.1, 1, 0.87))
        fig.savefig(target / f"digit_{kind}.png", dpi=150)
        plt.close(fig)


def main() -> None:
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    build_diagnostic_figures()
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
    for name, run in [("screening_2026.json", "stn2026_controlled"),
                      ("reference_2023.json", "stn2023_control")]:
        shutil.copy2(BASE / "analysis/ef" / run / "metrics.json", download / name)
    print(f"Built Serbian/English figures and evidence downloads: {SITE}")


if __name__ == "__main__":
    main()
