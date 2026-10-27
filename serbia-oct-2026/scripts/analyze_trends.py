# -*- coding: utf-8 -*-
"""
Trend analysis of the intraday capture of the Serbian parliamentary election
of 25.10.2026 (RIK round 680072).

Sources, merged into one intraday dataset:
  data/trends/{national,regions,results}.csv  — night captures (zip), ~hourly,
      21:04 UTC 25.10 → 07:04 UTC 26.10;
  data/raw/680072/<stamp>/{national_0,region_*}.json — later snapshots written
      by scripts/scrape_rik.py (parsed and appended to the trends CSVs, so the
      CSVs stay the single normalized intraday dataset; idempotent — a
      snapshot is appended only if its fetch timestamp is new).

Outputs:
  analysis/trends/charts/0*.png  — count-night dynamics figures
  analysis/trends/metrics.json   — key numbers quoted in the reports

Run:
  analysis-tool/.venv/bin/python serbia-oct-2026/scripts/analyze_trends.py
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
DATA = BASE / "data"
TRENDS = DATA / "trends"
RAW = DATA / "raw" / "680072"
OUT = BASE / "analysis" / "trends" / "charts"

sys.path.insert(0, str(HERE))
import rik_api  # noqa: E402

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

NAVY, AMBER, GREEN, RED, GRAY = "#16324f", "#e6a817", "#1e8e5a", "#c0392b", "#9aa5b1"

# candidate_id -> (short chart label, colour)
LISTS = {
    1: ("Vučić — Ujedinjena Srbija", NAVY),
    2: ("Dacić — SPS", RED),
    3: ("Students", AMBER),
    5: ("VMSZ", GREEN),
    8: ("Jovanović", GRAY),
}
ZONE = dt.timezone(dt.timedelta(hours=1))  # Serbia, CET (UTC+1) on 25–26.10.2026


def to_local(ts: pd.Timestamp) -> pd.Timestamp:
    """UTC capture time -> naive Serbian local wall time (CET, +1)."""
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.tz_convert(ZONE).tz_localize(None)


# ---------- merging late snapshots into the trends CSVs ----------

def turnout_from_pie(raw: dict) -> float:
    """RIK's own turnout: 'Изашло/Није изашло' pie = voted vs not voted among counted stations."""
    try:
        data = raw["processed_config"]["data"]["datasets"][0]["data"]
        labels = raw["processed_config"]["data"]["labels"]
        voted = next(float(data[i]) for i, l in enumerate(labels) if l.startswith("Изашло"))
        total = sum(float(x) for x in data)
        return round(voted / total * 100, 2) if total else 0.0
    except (KeyError, IndexError, TypeError, StopIteration, ValueError):
        return 0.0


def parse_raw_files(fetch_iso: str, files: list[Path]) -> tuple[dict | None, list[dict], list[dict]]:
    """One scrape pass (a pass may split across several stamp dirs) -> (national, regions, results)."""
    nat_row, reg_rows, res_rows = None, [], []
    for fname in sorted(files):
        raw = json.loads(fname.read_text(encoding="utf-8"))
        ssn = raw.get("stat_sum_numbers", {})
        parsed = rik_api.parse_rik_datetime(ssn.get("datetime", ""))
        source_ts = dt.datetime.fromisoformat(parsed).strftime("%d.%m.%Y %H:%M:%S") if parsed else ""
        valid, invalid = rik_api.ballots_from_sum_config(raw)
        common = {"fetch_ts_utc": fetch_iso, "source_ts": source_ts,
                  "election": "RS-680072", "race": "parliament"}
        prog = {"units_total": rik_api.parse_int(ssn.get("number_of_stations")),
                "units_counted": rik_api.parse_int(ssn.get("processed_stations"))}
        prog["pct_counted"] = round(prog["units_counted"] / max(1, prog["units_total"]) * 100, 2)
        if fname.stem == "national_0":
            nat_row = {**common,
                       "registered": rik_api.parse_int(ssn.get("total_voters")),
                       "voters": rik_api.parse_int(ssn.get("available")),
                       "turnout_pct": turnout_from_pie(raw),
                       "votes_total": valid + invalid,
                       "votes_valid": valid,
                       "votes_blank": "",
                       "votes_invalid": invalid,
                       **prog,
                       "units_label": "birackih mesta (polling stations)"}
        elif fname.stem.startswith("region_"):
            reg_rows.append({**common, "area_level": "region",
                             "area_code": int(fname.stem.split("_")[1]),
                             "area_name": "",  # filled from results table below
                             "registered": rik_api.parse_int(ssn.get("total_voters")),
                             "voters": rik_api.parse_int(ssn.get("available")),
                             "turnout_pct": turnout_from_pie(raw),
                             **prog})
        else:
            continue
        level = "country" if fname.stem == "national_0" else "region"
        for lst in raw.get("table_data", []):
            res_rows.append({**common, "area_level": level,
                             "area_code": 0 if level == "country" else int(fname.stem.split("_")[1]),
                             "area_name": "Србија" if level == "country" else "",
                             "candidate_id": int(lst["count_number"]),
                             "candidate": lst.get("list_name", "").strip(),
                             "party": "", "votes": rik_api.parse_int(lst.get("won_number")),
                             "pct": rik_api.parse_float(lst.get("won_percent"))})
    return nat_row, reg_rows, res_rows


def snapshot_passes() -> list[tuple[str, list[Path]]]:
    """Group raw snapshot dirs into passes (one pass splits into dirs seconds apart)."""
    groups: list[list[Path]] = []
    dirs = [p for root in (RAW, DATA / "checks" / "680072") if root.exists()
            for p in root.iterdir() if p.is_dir()]
    for d in sorted(dirs, key=lambda p: p.name):
        if groups:
            prev = dt.datetime.strptime(groups[-1][-1].name, "%Y%m%d_%H%M%S")
            cur = dt.datetime.strptime(d.name, "%Y%m%d_%H%M%S")
            if (cur - prev).total_seconds() <= 300:
                groups[-1].append(d)
                continue
        groups.append([d])
    out = []
    for g in groups:
        files = [f for d in g for f in d.glob("*.json") if f.name != "normalized.json"]
        fetch_iso = dt.datetime.strptime(g[0].name, "%Y%m%d_%H%M%S").replace(
            tzinfo=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        out.append((fetch_iso, files))
    return out


def region_names(res: pd.DataFrame) -> dict:
    r = res[res.area_level == "region"].dropna(subset=["area_name"])
    return r.drop_duplicates("area_code").set_index("area_code")["area_name"].to_dict()


def append_late_snapshots(nat: pd.DataFrame, reg: pd.DataFrame, res: pd.DataFrame
                          ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Append scrape_rik.py snapshots (data/raw/680072/<stamp>) newer than the CSV history."""
    if not RAW.exists():
        return nat, reg, res
    known = set(pd.to_datetime(nat.fetch_ts_utc, utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ"))
    rnames = region_names(res)
    new_nat, new_reg, new_res = [], [], []
    for fetch_iso, files in snapshot_passes():
        if fetch_iso in known:
            continue
        nat_row, reg_rows, res_rows = parse_raw_files(fetch_iso, files)
        if nat_row is None:
            continue
        known.add(fetch_iso)
        for r in reg_rows:
            r["area_name"] = rnames.get(r["area_code"], "")
        for r in res_rows:
            if r["area_level"] == "region":
                r["area_name"] = rnames.get(r["area_code"], "")
        new_nat.append(nat_row)
        new_reg.extend(reg_rows)
        new_res.extend(res_rows)
    if not new_nat:
        return nat, reg, res
    for df in (nat, reg, res):
        # keep the CSV column in one canonical format ("%Y-%m-%dT%H:%M:%SZ")
        ts = pd.to_datetime(df.fetch_ts_utc, utc=True)
        df["fetch_ts_utc"] = ts.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    nat = pd.concat([nat, pd.DataFrame(new_nat)], ignore_index=True)
    nat["fetch_ts"] = pd.to_datetime(nat.fetch_ts_utc, utc=True)
    nat = nat.sort_values("fetch_ts").reset_index(drop=True)
    reg = pd.concat([reg, pd.DataFrame(new_reg)], ignore_index=True)
    reg["fetch_ts"] = pd.to_datetime(reg.fetch_ts_utc, utc=True)
    reg = reg.sort_values("fetch_ts").reset_index(drop=True)
    res = pd.concat([res, pd.DataFrame(new_res)], ignore_index=True)
    res["fetch_ts"] = pd.to_datetime(res.fetch_ts_utc, utc=True)
    res = res.sort_values("fetch_ts").reset_index(drop=True)

    TRENDS.mkdir(parents=True, exist_ok=True)
    nat.drop(columns="fetch_ts").to_csv(TRENDS / "national.csv", index=False)
    reg.drop(columns="fetch_ts").to_csv(TRENDS / "regions.csv", index=False)
    res.drop(columns="fetch_ts").to_csv(TRENDS / "results.csv", index=False)
    print(f"appended {len(new_nat)} snapshot(s) from data/raw/680072 to data/trends/*.csv")
    return nat, reg, res


# ---------- figures ----------

def _xaxis(ax, times=None):
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.set_xlabel("election night, Serbian local time (CET)")


def fig_national(nat: pd.DataFrame) -> None:
    t = [to_local(x) for x in nat.fetch_ts]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.4))
    axes[0].plot(t, nat.pct_counted, color=NAVY, marker="o", ms=3.5, lw=1.6)
    axes[0].set_title("polling stations counted, %")
    axes[0].set_ylim(0, 103)
    axes[1].plot(t, nat.turnout_pct, color=GREEN, marker="o", ms=3.5, lw=1.6)
    axes[1].set_title("turnout among counted stations, %")
    lo, hi = nat.turnout_pct.min(), nat.turnout_pct.max()
    axes[1].set_ylim(lo - 0.25, hi + 0.25)
    axes[2].plot(t, nat.votes_valid / 1e6, color=AMBER, marker="o", ms=3.5, lw=1.6)
    axes[2].set_title("valid ballots counted, millions")
    for ax in axes:
        ax.grid(alpha=0.25)
        _xaxis(ax, t)
    fig.suptitle("Serbia, National Assembly 25.10.2026 — pace of the count (RIK intraday)", y=1.02)
    fig.tight_layout()
    fig.savefig(OUT / "01_national_dynamics.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_share_race(res: pd.DataFrame, nat: pd.DataFrame) -> None:
    c = res[res.area_level == "country"]
    piv = c.pivot_table(index="fetch_ts", columns="candidate_id", values="pct", aggfunc="first")
    t = [to_local(x) for x in piv.index]
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    for cid, (label, color) in LISTS.items():
        if cid in piv:
            ax.plot(t, piv[cid], color=color, lw=2.0 if cid in (1, 3) else 1.2,
                    marker="o", ms=3.5, label=label)
    others = piv.drop(columns=list(LISTS), errors="ignore").sum(axis=1)
    ax.plot(t, others, color=GRAY, lw=1.2, ls="--", label="remaining lists")
    # crossover moment
    diff = piv[3] - piv[1]
    flip_i = (diff > 0).idxmax()
    fx, fy = to_local(flip_i), piv.loc[flip_i, 3]
    ax.annotate(f"students take the lead\nbefore {fx:%H:%M} CET (~35% counted)",
                xy=(fx, fy), xytext=(30, 28), textcoords="offset points",
                fontsize=9, arrowprops=dict(arrowstyle="->", color="0.35"))
    last = piv.index.max()
    ax.annotate(f"{piv.loc[last, 3]:.1f}%", xy=(t[-1], piv.loc[last, 3]),
                xytext=(4, 2), textcoords="offset points", color=AMBER, fontweight="bold")
    ax.annotate(f"{piv.loc[last, 1]:.1f}%", xy=(t[-1], piv.loc[last, 1]),
                xytext=(4, -12), textcoords="offset points", color=NAVY, fontweight="bold")
    ax.set_ylabel("RIK displayed share of ballots, %")
    ax.set_ylim(0, 60)
    ax.grid(alpha=0.25)
    ax.legend(loc="center left", bbox_to_anchor=(0.35, 0.38), frameon=False, fontsize=9)
    ax.set_title("RIK displayed vote shares through the count\n"
                 "Vučić's list leads only while the first ~30% of stations are in")
    _xaxis(ax, t)
    fig.tight_layout()
    fig.savefig(OUT / "02_share_race.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_margin_counted(res: pd.DataFrame, nat: pd.DataFrame) -> None:
    c = res[res.area_level == "country"]
    piv = c.pivot_table(index="fetch_ts", columns="candidate_id", values="pct", aggfunc="first")
    margin = (piv[3] - piv[1]).dropna()
    counted = nat.set_index("fetch_ts").pct_counted
    counted.index = pd.to_datetime(counted.index, utc=True)
    m = pd.concat([margin, counted.reindex(margin.index)], axis=1)
    m.columns = ["margin", "counted"]
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    ax.axhline(0, color="0.6", lw=0.8)
    ax.plot(m.counted, m.margin, color=AMBER, marker="o", ms=4, lw=1.8)
    for _, row in m.iterrows():
        if row.counted > 90 and row.name not in (m.index[-1], m.margin.idxmax()):
            continue
        offset = (-75, 24) if row.name == m.margin.idxmax() else (0, 7)
        if row.name == m.index[-1]:
            offset = (-75, -24)
        ax.annotate(f"{to_local(row.name):%H:%M}", xy=(row.counted, row.margin),
                    xytext=offset, textcoords="offset points", fontsize=7.5,
                    ha="center", color="0.35",
                    arrowprops={"arrowstyle": "-", "color": "0.6", "lw": 0.6}
                    if row.name in (m.index[-1], m.margin.idxmax()) else None)
    ax.set_ylim(m.margin.min() - 1, m.margin.max() + 2)
    ax.set_xlabel("stations counted, %")
    ax.set_ylabel("Students − Vučić, percentage points")
    ax.grid(alpha=0.25)
    ax.set_title("Students − Vučić margin through the count")
    fig.tight_layout()
    fig.savefig(OUT / "03_margin_vs_counted.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


REGION_ORDER = ["Београдски регион", "Регион Војводине", "Регион Шумадије и Западне Србије",
                "Регион Јужне и Источне Србије", "Регион Косово и Метохија",
                "Заводи за извршење кривичних санкција"]
REGION_TITLE = {"Београдски регион": "Belgrade", "Регион Војводине": "Vojvodina",
                "Регион Шумадије и Западне Србије": "Šumadija & W. Serbia",
                "Регион Јужне и Источне Србије": "S. & E. Serbia",
                "Регион Косово и Метохија": "Kosovo & Metohija",
                "Заводи за извршење кривичних санкција": "prisons"}


def fig_regions(reg: pd.DataFrame, res: pd.DataFrame) -> None:
    r = res[res.area_level == "region"]
    regions = [x for x in REGION_ORDER if x in set(r.area_name)]
    fig, axes = plt.subplots(2, 3, figsize=(12.5, 6.4), sharex=True)
    for ax, area in zip(axes.flat, regions):
        sub = r[r.area_name == area].pivot_table(
            index="fetch_ts", columns="candidate_id", values="pct", aggfunc="first")
        t = [to_local(x) for x in sub.index]
        ax.plot(t, sub[3], color=AMBER, lw=1.8, marker="o", ms=3, label="Students")
        ax.plot(t, sub[1], color=NAVY, lw=1.8, marker="o", ms=3, label="Vučić")
        prog = reg[reg.area_name == area].set_index("fetch_ts").pct_counted
        ax2 = ax.twinx()
        ax2.plot([to_local(x) for x in prog.index], prog, color="0.75", lw=1.0, ls=":")
        ax2.set_ylim(0, 105)
        ax2.spines["right"].set_visible(False)
        ax2.tick_params(right=False, labelright=False)
        ax.set_title(REGION_TITLE.get(area, area), fontsize=10)
        ax.grid(alpha=0.25)
        ax.set_ylim(0, 80)
    axes.flat[0].legend(loc="upper left", frameon=False, fontsize=8)
    for ax in axes.flat[-3:]:
        _xaxis(ax, [])
    fig.suptitle("Students vs Vučić by region (solid, RIK displayed % of ballots; dotted: stations counted, %)",
                 y=1.0)
    fig.tight_layout()
    fig.savefig(OUT / "04_regional_dynamics.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_first_final(res: pd.DataFrame) -> None:
    r = res[res.area_level == "region"]
    regions = [x for x in REGION_ORDER if x in set(r.area_name)]
    first_ts, last_ts = r.fetch_ts.min(), r.fetch_ts.max()
    rows = []
    for area in regions:
        for ts, tag in [(first_ts, "first"), (last_ts, "final")]:
            sub = r[(r.area_name == area) & (r.fetch_ts == ts)]
            v = float(sub[sub.candidate_id == 1].pct.iloc[0])
            s = float(sub[sub.candidate_id == 3].pct.iloc[0])
            rows.append({"area": area, "tag": tag, "margin": s - v})
    d = pd.DataFrame(rows).pivot(index="area", columns="tag", values="margin")
    d = d.reindex(regions)
    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    y = range(len(d))
    ax.axvline(0, color="0.6", lw=0.8)
    for i, area in enumerate(d.index):
        f, l = d.loc[area, "first"], d.loc[area, "final"]
        ax.plot([f, l], [i, i], color="0.75", lw=1.4, zorder=1)
        ax.scatter([f], [i], color=NAVY, s=34, zorder=2)
        ax.scatter([l], [i], color=AMBER, s=44, zorder=3)
    ax.set_yticks(list(y))
    ax.set_yticklabels([REGION_TITLE.get(a, a) for a in d.index])
    ax.set_xlabel("Students − Vučić margin, percentage points")
    ax.scatter([], [], color=NAVY, s=34, label=f"first snapshot ({to_local(first_ts):%H:%M} CET)")
    ax.scatter([], [], color=AMBER, s=44, label=f"latest capture ({to_local(last_ts):%H:%M} CET)")
    ax.legend(loc="upper left", frameon=False, fontsize=8.5)
    ax.grid(alpha=0.25, axis="x")
    ax.set_title("Count-night swing: territorial regions moved toward the students,\n"
                 "Kosovo and the prisons moved the other way")
    fig.tight_layout()
    fig.savefig(OUT / "05_region_first_final.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_special(reg: pd.DataFrame, res: pd.DataFrame) -> None:
    areas = {"Србија": "national", "Заводи за извршење кривичних санкција": "prisons",
             "Иностранство": "abroad"}
    r = res[(res.area_level == "region") | (res.area_level == "country")]
    last_ts = r.fetch_ts.max()
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.8))
    # (a) counting progress of abroad
    ab = reg[reg.area_name == "Иностранство"].set_index("fetch_ts")
    ax = axes[0]
    ax.plot([to_local(x) for x in ab.index], ab.pct_counted, color=RED, marker="o", ms=3.5)
    ax.set_title("abroad: stations counted, %")
    ax.set_ylim(-3, 103)
    _xaxis(ax)
    ax.annotate(f"{ab.pct_counted.iloc[-1]:.1f}% at {to_local(ab.index.max()):%H:%M} CET,\n"
                f"{int(ab.units_counted.iloc[-1])}/{int(ab.units_total.iloc[-1])} stations",
                xy=(0.04, 0.08), xycoords="axes fraction", fontsize=8.5, color=RED)
    # (b) turnout counted vs final shares
    ax = axes[1]
    names, turnout, students, vucic = [], [], [], []
    for area, label in areas.items():
        if area == "Србија":
            tr = reg[reg.area_name == "Београдски регион"]  # placeholder, replaced below
        sub_r = r[(r.area_name == area) & (r.fetch_ts == last_ts)] if area != "Србија" else None
        if area == "Србија":
            c = r[(r.area_level == "country") & (r.fetch_ts == last_ts)]
            names.append(label)
            students.append(float(c[c.candidate_id == 3].pct.iloc[0]))
            vucic.append(float(c[c.candidate_id == 1].pct.iloc[0]))
            g = reg[reg.fetch_ts == last_ts]
            turnout.append(float(100 * g.voters.sum() /
                                 (g.voters / (g.turnout_pct / 100)).sum()))
        else:
            if sub_r.empty:
                continue
            names.append(label)
            students.append(float(sub_r[sub_r.candidate_id == 3].pct.iloc[0]))
            vucic.append(float(sub_r[sub_r.candidate_id == 1].pct.iloc[0]))
            tr = reg[(reg.area_name == area) & (reg.fetch_ts == last_ts)]
            turnout.append(float(tr.turnout_pct.iloc[0]) if len(tr) else 0.0)
    x = range(len(names))
    ax.bar([i - 0.22 for i in x], turnout, width=0.42, color=GRAY, label="turnout, %")
    ax.bar([i for i in x], students, width=0.42, color=AMBER, label="Students, RIK %")
    ax.bar([i + 0.22 for i in x], vucic, width=0.42, color=NAVY, label="Vučić, RIK %")
    ax.set_xticks(list(x))
    ax.set_xticklabels(names, fontsize=8.5)
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("latest capture: turnout vs shares")
    # (c) prisons per-station scatter
    ax = axes[2]
    st_path = DATA / "timeline" / "680072" / "stations.csv"
    if st_path.exists():
        st = pd.read_csv(st_path)
        prisons = st[st.region_code == 100]
        rest = st[(st.region_code != 100) & (st.region_code != 101)]
        for d, color, label in [(rest, GRAY, "territorial stations"), (prisons, RED, "prison stations")]:
            t = 100 * d.voted / d.registered
            s = 100 * d["votes:3"] / d.valid
            ax.scatter(t, s, s=6, alpha=0.35 if d is rest else 0.9,
                       color=color, label=label)
        ax.set_xlabel("station turnout, %")
        ax.set_ylabel("Students RIK displayed share of ballots, %")
        ax.legend(frameon=False, fontsize=8)
        ax.set_title("prison stations vs the rest (station-level capture)")
    else:
        ax.text(0.5, 0.5, "station capture not available yet", ha="center", va="center",
                transform=ax.transAxes)
        ax.set_title("prison stations vs the rest")
    for ax in list(axes):
        ax.grid(alpha=0.25)
    fig.suptitle("Special registers: the abroad count and the prisons", y=1.02)
    fig.tight_layout()
    fig.savefig(OUT / "06_special_areas.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------- metrics ----------

def build_metrics(nat: pd.DataFrame, reg: pd.DataFrame, res: pd.DataFrame) -> dict:
    c = res[res.area_level == "country"]
    piv = c.pivot_table(index="fetch_ts", columns="candidate_id", values="pct", aggfunc="first")
    first_ts, last_ts = c.fetch_ts.min(), c.fetch_ts.max()
    margin = piv[3] - piv[1]
    flip_ts = margin[margin > 0].index.min()
    pre_flip_ts = margin.index[margin.index < flip_ts].max()
    nindex = nat.set_index("fetch_ts")
    # The tail estimate needs a substantive increment; repeated stamps can differ only by rounding.
    night_end = nat[nat.fetch_ts <= pd.Timestamp("2026-10-26T08:00:00Z")].iloc[-1]
    last = piv.loc[last_ts]    # RIK turnout is relative to the register of the already-counted stations,
    # so the register covered by the count at t is voters / (turnout/100) and
    # the turnout of votes added between two snapshots is dV / dR.
    def covered_register(row) -> float:
        return row.voters / (row.turnout_pct / 100.0) if row.turnout_pct else 0.0
    v0, r0 = nat.voters.iloc[0], covered_register(nat.iloc[0])
    v1, r1 = nat.voters.iloc[-1], covered_register(nat.iloc[-1])
    late_turnout = 100 * (v1 - v0) / (r1 - r0) if r1 > r0 else None
    vm, rm = night_end.voters, covered_register(night_end)
    tail_turnout = 100 * (v1 - vm) / (r1 - rm) if r1 > rm else None

    regions_last = {}
    for area in sorted(set(reg.area_name)):
        sub = res[(res.area_name == area) & (res.fetch_ts == last_ts)]
        prog = reg[(reg.area_name == area) & (reg.fetch_ts == last_ts)]
        if sub.empty:
            continue
        regions_last[area] = {
            "students_pct": float(sub[sub.candidate_id == 3].pct.iloc[0]),
            "vucic_pct": float(sub[sub.candidate_id == 1].pct.iloc[0]),
            "pct_counted": float(prog.pct_counted.iloc[0]) if len(prog) else None,
            "turnout_pct": float(prog.turnout_pct.iloc[0]) if len(prog) else None,
        }
    latest_votes = c[c.fetch_ts == last_ts].groupby("candidate_id").votes.sum()
    assert int(latest_votes.sum()) == int(nat.votes_valid.iloc[-1])
    return {
        "ballot_breakdown": {
            "valid": int(nat.votes_valid.iloc[-1]),
            "invalid": int(nat.votes_invalid.iloc[-1]),
            "denominator": int(nat.votes_total.iloc[-1]),
            "other_lists": int(latest_votes.drop(index=[1, 2, 3]).sum()),
            "list_votes": {int(k): int(v) for k, v in latest_votes.items()},
        },
        "snapshots": len(nat),
        "first_fetch_utc": nat.fetch_ts_utc.iloc[0],
        "last_fetch_utc": nat.fetch_ts_utc.iloc[-1],
        "last_source_ts": nat.source_ts.iloc[-1],
        "registered": int(nat.registered.iloc[-1]),
        "turnout_pct": float(nat.turnout_pct.iloc[-1]),
        "stations_total": int(nat.units_total.iloc[-1]),
        "stations_counted": int(nat.units_counted.iloc[-1]),
        "pct_counted": float(nat.pct_counted.iloc[-1]),
        "votes_valid": int(nat.votes_valid.iloc[-1]),
        "shares_final": {int(k): float(v) for k, v in last.items()},
        "flip_at_fetch_utc": str(flip_ts),
        "flip_previous_fetch_utc": str(pre_flip_ts),
        "flip_counted_interval_pct": [float(nindex.loc[pre_flip_ts, "pct_counted"]),
                                      float(nindex.loc[flip_ts, "pct_counted"])],
        "margin_monotonic_at_snapshots": bool((margin.diff().dropna() >= -0.02).all()),
        "implied_tail_from_fetch_utc": str(night_end.fetch_ts),
        "shares_denominator": "RIK displayed percentages; valid plus invalid ballots",
        "ballots_accounting_gap": int(nat.voters.iloc[-1] - nat.votes_total.iloc[-1]),
        "margin_first_pp": float(margin.iloc[0]),
        "margin_final_pp": float(margin.iloc[-1]),
        "turnout_first_pct": float(nat.turnout_pct.iloc[0]),
        "turnout_final_pct": float(nat.turnout_pct.iloc[-1]),
        "implied_late_count_turnout_pct": round(late_turnout, 2) if late_turnout else None,
        "implied_tail_turnout_pct": round(tail_turnout, 2) if tail_turnout else None,
        "regions_final": regions_last,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    nat = pd.read_csv(TRENDS / "national.csv")
    reg = pd.read_csv(TRENDS / "regions.csv")
    res = pd.read_csv(TRENDS / "results.csv")
    for df in (nat, reg, res):
        df["fetch_ts"] = pd.to_datetime(df.fetch_ts_utc, utc=True)

    nat, reg, res = append_late_snapshots(nat, reg, res)

    fig_national(nat)
    fig_share_race(res, nat)
    fig_margin_counted(res, nat)
    fig_regions(reg, res)
    fig_first_final(res)
    fig_special(reg, res)

    metrics = build_metrics(nat, reg, res)
    (BASE / "analysis" / "trends" / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"charts -> {OUT}")
    print(json.dumps(metrics, ensure_ascii=False, indent=1)[:2000])


if __name__ == "__main__":
    main()
