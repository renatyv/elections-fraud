# -*- coding: utf-8 -*-
"""
Trend analysis of the intraday capture of the Bulgarian presidential election
of 25.10.2026, round 1 (results.cik.bg/pvr202610).

Sources (normalized night captures, see data/trends/README.md):
  data/trends/national.csv          — 10 hourly snapshots, 22:07 UTC 25.10 →
                                      07:03 UTC 26.10; only the "обработени X%"
                                      СИК-protocol progress line is populated;
  data/trends/results.csv           — fetch × area (country / 31 MIR + the
                                      abroad aggregate MIR 32) × candidate
                                      pair, votes + displayed %;
  data/trends/intraday_turnout.csv  — official intraday turnout reports
                                      (11:00 and 16:00 EET), country row +
                                      31 MIR rows from the portal's mapData.

Outputs:
  analysis/trends/charts/0*.png  — count-night dynamics figures
  analysis/trends/metrics.json   — key numbers quoted in the reports

Run:
  analysis-tool/.venv/bin/python bulgaria-oct-2026/scripts/analyze_trends.py
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
TRENDS = BASE / "data" / "trends"
OUT = BASE / "analysis" / "trends" / "charts"

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

NAVY, AMBER, RED, GREEN, PURPLE, GRAY = ("#16324f", "#e6a817", "#c0392b",
                                         "#1e8e5a", "#7d5ba6", "#9aa5b1")

# candidate_id (string; "-" is the "Не подкрепям никого" option) -> (chart label, colour)
CANDS: dict[str, tuple[str, str]] = {
    "25": ("Yotova", NAVY),
    "4": ("Gyurov", AMBER),
    "11": ("Kostadinov — Vazrazhdane", RED),
    "17": ("Vasilev — MECH", GREEN),
    "19": ("Mihaylov — Velichie", PURPLE),
}
NOSUPPORT = "-"  # "Не подкрепям никого"
RUNOFF_LINE = 50.0
REGISTER = 6_637_238  # national register, from the official intraday page

ZONE = dt.timezone(dt.timedelta(hours=2))  # All captures follow the 25 October DST change.

ABROAD_CODE = 32       # MIR 32 "Обобщени данни" — the aggregated abroad row
SOFTIA = {23, 24, 25}  # the three Sofia MIRs


def to_local(ts: pd.Timestamp) -> pd.Timestamp:
    """UTC capture time -> naive local wall time (fixed EET, UTC+2)."""
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.tz_convert(ZONE).tz_localize(None)


def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    nat = pd.read_csv(TRENDS / "national.csv")
    nat["fetch_ts"] = pd.to_datetime(nat.fetch_ts_utc, utc=True)
    res = pd.read_csv(TRENDS / "results.csv")
    res["candidate_id"] = res.candidate_id.astype(str)
    res["area_code_int"] = res.area_code.astype(int)
    res["fetch_ts"] = pd.to_datetime(res.fetch_ts_utc, utc=True)
    tu = pd.read_csv(TRENDS / "intraday_turnout.csv")
    tu["area_code_int"] = tu.area_code.astype(int)
    return nat, res, tu


def _xaxis(ax) -> None:
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.set_xlabel("election night, local time (EET, fixed UTC+2)")


# ---------- figures ----------

def fig_count_pace(nat: pd.DataFrame, res: pd.DataFrame, tu: pd.DataFrame) -> None:
    t = [to_local(x) for x in nat.fetch_ts]
    votes = (res[res.area_level == "country"]
             .groupby("fetch_ts").votes.sum().reindex(nat.fetch_ts))
    off = (tu[(tu.area_level == "country") & (tu.source.str.startswith("http"))]
           .drop_duplicates("as_of_local").sort_values("as_of_local"))
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.4))
    ax = axes[0]
    ax.plot(t, nat.pct_counted, color=NAVY, marker="o", ms=3.5, lw=1.6)
    ax.set_title("СИК protocols processed, %")
    ax.set_ylim(0, 103)
    i0, i1 = nat.pct_counted.eq(95.29).to_numpy().nonzero()[0][[0, -1]]
    ax.annotate("count paused at 95.29%\n(07:05–08:02 EET)", xy=(t[i1], 95.29),
                xytext=(-90, -42), textcoords="offset points", fontsize=8.5,
                color="0.35", arrowprops=dict(arrowstyle="->", color="0.5"))
    ax = axes[1]
    ax.plot(t, votes / 1e6, color=AMBER, marker="o", ms=3.5, lw=1.6)
    ax.set_title("listed votes counted, millions")
    ax.annotate(f"{votes.iloc[-1]/1e6:.2f} M at 98.99% processed",
                xy=(t[-1], votes.iloc[-1] / 1e6), xytext=(-130, -8),
                textcoords="offset points", fontsize=8.5, color="0.35")
    ax = axes[2]
    xs = list(range(len(off)))
    bars = ax.bar(xs, off.turnout_pct, width=0.5, color=GREEN, alpha=0.85)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{s} EET" for s in off.as_of_local])
    for b, v in zip(bars, off.turnout_pct):
        ax.annotate(f"{v:.2f}%", xy=(b.get_x() + b.get_width() / 2, v),
                    xytext=(0, 3), textcoords="offset points", ha="center", fontsize=9)
    ax.set_title("official intraday turnout")
    ax.set_ylim(0, 19)
    for ax in axes:
        ax.grid(alpha=0.25)
    _xaxis(axes[0])
    _xaxis(axes[1])
    fig.suptitle("Bulgaria, president 25.10.2026 — pace of the count (CIK intraday)", y=1.02)
    fig.tight_layout()
    fig.savefig(OUT / "01_count_pace.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_share_race(res: pd.DataFrame) -> None:
    c = res[res.area_level == "country"]
    piv = c.pivot_table(index="fetch_ts", columns="candidate_id", values="pct", aggfunc="first")
    t = [to_local(x) for x in piv.index]
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    for cid, (label, color) in CANDS.items():
        if cid in piv:
            lw = 2.2 if cid in ("25", "4") else 1.3
            ax.plot(t, piv[cid], color=color, lw=lw, marker="o", ms=3.5, label=label)
    nosup = piv[NOSUPPORT]
    ax.plot(t, nosup, color=GRAY, lw=1.2, ls="--", label="“Не подкрепям никого”")
    others = piv.drop(columns=[*CANDS, NOSUPPORT]).sum(axis=1)
    ax.plot(t, others, color="0.7", lw=1.0, ls=":", label="remaining 22 pairs")
    ax.axhline(RUNOFF_LINE, color="0.4", lw=0.8, ls="-.")
    ax.annotate("absolute majority — not reached by anyone", xy=(t[1], RUNOFF_LINE),
                xytext=(0, 4), textcoords="offset points", fontsize=8.5, color="0.35")
    last = piv.index.max()
    for cid in ("25", "4", "11"):
        _, color = CANDS[cid]
        ax.annotate(f"{piv.loc[last, cid]:.1f}%", xy=(t[-1], piv.loc[last, cid]),
                    xytext=(5, 0), textcoords="offset points", color=color, fontweight="bold")
    ax.set_ylabel("CIK displayed share of listed votes, %")
    ax.set_ylim(0, 57)
    ax.set_xlim(t[0], t[-1] + pd.Timedelta(hours=1.2))
    ax.grid(alpha=0.25)
    leg = ax.legend(loc="center left", bbox_to_anchor=(0.03, 0.52), frameon=True, fontsize=9)
    leg.get_frame().set_facecolor("white")
    leg.get_frame().set_edgecolor("none")
    leg.get_frame().set_alpha(0.88)
    ax.set_title("Vote shares through the count: no lead change —\n"
                 "Yotova vs Gyurov goes to the 1 November runoff")
    _xaxis(ax)
    fig.tight_layout()
    fig.savefig(OUT / "02_share_race.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_margin_vs_counted(res: pd.DataFrame, nat: pd.DataFrame) -> None:
    c = res[res.area_level == "country"]
    piv = c.pivot_table(index="fetch_ts", columns="candidate_id", values="pct", aggfunc="first")
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
    ax.annotate("bounce at 03:07 EET:\nmargin widens by 1.6 pp",
                xy=(m.counted.iloc[3], m.margin.iloc[3]), xytext=(26, 8),
                textcoords="offset points", fontsize=8.5, color=NAVY,
                arrowprops=dict(arrowstyle="->", color="0.5"))
    ax.set_xlabel("СИК protocols processed, %")
    ax.set_ylabel("Yotova − Gyurov, percentage points")
    ax.set_ylim(0, 7)
    ax.grid(alpha=0.25)
    ax.set_title("Yotova − Gyurov margin through the count:\n"
                 "narrowed from 5.2 to 2.7 pp, one reversal at ~48% processed")
    fig.tight_layout()
    fig.savefig(OUT / "03_margin_vs_counted.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_final_margins(res: pd.DataFrame) -> None:
    mir = res[res.area_level == "mir"]
    last_ts = mir.fetch_ts.max()
    last = mir[mir.fetch_ts == last_ts]
    pv = last.pivot_table(index="area_code_int", columns="candidate_id",
                          values="pct", aggfunc="first")
    names = last.drop_duplicates("area_code_int").set_index("area_code_int").area_name
    d = pd.DataFrame({"name": names, "margin": pv["25"] - pv["4"]})
    d = d.sort_values("margin")
    fig, ax = plt.subplots(figsize=(8.6, 8.6))
    y = range(len(d))
    colors = [NAVY if v >= 0 else AMBER for v in d.margin]
    ax.barh(list(y), d.margin, color=colors, alpha=0.88, height=0.66)
    ax.set_yticks(list(y))
    labels = [f"{c:>2} {n}" for c, n in zip(d.index, d.name)]
    labels[d.index.get_loc(ABROAD_CODE)] += "  (abroad aggregate)"
    ax.set_yticklabels(labels, fontsize=8.5)
    for i, v in enumerate(d.margin):
        ax.annotate(f"{v:+.1f}", xy=(v, i), xytext=(4 if v >= 0 else -4, 0),
                    textcoords="offset points", va="center",
                    ha="left" if v >= 0 else "right", fontsize=7.5, color="0.3")
    ax.axvline(0, color="0.6", lw=0.8)
    ax.set_xlabel("final Yotova − Gyurov margin, percentage points")
    ax.set_xlim(-38, 32)
    ax.grid(alpha=0.25, axis="x")
    ax.scatter([], [], color=NAVY, s=30, label="Yotova leads (27 of 31 domestic MIRs)")
    ax.scatter([], [], color=AMBER, s=30, label="Gyurov leads (3 Sofia MIRs, Plovdiv-city, abroad)")
    ax.legend(loc="upper left", frameon=False, fontsize=8.5)
    ax.set_title("Where each runner-up votes: final margin by MIR")
    fig.tight_layout()
    fig.savefig(OUT / "04_final_margins_by_mir.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_first_final_swing(res: pd.DataFrame) -> None:
    mir = res[res.area_level == "mir"]
    first_ts, last_ts = mir.fetch_ts.min(), mir.fetch_ts.max()
    rows = []
    for code, sub in mir.groupby("area_code_int"):
        for ts, tag in [(first_ts, "first"), (last_ts, "final")]:
            s = sub[sub.fetch_ts == ts]
            pv = s.set_index("candidate_id").pct
            # the abroad aggregate is empty in the very first snapshot
            if pv.dropna().empty:
                continue
            rows.append({"code": code, "tag": tag, "margin": pv["25"] - pv["4"]})
    d = pd.DataFrame(rows).pivot(index="code", columns="tag", values="margin").dropna()
    names = mir[mir.fetch_ts == last_ts].drop_duplicates("area_code_int") \
        .set_index("area_code_int").area_name
    d["name"] = names
    d = d.sort_values("final")
    fig, ax = plt.subplots(figsize=(8.4, 8.4))
    y = range(len(d))
    ax.axvline(0, color="0.6", lw=0.8)
    for i, (code, row) in enumerate(d.iterrows()):
        moved = row.final - row.first
        color = AMBER if moved > 0 else NAVY
        ax.plot([row.first, row.final], [i, i], color="0.78", lw=1.4, zorder=1)
        ax.scatter([row.first], [i], color="0.45", s=26, zorder=2)
        ax.scatter([row.final], [i], color=color, s=40, zorder=3)
    ax.set_yticks(list(y))
    labels = [f"{c:>2} {n}" for c, n in zip(d.index, d.name)]
    labels[d.index.get_loc(ABROAD_CODE)] += "  (abroad)"
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.set_xlabel("Yotova − Gyurov margin, percentage points")
    ax.scatter([], [], color="0.45", s=26, label=f"first snapshot ({to_local(first_ts):%H:%M} EET)")
    ax.scatter([], [], color=NAVY, s=40, label="latest capture: margin moved toward Yotova")
    ax.scatter([], [], color=AMBER, s=40, label="latest capture: margin moved toward Gyurov")
    ax.legend(loc="lower right", frameon=False, fontsize=8.5)
    ax.grid(alpha=0.25, axis="x")
    ax.set_title("Count-night swing by MIR (first → last snapshot)")
    fig.tight_layout()
    fig.savefig(OUT / "05_first_final_swing.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_turnout(tu: pd.DataFrame, res: pd.DataFrame) -> None:
    off = (tu[(tu.area_level == "mir") & (tu.source == "mapData")
              & (tu.as_of_local.astype(str) == "16:00")]
           .drop_duplicates("area_code_int"))
    mir = res[res.area_level == "mir"]
    last_ts = mir.fetch_ts.max()
    last = mir[mir.fetch_ts == last_ts]
    pv = last.pivot_table(index="area_code_int", columns="candidate_id",
                          values="pct", aggfunc="first")
    names = last.drop_duplicates("area_code_int").set_index("area_code_int").area_name
    d = pd.DataFrame({"name": names,
                      "margin": pv["25"] - pv["4"],
                      "turnout": off.set_index("area_code_int").turnout_pct}).dropna()
    d = d[d.index != ABROAD_CODE]
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), width_ratios=[1.15, 1])
    ax = axes[0]
    dd = d.sort_values("turnout")
    y = range(len(dd))
    ax.barh(list(y), dd.turnout, color=GREEN, alpha=0.8, height=0.66)
    ax.set_yticks(list(y))
    ax.set_yticklabels([f"{c:>2} {n}" for c, n in zip(dd.index, dd.name)], fontsize=8)
    for i, v in enumerate(dd.turnout):
        ax.annotate(f"{v:.1f}", xy=(v, i), xytext=(3, 0), textcoords="offset points",
                    va="center", fontsize=7, color="0.3")
    country = float(tu[(tu.area_level == "country")
                       & (tu.as_of_local.astype(str) == "16:00")].turnout_pct.iloc[0])
    ax.axvline(country, color=RED, lw=1.1, ls="--")
    ax.annotate(f"country {country:.2f}%", xy=(country, 0.8), xytext=(4, 0),
                textcoords="offset points", fontsize=8.5, color=RED)
    ax.set_xlabel("official turnout at 16:00 EET, %")
    ax.set_xlim(0, 29)
    ax.grid(alpha=0.25, axis="x")
    ax.set_title("16:00 turnout by MIR: Kardzhali 6.8% → Sofia-23 25.9%")
    ax = axes[1]
    ax.scatter(d.turnout, d.margin, s=34, color=NAVY, alpha=0.75)
    r = float(np.corrcoef(d.turnout, d.margin)[0, 1])
    for code, row in d.iterrows():
        if code in SOFTIA or code in (9, 16, 3):
            ax.annotate(f"{row.name}", xy=(row.turnout, row.margin), xytext=(4, 3),
                        textcoords="offset points", fontsize=7.5, color="0.35")
    ax.axhline(0, color="0.6", lw=0.8)
    ax.set_xlabel("official turnout at 16:00 EET, %")
    ax.set_ylabel("final Yotova − Gyurov margin, pp")
    ax.grid(alpha=0.25)
    ax.set_title(f"High-turnout districts lean toward Gyurov (r = {r:+.2f}, 31 MIRs)")
    fig.suptitle("Turnout geography vs the runoff pair", y=1.0)
    fig.tight_layout()
    fig.savefig(OUT / "06_turnout_vs_margin.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------- metrics ----------

def build_metrics(nat: pd.DataFrame, res: pd.DataFrame, tu: pd.DataFrame) -> dict:
    c = res[res.area_level == "country"]
    piv = c.pivot_table(index="fetch_ts", columns="candidate_id", values="pct", aggfunc="first")
    votes = c.groupby("fetch_ts").votes.sum().reindex(nat.fetch_ts)
    last = piv.index.max()
    margin = piv["25"] - piv["4"]
    mir = res[res.area_level == "mir"]
    last_ts = mir.fetch_ts.max()
    off_c = (tu[(tu.area_level == "country") & (tu.source.str.startswith("http"))]
             .drop_duplicates("as_of_local").sort_values("as_of_local"))

    per_mir: dict[str, dict] = {}
    for code, sub in mir.groupby("area_code_int"):
        s = sub[sub.fetch_ts == last_ts].set_index("candidate_id")
        f = sub[sub.fetch_ts == sub.fetch_ts.min()].set_index("candidate_id").pct
        first_margin = float(f["25"] - f["4"]) if not f.dropna().empty else None
        per_mir[str(code)] = {
            "name": str(sub.area_name.dropna().iloc[0] if sub.area_name.dropna().empty is False else ""),
            "yotova_pct": float(s.pct["25"]),
            "gyurov_pct": float(s.pct["4"]),
            "kostadinov_pct": float(s.pct["11"]),
            "margin_yotova_gyurov_pp": float(s.pct["25"] - s.pct["4"]),
            "margin_first_snapshot_pp": first_margin,
            "turnout16_pct": float(
                tu[(tu.area_code_int == code) & (tu.as_of_local.astype(str) == "16:00")]
                .turnout_pct.dropna().iloc[0]) if len(
                tu[(tu.area_code_int == code) & (tu.as_of_local.astype(str) == "16:00")]
                .turnout_pct.dropna()) else None,
        }

    return {
        "election": "BG-pvr202610 president, round 1 (25.10.2026)",
        "snapshots": len(nat),
        "first_fetch_utc": nat.fetch_ts_utc.iloc[0],
        "last_fetch_utc": nat.fetch_ts_utc.iloc[-1],
        "pct_counted_series": {str(ts): float(v) for ts, v in
                               zip(nat.fetch_ts_utc, nat.pct_counted) if pd.notna(v)},
        "count_pause_pct": 95.29,
        "count_pause_fetch_utc": [str(nat.loc[nat.pct_counted.eq(95.29), "fetch_ts_utc"].iloc[0]),
                                  str(nat.loc[nat.pct_counted.eq(95.29), "fetch_ts_utc"].iloc[-1])],
        "register": REGISTER,
        "listed_votes_final": int(votes.iloc[-1]),
        "listed_votes_share_of_register_pct": round(100 * votes.iloc[-1] / REGISTER, 2),
        "listed_votes_denominator_note": ("sum of votes for all listed pairs incl. "
                                          "“Не подкрепям никого”; invalid ballots unknown "
                                          "from this capture — a lower bound on turnout"),
        "official_intraday_turnout": {str(r.as_of_local): float(r.turnout_pct)
                                      for r in off_c.itertuples()},
        "shares_final_pct": {cid: float(piv.loc[last, cid]) for cid in piv.columns},
        "runoff": {"pair": ["Yotova", "Gyurov"], "date": "2026-11-01",
                   "top_share_pct": float(piv.loc[last, "25"])},
        "margin_yotova_gyurov_pp": {str(ts): float(v) for ts, v in margin.items()},
        "margin_monotonic": bool((margin.diff().dropna() <= 0).all()),
        "margin_bounce_at_utc": str(margin.diff().idxmax()),
        "leaders_domestic": {"yotova": 27, "gyurov": 4},
        "abroad_aggregate_mir32": {k: per_mir["32"][k] for k in
                                   ("yotova_pct", "gyurov_pct", "kostadinov_pct")},
        "per_mir": per_mir,
        "consistency_mir_sum_equals_country_final": bool(
            abs(mir[mir.fetch_ts == last_ts].groupby("area_code_int").votes.sum().sum()
                - votes.iloc[-1]) < 1e-6),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    nat, res, tu = load()

    fig_count_pace(nat, res, tu)
    fig_share_race(res)
    fig_margin_vs_counted(res, nat)
    fig_final_margins(res)
    fig_first_final_swing(res)
    fig_turnout(tu, res)

    metrics = build_metrics(nat, res, tu)
    (BASE / "analysis" / "trends" / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"charts -> {OUT}")
    print(json.dumps({k: metrics[k] for k in (
        "snapshots", "listed_votes_final", "listed_votes_share_of_register_pct",
        "official_intraday_turnout", "shares_final_pct", "margin_monotonic",
        "margin_bounce_at_utc", "consistency_mir_sum_equals_country_final")},
        ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
