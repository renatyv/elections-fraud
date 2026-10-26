#!/usr/bin/env python3
"""Intraday count dynamics — Brazil, 2nd round 25.10.2026 (from data/trends/).

13 snapshots of the TSE results portal (20:07 UTC 25.10 → 07:52 UTC 26.10):
  - president: Lula × Flávio Bolsonaro share trajectory as counting progressed,
    decomposition of the swing by reporting order of states;
  - incremental swing decomposition by UF (which states' batches moved the line);
  - turnout / blank / null trajectory over the night;
  - governor runoffs in 6 states: final margins and intraday lead changes;
  - cross-checks of the final captured totals against the per-section CSVs.

Output: analysis/trends/trends_summary.json, swing_decomposition.csv,
uf_final_twoway.csv (+ prints headline numbers).
Run from analysis-tool/: uv run python ../brazil-oct-2026-round-1/scripts/analyze_trends.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

BR = Path(__file__).resolve().parents[1]
TRENDS = BR / "data" / "trends"
OUT = BR / "analysis" / "trends"


def main() -> None:
    nat = pd.read_csv(TRENDS / "national.csv", parse_dates=["fetch_ts_utc"])
    res = pd.read_csv(TRENDS / "results.csv", parse_dates=["fetch_ts_utc"])
    reg = pd.read_csv(TRENDS / "regions.csv", parse_dates=["fetch_ts_utc"])

    summary: dict = {"n_snapshots": int(nat.fetch_ts_utc.nunique()),
                     "window_utc": [str(nat.fetch_ts_utc.min()), str(nat.fetch_ts_utc.max())]}

    # ── president: share trajectory vs counting progress ────────────────────
    pres = nat[nat.race == "president"].sort_values("fetch_ts_utc")
    pres_res = res[(res.race == "president") & (res.area_level == "country")].merge(
        pres[["fetch_ts_utc", "pct_counted", "source_ts"]], on=["fetch_ts_utc", "source_ts"],
        suffixes=("", "_nat"))
    traj = pres_res[["fetch_ts_utc", "pct_counted", "candidate", "pct", "votes"]]
    piv = traj.pivot_table(index="pct_counted", columns="candidate", values="pct")
    summary["president_trajectory"] = piv.round(2).reset_index().to_dict(orient="records")

    first, last = piv.index.min(), piv.index.max()
    l_first, l_last = piv.loc[first, "LULA"], piv.loc[last, "LULA"]
    summary["president_lula_swing_pp"] = round(float(l_last - l_first), 2)
    summary["president_first_last"] = {
        "pct_counted": [float(first), float(last)],
        "LULA": [float(l_first), float(l_last)],
        "FLAVIO BOLSONARO": [float(piv.loc[first, "FLAVIO BOLSONARO"]),
                              float(piv.loc[last, "FLAVIO BOLSONARO"])],
    }

    # final captured totals (votes at last fetch)
    fin = pres_res[pres_res.fetch_ts_utc == pres_res.fetch_ts_utc.max()]
    summary["president_final_votes"] = {r.candidate: int(r.votes) for r in fin.itertuples()}
    nat_fin = pres.iloc[-1]
    summary["president_final"] = {
        "registered": int(nat_fin.registered), "voters": int(nat_fin.voters),
        "turnout_pct": float(nat_fin.turnout_pct),
        "blank": int(nat_fin.votes_blank), "null": int(nat_fin.votes_invalid),
        "units_total": int(nat_fin.units_total), "units_counted": int(nat_fin.units_counted),
        "source_ts_final": str(nat_fin.source_ts),
        "lula_pct_valid": float(fin[fin.candidate == "LULA"].pct.iloc[0]),
        "bolsonaro_pct_valid": float(fin[fin.candidate == "FLAVIO BOLSONARO"].pct.iloc[0]),
        "margin_pp": round(float(fin[fin.candidate == "LULA"].pct.iloc[0]
                                 - fin[fin.candidate == "FLAVIO BOLSONARO"].pct.iloc[0]), 2),
    }

    # half-counted midpoint: where did the race stand
    mid = piv.index[(piv.index.to_numpy() - 50).__abs__().argsort()[0]]
    summary["president_at_half_counted"] = {"pct_counted": float(mid),
                                            "LULA": float(piv.loc[mid, "LULA"]),
                                            "FLAVIO BOLSONARO": float(piv.loc[mid, "FLAVIO BOLSONARO"])}

    # ── state reporting order vs national swing ──────────────────────────────
    # use the first snapshot where each UF passed 50% counted (from regions.csv)
    pr = reg[reg.race == "president"].copy()
    pr["half"] = pr.pct_counted >= 50.0
    reached = pr[pr.half].groupby("area_code").fetch_ts_utc.min()
    uf_fin = pr[pr.fetch_ts_utc == pr.fetch_ts_utc.max()][
        ["area_code", "area_name", "turnout_pct", "pct_counted"]]
    # per-UF final two-way share of the president (from results.csv uf rows)
    uf_res = res[(res.race == "president") & (res.area_level == "uf")
                 & (res.fetch_ts_utc == res.fetch_ts_utc.max())]
    tw = uf_res.pivot_table(index="area_code", columns="candidate", values="votes")
    tw["LULA_tw"] = 100.0 * tw["LULA"] / (tw["LULA"] + tw["FLAVIO BOLSONARO"])
    tw = tw.join(reached.rename("reached_50pct"))
    tw["area_name"] = uf_fin.set_index("area_code").area_name
    tw["early_reporter"] = tw.reached_50pct < tw.reached_50pct.median()
    grp = tw.groupby("early_reporter").agg(
        ufs=("LULA_tw", "size"), mean_lula_tw=("LULA_tw", "mean"),
        total_votes=("LULA", lambda s: int(tw.loc[s.index, ["LULA", "FLAVIO BOLSONARO"]].sum(axis=1).sum())))
    summary["early_vs_late_states"] = {
        "early (first half to 50% counted)": {"n_ufs": int(grp.loc[True, "ufs"]),
                                               "mean_lula_twoway_pct": round(float(grp.loc[True, "mean_lula_tw"]), 2)},
        "late (second half)": {"n_ufs": int(grp.loc[False, "ufs"]),
                               "mean_lula_twoway_pct": round(float(grp.loc[False, "mean_lula_tw"]), 2)},
        "note": "UFs grouped by the snapshot at which they crossed 50% of sections counted",
    }
    tw.reset_index().to_csv(OUT / "uf_final_twoway.csv", index=False)

    # ── full snapshot timeline: shares, turnout of counted, blank/null share ──
    fin_pct = pres_res.pivot_table(index="fetch_ts_utc", columns="candidate", values="pct")
    tl = pres.set_index("fetch_ts_utc").join(fin_pct)
    tl["invalid_pct"] = (tl.votes_invalid / tl.votes_total * 100).round(2)
    tl["blank_pct"] = (tl.votes_blank / tl.votes_total * 100).round(2)
    tlr = tl.reset_index()[[
        "fetch_ts_utc", "source_ts", "pct_counted", "LULA", "FLAVIO BOLSONARO",
        "turnout_pct", "invalid_pct", "blank_pct"]].rename(
        columns={"FLAVIO BOLSONARO": "BOLSONARO"})
    tlr["fetch_ts_utc"] = tlr.fetch_ts_utc.astype(str)
    summary["timeline"] = tlr.to_dict(orient="records")

    # ── incremental swing decomposition by UF ─────────────────────────────────
    # Between consecutive snapshots, each UF adds a batch of two-way votes with
    # its own share; contribution_u = (ΔV_u / V_t)·(s_u − S_prev), summing
    # exactly to the two-way change of the step. S is computed from the same
    # UF sums to keep the identity exact — in the first ~2 snapshots the
    # portal's UF table lags the country ticker (see uf_vs_country_coverage).
    ufp = res[(res.race == "president") & (res.area_level == "uf")]
    snaps = sorted(pres.fetch_ts_utc.unique())
    L = ufp[ufp.candidate == "LULA"].pivot_table(
        index="fetch_ts_utc", columns="area_code", values="votes").reindex(snaps)
    B = ufp[ufp.candidate == "FLAVIO BOLSONARO"].pivot_table(
        index="fetch_ts_utc", columns="area_code", values="votes").reindex(snaps)
    V = L + B                                    # cumulative two-way votes per UF
    S = 100.0 * L.sum(axis=1) / V.sum(axis=1)    # national two-way from UF sums
    nat_tw = pres_res.pivot_table(index="fetch_ts_utc", columns="candidate",
                                  values="votes").reindex(snaps)
    S_country = 100.0 * nat_tw["LULA"] / (nat_tw["LULA"] + nat_tw["FLAVIO BOLSONARO"])
    summary["uf_vs_country_coverage"] = [
        {"pct_counted": float(p), "uf_two_way": int(V.sum(axis=1).iloc[i]),
         "country_two_way": int((nat_tw["LULA"] + nat_tw["FLAVIO BOLSONARO"]).iloc[i]),
         "lula_tw_uf": round(float(S.iloc[i]), 2),
         "lula_tw_country": round(float(S_country.iloc[i]), 2)}
        for i, p in enumerate(pres.set_index("fetch_ts_utc").pct_counted.reindex(snaps))]
    pctc = pres.set_index("fetch_ts_utc").pct_counted.reindex(snaps)

    steps = []
    contrib = {uf: 0.0 for uf in V.columns}      # pp contribution, anchor onwards
    ANCHOR = 2                                   # snapshot index with ~85% uf coverage
    phase_of = lambda p0: "early" if p0 < 2 else ("middle" if p0 < 95 else "tail")
    phase_stats: dict[str, dict[str, float]] = {}
    for i in range(1, len(snaps)):
        dv = V.iloc[i] - V.iloc[i - 1]
        dl = L.iloc[i] - L.iloc[i - 1]
        dV_total = float(V.iloc[i].sum() - V.iloc[i - 1].sum())
        if dV_total <= 0:
            continue
        s_u = dl / dv.where(dv > 0)              # Lula share of the batch
        w = dv / V.iloc[i].sum()
        c = w * (100.0 * s_u - S.iloc[i - 1])
        c = c.fillna(0.0)
        if i > ANCHOR:                           # steps starting at the anchor
            for uf, val in c.items():
                contrib[uf] += float(val)
        dl_total = float(L.iloc[i].sum() - L.iloc[i - 1].sum())
        ph = phase_of(float(pctc.iloc[i - 1]))
        agg = phase_stats.setdefault(ph, {"votes": 0.0, "lula": 0.0})
        agg["votes"] += dV_total
        agg["lula"] += dl_total
        steps.append({
            "from_pct": float(pctc.iloc[i - 1]), "to_pct": float(pctc.iloc[i]),
            "phase": ph,
            "inc_two_way_votes": int(round(dV_total)),
            "inc_lula_twoway_pct": round(100.0 * dl_total / dV_total, 2),
            "national_lula_tw_after": round(float(S.iloc[i]), 2),
        })
    summary["counting_steps"] = steps
    summary["phase_batches"] = {
        ph: {"two_way_votes": int(round(a["votes"])),
             "lula_twoway_pct": round(100.0 * a["lula"] / a["votes"], 2)}
        for ph, a in sorted(phase_stats.items())}
    summary["swing_decomposed"] = {
        "note": "per-UF contributions anchored at the 1.56%-counted snapshot, the "
                "first where the portal's UF table covers ~85% of the country "
                "ticker; the 58.59%→52.16% country swing before that cannot be "
                "decomposed by UF",
        "anchor_pct_counted": float(pctc.iloc[ANCHOR]),
        "anchor_lula_tw": round(float(S.iloc[ANCHOR]), 2),
        "final_lula_tw": round(float(S.iloc[-1]), 2),
        "swing_pp": round(float(S.iloc[-1] - S.iloc[ANCHOR]), 2),
        "sum_contributions_pp": round(sum(contrib.values()), 2),
    }

    dec = pd.DataFrame({
        "area_code": list(contrib.keys()),
        "swing_contribution_pp": [round(v, 3) for v in contrib.values()],
    }).merge(tw[["area_name", "LULA_tw", "reached_50pct"]].reset_index()
             .rename(columns={"index": "area_code"}), on="area_code", how="left")
    dec = dec.sort_values("swing_contribution_pp")
    dec.to_csv(OUT / "swing_decomposition.csv", index=False)
    fmt_top = lambda rows: [
        {"uf": r.area_code.upper(), "pp": round(r.swing_contribution_pp, 2),
         "lula_tw_final": round(float(r.LULA_tw), 1)} for r in rows]
    summary["swing_by_uf"] = {
        "note": "contribution to the two-way swing of Lula from the anchor "
                f"({summary['swing_decomposed']['anchor_pct_counted']:.2f}% counted, "
                f"{summary['swing_decomposed']['anchor_lula_tw']:.2f}% Lula) to the "
                "final; positive = moved the line towards Lula",
        "top_against_lula": fmt_top(dec.head(5).itertuples()),
        "top_for_lula": fmt_top(dec.tail(5).sort_values("swing_contribution_pp").itertuples()),
    }

    # ── governor runoffs: intraday lead changes ───────────────────────────────
    govs_dyn = []
    for race, g in res[res.race.str.startswith("governor")].groupby("race"):
        gf = g[g.fetch_ts_utc == g.fetch_ts_utc.max()].sort_values("votes", ascending=False)
        if len(gf) < 2:
            continue
        w_, r_ = gf.iloc[0], gf.iloc[1]
        ser = g[g.candidate.isin([w_.candidate, r_.candidate])].pivot_table(
            index="fetch_ts_utc", columns="candidate", values="pct")
        margin = ser[w_.candidate] - ser[r_.candidate]
        lead = (margin > 0).astype(int)
        changes = int((lead.diff().abs() > 0).sum())
        first_lead = str(margin[margin > 0].index.min()) if (margin > 0).any() else None
        govs_dyn.append({
            "race": race.replace("governor-", "").upper(),
            "winner": w_.candidate, "runner_up": r_.candidate,
            "margin_first_snapshot_pp": round(float(margin.iloc[0]), 2),
            "margin_final_pp": round(float(margin.iloc[-1]), 2),
            "margin_min_pp": round(float(margin.min()), 2),
            "margin_max_pp": round(float(margin.max()), 2),
            "lead_changes": changes,
            "winner_led_from": first_lead,
        })
    summary["governor_intraday"] = sorted(govs_dyn, key=lambda d: d["margin_final_pp"])


    # ── governor runoffs: final margins ───────────────────────────────────────
    govs = []
    for race, g in res[res.race.str.startswith("governor")].groupby("race"):
        gf = g[g.fetch_ts_utc == g.fetch_ts_utc.max()].sort_values("votes", ascending=False)
        top2 = gf.head(2)
        if len(top2) < 2:
            continue
        govs.append({
            "race": race.replace("governor-", "").upper(),
            "winner": top2.iloc[0].candidate, "winner_pct": float(top2.iloc[0].pct),
            "runner_up": top2.iloc[1].candidate, "runner_up_pct": float(top2.iloc[1].pct),
            "margin_pp": round(float(top2.iloc[0].pct - top2.iloc[1].pct), 2),
            "turnout_pct": float(nat[nat.race == race].iloc[-1].turnout_pct),
        })
    summary["governor_runoffs"] = sorted(govs, key=lambda d: -d["margin_pp"])

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "trends_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
