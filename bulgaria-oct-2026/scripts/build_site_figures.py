"""Rebuild the Bulgarian/English public-page figures from the night capture.

Reads the same normalized capture as analyze_trends.py (data/trends/) and
draws the six count-night charts once per page language into
site/bulgaria-oct-2026/img/{en,bg}/. District (MIR) names keep their official
Cyrillic form on the Bulgarian charts and use a fixed transliteration on the
English ones; dynamic numbers switch to the Bulgarian decimal comma.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
SITE = BASE.parent / "site/bulgaria-oct-2026"

NAVY, AMBER, RED, GREEN, PURPLE, GRAY = ("#16324f", "#e6a817", "#c0392b",
                                         "#1e8e5a", "#7d5ba6", "#9aa5b1")

CANDS: dict[str, dict[str, str]] = {
    "en": {"25": "Yotova", "4": "Gyurov",
           "11": "Kostadinov — Vazrazhdane", "17": "Vasilev — MECH",
           "19": "Mihaylov — Velichie"},
    "bg": {"25": "Йотова", "4": "Гюров",
           "11": "Костадинов — Възраждане", "17": "Василев — МЕЧ",
           "19": "Михайлов — Величие"},
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
ABROAD_CODE = 32
SOFTIA = {23, 24, 25}
NOSUPPORT = "-"
RUNOFF_LINE = 50.0
REGISTER = 6_637_238

ZONE = dt.timezone(dt.timedelta(hours=2))  # fixed EET for chart readability

LABELS: dict[str, dict[str, str]] = {
    "en": {
        "pace_title": "Bulgaria, president 25.10.2026 — pace of the count (CIK intraday)",
        "sik_pct": "СИК protocols processed, %",
        "paused": "portal unchanged at 95.29%\n(07:05–08:02)",
        "votes_title": "listed votes counted, millions",
        "votes_note": "1.51 M listed votes at 98.99% processed",
        "turnout_title": "official intraday turnout",
        "night_xlabel": "election night, local time (EET, fixed UTC+2)",
        "shares_title": "Vote shares through the count: no lead change —\n"
                        "Yotova vs Gyurov goes to the 1 November runoff",
        "shares_ylabel": "CIK displayed share of listed votes, %",
        "nosup": "“Do not support anyone”",
        "others": "remaining 22 pairs",
        "majority": "absolute majority — not reached by anyone",
        "margin_title": "Yotova − Gyurov margin through the count:\n"
                        "narrowed from 5.2 to 2.7 pp, one bounce at ~48% processed",
        "pp_ylabel": "Yotova − Gyurov, percentage points",
        "bounce": "bounce at 03:07:\nmargin widens by 1.6 pp",
        "mir_title": "Where each runner-up votes: final margin by MIR",
        "mir_xlabel": "final Yotova − Gyurov margin, pp",
        "mir_leg_y": "Yotova leads (27 of 31 domestic MIRs)",
        "mir_leg_g": "Gyurov leads (3 Sofia MIRs, Plovdiv-city, abroad)",
        "mir_abroad": "  (abroad aggregate)",
        "swing_title": "Count-night swing by MIR (first → last snapshot)",
        "swing_first": "first snapshot ({t} EET)",
        "swing_to_y": "latest capture: margin moved toward Yotova",
        "swing_to_g": "latest capture: margin moved toward Gyurov",
        "swing_abroad": "  (abroad)",
        "tu_t1": "16:00 turnout by MIR: Kardzhali 6.8% → Sofia-23 25.9%",
        "tu_xlabel": "official turnout at 16:00 EET, %",
        "tu_country": "country {v}%",
        "tu_ylabel": "final Yotova − Gyurov margin, pp",
        "tu_t2": "High-turnout districts lean toward Gyurov (r = {r}, 31 MIRs)",
        "tu_suptitle": "Turnout geography vs the runoff pair",
    },
    "bg": {
        "pace_title": "България, президент 25.10.2026 — темп на броенето (ЦИК, вътрешнодневни данни)",
        "sik_pct": "Обработени протоколи на СИК, %",
        "paused": "порталът остава на 95,29%\n(07:05–08:02)",
        "votes_title": "изброени гласове, милиони",
        "votes_note": "1,51 млн гласа при 98,99% обработени",
        "turnout_title": "официална вътрешнодневна активност",
        "night_xlabel": "изборна нощ, местно време (EET, фиксирано UTC+2)",
        "shares_title": "Дялове през нощта: без смяна на водещия —\n"
                        "Йотова срещу Гюров на балотаж на 1 ноември",
        "shares_ylabel": "Показан от ЦИК дял от гласувалите по списъците, %",
        "nosup": "„Не подкрепям никого“",
        "others": "останалите 22 двойки",
        "majority": "абсолютно мнозинство — никой не го достига",
        "margin_title": "Разлика Йотова − Гюров през броенето:\n"
                        "от 5,2 на 2,7 п.п., един скок при ~48% обработени",
        "pp_ylabel": "Йотова − Гюров, процентни пункта",
        "bounce": "скок в 03:07 ч.:\nмаржът се разширява с 1,6 п.п.",
        "mir_title": "Краен марж Йотова − Гюров по МИР",
        "mir_xlabel": "краен марж Йотова − Гюров, п.п.",
        "mir_leg_y": "Йотова води (27 от 31 вътрешен МИР)",
        "mir_leg_g": "Гюров води (3 софийски МИР, Пловдив град, чужбина)",
        "mir_abroad": "  (чужбина, обобщено)",
        "swing_title": "Промяна на маржа през нощта по МИР (първи → последен пресек)",
        "swing_first": "първи пресек ({t} ч. EET)",
        "swing_to_y": "последно измерване: маржът тръгва към Йотова",
        "swing_to_g": "последно измерване: маржът тръгва към Гюров",
        "swing_abroad": "  (чужбина)",
        "tu_t1": "Активност в 16:00 по МИР: Кърджали 6,8% → София 23 25,9%",
        "tu_xlabel": "официална активност в 16:00 EET, %",
        "tu_country": "страната {v}%",
        "tu_ylabel": "краен марж Йотова − Гюров, п.п.",
        "tu_t2": "Районите с по-висока активност клонят към Гюров (r = {r}, 31 МИР)",
        "tu_suptitle": "География на активността и двойката за балотаж",
    },
}


def to_local(ts: pd.Timestamp) -> pd.Timestamp:
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.tz_convert(ZONE).tz_localize(None)


def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    trends = BASE / "data" / "trends"
    nat = pd.read_csv(trends / "national.csv")
    nat["fetch_ts"] = pd.to_datetime(nat.fetch_ts_utc, utc=True)
    res = pd.read_csv(trends / "results.csv")
    res["candidate_id"] = res.candidate_id.astype(str)
    res["area_code_int"] = res.area_code.astype(int)
    res["fetch_ts"] = pd.to_datetime(res.fetch_ts_utc, utc=True)
    tu = pd.read_csv(trends / "intraday_turnout.csv")
    tu["area_code_int"] = tu.area_code.astype(int)
    return nat, res, tu


def _xaxis(ax, text: dict[str, str]) -> None:
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.set_xlabel(text["night_xlabel"])


def fig_pace(nat: pd.DataFrame, res: pd.DataFrame, tu: pd.DataFrame,
             text: dict[str, str], dec: str, target: Path) -> None:
    t = [to_local(x) for x in nat.fetch_ts]
    votes = (res[res.area_level == "country"]
             .groupby("fetch_ts").votes.sum().reindex(nat.fetch_ts))
    off = (tu[(tu.area_level == "country") & (tu.source.str.startswith("http"))]
           .drop_duplicates("as_of_local").sort_values("as_of_local"))
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.4))
    ax = axes[0]
    ax.plot(t, nat.pct_counted, color=NAVY, marker="o", ms=3.5, lw=1.6)
    ax.set_title(text["sik_pct"])
    ax.set_ylim(0, 103)
    i0, i1 = nat.pct_counted.eq(95.29).to_numpy().nonzero()[0][[0, -1]]
    ax.annotate(text["paused"], xy=(t[i1], 95.29), xytext=(10, -62),
                textcoords="offset points", fontsize=8.5, color="0.35",
                arrowprops=dict(arrowstyle="->", color="0.5"))
    ax = axes[1]
    ax.plot(t, votes / 1e6, color=AMBER, marker="o", ms=3.5, lw=1.6)
    ax.set_title(text["votes_title"])
    ax.annotate(text["votes_note"], xy=(t[-1], votes.iloc[-1] / 1e6),
                xytext=(-130, -8), textcoords="offset points", fontsize=8.5,
                color="0.35")
    ax = axes[2]
    xs = list(range(len(off)))
    bars = ax.bar(xs, off.turnout_pct, width=0.5, color=GREEN, alpha=0.85)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{s} EET" for s in off.as_of_local])
    for b, v in zip(bars, off.turnout_pct):
        ax.annotate(f"{v:.2f}%".replace(".", dec), xy=(b.get_x() + b.get_width() / 2, v),
                    xytext=(0, 3), textcoords="offset points", ha="center", fontsize=9)
    ax.set_title(text["turnout_title"])
    ax.set_ylim(0, 19)
    for ax in axes:
        ax.grid(alpha=0.25)
    _xaxis(axes[0], text)
    _xaxis(axes[1], text)
    fig.suptitle(text["pace_title"], y=1.02)
    fig.tight_layout()
    fig.savefig(target / "pace.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_shares(res: pd.DataFrame, text: dict[str, str], cands: dict[str, str],
               dec: str, target: Path) -> None:
    c = res[res.area_level == "country"]
    piv = c.pivot_table(index="fetch_ts", columns="candidate_id", values="pct",
                        aggfunc="first")
    t = [to_local(x) for x in piv.index]
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    for cid, label in cands.items():
        lw = 2.2 if cid in ("25", "4") else 1.3
        ax.plot(t, piv[cid], lw=lw, marker="o", ms=3.5, label=label,
                color={"25": NAVY, "4": AMBER, "11": RED, "17": GREEN,
                       "19": PURPLE}[cid])
    ax.plot(t, piv[NOSUPPORT], color=GRAY, lw=1.2, ls="--", label=text["nosup"])
    others = piv.drop(columns=[*cands, NOSUPPORT]).sum(axis=1)
    ax.plot(t, others, color="0.7", lw=1.0, ls=":", label=text["others"])
    ax.axhline(RUNOFF_LINE, color="0.4", lw=0.8, ls="-.")
    ax.annotate(text["majority"], xy=(t[1], RUNOFF_LINE), xytext=(0, 4),
                textcoords="offset points", fontsize=8.5, color="0.35")
    last = piv.index.max()
    for cid, color in [("25", NAVY), ("4", AMBER), ("11", RED)]:
        ax.annotate(f"{piv.loc[last, cid]:.1f}%".replace(".", dec),
                    xy=(t[-1], piv.loc[last, cid]), xytext=(5, 0),
                    textcoords="offset points", color=color, fontweight="bold")
    ax.set_ylabel(text["shares_ylabel"])
    ax.set_ylim(0, 57)
    ax.set_xlim(t[0], t[-1] + pd.Timedelta(hours=1.2))
    ax.grid(alpha=0.25)
    leg = ax.legend(loc="center left", bbox_to_anchor=(0.03, 0.52), frameon=True,
                    fontsize=9)
    leg.get_frame().set_facecolor("white")
    leg.get_frame().set_edgecolor("none")
    leg.get_frame().set_alpha(0.88)
    ax.set_title(text["shares_title"])
    _xaxis(ax, text)
    fig.tight_layout()
    fig.savefig(target / "shares.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_margin(res: pd.DataFrame, nat: pd.DataFrame, text: dict[str, str],
               dec: str, target: Path) -> None:
    c = res[res.area_level == "country"]
    piv = c.pivot_table(index="fetch_ts", columns="candidate_id", values="pct",
                        aggfunc="first")
    margin = (piv["25"] - piv["4"]).dropna()
    counted = nat.set_index("fetch_ts").pct_counted
    counted.index = pd.to_datetime(counted.index, utc=True)
    m = pd.concat([margin, counted.reindex(margin.index)], axis=1)
    m.columns = ["margin", "counted"]
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    ax.plot(m.counted, m.margin, color=NAVY, marker="o", ms=4, lw=1.8)
    for ts, row in m.iterrows():
        if row.name == m.index[-1]:
            off = (0, 10)
        elif row.name == m.index[-2]:
            off = (-6, -14)
        elif row.name == m.index[3]:
            off = (10, 10)
        else:
            off = (0, 8)
        ax.annotate(f"{to_local(ts):%H:%M}", xy=(row.counted, row.margin),
                    xytext=off, textcoords="offset points", fontsize=7.5,
                    ha="center", color="0.35")
    ax.annotate(text["bounce"], xy=(m.counted.iloc[3], m.margin.iloc[3]),
                xytext=(26, 8), textcoords="offset points", fontsize=8.5,
                color=NAVY, arrowprops=dict(arrowstyle="->", color="0.5"))
    ax.set_xlabel(text["sik_pct"])
    ax.set_ylabel(text["pp_ylabel"])
    ax.set_ylim(0, 7)
    ax.grid(alpha=0.25)
    ax.set_title(text["margin_title"])
    fig.tight_layout()
    fig.savefig(target / "margin.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def _mir_name(code: int, names: pd.Series, lang: str) -> str:
    return str(names[code]) if lang == "bg" else MIR_EN[int(code)]


def fig_mir(res: pd.DataFrame, text: dict[str, str], lang: str, dec: str,
            target: Path) -> None:
    mir = res[res.area_level == "mir"]
    last = mir[mir.fetch_ts == mir.fetch_ts.max()]
    pv = last.pivot_table(index="area_code_int", columns="candidate_id",
                          values="pct", aggfunc="first")
    names = last.drop_duplicates("area_code_int").set_index("area_code_int").area_name
    d = pd.DataFrame({"margin": pv["25"] - pv["4"]}).sort_values("margin")
    fig, ax = plt.subplots(figsize=(8.6, 8.6))
    y = range(len(d))
    ax.barh(list(y), d.margin, color=[NAVY if v >= 0 else AMBER for v in d.margin],
            alpha=0.88, height=0.66)
    ax.set_yticks(list(y))
    labels = [f"{c:>2} {_mir_name(c, names, lang)}" for c in d.index]
    if lang == "bg":  # the English transliteration already says "abroad"
        labels[d.index.get_loc(ABROAD_CODE)] += text["mir_abroad"]
    ax.set_yticklabels(labels, fontsize=8.5)
    for i, v in enumerate(d.margin):
        ax.annotate(f"{v:+.1f}".replace(".", dec), xy=(v, i),
                    xytext=(4 if v >= 0 else -4, 0), textcoords="offset points",
                    va="center", ha="left" if v >= 0 else "right", fontsize=7.5,
                    color="0.3")
    ax.axvline(0, color="0.6", lw=0.8)
    ax.set_xlabel(text["mir_xlabel"])
    ax.set_xlim(-38, 32)
    ax.grid(alpha=0.25, axis="x")
    ax.scatter([], [], color=NAVY, s=30, label=text["mir_leg_y"])
    ax.scatter([], [], color=AMBER, s=30, label=text["mir_leg_g"])
    ax.legend(loc="upper left", frameon=False, fontsize=8.5)
    ax.set_title(text["mir_title"])
    fig.tight_layout()
    fig.savefig(target / "mir.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_swing(res: pd.DataFrame, text: dict[str, str], lang: str, target: Path) -> None:
    mir = res[res.area_level == "mir"]
    first_ts, last_ts = mir.fetch_ts.min(), mir.fetch_ts.max()
    rows = []
    for code, sub in mir.groupby("area_code_int"):
        for ts, tag in [(first_ts, "first"), (last_ts, "final")]:
            s = sub[sub.fetch_ts == ts].set_index("candidate_id").pct
            if s.dropna().empty:  # the abroad aggregate is empty in snapshot 1
                continue
            rows.append({"code": code, "tag": tag, "margin": s["25"] - s["4"]})
    d = pd.DataFrame(rows).pivot(index="code", columns="tag", values="margin").dropna()
    d["name"] = (mir[mir.fetch_ts == last_ts].drop_duplicates("area_code_int")
                 .set_index("area_code_int").area_name)
    d = d.sort_values("final")
    fig, ax = plt.subplots(figsize=(8.4, 8.4))
    ax.axvline(0, color="0.6", lw=0.8)
    for i, (code, row) in enumerate(d.iterrows()):
        color = NAVY if row.final - row.first > 0 else AMBER
        ax.plot([row.first, row.final], [i, i], color="0.78", lw=1.4, zorder=1)
        ax.scatter([row.first], [i], color="0.45", s=26, zorder=2)
        ax.scatter([row.final], [i], color=color, s=40, zorder=3)
    ax.set_yticks(list(range(len(d))))
    labels = [f"{c:>2} {_mir_name(c, d.name, lang)}" for c in d.index]
    if lang == "bg":  # the English transliteration already says "abroad"
        labels[d.index.get_loc(ABROAD_CODE)] += text["swing_abroad"]
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.set_xlabel(text["mir_xlabel"])
    ax.scatter([], [], color="0.45", s=26,
               label=text["swing_first"].format(t=f"{to_local(first_ts):%H:%M}"))
    ax.scatter([], [], color=NAVY, s=40, label=text["swing_to_y"])
    ax.scatter([], [], color=AMBER, s=40, label=text["swing_to_g"])
    ax.legend(loc="lower right", frameon=False, fontsize=8.5)
    ax.grid(alpha=0.25, axis="x")
    ax.set_title(text["swing_title"])
    fig.tight_layout()
    fig.savefig(target / "swing.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_turnout(tu: pd.DataFrame, res: pd.DataFrame, text: dict[str, str],
                lang: str, dec: str, target: Path) -> None:
    off = (tu[(tu.area_level == "mir") & (tu.source == "mapData")
              & (tu.as_of_local.astype(str) == "16:00")]
           .drop_duplicates("area_code_int"))
    mir = res[res.area_level == "mir"]
    last = mir[mir.fetch_ts == mir.fetch_ts.max()]
    pv = last.pivot_table(index="area_code_int", columns="candidate_id",
                          values="pct", aggfunc="first")
    names = last.drop_duplicates("area_code_int").set_index("area_code_int").area_name
    d = pd.DataFrame({"margin": pv["25"] - pv["4"],
                      "turnout": off.set_index("area_code_int").turnout_pct}).dropna()
    d = d[d.index != ABROAD_CODE]
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), width_ratios=[1.15, 1])
    ax = axes[0]
    dd = d.sort_values("turnout")
    ax.barh(list(range(len(dd))), dd.turnout, color=GREEN, alpha=0.8, height=0.66)
    ax.set_yticks(list(range(len(dd))))
    ax.set_yticklabels([f"{c:>2} {_mir_name(c, names, lang)}" for c in dd.index],
                       fontsize=8)
    for i, v in enumerate(dd.turnout):
        ax.annotate(f"{v:.1f}".replace(".", dec), xy=(v, i), xytext=(3, 0),
                    textcoords="offset points", va="center", fontsize=7, color="0.3")
    country = float(tu[(tu.area_level == "country")
                       & (tu.as_of_local.astype(str) == "16:00")].turnout_pct.iloc[0])
    ax.axvline(country, color=RED, lw=1.1, ls="--")
    ax.annotate(text["tu_country"].format(v=f"{country:.2f}".replace(".", dec)),
                xy=(country, 0.8), xytext=(4, 0), textcoords="offset points",
                fontsize=8.5, color=RED)
    ax.set_xlabel(text["tu_xlabel"])
    ax.set_xlim(0, 29)
    ax.grid(alpha=0.25, axis="x")
    ax.set_title(text["tu_t1"])
    ax = axes[1]
    ax.scatter(d.turnout, d.margin, s=34, color=NAVY, alpha=0.75)
    r = float(np.corrcoef(d.turnout, d.margin)[0, 1])
    for code, row in d.iterrows():
        if code in SOFTIA or code in (9, 16, 3):
            ax.annotate(f"{row.name}", xy=(row.turnout, row.margin), xytext=(4, 3),
                        textcoords="offset points", fontsize=7.5, color="0.35")
    ax.axhline(0, color="0.6", lw=0.8)
    ax.set_xlabel(text["tu_xlabel"])
    ax.set_ylabel(text["tu_ylabel"])
    ax.grid(alpha=0.25)
    ax.set_title(text["tu_t2"].format(r=f"{r:+.2f}".replace(".", "," if dec == "," else ".")))
    fig.suptitle(text["tu_suptitle"], y=1.0)
    fig.tight_layout()
    fig.savefig(target / "turnout.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def build_figures(lang: str) -> None:
    text = LABELS[lang]
    dec = "," if lang == "bg" else "."
    target = SITE / "img" / lang
    target.mkdir(parents=True, exist_ok=True)
    nat, res, tu = load()
    assert len(nat) == 10

    fig_pace(nat, res, tu, text, dec, target)
    fig_shares(res, text, CANDS[lang], dec, target)
    fig_margin(res, nat, text, dec, target)
    fig_mir(res, text, lang, dec, target)
    fig_swing(res, text, lang, target)
    fig_turnout(tu, res, text, lang, dec, target)

    # the quoted numbers must match the metrics the page cites
    metrics = json.loads((BASE / "analysis" / "trends" / "metrics.json").read_text())
    last = res[res.area_level == "country"].fetch_ts.max()
    end = res[(res.area_level == "country") & (res.fetch_ts == last)].set_index("candidate_id").pct
    assert abs(end["25"] - metrics["shares_final_pct"]["25"]) < 1e-9
    assert abs(end["4"] - metrics["shares_final_pct"]["4"]) < 1e-9


def fig_forensics(lang: str) -> None:
    frame = pd.read_csv(BASE / "data/ef/results_freguesias.csv")
    metrics = json.loads((BASE / "analysis/ef/metrics.json").read_text())
    turnout = 100 * frame.voted / frame.registered_voters
    share = 100 * frame["votes:Yotova"] / frame.voted
    cutoff = metrics["shpilkin"]["t_cut"]
    edges = np.arange(0, 100.5, 0.5)
    centers = (edges[:-1] + edges[1:]) / 2
    leader, _ = np.histogram(turnout, bins=edges, weights=frame["votes:Yotova"])
    rest, _ = np.histogram(turnout, bins=edges, weights=frame.voted - frame["votes:Yotova"])
    bg = lang == "bg"
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.3))
    ax = axes[0]
    ax.plot(centers, leader, color=NAVY, label="Йотова" if bg else "Yotova")
    ax.plot(centers, rest, color=GRAY, label="Всички други бюлетини" if bg else "All other ballots")
    ax.axvspan(cutoff, 100, color=AMBER, alpha=0.18)
    ax.axvline(cutoff, color=AMBER, ls="--", label="Праг 50,48%" if bg else "Cutoff 50.48%")
    ax.set_ylabel("Гласове в интервали от 0,5 п.п." if bg else "Votes per 0.5-point turnout bin")
    ax.set_title("Опашката не е оценка на измама" if bg else "Tail mass is not a fraud estimate")
    ax.legend(frameon=False, fontsize=8)
    ax = axes[1]
    ax.scatter(turnout, share, s=4, alpha=0.15, color=NAVY, rasterized=True)
    ax.set_ylabel("Йотова, % от гласувалите" if bg else "Yotova, % of ballots cast")
    ax.set_title("Активност × дял: претеглено r = −0,140" if bg else "Turnout × share: weighted r = −0.140")
    for ax in axes:
        ax.set_xlabel("Секционна активност, %" if bg else "Section turnout, %")
        ax.set_xlim(0, 101)
        ax.grid(alpha=0.2)
    fig.suptitle("10 616 вътрешни секции · без историческа контрола" if bg else
                 "10,616 domestic sections · no historical control")
    fig.tight_layout()
    fig.savefig(SITE / "img" / lang / "forensics.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def bundle_downloads() -> None:
    target = SITE / "downloads"
    target.mkdir(exist_ok=True)
    sources = {
        "trends.md": BASE / "analysis/trends/README.md",
        "metrics.json": BASE / "analysis/trends/metrics.json",
        "forensics.md": BASE / "REPORT_statistical_fraud_analysis.md",
        "forensics.json": BASE / "analysis/ef/metrics.json",
        "sensitivity.json": BASE / "analysis/ef/sensitivity.json",
        "source-check.json": BASE / "data/official_20261027/summary.json",
        "eligibility.json": BASE / "data/ef/audit.json",
        "sections.csv": BASE / "data/ef/results_freguesias.csv",
        "exclusions.csv": BASE / "data/ef/exclusions.csv",
    }
    for name, source in sources.items():
        shutil.copyfile(source, target / name)
    with ZipFile(target / "forensics-outputs.zip", "w", ZIP_DEFLATED) as archive:
        for source in sorted((BASE / "analysis/ef").rglob("*")):
            if source.is_file():
                archive.write(source, source.relative_to(BASE / "analysis/ef"))


def main() -> None:
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False})
    for lang in LABELS:
        build_figures(lang)
        fig_forensics(lang)
        print(f"figures[{lang}] -> {SITE / 'img' / lang}")
    bundle_downloads()


if __name__ == "__main__":
    main()
