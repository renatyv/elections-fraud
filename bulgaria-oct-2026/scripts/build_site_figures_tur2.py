"""Round-2 (runoff, 1 Nov 2026) public-page figures from the final protocol capture.

Aggregates both captured protocol sets (round 1: data/official_20261027,
round 2: data/official_20261102_tur2) at district level, draws the three overview charts and ten method
charts once per page language into site/bulgaria-oct-2026-round-2
/img/{en,bg}/, and bundles the downloadable analysis outputs. District names
keep their official Cyrillic form on the Bulgarian charts and a fixed
transliteration on the English ones; dynamic numbers switch to the Bulgarian
decimal comma.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
SITE = BASE.parent / "site/bulgaria-oct-2026-round-2"

NAVY, AMBER, RED, GREEN, GRAY = ("#16324f", "#e6a817", "#c0392b",
                                 "#1e8e5a", "#9aa5b1")

YOTOVA, GYUROV = "25", "4"          # ballot numbers of the runoff pair
ABROAD = 32

MIR_BG = {
    1: "Благоевград", 2: "Бургас", 3: "Варна", 4: "Велико Търново",
    5: "Видин", 6: "Враца", 7: "Габрово", 8: "Добрич", 9: "Кърджали",
    10: "Кюстендил", 11: "Ловеч", 12: "Монтана", 13: "Пазарджик",
    14: "Перник", 15: "Плевен", 16: "Пловдив Град", 17: "Пловдив Област",
    18: "Разград", 19: "Русе", 20: "Силистра", 21: "Сливен", 22: "Смолян",
    23: "София 23 МИР", 24: "София 24 МИР", 25: "София 25 МИР",
    26: "София Област", 27: "Стара Загора", 28: "Търговище", 29: "Хасково",
    30: "Шумен", 31: "Ямбол", 32: "Обобщени данни",
}
MIR_EN = {
    1: "Blagoevgrad", 2: "Burgas", 3: "Varna", 4: "Veliko Tarnovo",
    5: "Vidin", 6: "Vratsa", 7: "Gabrovo", 8: "Dobrich", 9: "Kardzhali",
    10: "Kyustendil", 11: "Lovech", 12: "Montana", 13: "Pazardzhik",
    14: "Pernik", 15: "Pleven", 16: "Plovdiv city", 17: "Plovdiv province",
    18: "Razgrad", 19: "Ruse", 20: "Silistra", 21: "Sliven", 22: "Smolyan",
    23: "Sofia-23", 24: "Sofia-24", 25: "Sofia-25", 26: "Sofia province",
    27: "Stara Zagora", 28: "Targovishte", 29: "Haskovo", 30: "Shumen",
    31: "Yambol", 32: "Abroad (aggregate)",
}

LABELS: dict[str, dict[str, str]] = {
    "en": {
        "mir_title": "Runoff margin by district: Yotova − Gyurov, 1 Nov 2026",
        "mir_xlabel": "Yotova − Gyurov margin, points",
        "mir_leg_y": "Yotova leads", "mir_leg_g": "Gyurov leads",
        "swing_title": "The same districts, seven days apart: first round → runoff",
        "swing_first": "First round (25 Oct)",
        "swing_to_y": "moved toward Yotova", "swing_to_g": "moved toward Gyurov",
        "tu_title1": "Turnout by district: runoff vs first round",
        "tu_title2": "Turnout × runoff margin (r = {r})",
        "tu_xlabel": "Turnout, % of register", "tu_ylabel": "Yotova − Gyurov, points",
        "tu_legend_r2": "runoff 1 Nov", "tu_legend_r1": "first round 25 Oct",
    },
    "bg": {
        "mir_title": "Разлика между Йотова и Гюров по райони, 1 ноември 2026 г.",
        "mir_xlabel": "Йотова − Гюров, пункта",
        "mir_leg_y": "води Йотова", "mir_leg_g": "води Гюров",
        "swing_title": "Същите райони седмица по-късно: първи тур → балотаж",
        "swing_first": "Първи тур (25 окт)",
        "swing_to_y": "към Йотова", "swing_to_g": "към Гюров",
        "tu_title1": "Активност по райони: балотаж и първи тур",
        "tu_title2": "Активност × разлика (r = {r})",
        "tu_xlabel": "Активност, % от списъка", "tu_ylabel": "Йотова − Гюров, пункта",
        "tu_legend_r2": "балотаж 1 ное", "tu_legend_r1": "първи тур 25 окт",
    },
}


def load_districts() -> pd.DataFrame:
    """Aggregate both protocol captures to district-level totals (all 32 areas)."""
    frames = []
    for tag, path in [("r1", BASE / "data/official_20261027/sections.json"),
                      ("r2", BASE / "data/official_20261102_tur2/sections.json")]:
        rows = pd.DataFrame(json.loads(path.read_text()))
        keep = rows[["district", "registered", "added", "voted"]].copy()
        keep["district"] = keep.district.astype(int)
        keep["yotova"] = rows.votes.map(lambda v: v.get(YOTOVA, 0))
        keep["gyurov"] = rows.votes.map(lambda v: v.get(GYUROV, 0))
        keep["registered"] = keep.registered + keep.added
        keep["tag"] = tag
        frames.append(keep)
    df = pd.concat(frames)
    df = df[(df.registered >= 100) & (df.voted > 0)]
    g = df.groupby(["tag", "district"]).sum(numeric_only=True)
    g["turnout"] = 100 * g.voted / g.registered
    g["margin"] = 100 * (g.yotova - g.gyurov) / g.voted
    return g.reset_index()


def _mir_name(code: int, lang: str) -> str:
    return f"{code:>2} {MIR_BG[code] if lang == 'bg' else MIR_EN[code]}"


def fig_mir(d: pd.DataFrame, text: dict[str, str], lang: str, dec: str,
            target: Path) -> None:
    r2 = d[(d.tag == "r2") & (d.district != ABROAD)].set_index("district")
    r2 = r2.sort_values("margin")
    abroad = d[(d.tag == "r2") & (d.district == ABROAD)].margin.iloc[0]
    fig, ax = plt.subplots(figsize=(8.6, 8.6))
    rows = list(r2.index) + [ABROAD]
    values = list(r2.margin) + [abroad]
    ax.barh(range(len(rows)), values,
            color=[NAVY if v >= 0 else AMBER for v in values], alpha=0.88, height=0.66)
    ax.set_yticks(range(len(rows)))
    labels = [_mir_name(int(c), lang) for c in rows]
    if lang == "bg":
        labels[-1] += " (задгр.)"
    ax.set_yticklabels(labels, fontsize=8.5)
    for i, v in enumerate(values):
        ax.annotate(f"{v:+.1f}".replace(".", dec), xy=(v, i),
                    xytext=(4 if v >= 0 else -4, 0), textcoords="offset points",
                    va="center", ha="left" if v >= 0 else "right", fontsize=7.5,
                    color="0.3")
    ax.axvline(0, color="0.6", lw=0.8)
    ax.set_xlabel(text["mir_xlabel"])
    ax.set_xlim(-45, 55)
    ax.grid(alpha=0.25, axis="x")
    ax.scatter([], [], color=NAVY, s=30, label=text["mir_leg_y"])
    ax.scatter([], [], color=AMBER, s=30, label=text["mir_leg_g"])
    ax.legend(loc="upper left", frameon=False, fontsize=8.5)
    ax.set_title(text["mir_title"])
    fig.tight_layout()
    fig.savefig(target / "mir.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_swing(d: pd.DataFrame, text: dict[str, str], lang: str, dec: str,
              target: Path) -> None:
    piv = d.pivot(index="district", columns="tag", values="margin")
    piv = piv.sort_values("r2")
    fig, ax = plt.subplots(figsize=(8.4, 8.4))
    ax.axvline(0, color="0.6", lw=0.8)
    for i, (code, row) in enumerate(piv.iterrows()):
        color = NAVY if row.r2 - row.r1 > 0 else AMBER
        ax.plot([row.r1, row.r2], [i, i], color="0.78", lw=1.4, zorder=1)
        ax.scatter([row.r1], [i], color="0.45", s=26, zorder=2)
        ax.scatter([row.r2], [i], color=color, s=40, zorder=3)
    ax.set_yticks(range(len(piv)))
    ax.set_yticklabels([_mir_name(int(c), lang) for c in piv.index], fontsize=8.5)
    ax.set_xlabel(text["mir_xlabel"])
    ax.scatter([], [], color="0.45", s=26, label=text["swing_first"])
    ax.scatter([], [], color=NAVY, s=40, label=text["swing_to_y"])
    ax.scatter([], [], color=AMBER, s=40, label=text["swing_to_g"])
    ax.legend(loc="lower right", frameon=False, fontsize=8.5)
    ax.grid(alpha=0.25, axis="x")
    ax.set_title(text["swing_title"])
    fig.tight_layout()
    fig.savefig(target / "swing.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_turnout(d: pd.DataFrame, text: dict[str, str], lang: str, dec: str,
                target: Path) -> float:
    dom = d[d.district != ABROAD]
    r2 = dom[dom.tag == "r2"].set_index("district")
    r1 = dom[dom.tag == "r1"].set_index("district")
    dd = r2.sort_values("turnout")
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), width_ratios=[1.15, 1])
    ax = axes[0]
    y = range(len(dd))
    ax.barh(y, dd.turnout, color=GREEN, alpha=0.55, height=0.62, label=text["tu_legend_r2"])
    r1m = r1.loc[dd.index, "turnout"]
    ax.scatter(r1m, y, color="0.35", s=18, zorder=3, label=text["tu_legend_r1"])
    ax.set_yticks(y)
    ax.set_yticklabels([_mir_name(int(c), lang) for c in dd.index], fontsize=8)
    for i, v in enumerate(dd.turnout):
        ax.annotate(f"{v:.1f}".replace(".", dec), xy=(v, i), xytext=(3, 0),
                    textcoords="offset points", va="center", fontsize=7, color="0.3")
    country = 100 * (dd.voted.sum()) / dd.registered.sum()
    ax.axvline(country, color=RED, lw=1.1, ls="--")
    ax.annotate(f"{country:.2f}".replace(".", dec), xy=(country, 0.8),
                xytext=(4, 0), textcoords="offset points", fontsize=8.5, color=RED)
    ax.set_xlabel(text["tu_xlabel"])
    ax.set_xlim(0, 48)
    ax.grid(alpha=0.25, axis="x")
    ax.legend(loc="lower right", frameon=False, fontsize=8.5)
    ax.set_title(text["tu_title1"])
    ax = axes[1]
    ax.scatter(r2.turnout, r2.margin, s=34, color=NAVY, alpha=0.75)
    r = float(np.corrcoef(r2.turnout, r2.margin)[0, 1])
    for code, row in r2.iterrows():
        if row.margin < 0 or row.turnout > 30:
            ax.annotate(f"{int(code)}", xy=(row.turnout, row.margin), xytext=(4, 3),
                        textcoords="offset points", fontsize=7.5, color="0.35")
    ax.axhline(0, color="0.6", lw=0.8)
    ax.set_xlabel(text["tu_xlabel"])
    ax.set_ylabel(text["tu_ylabel"])
    ax.grid(alpha=0.25)
    ax.set_title(text["tu_title2"].format(r=f"{r:+.2f}".replace(".", dec)))
    fig.tight_layout()
    fig.savefig(target / "turnout.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return r


def fig_methods(lang: str, target: Path) -> None:
    """Render each method from the saved inputs and metrics, without rerunning tests."""
    from election_forensics.digit_tests import BENFORD_2ND, digit_freqs, digit_null_band

    def text(en: str, bg: str) -> str:
        return bg if lang == "bg" else en

    def save(fig: plt.Figure, name: str) -> None:
        for ax in fig.axes:
            ax.grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(target / f"{name}.png", dpi=150, bbox_inches="tight")
        plt.close(fig)

    frame = pd.read_csv(BASE / "data/ef_tur2/results_freguesias.csv")
    metrics = json.loads((BASE / "analysis/ef_tur2/metrics.json").read_text())
    assert len(frame) == metrics["n_units"]
    turnout = 100 * frame.voted / frame.registered_voters
    share = 100 * frame["votes:Yotova"] / frame.voted
    turnout_label = text("Section turnout, %", "Секционна активност, %")
    share_label = text("Support for Yotova, %", "Подкрепа за Йотова, %")
    sections_label = text("Sections", "Секции")
    observed_label = text("Observed", "Наблюдавано")
    null_label = text("Computer comparison", "Компютърно сравнение")

    fig, ax = plt.subplots(figsize=(8, 4))
    edges = np.arange(0, 100.5, 0.5)
    centers = (edges[:-1] + edges[1:]) / 2
    for values, color, label in [
        (frame["votes:Yotova"], NAVY, text("Yotova ballots", "Бюлетини за Йотова")),
        (frame.voted - frame["votes:Yotova"], GRAY, text("Other signatures", "Останали подписи")),
    ]:
        counts, _ = np.histogram(turnout, bins=edges, weights=values)
        ax.plot(centers, counts, color=color, label=label)
    ax.axvspan(metrics["shpilkin"]["t_cut"], 100, color=AMBER, alpha=0.2)
    ax.axvline(metrics["shpilkin"]["t_cut"], color=AMBER, ls="--",
               label=text("Round-1 cutoff: 50.48%", "Праг от първия тур: 50,48%"))
    ax.set(xlabel=turnout_label, ylabel=text("Count per 0.5-point bin", "Брой в интервал от 0,5 п.п."),
           title=text("High-turnout tail: 28,904 Yotova ballots", "Опашка с висока активност: 28 904 бюлетини за Йотова"))
    ax.legend(fontsize=8)
    save(fig, "shpilkin")

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, party, name, color in zip(axes, ["Yotova", "Gyurov"],
                                     [text("Yotova", "Йотова"), text("Gyurov", "Гюров")], [NAVY, AMBER]):
        ax.scatter(turnout, 100 * frame[f"votes:{party}"] / frame.voted,
                   s=5, alpha=0.18, color=color, rasterized=True)
        ax.set(xlabel=turnout_label, ylabel=text("Support for candidate, %", "Подкрепа за кандидата, %"),
               title=name, xlim=(0, 101), ylim=(0, 101))
    save(fig, "comet")

    fig, ax = plt.subplots(figsize=(7.5, 4.7))
    from matplotlib.colors import LogNorm
    density = ax.hist2d(turnout, share, bins=60, weights=frame.registered_voters,
                        norm=LogNorm(), cmap="viridis", cmin=1)
    for key, marker, color, label in [
        ("mean_main", "o", "white", text("Group 1 centre", "Център на група 1")),
        ("mean_anom", "s", "#ffcc66", text("Group 2 centre", "Център на група 2")),
    ]:
        ax.scatter(*metrics["fingerprint"][key], marker=marker, s=90,
                   facecolors="none", edgecolors=color, label=label)
    ax.set(xlabel=turnout_label, ylabel=share_label,
           title=text("Two groups found in the voting patterns", "Две групи в моделите на гласуване"))
    ax.legend(fontsize=8, facecolor="#333333", labelcolor="white")
    fig.colorbar(density[3], ax=ax, label=text("People on voter lists in each square", "Избиратели в списъците във всяко квадратче"))
    save(fig, "fingerprint")

    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    for ax, key, title in zip(axes, ["integer_peaks_turnout", "integer_peaks_leader_share"],
                              [text("Whole-number turnout", "Активност с цял процент"),
                               text("Whole-number Yotova share", "Цял процент за Йотова")]):
        result = metrics[key]
        values = [result["observed_pct"], result["null_pct"]]
        ax.bar([observed_label, null_label], values, color=[NAVY, GRAY])
        ax.set(ylabel=text("Stations with whole-number percentages, %", "Секции с цели проценти, %"),
               title=f'{title} · z = {result["z"]:+.2f}')
        ax.set_ylim(0, max(values) * 1.2)
        for i, value in enumerate(values):
            ax.text(i, value, f"{value:.3f}%", ha="center", va="bottom")
    save(fig, "integer")

    for method, test in [("benford", "benford2"), ("last", "last")]:
        fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
        for ax, party, name in zip(axes, ["Yotova", "Gyurov"],
                                   [text("Yotova", "Йотова"), text("Gyurov", "Гюров")]):
            counts = frame[f"votes:{party}"].to_numpy()
            observed = digit_freqs(counts, test)
            band = digit_null_band(counts, test)
            reference = BENFORD_2ND if test == "benford2" else np.full(10, 0.1)
            ax.bar(np.arange(10), 100 * observed, color=NAVY, alpha=0.8, label=observed_label)
            ax.plot(np.arange(10), 100 * reference, color=RED, marker=".",
                    label=text("Benford’s rule", "Правило на Бенфорд") if test == "benford2"
                    else text("Equal share for each digit", "Равен дял за всяка цифра"))
            ax.fill_between(np.arange(10), 100 * band[0], 100 * band[1], color=AMBER, alpha=0.35,
                            label=text("95% range in computer comparisons", "95% диапазон в компютърните сравнения"))
            ax.set(xticks=np.arange(10), xlabel=text("Digit", "Цифра"),
                   ylabel=text("Station vote counts, %", "Секционни резултати, %"), title=name)
        axes[0].legend(fontsize=7, loc="lower left")
        save(fig, method)

    neighbors = pd.read_csv(BASE / "analysis/ef_tur2/tables/neighbors_z.csv")
    assert int(neighbors.flag.sum()) == metrics["neighbors_flagged"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for flagged, color, label in [(False, NAVY, text("Other stations", "Останали секции")),
                                  (True, AMBER, text("364 stations to review", "364 секции за преглед"))]:
        subset = neighbors[neighbors.flag == flagged]
        ax.scatter(subset.z_turnout, subset.z_share, s=7, alpha=0.35, color=color, label=label)
    for threshold in [-4, 4]:
        ax.axvline(threshold, ls="--", color=GRAY)
        ax.axhline(threshold, ls="--", color=GRAY)
    ax.set(xlabel=text("Turnout difference\nfrom local stations (score)", "Разлика в активността\nспрямо местните секции (оценка)"),
           ylabel=text("Yotova support difference (score)", "Разлика в подкрепата за Йотова (оценка)"))
    ax.legend(fontsize=8)
    save(fig, "outliers")

    anomalies = pd.read_csv(BASE / "analysis/ef_tur2/tables/ml_anomalies.csv")
    assert int(anomalies.is_anomaly.sum()) == metrics["ml_flagged"]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(anomalies.anomaly_score, bins=50, color=NAVY, alpha=0.8)
    ax.axvline(anomalies.loc[anomalies.is_anomaly, "anomaly_score"].min(), color=AMBER, ls="--",
               label=text("Chosen 1%: 107 stations", "Избран 1%: 107 секции"))
    ax.set(xlabel=text("How unusual the station looks (higher = more unusual)", "Колко необичайна изглежда секцията (повече = по-необичайна)"),
           ylabel=sections_label)
    ax.legend(fontsize=8)
    save(fig, "ml")

    previous = pd.read_csv(BASE / "data/ef_tur2/results_all_previous.csv")
    swing = pd.read_csv(BASE / "analysis/ef_tur2/tables/swing_vs_previous.csv")
    assert len(swing) == metrics["swing"]["n"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].hist(100 * previous.voted / previous.registered_voters, bins=np.arange(0, 101, 1),
                 histtype="step", color=GRAY, label=text("Round 1: checked stations", "Първи тур: проверявани секции"))
    axes[0].hist(turnout, bins=np.arange(0, 101, 1), histtype="step", color=NAVY,
                 label=text("Runoff: checked stations", "Балотаж: проверявани секции"))
    axes[0].set(xlabel=turnout_label, ylabel=sections_label)
    axes[0].legend(fontsize=7)
    axes[1].hist(swing.d_turnout, bins=np.arange(-101, 102, 2), color=NAVY, alpha=0.8)
    for threshold in [-15, 15]:
        axes[1].axvline(threshold, color=AMBER, ls="--")
    axes[1].set(xlabel=text("Turnout change at the same stations, points", "Промяна на активността в същите секции, п.п."),
                ylabel=sections_label, title=text("The same 10,581 stations in both rounds", "Същите 10 581 секции в двата тура"))
    save(fig, "control")

    result = metrics["selftest"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    labels = [text("Original", "Оригинал"), text("After adding votes", "След добавяне на гласове")]
    axes[0].bar(labels, [result["clean_tail_party"], result["injected_tail_party"]], color=[NAVY, AMBER])
    axes[0].set(ylabel=text("Yotova votes at high turnout", "Гласове за Йотова при висока активност"),
                title=text("Adding votes: count grows ×5.35", "Добавени гласове: сбор ×5,35"))
    axes[1].bar([text("Original", "Оригинал"), text("Rounded turnout", "Закръглена активност")],
                [result["peaks_z_clean"], result["peaks_z_rounded"]], color=[NAVY, AMBER])
    axes[1].axhline(0, color=GRAY)
    axes[1].set(ylabel=text("Round-number score", "Оценка за кръгли проценти"),
                title=text("A separate experiment: rounding turnout", "Отделен опит: закръгляне на активността"))
    save(fig, "selftest")


def bundle_downloads(report: Path) -> None:
    target = SITE / "downloads"
    target.mkdir(exist_ok=True)
    sources = {
        "forensics.md": report,
        "forensics.json": BASE / "analysis/ef_tur2/metrics.json",
        "sensitivity.json": BASE / "analysis/ef_tur2/sensitivity.json",
        "source-check.json": BASE / "data/official_20261102_tur2/summary.json",
        "eligibility.json": BASE / "data/ef_tur2/audit.json",
        "sections.csv": BASE / "data/ef_tur2/results_freguesias.csv",
        "exclusions.csv": BASE / "data/ef_tur2/exclusions.csv",
    }
    for name, source in sources.items():
        shutil.copyfile(source, target / name)
    with ZipFile(target / "forensics-outputs.zip", "w", ZIP_DEFLATED) as archive:
        for source in sorted((BASE / "analysis/ef_tur2").rglob("*")):
            if source.is_file():
                archive.write(source, source.relative_to(BASE / "analysis/ef_tur2"))


def main() -> None:
    bundle_downloads(BASE / "REPORT_statistical_fraud_analysis_round2.md")
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False})
    d = load_districts()
    for lang, text in LABELS.items():
        dec = "," if lang == "bg" else "."
        target = SITE / "img" / lang
        target.mkdir(parents=True, exist_ok=True)
        fig_mir(d, text, lang, dec, target)
        fig_swing(d, text, lang, dec, target)
        r = fig_turnout(d, text, lang, dec, target)
        details = SITE / "img/details" / lang
        details.mkdir(parents=True, exist_ok=True)
        fig_methods(lang, details)
        print(f"figures[{lang}] -> {target} (turnout-margin r={r:+.2f})")


if __name__ == "__main__":
    main()
