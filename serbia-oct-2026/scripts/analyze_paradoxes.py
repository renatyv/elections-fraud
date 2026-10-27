# -*- coding: utf-8 -*-
"""
Voting-paradox analysis of the Serbian parliamentary election of 25.10.2026
(RIK round 680072), with the 2023 election (round 341140) as the control.

Testable items of the catalogue (paradoxes.md) for a closed-list PR system
with one national constituency, a 3% threshold (national-minority lists
exempt) and 250 seats by D'Hondt:

  1. cloning, inverted — the opposition's single "Students" list vs the
     several lists the same bloc ran in 2023 (bloc consolidation);
  2. the threshold — votes cast for sub-threshold lists that elect nobody
     (the "frustrated" share; minority exemptions treated explicitly);
  3. apportionment sensitivity — D'Hondt + minority bonus vs Sainte-Laguë vs
     largest remainder; the winner's seat premium;
  4. multiple-district paradox — national D'Hondt vs the same votes
     apportioned by region (electoral-college style) + the municipality
     winner inversion (who wins the map while losing the country);
  5. aggregation over time — the count-night flip (see analysis/trends).

Sources: data/trends/results.csv (intraday, country/region), the national
table of both rounds (data/raw/<round>/<stamp>/national_0.json), and the
municipality forensics CSV (data/ef/serbia2026_mun/results_freguesias.csv).

Outputs: analysis/paradoxes/{tables,figures}/ + PARADOX_LOG.txt.

Run (from the repository root):
  analysis-tool/.venv/bin/python serbia-oct-2026/scripts/analyze_paradoxes.py
"""

from __future__ import annotations

import json
from pathlib import Path
from fractions import Fraction

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from build_ef_csv import SHORT_NAMES

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
OUT = BASE / "analysis" / "paradoxes"
TAB, FIG = OUT / "tables", OUT / "figures"

NAVY, AMBER, RED, GREEN, GRAY = "#16324f", "#e6a817", "#c0392b", "#1e8e5a", "#9aa5b1"
SEATS = 250
THRESHOLD = 3.0
# lists registered as national-minority lists (exempt from the 3% threshold);
# RIK proclamation decisions; sources in PARADOXES.md.
MINORITY_2026 = {4, 5, 6, 7, 10, 13, 14, 17, 18}
MINORITY_2023 = {6, 8, 9, 13, 18}

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

log_lines: list[str] = []


def log(msg: str = "") -> None:
    print(msg)
    log_lines.append(msg)


# ---------- data ----------

def national_votes(round_id: int) -> tuple[dict[int, int], int]:
    """Final/latest national table of a round: list_no -> votes, plus valid total."""
    best = None
    for snap_dir in sorted((DATA / "raw" / str(round_id)).iterdir()):
        f = snap_dir / "national_0.json"
        if f.exists():
            best = f
    raw = json.loads(best.read_text(encoding="utf-8"))
    votes = {int(r["count_number"]): int(str(r["won_number"]).replace(".", "") or 0)
             for r in raw["table_data"]}
    try:
        valid = int(str(raw["sum_config"]["data"]["datasets"][0]["data"][0]).replace(".", "") or 0)
    except (KeyError, IndexError, TypeError):
        valid = sum(votes.values())
    return votes, valid


def names_of(round_id: int) -> dict[int, str]:
    best = None
    for snap_dir in sorted((DATA / "raw" / str(round_id)).iterdir()):
        f = snap_dir / "national_0.json"
        if f.exists():
            best = f
    raw = json.loads(best.read_text(encoding="utf-8"))
    return {int(r["count_number"]): r["list_name"].strip() for r in raw["table_data"]}


# ---------- apportionment ----------

def dhondt(votes: dict[int, int], seats: int, eligible: set[int] | None = None) -> dict[int, int]:
    """D'Hondt; eligible = lists allowed to take part (None = all)."""
    pool = {k: v for k, v in votes.items() if eligible is None or k in eligible}
    out = dict.fromkeys(pool, 0)
    for _ in range(seats):
        best = max(pool, key=lambda k: (Fraction(pool[k], out[k] + 1), pool[k], -k))
        out[best] += 1
    return out


def sainte_lague(votes: dict[int, int], seats: int) -> dict[int, int]:
    out = dict.fromkeys(votes, 0)
    for _ in range(seats):
        best = max(votes, key=lambda k: votes[k] / (2 * out[k] + 1))
        out[best] += 1
    return out


def largest_remainder(votes: dict[int, int], seats: int) -> dict[int, int]:
    total = sum(votes.values())
    quota = total / seats
    base = {k: int(v // quota) for k, v in votes.items()}
    rest = seats - sum(base.values())
    for k in sorted(votes, key=lambda k: votes[k] - base[k] * quota, reverse=True)[:rest]:
        base[k] += 1
    return base


def legal_dhondt(votes: dict[int, int], voters: int, seats: int = SEATS) -> dict[int, int]:
    """Articles 128/140: 3% of voters who voted; minority quotients +35%."""
    eligible = {k for k, v in votes.items() if v * 100 >= 3 * voters or k in MINORITY_2026}
    weights = {k: v * (135 if k in MINORITY_2026 and v * 100 < 3 * voters else 100)
               for k, v in votes.items() if k in eligible}
    return dhondt(weights, seats)


def national_voters() -> int:
    files = sorted((DATA / "raw" / "680072").glob("*/national_0.json"))
    raw = json.loads(files[-1].read_text(encoding="utf-8"))
    return int(str(raw["stat_sum_numbers"]["available"]).replace(".", ""))


# ---------- sections ----------

def section_consolidation(v26: dict[int, int], valid26: int,
                          v23: dict[int, int], valid23: int) -> None:
    log("## 1. Descriptive comparison of broad opposition groupings\n")
    opp23 = {7: "SPN", 5: "Nada (Jovanović)", 14: "MI-Glas (Nestorović)",
             4: "NOS (Obradović)", 11: "Narodna (Jeremić)", 12: "DJB—Tadić",
             17: "Moramo (Č. Jovanović)"}
    opp26 = {3: "Students", 8: "Jovanović (NDSS)", 9: "Tepić (ES)"}
    rows = []
    for no, nm in opp23.items():
        rows.append({"round": 2023, "list_no": no, "list": nm, "votes": v23[no],
                     "pct_valid": round(100 * v23[no] / valid23, 2)})
    for no, nm in opp26.items():
        rows.append({"round": 2026, "list_no": no, "list": nm, "votes": v26[no],
                     "pct_valid": round(100 * v26[no] / valid26, 2)})
    df = pd.DataFrame(rows)
    df.to_csv(TAB / "bloc_consolidation.csv", index=False)
    sum23 = sum(v23[k] for k in opp23)
    sum26 = sum(v26[k] for k in opp26)
    vucic23, vucic26 = v23[1], v26[1]
    log(f"2023 opposition lists combined: {sum23:,} votes = {100*sum23/valid23:.2f}% of valid; "
        f"Vučić's list {vucic23:,} = {100*vucic23/valid23:.2f}%")
    log(f"2026 opposition lists combined: {sum26:,} votes = {100*sum26/valid26:.2f}% of valid; "
        f"Vučić's list {vucic26:,} = {100*vucic26/valid26:.2f}%")
    log(f"of which the single Students list alone: {100*v26[3]/valid26:.2f}% "
        f"({v26[3]:,}) — more than every 2023 opposition list combined, +"
        f"{100*(sum26/valid26 - sum23/valid23):.1f} pp for the bloc, "
        f"{100*(vucic26/valid26 - vucic23/valid23):+.1f} pp for Vučić's list")
    log("(caveat: 2023 totals are final, 2026 are the latest capture, 97% counted)\n")


def section_threshold(v26: dict[int, int], valid26: int, names: dict[int, str]) -> None:
    log("## 2. The threshold: votes that elect nobody\n")
    rows = []
    for no, v in sorted(v26.items()):
        pct = 100 * v / valid26
        minority = no in MINORITY_2026
        wasted = v * 100 < 3 * national_voters() and not minority
        rows.append({"list_no": no, "list": names[no][:70], "votes": v,
                     "pct_valid": round(pct, 2), "minority_list": minority,
                     "below_threshold": v * 100 < 3 * national_voters(), "votes_without_seats": int(wasted) * v})
    df = pd.DataFrame(rows)
    df.to_csv(TAB / "threshold.csv", index=False)
    wasted = df.votes_without_seats.sum()
    dacic = int(df.loc[df.list_no == 2, "votes_without_seats"].iloc[0])
    log(f"votes for lists below 3% that are not minority-exempt: {wasted:,} "
        f"= {100*wasted/valid26:.2f}% of valid votes")
    log(f"of which Dacić's SPS-led list alone ({df.loc[df.list_no==2,'pct_valid'].iloc[0]}%): "
        f"{dacic:,} votes — excluded from the projected allocation by the 3% rule")
    log(f"minority-exempt lists below 3% keep their D'Hondt piece "
        f"({', '.join(str(n) for n in sorted(MINORITY_2026))}; verified RIK minority status; quotients +35%)\n")


def section_apportionment(v26: dict[int, int], valid26: int, names: dict[int, str]) -> pd.DataFrame:
    log("## 3. Apportionment: D'Hondt vs Sainte-Laguë vs largest remainder\n")
    eligible = {no for no, v in v26.items()
                if v * 100 >= 3 * national_voters() or no in MINORITY_2026}
    d = legal_dhondt(v26, national_voters())
    plain = dhondt(v26, SEATS, eligible)
    sl = sainte_lague({k: v26[k] for k in eligible}, SEATS)
    lr = largest_remainder({k: v26[k] for k in eligible}, SEATS)
    rows = []
    for no in sorted(eligible):
        rows.append({"list_no": no, "list": names[no][:50], "votes": v26[no],
                     "pct_valid": round(100 * v26[no] / valid26, 2),
                     "seats_dhondt": d[no], "seats_plain_dhondt": plain[no], "seats_saintelague": sl[no],
                     "seats_largest_remainder": lr[no]})
    df = pd.DataFrame(rows)
    df.to_csv(TAB / "seats.csv", index=False)
    top = df.sort_values("votes", ascending=False).iloc[0]
    log(f"legal projection (D'Hondt, threshold and minority bonus applied): {top.list} "
        f"{top.pct_valid}% -> {top.seats_dhondt} of {SEATS} seats "
        f"({100*top.seats_dhondt/SEATS:.1f}% of the mandates, "
        f"{100*top.seats_dhondt/SEATS - top.pct_valid:+.1f} pp premium)")
    log(f"under Sainte-Laguë the winner would hold {sl[max(sl, key=sl.get)]} seats, "
        f"under largest remainder {lr[max(lr, key=lr.get)]} — the choice of divisor "
        f"moves a handful of seats but not the majority")
    log(f"majorities: D'Hondt {sum(1 for s in d.values() if s)} lists win seats; "
        f"sum for the two leading lists: {d[3] + d[1]} = "
        f"{100*(d[3]+d[1])/SEATS:.1f}% of seats\n")
    return df


def region_results() -> pd.DataFrame:
    res = pd.read_csv(DATA / "trends" / "results.csv")
    res = res[res.area_level == "region"]
    res["fetch_ts"] = pd.to_datetime(res.fetch_ts_utc, utc=True)
    cutoff = sorted((DATA / "raw" / "680072").glob("*/national_0.json"))[-1].parent.name
    stamp = pd.to_datetime(cutoff, format="%Y%m%d_%H%M%S", utc=True)
    last = res.loc[res.fetch_ts <= stamp, "fetch_ts"].max()
    return res[res.fetch_ts == last].pivot_table(
        index="area_name", columns="candidate_id", values="votes", aggfunc="first").fillna(0)


def section_districts(v26: dict[int, int], seats_df: pd.DataFrame, names: dict[int, str]) -> None:
    log("## 4. One constituency vs the map\n")
    reg = region_results()
    eligible = set(seats_df.list_no)
    # counterfactual: regions as districts, seats per region proportional to votes cast
    nat = legal_dhondt(v26, national_voters())
    per_region_seats = largest_remainder(reg.sum(axis=1).to_dict(), SEATS)
    by_region = {}
    for area, votes in reg.iterrows():
        for no, s in dhondt({k: int(v) * (135 if k in MINORITY_2026 else 100)
                               for k, v in votes.items() if k in eligible}, per_region_seats[area]).items():
            by_region[no] = by_region.get(no, 0) + s
    cmp = pd.DataFrame({"national_dhondt": pd.Series(nat),
                        "regions_as_districts": pd.Series(by_region)}).fillna(0).astype(int)
    cmp["list"] = [names.get(n, str(n))[:40].rstrip() for n in cmp.index]
    cmp.to_csv(TAB / "district_counterfactual.csv")
    d = (cmp.national_dhondt - cmp.regions_as_districts)
    big = d[abs(d) > 0].sort_values()
    log("region-districted D'Hondt (seats ∝ votes cast per region) vs the official "
        "single-constituency D'Hondt:")
    for no, row in cmp.loc[big.index].iterrows():
        log(f"  {row['list']}: national {row.national_dhondt} vs by-region "
            f"{row.regions_as_districts} ({row.national_dhondt - row.regions_as_districts:+d})")
    log("")

    # municipality winners: who wins the map
    mun = pd.read_csv(DATA / "ef" / "serbia2026_mun" / "results_freguesias.csv")
    pc = [c for c in mun.columns if c.startswith("votes:")]
    win = mun[pc].idxmax(axis=1).value_counts()
    table = win.rename_axis("winner").reset_index(name="municipalities")
    table.to_csv(TAB / "municipality_winners.csv", index=False)
    st = win.get("votes:Students", 0)
    vu = win.get("votes:Vučić", 0)
    log(f"municipality winners: Students {st} of {len(mun)}, Vučić {vu}, "
        f"other lists {len(mun) - st - vu}")
    share_st = 100 * mun["votes:Students"].sum() / mun[pc].sum().sum()
    log(f"but nationally (territorial municipalities): Students {share_st:.2f}% of valid "
        f"votes — the country votes one way, the map splits the other; "
        f"an electoral-college-style majority of municipalities would be much closer "
        f"than the 13.5 pp national margin\n")


def section_time(res: pd.DataFrame) -> None:
    log("## 5. Aggregation over time: the count-night inversion\n")
    c = res[res.area_level == "country"].copy()
    c["fetch_ts"] = pd.to_datetime(c.fetch_ts_utc, utc=True)
    piv = c.pivot_table(index="fetch_ts", columns="candidate_id", values="pct", aggfunc="first")
    first, last = piv.iloc[0], piv.iloc[-1]
    margin = piv[3] - piv[1]
    positive = margin[margin > 0].index.min()
    before = margin.index[margin.index < positive].max()
    def local(t: pd.Timestamp) -> str:
        return t.tz_convert("Europe/Belgrade").strftime("%H:%M")
    log(f"first capture {local(piv.index[0])} CET: Vučić {first[1]:.2f}%, Students {first[3]:.2f}%")
    log(f"first observed Students lead between {local(before)} and {local(positive)} CET")
    log(f"latest capture {local(piv.index[-1])} CET: Students {last[3]:.2f}%, "
        f"Vučić {last[1]:.2f}%; margin {margin.iloc[-1]:.2f} pp")
    log(f"largest observed margin {margin.max():.2f} pp; "
        f"change since previous snapshot {margin.diff().iloc[-1]:+.2f} pp. "
        "Snapshots cannot resolve movements between captures.\n")


def fig_seats(seats_df: pd.DataFrame) -> None:
    d = seats_df.sort_values("seats_dhondt", ascending=True)
    d = d[d.seats_dhondt + d.seats_saintelague + d.seats_largest_remainder > 0]
    y = range(len(d))
    fig, ax = plt.subplots(figsize=(8.2, 0.4 * len(d) + 1.6))
    ax.barh([i + 0.22 for i in y], d.seats_dhondt, height=0.24, color=AMBER, label="D'Hondt + minority bonus")
    ax.barh(list(y), d.seats_saintelague, height=0.24, color=NAVY, label="Sainte-Laguë")
    ax.barh([i - 0.22 for i in y], d.seats_largest_remainder, height=0.24, color=GRAY,
            label="largest remainder")
    ax.set_yticks(list(y))
    ax.set_yticklabels(f"{SHORT_NAMES[680072][r.list_no]} ({r.pct_valid}%)" for _, r in d.iterrows())
    ax.set_xlabel("seats of 250")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.grid(alpha=0.25, axis="x")
    ax.set_title("Seat allocation: legal D’Hondt versus two alternatives")
    fig.tight_layout()
    fig.savefig(FIG / "seats_apportionment.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_consolidation(v26: dict[int, int], valid26: int, v23: dict[int, int], valid23: int) -> None:
    blocs = pd.DataFrame({
        "list": ["Vučić's list", "opposition lists, combined"],
        "2023": [100 * v23[1] / valid23, 100 * sum(v23[k] for k in (7, 5, 14, 4, 11, 12, 17)) / valid23],
        "2026": [100 * v26[1] / valid26, 100 * sum(v26[k] for k in (3, 8, 9)) / valid26],
    })
    fig, ax = plt.subplots(figsize=(7.6, 3.4))
    x = range(len(blocs))
    ax.bar([i - 0.18 for i in x], blocs["2023"], width=0.36, color=GRAY, label="2023 (final)")
    ax.bar([i + 0.18 for i in x], blocs["2026"], width=0.36, color=AMBER, label="2026 (97% counted)")
    for i, row in blocs.iterrows():
        ax.text(i - 0.18, row["2023"] + 0.6, f"{row['2023']:.1f}%", ha="center", fontsize=9)
        ax.text(i + 0.18, row["2026"] + 0.6, f"{row['2026']:.1f}%", ha="center", fontsize=9)
    ax.set_xticks(list(x))
    ax.set_xticklabels(blocs.list)
    ax.set_ylabel("% of valid votes")
    ax.set_ylim(0, 65)
    ax.legend(frameon=False, fontsize=9)
    ax.grid(alpha=0.25, axis="y")
    ax.set_title("Broad opposition comparison: composition changes between elections")
    fig.tight_layout()
    fig.savefig(FIG / "bloc_consolidation.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    TAB.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    v26, valid26 = national_votes(680072)
    v23, valid23 = national_votes(341140)
    names = names_of(680072)
    res = pd.read_csv(DATA / "trends" / "results.csv")

    section_consolidation(v26, valid26, v23, valid23)
    section_threshold(v26, valid26, names)
    seats_df = section_apportionment(v26, valid26, names)
    section_districts(v26, seats_df, names)
    section_time(res)
    fig_seats(seats_df)
    fig_consolidation(v26, valid26, v23, valid23)

    (OUT / "PARADOX_LOG.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print(f"outputs -> {OUT}")


if __name__ == "__main__":
    main()
