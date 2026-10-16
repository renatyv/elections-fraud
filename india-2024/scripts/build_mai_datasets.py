"""Build analysis-tool (MAI-format) datasets from the collected sources.

Outputs (each a directory with results_freguesias.csv):

  data/mai_pc_2024    — 2024 Lok Sabha, units = parliamentary constituencies
                         (official ECI in-rolls export; 542 PCs, Surat unopposed)
                         + results_all_previous.csv (2014 linked by PC name)
  data/mai_pc_2014    — 2014 control, same unit (ECI candidate-wise + PC turnout)
  data/mai_up_ac_2024 — Uttar Pradesh 2024, units = assembly segments (Form 20),
                         candidate columns labeled with parties by matching the
                         per-PC Form-20 column sums to the official PC totals
  data/mai_up_ac_2014 — UP 2014 control at the same AC grain (booth electors +
                         booth results aggregated)

Unit rows carry key/name/path so that swing_vs_previous and the district
correlations of analysis-tool work. `voted` is always total ballots polled
(valid + rejected; for the 2014 UP control only valid votes are available);
party columns are candidate votes grouped by party.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"

# in-rows party names are ECI abbreviations; the 2014 exports use full names
UP_KEEP = ["BJP", "SP", "INC", "BSP", "RLD", "ASPKR", "ADAL"]
# full 2014 party names → ECI abbreviations, so 2014/2024 columns share names
ABBR = {
    "Bharatiya Janata Party": "BJP", "Indian National Congress": "INC",
    "All India Trinamool Congress": "AITC", "Bahujan Samaj Party": "BSP",
    "Samajwadi Party": "SP", "Shiv Sena": "SHS",
    "All India Anna Dravida Munnetra Kazhagam": "AIADMK", "Telugu Desam Party": "TDP",
    "Yuvajana Sramika Rythu Congress Party": "YSRCP",
    "Communist Party of India (Marxist)": "CPI(M)", "Independent": "IND", "NOTA": "NOTA",
}
KEEP_2014 = ["BJP", "INC", "AITC", "BSP", "SP", "SHS", "AIADMK", "TDP", "YSRCP", "CPI(M)", "IND", "NOTA"]


def _finish(df: pd.DataFrame, keep_parties: list[str] | None) -> pd.DataFrame:
    if "valid" in df.columns:
        df["null_votes"] = df["voted"] - df["valid"]
        df["blank_votes"] = 0.0
    # parent territory = second path component (state nationally, PC in UP)
    df["parent_key"] = df["path"].astype(str).str.split(" > ").str[1]
    """votes:* wide columns, Others lumped, MAI frame columns ordered."""
    votes = [c for c in df.columns if c.startswith("votes:")]
    if keep_parties is not None:
        main = [f"votes:{p}" for p in keep_parties if f"votes:{p}" in df.columns]
        df["votes:Others"] = df[votes].drop(columns=main).sum(axis=1)
        votes = main + ["votes:Others"]
    keep = ["key", "level", "name", "path", "parent_key", "registered_voters", "voted",
            "blank_votes", "null_votes"] + votes
    return df[keep]


def _state_slug(s: pd.Series) -> pd.Series:
    return s.str.replace(" ", "", regex=False).str.replace("&", "and", regex=False).str.lower()


def national_2024() -> pd.DataFrame:
    ir = pd.read_csv(
        DATA / "results_pc" / "in-rolls_2024_constituencywise_detailed_result.csv",
        encoding="utf-8-sig",
    )
    polled_col = "Total Votes Polled In\nThe Constituency"
    ir["party"] = ir["Party Name"].fillna("NOTA")
    g = ir.groupby(["State Name", "PC Name"], sort=False)
    meta = g.agg(electors=("Total Electors", "first"), polled=(polled_col, "first"),
                 valid=("Valid Votes", "first"))
    votes = ir.groupby(["State Name", "PC Name", "party"])["Total"].sum().unstack("party")
    votes.columns = [f"votes:{c}" for c in votes.columns]
    df = meta.join(votes).reset_index()
    df = df.rename(columns={"State Name": "state", "PC Name": "name",
                            "electors": "registered_voters", "polled": "voted"})
    # unique keys: state slug + per-state sequence
    df["key"] = _state_slug(df.state) + "-" + df.groupby("state").cumcount().add(1).astype(str)
    df["path"] = "India > " + df.state + " > " + df.name
    df["level"] = 3
    out = _finish(df, None)  # keep all national party columns
    out_dir = DATA / "mai_pc_2024"
    out_dir.mkdir(exist_ok=True)
    out.to_csv(out_dir / "results_freguesias.csv", index=False)
    print(f"mai_pc_2024: {len(out)} PCs, turnout {100 * out.voted.sum() / out.registered_voters.sum():.2f}%, "
          f"BJP {100 * out['votes:BJP'].sum() / out.voted.sum():.2f}% of ballots")
    return out


def national_2014() -> pd.DataFrame:
    cand = pd.read_csv(DATA / "control_2014" / "eci-2014-candidate-wise.csv")
    turn = pd.read_csv(DATA / "control_2014" / "eci-2014-pc-turnout.csv")
    for c in ["Total Electors", "Total Voters"]:
        turn[c] = pd.to_numeric(turn[c].astype(str).str.replace(",", "", regex=False))
    cand["Party"] = cand["Party"].fillna("NOTA").map(lambda p: ABBR.get(p, p))
    cand = cand.rename(columns={"Constituency": "PC Name"})
    votes = cand.groupby(["State", "PC Name", "Party"])["Votes"].sum().unstack("Party")
    votes.columns = [f"votes:{c}" for c in votes.columns]
    t = turn.set_index(["State", "PC Name"])[["Total Electors", "Total Voters"]]
    df = t.join(votes).reset_index()
    df = df.rename(columns={"State": "state", "PC Name": "name",
                            "Total Electors": "registered_voters", "Total Voters": "voted"})
    df["key"] = _state_slug(df.state) + "-" + df.groupby("state").cumcount().add(1).astype(str)
    df["path"] = "India > " + df.state + " > " + df.name
    df["level"] = 3
    valid = cand.groupby(["State", "PC Name"])["Votes"].sum().rename("valid")
    df = df.merge(valid, left_on=["state", "name"], right_index=True, how="left")
    out = _finish(df, KEEP_2014)
    out_dir = DATA / "mai_pc_2014"
    out_dir.mkdir(exist_ok=True)
    out.to_csv(out_dir / "results_freguesias.csv", index=False)
    print(f"mai_pc_2014: {len(out)} PCs, turnout {100 * out.voted.sum() / out.registered_voters.sum():.2f}%, "
          f"BJP {100 * out['votes:BJP'].sum() / out.voted.sum():.2f}% of ballots")
    return out


def _norm(s: str) -> str:
    return " ".join(str(s).upper().replace("&", "AND").replace("-", " ").replace(".", "").split())


def link_2014_to_2024(prev: pd.DataFrame) -> None:
    """results_all_previous.csv for the 2024 dir: 2014 rows keyed to 2024 PC keys.

    Match on (state, name); fall back to name only when the name is unique on
    both sides (state renames like Orissa→Odisha, Delhi→NCT; but two
    Aurangabads in different states must not collapse onto one key)."""
    cur = pd.read_csv(DATA / "mai_pc_2024" / "results_freguesias.csv")
    cur["_nm"] = cur.name.map(_norm)
    cur["_st"] = cur.path.str.split(" > ").str[1].map(_norm)
    prev["_nm"] = prev.name.map(_norm)
    prev["_st"] = prev.path.str.split(" > ").str[1].map(_norm)
    by_state = cur.drop_duplicates(["_st", "_nm"]).set_index(["_st", "_nm"])["key"]
    name_counts = cur["_nm"].value_counts()
    unique_names = set(name_counts[name_counts == 1].index)
    by_name = cur.drop_duplicates("_nm").set_index("_nm")["key"]

    def _key(r: pd.Series):
        k = by_state.get((r["_st"], r["_nm"]))
        if pd.notna(k):
            return k
        if r["_nm"] in unique_names:
            return by_name[r["_nm"]]
        return None

    prev["key"] = prev.apply(_key, axis=1)
    linked = prev.dropna(subset=["key"]).drop(columns=["_nm", "_st"], errors="ignore")
    linked.to_csv(DATA / "mai_pc_2024" / "results_all_previous.csv", index=False)
    print(f"  linked 2014→2024 PCs: {len(linked)} of {len(prev)} (2024 total {cur.key.nunique()}); "
          f"duplicate keys: {int(linked.key.duplicated().sum())}")


def up_ac_2024() -> None:
    ac = pd.read_csv(DATA / "form20" / "parsed" / "up_ac_clean.csv")
    ir = pd.read_csv(
        DATA / "results_pc" / "in-rolls_2024_constituencywise_detailed_result.csv",
        encoding="utf-8-sig",
    )
    ir_up = ir[ir["State Name"] == "Uttar Pradesh"]
    cand_cols = [c for c in ac.columns if c.startswith("votes:c")]
    rows, diag = [], []
    for pc, g in ac.groupby("pc_name"):
        off = ir_up[ir_up["PC Name"] == pc]
        off = off[~off["Party Name"].eq("NOTA")].sort_values("Total", ascending=False)
        off_totals = off["Total"].to_numpy()
        form_totals = g[cand_cols].sum()
        n = min(len(off_totals), len(form_totals))
        # rank-pair matching: PC-level column sums vs official totals, both sorted desc
        cols_by_size = form_totals.sort_values(ascending=False).index.tolist()
        rank_party = {rank: off.iloc[rank]["Party Name"] for rank in range(n)}
        col_party = {c: rank_party[i] for i, c in enumerate(cols_by_size[:n])}
        err = abs(sorted(form_totals, reverse=True)[:n] - off_totals[:n]).sum() / off_totals[:n].sum()
        diag.append({"pc": pc, "n_official": len(off), "n_form": int((form_totals > 0).sum()),
                     "match_err": err, "col_party": col_party})
        for _, r in g.iterrows():
            votes: dict[str, float] = {}
            for c in cand_cols:
                v = r[c]
                if v > 0 and c in col_party:
                    p = col_party[c]
                    votes[p] = votes.get(p, 0) + v
            votes["NOTA"] = r["nota"]
            rows.append({"ac": f"{int(r.ac_no)}-{r.ac_name}", "pc": pc, "district": r.district,
                         "registered_voters": r.registered_voters, "voted": r.voted,
                         "valid": r.valid_votes + r.nota,
                         **{f"votes:{k}": v for k, v in votes.items()}})
    df = pd.DataFrame(rows)
    df["key"] = df.ac
    df["name"] = df.ac
    df["path"] = "Uttar Pradesh > " + df.pc
    df["level"] = 3
    out = _finish(df, UP_KEEP)
    out_dir = DATA / "mai_up_ac_2024"
    out_dir.mkdir(exist_ok=True)
    out.to_csv(out_dir / "results_freguesias.csv", index=False)
    d = pd.DataFrame(diag).sort_values("match_err", ascending=False)
    d.to_csv(out_dir / "party_matching_diagnostics.csv", index=False)
    pd.DataFrame([{"pc": r["pc"], "col": c, "party": p} for r in diag for c, p in r["col_party"].items()]
                 ).to_csv(out_dir / "pc_candidate_party_map.csv", index=False)
    print(f"mai_up_ac_2024: {len(out)} ACs ({out.registered_voters.notna().sum()} with electors); "
          f"party-match err median {d.match_err.median():.3%}, worst {d.match_err.max():.3%} ({d.iloc[0].pc})")
    return out


def up_ac_2014() -> None:
    import tarfile

    with tarfile.open(DATA / "control_2014" / "booth-results-up.csv.tgz") as tf:
        v14 = pd.read_csv(tf.extractfile("uttar-pradesh.csv"))
    el = pd.read_csv(DATA / "control_2014" / "booth-wise-electors.csv")
    reg = el[el.state.eq("S24")].groupby("ac")["total"].sum()
    votes = v14.pivot_table(index="ac", columns="party", values="votes", aggfunc="sum")
    votes = votes.rename(columns={p: ABBR.get(p, p) for p in votes.columns})
    keep_2014 = [p for p in ["BJP", "SP", "INC", "BSP"] if p in votes.columns]
    votes["Others"] = votes.drop(columns=keep_2014).sum(axis=1)
    votes = votes[keep_2014 + ["Others"]]
    votes.columns = [f"votes:{c}" for c in votes.columns]
    pc_names = v14.drop_duplicates("ac").set_index("ac")["pc_name"]
    df = votes.join(reg.rename("registered_voters")).join(v14.groupby("ac")["votes"].sum().rename("voted"))
    df["valid"] = df["voted"]
    df = df.reset_index()
    df["key"] = [f"ac-{int(a)}" for a in df.ac]
    df["name"] = [f"AC {int(a)}" for a in df.ac]
    df["path"] = "Uttar Pradesh > " + pc_names.reindex(df.ac).astype(str).values
    df["level"] = 3
    out = _finish(df, keep_2014)
    out_dir = DATA / "mai_up_ac_2014"
    out_dir.mkdir(exist_ok=True)
    out.to_csv(out_dir / "results_freguesias.csv", index=False)
    print(f"mai_up_ac_2014: {len(out)} ACs, turnout {100 * out.voted.sum() / out.registered_voters.sum():.2f}% "
          f"(valid-only numerator)")


def up_booth_2014() -> None:
    """UP 2014 at polling-station level: the one year with per-booth electors."""
    import tarfile

    with tarfile.open(DATA / "control_2014" / "booth-results-up.csv.tgz") as tf:
        v14 = pd.read_csv(tf.extractfile("uttar-pradesh.csv"))
    el = pd.read_csv(DATA / "control_2014" / "booth-wise-electors.csv", dtype={"ac": int})
    reg = el[el.state.eq("S24")].set_index(["ac", "booth"])["total"]
    votes = v14.pivot_table(index=["pc", "ac", "booth"], columns="party",
                            values="votes", aggfunc="sum")
    votes = votes.rename(columns={p: ABBR.get(p, p) for p in votes.columns})
    keep = [p for p in ["BJP", "SP", "INC", "BSP"] if p in votes.columns]
    votes["Others"] = votes.drop(columns=keep).sum(axis=1)
    votes = votes[keep + ["Others"]]
    votes.columns = [f"votes:{c}" for c in votes.columns]
    df = votes.join(reg.rename("registered_voters"), on=["ac", "booth"])
    df = df.dropna(subset=["registered_voters"])
    df["voted"] = df[[c for c in df.columns if c.startswith("votes:")]].sum(axis=1)
    df["valid"] = df["voted"]
    # 445 booths (0.3%) where the two ECI exports disagree on the booth key
    # (votes of another station land on this elector count, ratio up to 22x)
    df = df[df.voted.le(df.registered_voters)]
    df = df.reset_index()
    df["key"] = [f"b{int(a)}-{int(b)}" for a, b in zip(df.ac, df.booth)]
    df["name"] = df.key
    df["path"] = "Uttar Pradesh > " + df.pc.astype(str)
    df["level"] = 3  # loader treats 3 as the lowest data level
    out = _finish(df, keep)
    out_dir = DATA / "mai_up_booth_2014"
    out_dir.mkdir(exist_ok=True)
    out.to_csv(out_dir / "results_freguesias.csv", index=False)
    print(f"mai_up_booth_2014: {len(out):,} booths, turnout "
          f"{100 * out.voted.sum() / out.registered_voters.sum():.2f}% (valid-only numerator)")


if __name__ == "__main__":
    national_2024()
    prev = national_2014()
    link_2014_to_2024(prev)
    up_ac_2024()
    up_ac_2014()
    up_booth_2014()
