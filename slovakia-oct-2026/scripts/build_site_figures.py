"""Building the figures of the public page site/slovakia-oct-2026.

Section figures (img/{sk,en}/) are drawn from the MAI adaptation and the
paradox tables; the details figures (img/details/{lang}/...) are the
analysis-tool outputs copied under the two languages (the ef-analyze plots
are labelled in English — the same files serve both languages).

Run (from the repository root):
    analysis-tool/.venv/bin/python slovakia-oct-2026/scripts/build_site_figures.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]  # slovakia-oct-2026/
EF = BASE / "data" / "ef"
OFF = BASE / "data" / "official"
PX = BASE / "analysis" / "paradoxes"
ANA = BASE / "analysis" / "ef"
SITE = BASE.parent / "site" / "slovakia-oct-2026"

GREEN, NAVY, RED, GRAY, AMBER = "#1e8e5a", "#16324f", "#c0392b", "#9aa5b1", "#e6a817"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

L = {
    "en": {
        "turnout_xlabel": "mayor-race turnout (valid ballots / registered), %",
        "turnout_ylabel": "precincts",
        "turnout_title": "The shape of an honest count: 6,024 precincts",
        "y2026": "2026", "y2022": "2022 (control)",
        "blocs_t": "Joint candidacies vs the bloc's combined 2022 vote (governor races)",
        "blocs_22": "2022: the bloc's candidates combined",
        "blocs_26": "2026: the single joint candidate",
        "winners_t": "Mayors elected by a minority",
        "winners_xlabel": "winning mayor's share of valid votes, %",
        "winners_ylabel": "municipalities",
        "line50": "50%",
        "dual_xlabel": "participation in the governor race, %",
        "dual_ylabel": "participation in the mayor race, %",
        "dual_t": "Two ballots, one visit: 3,556 polling stations",
        "dual_note": "villages with the largest gaps: Jarovnice, Zlaté Klasy,\nBystrany, Jasov, Pavlovce nad Uhom, Lomnička…",
        "intraday_xlabel": "ballots counted, %",
        "intraday_ylabel": "candidate share of counted votes, %",
        "intraday_t": "Košický kraj, governor race — the count never flipped (final: Trnka 32.0%, Porvažník 30.7%)",
        "swing_t": "Mayor race: party shares of valid votes, 2022 → 2026 (national)",
        "swing_22": "2022", "swing_26": "2026",
    },
    "sk": {
        "turnout_xlabel": "účasť vo voľbách starostov (platné hlasy / zapísaní voliči), %",
        "turnout_ylabel": "počet okrskov",
        "turnout_title": "Tvar počtu bez zásahov: 6 024 okrskov",
        "y2026": "2026", "y2022": "2022 (kontrola)",
        "blocs_t": "Spoločná kandidácia 2026 vs. hlasy bloku spolu z roku 2022 (voľby predsedov)",
        "blocs_22": "2022: kandidáti bloku spolu",
        "blocs_26": "2026: jediný spoločný kandidát",
        "winners_t": "Starostovia zvolení menšinou hlasov",
        "winners_xlabel": "podiel zvoleného starostu na platných hlasoch, %",
        "winners_ylabel": "počet obcí",
        "line50": "50 %",
        "dual_xlabel": "účasť vo voľbách predsedu VÚC, %",
        "dual_ylabel": "účasť vo voľbách starostov, %",
        "dual_t": "Dve hlasy, jedna návšteva: 3 556 okrskov",
        "dual_note": "obce s najväčším rozdielom: Jarovnice, Zlaté Klasy,\nBystrany, Jasov, Pavlovce nad Uhom, Lomnička…",
        "intraday_xlabel": "prepočítané hlasovacie lístky, %",
        "intraday_ylabel": "podiel kandidáta na prepočítaných hlasoch, %",
        "intraday_t": "Košický kraj, predseda — vedenie sa počas sčítania nezmenilo (Trnka 32,0 %, Porvažník 30,7 %)",
        "swing_t": "Voľby starostov: podiely strán na platných hlasoch, 2022 → 2026 (SR)",
        "swing_22": "2022", "swing_26": "2026",
    },
}

KRAJ_SK = {1: "Bratislavský", 2: "Trnavský", 3: "Trenčiansky", 4: "Nitriansky",
           5: "Žilinský", 6: "Banskobystrický", 7: "Prešovský", 8: "Košický"}


def turnout_hist(lang: str) -> None:
    cur = pd.read_csv(EF / "oso2026" / "results_freguesias.csv")
    prv = pd.read_csv(EF / "oso2022" / "results_freguesias.csv")
    t26 = 100 * cur["voted"] / cur["registered_voters"]
    t22 = 100 * prv["voted"] / prv["registered_voters"]
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    bins = np.arange(0, 105, 2.5)
    ax.hist(t22.clip(0, 100), bins=bins, color=GRAY, alpha=0.55, label=L[lang]["y2022"])
    ax.hist(t26.clip(0, 100), bins=bins, color=GREEN, alpha=0.62, label=L[lang]["y2026"])
    ax.set_xlabel(L[lang]["turnout_xlabel"])
    ax.set_ylabel(L[lang]["turnout_ylabel"])
    ax.set_title(L[lang]["turnout_title"], fontsize=11)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(SITE / "img" / lang / "turnout.png", dpi=150)
    plt.close(fig)


def blocs(lang: str) -> None:
    df = pd.read_csv(PX / "tables" / "bloc_consolidation.csv")
    df = df.sort_values(["kraj", "bloc"], ascending=[True, False]).reset_index(drop=True)
    labels = [f"{KRAJ_SK[int(r.kraj)]}: {'vládna' if 'vládny' in r.bloc else 'opozičná'} koalícia"
              for r in df.itertuples()]
    labels_en = [f"{'govt' if 'vládny' in r.bloc else 'opposition'} bloc, {KRAJ_SK[int(r.kraj)]}"
                 for r in df.itertuples()]
    y = np.arange(len(df))[::-1]
    fig, ax = plt.subplots(figsize=(8.6, 6.4))
    ax.barh(y + 0.19, df["votes_2022_combined"], height=0.36, color=GRAY, label=L[lang]["blocs_22"])
    ax.barh(y - 0.19, df["votes_2026_joint"], height=0.36, color=GREEN, label=L[lang]["blocs_26"])
    for yy, r in zip(y, df.itertuples()):
        if r.votes_2022_combined > 0:
            ax.text(r.votes_2022_combined + 2500, yy + 0.19, f"{r.votes_2022_combined // 1000}k",
                    va="center", fontsize=7.5, color="#555")
        ax.text(r.votes_2026_joint + 2500, yy - 0.19,
                f"{r.joint_2026.split()[0]} {r.votes_2026_joint // 1000}k",
                va="center", fontsize=7.5, color=GREEN)
    ax.set_yticks(y)
    ax.set_yticklabels(labels if lang == "sk" else labels_en, fontsize=8.5)
    ax.set_xlabel("votes")
    ax.set_title(L[lang]["blocs_t"], fontsize=11)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    ax.set_xlim(0, 230000)
    fig.tight_layout()
    fig.savefig(SITE / "img" / lang / "blocs.png", dpi=150)
    plt.close(fig)


def winners(lang: str) -> None:
    win26 = pd.read_csv(PX / "tables" / "mayor_winners_2026.csv")
    f22 = pd.read_csv(OFF / "OSO2022_SK_tab05f.csv", sep="|")
    agg = f22.groupby(["OBEC", "PC_HL"])["P_HL"].sum().reset_index()
    agg["share"] = 100 * agg["P_HL"] / agg.groupby("OBEC")["P_HL"].transform("sum")
    win22 = agg.loc[agg.groupby("OBEC")["P_HL"].idxmax()]
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    bins = np.arange(20, 105, 5)
    ax.hist(win22["share"].clip(20, 100), bins=bins, color=GRAY, alpha=0.55, label=L[lang]["y2022"])
    ax.hist(win26["share"].clip(20, 100), bins=bins, color=GREEN, alpha=0.62, label=L[lang]["y2026"])
    ax.axvline(50, color=RED, lw=1.4, ls="--")
    ax.text(50.4, ax.get_ylim()[1] * 0.92, L[lang]["line50"], color=RED, fontsize=9)
    ax.set_xlabel(L[lang]["winners_xlabel"])
    ax.set_ylabel(L[lang]["winners_ylabel"])
    ax.set_title(L[lang]["winners_t"], fontsize=11)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(SITE / "img" / lang / "winners.png", dpi=150)
    plt.close(fig)


def dual(lang: str) -> None:
    m = pd.read_csv(PX / "tables" / "dual_ballot_join.csv")
    t_k = 100 * m["P_ZUC_K"] / m["P_ZAP_K"]
    t_o = 100 * m["P_ZUC_O"] / m["P_ZAP_O"]
    big = m["d"].abs() > 300
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    ax.scatter(t_k[~big], t_o[~big], s=3, alpha=0.25, color=NAVY, edgecolors="none", label="okrsky")
    ax.scatter(t_k[big], t_o[big], s=9, alpha=0.85, color=RED, edgecolors="none",
               label="|Δ| > 300 voličov")
    ax.plot([0, 100], [0, 100], color=GRAY, lw=1, ls="--")
    ax.annotate(L[lang]["dual_note"], xy=(0.03, 0.97), xycoords="axes fraction",
                va="top", fontsize=8, color=RED)
    ax.set_xlabel(L[lang]["dual_xlabel"])
    ax.set_ylabel(L[lang]["dual_ylabel"])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_title(L[lang]["dual_t"], fontsize=11)
    ax.legend(frameon=False, loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(SITE / "img" / lang / "dual.png", dpi=150)
    plt.close(fig)


def intraday(lang: str) -> None:
    res = pd.read_csv(BASE / "data/trends/results.csv", parse_dates=["fetch_ts_utc"])
    nat = pd.read_csv(BASE / "data/trends/national.csv", parse_dates=["fetch_ts_utc"])
    k8 = res[(res["area_code"] == 8) & res["race"].str.startswith("regional")].copy()
    prog = nat[nat["race"] == "regional (OSK)"][["fetch_ts_utc", "pct_counted"]]
    k8 = k8.merge(prog, on="fetch_ts_utc", how="left").sort_values(["candidate", "fetch_ts_utc"])
    assert k8["pct_counted"].notna().all()
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    for cand, g in k8.groupby("candidate"):
        g = g.sort_values("fetch_ts_utc")
        short = g["candidate"].iloc[0].split()[-1]
        winner = g["pct"].iloc[-1] == k8.groupby("candidate")["pct"].last().max()
        ax.plot(g["pct_counted"], g["pct"],
                lw=2.6 if winner else (1.4 if g["pct"].iloc[-1] > 20 else 0.9),
                color=GREEN if winner else (NAVY if g["pct"].iloc[-1] > 20 else GRAY))
        ax.text(g["pct_counted"].iloc[-1] + 0.6, g["pct"].iloc[-1], short,
                fontsize=8, va="center",
                color=GREEN if winner else (NAVY if g["pct"].iloc[-1] > 20 else "#777"))
    ax.set_xlabel(L[lang]["intraday_xlabel"])
    ax.set_ylabel(L[lang]["intraday_ylabel"])
    ax.set_title(L[lang]["intraday_t"], fontsize=10.5)
    ax.set_xlim(30, 108)
    fig.tight_layout()
    fig.savefig(SITE / "img" / lang / "intraday.png", dpi=150)
    plt.close(fig)


def swing(lang: str) -> None:
    cur = pd.read_csv(EF / "oso2026" / "results_freguesias.csv")
    prv = pd.read_csv(EF / "oso2026" / "results_all_previous.csv")
    cols = [c for c in cur.columns if c.startswith("votes:")]
    s26 = cur[cols].sum()
    s22 = prv[[c for c in cols if c in prv.columns]].sum().reindex(cols, fill_value=0)
    alias = {"Hlas - sociálna demokracia": "HLAS - sociálna demokracia",
             "SOM Slovensko": "SOM SLOVENSKO", "NK/NEKA": "NEKA",
             "SZÖVETSÉG - ALIANCIA": "Magyar Szövetség - Maďarská aliancia"}
    for a, b in alias.items():
        s22[f"votes:{b}"] = s22.get(f"votes:{b}", 0) + s22.get(f"votes:{a}", 0)
        s22 = s22.drop(f"votes:{a}", errors="ignore")
    sh26 = 100 * s26 / cur["voted"].sum()
    sh22 = 100 * s22 / prv["voted"].sum()
    top = sh26.sort_values(ascending=False).head(12)[::-1]
    names = [c.removeprefix("votes:") for c in top.index]
    names = [n if n != "Magyar Szövetség - Maďarská aliancia" else "Magyar Szövetség" for n in names]
    y = np.arange(len(top))
    fig, ax = plt.subplots(figsize=(8.6, 5.6))
    ax.barh(y + 0.19, sh22[top.index], height=0.36, color=GRAY, label=L[lang]["swing_22"])
    ax.barh(y - 0.19, sh26[top.index], height=0.36, color=GREEN, label=L[lang]["swing_26"])
    for yy, a, b in zip(y, sh22[top.index], sh26[top.index]):
        ax.text(a + 0.35, yy + 0.19, f"{a:.1f}", va="center", fontsize=7.5, color="#555")
        ax.text(b + 0.35, yy - 0.19, f"{b:.1f}", va="center", fontsize=7.5, color=GREEN)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=8.5)
    ax.set_xlabel("% of valid votes")
    ax.set_title(L[lang]["swing_t"], fontsize=11)
    ax.legend(frameon=False, loc="lower right")
    ax.set_xlim(0, 70)
    fig.tight_layout()
    fig.savefig(SITE / "img" / lang / "swing.png", dpi=150)
    plt.close(fig)


DETAILS = {
    "kosicky": ANA / "osk2026_k8" / "figures",
    "mayors": ANA / "oso2026" / "figures",
}
DETAIL_FILES = {
    "kosicky": ["shpilkin_core", "comet_scatter", "fingerprint_2d", "integer_peaks",
                "controls_turnout", "selftest"],
    "mayors": ["shpilkin_core", "digit_last", "neighbors_outliers", "ml_anomalies",
               "swing_previous", "selftest"],
}


def details() -> None:
    for race, src in DETAILS.items():
        for lang in ("en", "sk"):
            dst = SITE / "img" / "details" / lang / race
            dst.mkdir(parents=True, exist_ok=True)
            for name in DETAIL_FILES[race]:
                shutil.copy(src / f"{name}.png", dst / f"{name}.png")


def main() -> None:
    for lang in ("en", "sk"):
        (SITE / "img" / lang).mkdir(parents=True, exist_ok=True)
        turnout_hist(lang)
        blocs(lang)
        winners(lang)
        dual(lang)
        intraday(lang)
        swing(lang)
    details()
    print(f"done: {SITE}/img/")


if __name__ == "__main__":
    main()
