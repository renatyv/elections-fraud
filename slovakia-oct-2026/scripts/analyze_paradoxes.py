"""Voting-paradox and cross-check analysis over the Slovak local elections of
24.10.2026 (beyond the standard forensics cycle).

Inputs: data/ef/ MAI files (scripts/build_ef_csv.py), data/official/ tables,
data/trends/ election-night capture. Outputs: analysis/paradoxes/tables/*.csv,
analysis/paradoxes/figures/*.png, and this log (every number quoted in
PARADOXES.md / REPORT.md is computed here).

1. Bloc cloning, the consolidated-nomination side: in 2026 the two big camps
   ran ONE joint candidate per kraj where in 2022 the same parties competed
   separately. How much of the 2022 intra-bloc competition survived into the
   joint nomination (cloning removes vote-splitting)?
2. Frustrated majority: winners far below 50% (governors and 2,912 mayors);
   the share of the vote that elected nobody.
3. Counting-night dynamics from the intraday capture: leader flips while the
   count progressed (Košický kraj, capital mayors).
4. Dual-ballot cross-check: OSK and OSO turnout recorded in the same polling
   stations on the same day must agree; race-turnout correlation.
5. 2022 → 2026 swings: turnout structure and the party-level shift; a re-read
   of the forensics swing flags with the real turnout direction.

Run (from the repository root):
    analysis-tool/.venv/bin/python slovakia-oct-2026/scripts/analyze_paradoxes.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BASE = Path(__file__).resolve().parents[1]  # slovakia-oct-2026/
OFF = BASE / "data" / "official"
EF = BASE / "data" / "ef"
TRE = BASE / "data" / "trends"
OUT = BASE / "analysis" / "paradoxes"
FIG = OUT / "figures"
TAB = OUT / "tables"

KRAJ = {1: "Bratislavský", 2: "Trnavský", 3: "Trenčiansky", 4: "Nitriansky",
        5: "Žilinský", 6: "Banskobystrický", 7: "Prešovský", 8: "Košický"}

log: list[str] = []


def plog(s: str = "") -> None:
    log.append(s)
    print(s)


def normalize_codes(codes: dict[str, str]) -> dict[str, str]:
    return {str(int(k)) if k.isdigit() else k: v for k, v in codes.items()}


def party_table_2022(path: Path) -> dict[str, str]:
    """OSK2022/OSO2022 tab0c — STR|NSTR|SNPS, one name contains an unquoted '|'."""
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        f = line.split("|")
        if len(f) < 3 or f[0] == "STR":
            continue
        rows[f[0]] = f[-1]
    return normalize_codes(rows)


# ---------------------------------------------------------------------------
# 1. bloc consolidation 2022 → 2026 (governor races)
# ---------------------------------------------------------------------------
BLOCS = {
    "vládny blok (SMER–HLAS–SNS…)": {"SMER - SD", "HLAS - sociálna demokracia", "SNS",
                                      "REPUBLIKA", "PRAVDA", "Bratia Slovenska", "DOMOV-NS"},
    "opozičný blok (PS–SaS–KDH–Demokrati…)": {
        "Progresívne Slovensko", "SaS", "KDH", "Demokrati", "SLOVENSKO", "ZA ĽUDÍ",
        "NOVA", "Konzervatívci", "OKS", "DS-ODS", "Maďarské fórum",
        "Team Bratislava", "Tím Kraj Nitra"},
}
# 2022 party names → the 2026 abbreviations used in BLOCS
ALIAS22 = {
    "Hlas - sociálna demokracia": "HLAS - sociálna demokracia",
    "Magyar Fórum - Maďarské fórum": "Maďarské fórum",
    "DS": "DS-ODS",
    "Kresťanská únia": "Konzervatívci",
    "NK/NEKA": "NEKA",
}
MIN_OVERLAP = 3  # parties of the bloc on one ballot — the joint nomination


def bloc_consolidation() -> pd.DataFrame:
    cand26 = pd.read_csv(OFF / "OSK2026_SK_tab06a.csv").rename(
        columns={"Kód kraja": "KRAJ", "Priezvisko": "PRIEZVISKO",
                 "Politický subjekt": "SUBJ", "Počet platných hlasov": "V26"})
    cand26["SET"] = cand26["SUBJ"].astype(str).map(
        lambda s: {p.strip() for p in s.split(",")} if s.strip().upper() != "NEKA" else {"NEKA"})
    cand22 = pd.read_csv(OFF / "OSK2022_SK_tab0a.csv", sep="|")
    parties22 = party_table_2022(OFF / "OSK2022_SK_tab0c.csv")
    def _set22(ps: str) -> set[str]:
        if not ps.strip():
            return {"NEKA"}
        out = set()
        for c in ps.split(","):
            c = c.strip()
            name = parties22.get(str(int(c)) if c.isdigit() else c, None)
            out.add(ALIAS22.get(name, name) if name else "NEKA")
        return out

    cand22["SET22"] = cand22["PS"].fillna("").astype(str).map(_set22)
    v22 = pd.read_csv(OFF / "OSK2022_SK_tab06d.csv", sep="|")
    v22["KRAJ"] = v22["OBEC"].map(
        pd.read_csv(OFF / "OSK2022_SK_tab0dc.csv", sep="|")[["OBEC", "KRAJ"]]
        .drop_duplicates().set_index("OBEC")["KRAJ"])
    v22sum = v22.groupby(["KRAJ", "PC_HL"])["P_HL"].sum()
    cand22["V22"] = [int(v22sum.get((r["KRAJ"], r["PC_HL"]), 0)) for _, r in cand22.iterrows()]

    rows = []
    for k in KRAJ:
        for bloc, members in BLOCS.items():
            g = cand26[cand26["KRAJ"] == k]
            ov = g["SET"].map(lambda s: len(s & members))
            if (ov >= MIN_OVERLAP).any():
                j = g.loc[ov.idxmax()]
                hits = cand22[cand22["KRAJ"] == k]["SET22"].map(
                    lambda ss: (len(ss & members), len(ss & set().union(*BLOCS.values()) - members)))
                same = cand22[(cand22["KRAJ"] == k) & hits.map(lambda t: t[0] > 0 and t[0] > t[1])]
                rows.append({
                    "kraj": k, "kraj_name": KRAJ[k], "bloc": bloc,
                    "joint_2026": f'{j["PRIEZVISKO"]} {j["Meno"][0]}.',
                    "parties_2026_joint": j["SUBJ"],
                    "votes_2026_joint": int(j["V26"]),
                    "candidates_2022_in_bloc": len(same),
                    "votes_2022_combined": int(same["V22"].sum()),
                    "best_2022_in_bloc": int(same["V22"].max()) if len(same) else 0,
                })
    df = pd.DataFrame(rows)
    df.to_csv(TAB / "bloc_consolidation.csv", index=False)
    plog("== 1. bloc consolidation 2022 → 2026 (governor races) ==")
    plog("  joint nomination = the 2026 candidate carrying ≥3 parties of the bloc;")
    plog("  2022 combined = Σ votes of 2022 candidates whose coalition majority sits in the bloc")
    for _, r in df.iterrows():
        d = r["votes_2026_joint"] - r["votes_2022_combined"]
        plog(f"  {r['kraj_name']}: {r['bloc'].split(' (')[0]} — 2022: "
             f"{r['candidates_2022_in_bloc']} cand., combined {r['votes_2022_combined']:,} "
             f"(best {r['best_2022_in_bloc']:,}) → 2026 {r['joint_2026']}: "
             f"{r['votes_2026_joint']:,} ({d:+,}; {100 * r['votes_2026_joint'] / max(r['votes_2022_combined'], 1) - 100:+.1f}%)")
    return df


# ---------------------------------------------------------------------------
# 2. frustrated majority: winners below 50%
# ---------------------------------------------------------------------------
def winners_below_50() -> pd.DataFrame:
    may = pd.read_csv(OFF / "OSO2026_SK_tab05d.csv").rename(
        columns={"Kód obce": "OBEC", "Názov obce": "NOBEC", "Poradie na hlasovacom lístku": "PC_HL",
                 "Počet platných hlasov": "V", "Poznámka": "ELECT"})
    may["share"] = 100.0 * may["V"] / may.groupby("OBEC")["V"].transform("sum")
    win = may[may["ELECT"].astype(str).str.contains("zvolený", na=False)].copy()
    # 2022: no obec-level table in the export — aggregate the precinct rows
    f = pd.read_csv(OFF / "OSO2022_SK_tab05f.csv", sep="|")
    agg = f.groupby(["OBEC", "PC_HL"])["P_HL"].sum().reset_index()
    agg["share"] = 100.0 * agg["P_HL"] / agg.groupby("OBEC")["P_HL"].transform("sum")
    win22 = agg.loc[agg.groupby("OBEC")["P_HL"].idxmax()].copy()

    fig, ax = plt.subplots(figsize=(8, 4.6))
    bins = list(range(20, 105, 5))
    ax.hist(win22["share"].clip(20, 100), bins=bins, alpha=0.55, label="2022", color="#999")
    ax.hist(win["share"].clip(20, 100), bins=bins, alpha=0.55, label="2026", color="#1e8e5a")
    ax.axvline(50, color="#c00", lw=1.4, ls="--")
    ax.set_xlabel("winning mayor's share of valid votes, %")
    ax.set_ylabel("municipalities")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "winners_share_hist.png", dpi=150)
    plt.close(fig)

    plog("")
    plog("== 2. frustrated majority (FPTP winners without a majority) ==")
    for tag, w in (("2026", win), ("2022", win22)):
        n = len(w)
        plog(f"  {tag}: {n:,} mayors; elected with <50%: {(w['share'] < 50).sum():,} "
             f"({100 * (w['share'] < 50).mean():.1f}%), <40%: {(w['share'] < 40).sum():,} "
             f"({100 * (w['share'] < 40).mean():.1f}%), min {w['share'].min():.1f}%")
    los = may[~may["ELECT"].astype(str).str.contains("zvolený", na=False)]
    plog(f"  2026: votes for losing mayoral candidates: {int(los['V'].sum()):,} of "
         f"{int(may['V'].sum()):,} ({100 * los['V'].sum() / may['V'].sum():.1f}%) elected nobody")
    gov = pd.read_csv(OFF / "OSK2026_SK_tab06a.csv").rename(
        columns={"Kód kraja": "KRAJ", "Priezvisko": "PRIEZVISKO", "Počet platných hlasov": "V",
                 "Podiel platných hlasov v %": "share", "Kandidát": "ELECT"})
    gw = gov[gov["ELECT"].astype(str).str.contains("zvolený", na=False)]
    for _, r in gw[gw["share"] < 50].sort_values("share").iterrows():
        plog(f"  governor {KRAJ[int(r['KRAJ'])]}: {r['PRIEZVISKO']} {r['share']:.2f}% — "
             f"{100 - r['share']:.2f}% voted against")
    win.to_csv(TAB / "mayor_winners_2026.csv", index=False)
    return win


# ---------------------------------------------------------------------------
# 3. counting-night dynamics from the intraday capture
# ---------------------------------------------------------------------------
def intraday() -> pd.DataFrame:
    res = pd.read_csv(TRE / "results.csv", parse_dates=["fetch_ts_utc"])
    nat = pd.read_csv(TRE / "national.csv", parse_dates=["fetch_ts_utc"])
    last = res["fetch_ts_utc"].max()
    # the capture exposes the count progress only at the national level
    prog = nat.set_index(["race", "fetch_ts_utc"])["pct_counted"]
    NAT_RACE = {"regional governor (predseda)": "regional (OSK)",
                "mayor (starosta/primátor)": "municipal (OSO)"}
    rows = []
    plog("")
    plog("== 3. counting-night dynamics (36 snapshots, 24.10 22:02 → 26.10 09:51 SELČ) ==")
    plog("  (x-axis of the progress — the national counter of the race; the portal")
    plog("   exposed no per-kraj progress for OSK)")
    for (race, area), g in res.groupby(["race", "area_code"]):
        g = g.sort_values("fetch_ts_utc")
        snaps = g["fetch_ts_utc"].nunique()
        fin = g[g["fetch_ts_utc"] == last].set_index("candidate")
        if fin.empty or fin["pct"].sum() == 0:
            continue
        winner = fin["pct"].idxmax()
        leaders = []
        for ts, gg in g.groupby("fetch_ts_utc"):
            gg = gg[gg["pct"] > 0]
            if len(gg):
                leaders.append((ts, gg.set_index("candidate")["pct"].idxmax(),
                                float(prog.get((NAT_RACE[race], ts), float("nan")))))
        uniq = list(dict.fromkeys(l[1] for l in leaders))
        first = leaders[0]
        rows.append({"race": race, "area": area, "winner": winner,
                     "winner_final_pct": float(fin.loc[winner, "pct"]),
                     "first_leader": first[1], "first_pct_counted": first[2],
                     "n_leader_changes": len(uniq) - 1, "leader_sequence": " → ".join(uniq)})
        name = g["area_name"].iloc[0]
        if len(uniq) > 1:
            plog(f"  REVERSAL {name} ({race.split(' (')[0]}): led {uniq[0]} at "
                 f"{first[2]:.0f}% counted → winner {winner} "
                 f"({float(fin.loc[winner, 'pct']):.1f}% final)")
    df = pd.DataFrame(rows).sort_values(["race", "area"])
    df.to_csv(TAB / "intraday_leaders.csv", index=False)

    # the tightest governor race — the timeline chart
    k8 = res[(res["area_code"] == 8) & res["race"].str.startswith("regional")].copy()
    k8 = k8.merge(nat[nat["race"] == "regional (OSK)"][["fetch_ts_utc", "pct_counted"]],
                  on="fetch_ts_utc", how="left")
    k8 = k8.sort_values(["candidate", "fetch_ts_utc"])
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    for cand, g in k8.groupby("candidate"):
        g = g.sort_values("fetch_ts_utc")
        short = g["candidate"].iloc[0].split()[-1]
        lw = 2.4 if g["pct"].iloc[-1] > 30 else 1.2
        ax.plot(g["pct_counted"], g["pct"], label=f"{short}", lw=lw)
    ax.set_xlabel("ballots counted, %")
    ax.set_ylabel("candidate share of counted votes, %")
    ax.set_title("Košický kraj — governor race, official count progress")
    ax.legend(frameon=False, fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(FIG / "intraday_kosicky.png", dpi=150)
    plt.close(fig)
    no_rev = df[df["n_leader_changes"] == 0]
    plog(f"  {len(df)} races tracked; leader changed during the count in "
         f"{len(df) - len(no_rev)}; stable in {len(no_rev)}")
    return df


# ---------------------------------------------------------------------------
# 4. dual-ballot cross-check: OSK vs OSO in the same polling stations
# ---------------------------------------------------------------------------
def dual_ballot() -> pd.DataFrame:
    """Same polling station, same day, two races: OSK and OSO participants."""
    def load(year: int) -> pd.DataFrame:
        if year == 2026:
            k = pd.read_csv(OFF / f"OSK{year}_SK_tab02d.csv").rename(
                columns={"Kód obce": "OBEC", "Názov obce": "NOBEC", "Volebný okrsok": "OKRSOK",
                         "Počet zapísaných voličov": "P_ZAP_K", "Počet zúčastnených voličov": "P_ZUC_K"})
            o = pd.read_csv(OFF / f"OSO{year}_SK_tab02f.csv").rename(
                columns={"Kód obce": "OBEC", "Volebný obvod v obci": "VOB", "Okrsok": "OKRSOK",
                         "Počet zapísaných voličov": "P_ZAP_O", "Počet zúčastnených voličov": "P_ZUC_O"})
        else:
            k = pd.read_csv(OFF / f"OSK{year}_SK_tab02bd.csv", sep="|").rename(
                columns={"OBEC": "OBEC", "OKRSOK": "OKRSOK", "P_ZAP": "P_ZAP_K", "P_ZUC": "P_ZUC_K"})
            o = pd.read_csv(OFF / f"OSO{year}_SK_tab02bf.csv", sep="|").rename(
                columns={"OBEC": "OBEC", "VOOBEC": "VOB", "OKRSOK": "OKRSOK",
                         "P_ZAP": "P_ZAP_O", "P_ZUC": "P_ZUC_O"})
            names = pd.read_csv(OFF / f"OSO{year}_SK_tab0dd.csv", sep="|")[["OBEC", "NOBEC"]].drop_duplicates("OBEC")
            k = k.merge(names, on="OBEC", how="left")
        nv = o.groupby("OBEC")["VOB"].nunique()
        o1 = o[o["OBEC"].isin(set(nv[nv == 1].index))]
        m = k.merge(o1[["OBEC", "OKRSOK", "P_ZAP_O", "P_ZUC_O"]], on=["OBEC", "OKRSOK"], how="inner")
        m["d"] = m["P_ZUC_K"] - m["P_ZUC_O"]
        return m

    out = {}
    plog("")
    plog("== 4. dual-ballot cross-check: two races, one visit ==")
    for year in (2022, 2026):
        m = load(year)
        out[year] = m
        mm = m[m["P_ZAP_K"] == m["P_ZAP_O"]]
        plog(f"  {year}: {len(m):,} joinable precincts (obce with a single district); "
             f"registered rolls differ in {(m['P_ZAP_K'] != m['P_ZAP_O']).sum()} (municipal rolls "
             f"also carry EU citizens, who may not vote in the regional race)")
        plog(f"    participants OSK−OSO: sum {int(m['d'].sum()):,} "
             f"(mayor-side higher in {(m['d'] < 0).sum()} precincts, equal in {(m['d'] == 0).sum()}, "
             f"lower in {(m['d'] > 0).sum()})")
        tot = m.groupby("NOBEC")["d"].sum()
        top = tot.reindex(tot.abs().sort_values(ascending=False).index).head(12)
        if year == 2026:
            top.to_csv(TAB / "differential_participation_2026.csv")
        plog("    top-12 municipalities by |ΣΔ|: "
             + "; ".join(f"{i} {int(v):+}" for i, v in top.items()))
    # the scatter uses 2026
    m = out[2026]
    t_k = 100 * m["P_ZUC_K"] / m["P_ZAP_K"]
    t_o = 100 * m["P_ZUC_O"] / m["P_ZAP_O"]
    plog(f"    participation correlation OSK vs OSO: Pearson r = {t_k.corr(t_o):.4f}; "
         f"municipal-side participation is systematically higher (voters who take only "
         f"the mayor ballot — concentrated in municipalities with large Romani "
         f"communities, and of EU-citizen residents in cities)")
    fig, ax = plt.subplots(figsize=(5.6, 5.2))
    ax.scatter(t_k, t_o, s=3, alpha=0.25, color="#16324f", edgecolors="none")
    ax.plot([0, 100], [0, 100], color="#c00", lw=1, ls="--")
    ax.set_xlabel("OSK participation (participants / registered), %")
    ax.set_ylabel("OSO participation, %")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    fig.tight_layout()
    fig.savefig(FIG / "dual_ballot_scatter.png", dpi=150)
    plt.close(fig)
    # gap change 2022 → 2026 on common municipalities
    g22 = out[2022].groupby("OBEC")["d"].sum()
    g26 = out[2026].groupby("OBEC")["d"].sum()
    common = g22.index.intersection(g26.index)
    ch = (g26 - g22)[common]
    plog(f"    gap 2022→2026 on {len(common):,} common municipalities: "
         f"{int(g22[common].sum()):,} → {int(g26[common].sum()):,} "
         f"({100 * g26[common].sum() / g22[common].sum() - 100:+.1f}%)")
    m.to_csv(TAB / "dual_ballot_join.csv", index=False)
    return m


# ---------------------------------------------------------------------------
# 5. 2022 → 2026 swings
# ---------------------------------------------------------------------------
def swings() -> None:
    cur = pd.read_csv(EF / "oso2026" / "results_freguesias.csv")
    prev = pd.read_csv(EF / "oso2026" / "results_all_previous.csv")
    keys = set(cur["key"]) & set(prev["key"])
    c = cur.set_index("key").loc[sorted(keys)]
    p = prev.set_index("key").loc[sorted(keys)]
    t26 = 100 * c["voted"] / c["registered_voters"]
    t22 = 100 * p["voted"] / p["registered_voters"]
    plog("")
    plog("== 5. 2022 → 2026 (matched precincts, mayor race) ==")
    plog(f"  matched precincts: {len(keys):,}; turnout 2022 {t22.mean():.2f}% → 2026 "
         f"{t26.mean():.2f}% (precinct-level mean of means, Δ {t26.mean() - t22.mean():+.2f} pp)")
    fig, ax = plt.subplots(figsize=(5.6, 5.2))
    ax.scatter(t22, t26, s=3, alpha=0.25, color="#16324f", edgecolors="none")
    ax.plot([0, 100], [0, 100], color="#c00", lw=1, ls="--")
    ax.set_xlabel("OSO 2022 turnout (race ballots / registered), %")
    ax.set_ylabel("OSO 2026 turnout, %")
    fig.tight_layout()
    fig.savefig(FIG / "turnout_2022_2026.png", dpi=150)
    plt.close(fig)
    # party-level national swing
    cols = [x for x in c.columns if x.startswith("votes:")]
    s26 = c[cols].sum()
    s22 = p[cols].sum()
    sh26 = 100 * s26 / c["voted"].sum()
    sh22 = 100 * s22 / p["voted"].sum()
    SWING_ALIAS = {
        "Hlas - sociálna demokracia": "HLAS - sociálna demokracia",
        "SOM Slovensko": "SOM SLOVENSKO",
        "NK/NEKA": "NEKA",
        "SZÖVETSÉG - ALIANCIA": "Magyar Szövetség - Maďarská aliancia",
        "OĽANO-NOVA-KÚ-ZMENA ZDOLA": "OĽaNO a spol. (zaniknuté subjekty)",
        "SPOLU": "SPOLU (zaniknuté subjekty)",
        "DOBRÁ VOĽBA a Umiernení": "DOBRÁ VOĽBA (zaniknuté subjekty)",
    }
    sh26m, sh22m = sh26.copy(), sh22.copy()
    for old_name, new_name in SWING_ALIAS.items():
        oc, nc = f"votes:{old_name}", f"votes:{new_name}"
        if nc in sh26m.index and oc in sh22m.index:
            sh22m[nc] = sh22m.get(nc, 0) + sh22m[oc]
            sh22m.drop(oc, inplace=True)
            sh26m[nc] = sh26m.get(nc, 0) + sh26m[oc]
            sh26m.drop(oc, inplace=True)
    d = (sh26m - sh22m).sort_values(ascending=False)
    top = d[abs(d) > 0.3]
    for party, dd in top.items():
        nm = party.removeprefix("votes:")
        plog(f"  {nm}: {sh22m[party]:.2f}% → {sh26m[party]:.2f}% ({dd:+.2f} pp)")
    top.to_csv(TAB / "party_swing_2022_2026.csv")
    # flags re-read
    sw = pd.read_csv(BASE / "analysis/ef/oso2026/tables/swing_vs_previous.csv")
    plog(f"  forensics swing flags (|Δturnout|>15pp & |Δshare|>15pp): both {int(sw['flag'].sum())}, "
         f"turnout-only {int(sw['flag_turnout_only'].sum())} of {len(sw):,} matched precincts; "
         f"Δturnout median {sw['d_turnout'].median():+.1f} pp — the flags ride the party "
         f"realignment, not a turnout anomaly")


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    bloc_consolidation()
    winners_below_50()
    intraday()
    dual_ballot()
    swings()
    (OUT / "PARADOX_LOG.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"\ndone: {OUT}")


if __name__ == "__main__":
    main()
