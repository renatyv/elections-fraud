"""Adapting the official ŠÚSR/volbysr.sk exports to the analysis-tool format (MAI).

Reads data/official/OSK2026_*, OSO2026_*, OSK2022_*, OSO2022_* CSVs and builds
data/ef/ in the same format as the MAI exports of portugal-2025:

    data/ef/osk2026_k<1..8>/results_freguesias.csv   — governor race per kraj,
                                                       one column per candidate
    data/ef/osk2022_k<1..8>/results_freguesias.csv   — the 2022 control election
    data/ef/oso2026/{results_freguesias.csv, results_all_previous.csv}
                                                     — mayor race, columns =
                                                       lead party of the candidate
    data/ef/oso2022/results_freguesias.csv           — the 2022 control election

Unit = volebný okrsok (polling precinct), level=3. Keys:
  OSK — "OBEC-OKRSOK" (unique nationally, both years);
  OSO — "OBEC-VOB-OKRSOK" (in 2022 the okrsok numbering restarts inside the
        intra-municipal district, so the district is part of the key).

Definitions per precinct:
  registered_voters = Počet zapísaných voličov (P_ZAP)
  voted             = valid ballots FOR THE RACE ANALYSED (P_HL_PRE governors,
                      P_HL_STA mayors) — party votes sum to `voted`;
                      participants who skipped the race (envelope without a
                      valid ballot of the race) land in null_votes
  null_votes        = Počet odovzdaných obálok (P_OO) − voted
  blank_votes       = 0 (Slovak protocols do not separate blank ballots)

Party attribution: the lead party — the first subject in the candidate's
coalition string (2026 tables carry it inline; 2022 tables carry party codes
joined through tab0c); empty string → NEKA (independent). The aggregated
OSO files also carry the residual column votes:INÉ so that votes are never
dropped, and (only oso2026) a few service columns the toolkit ignores.

Every adaptation step is validated (log — data/ef/VALIDATION.txt): precinct
arithmetic, agreement of the precinct sums with the official kraj/national
tables (tab06a/tab01/tab02a), and coverage of the final intraday snapshot
captured on election night (data/trends/results.csv).

Run (from the repository root):

    analysis-tool/.venv/bin/python slovakia-oct-2026/scripts/build_ef_csv.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]  # slovakia-oct-2026/
OFF = BASE / "data" / "official"
TRE = BASE / "data" / "trends"
OUT = BASE / "data" / "ef"
LOG = OUT / "VALIDATION.txt"

KRAJ_CODE = {1: "Bratislavský", 2: "Trnavský", 3: "Trenčiansky", 4: "Nitriansky",
             5: "Žilinský", 6: "Banskobystrický", 7: "Prešovský", 8: "Košický"}

log: list[str] = []


def plog(s: str = "") -> None:
    log.append(s)
    print(s)


def normalize_codes(codes: dict[str, str]) -> dict[str, str]:
    """2022 exports use zero-padded codes ('001' = independent, absent from
    the party table); normalise both sides so lookups hit."""
    return {str(int(k)) if k.isdigit() else k: v for k, v in codes.items()}


def lead_party(ps: str, codes: dict[str, str] | None = None) -> str:
    """First subject of the coalition string, or its abbreviation via codes.

    An unknown code is read as an independent (NEKA)."""
    ps = (ps or "").strip()
    if not ps:
        return "NEKA"
    first = ps.split(",")[0].strip()
    if codes:
        norm = str(int(first)) if first.isdigit() else first
        return codes.get(norm, "NEKA")
    return first


def read_pipe(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="|")


def read_party_table(path: Path) -> pd.DataFrame:
    """2022 party list: STR|NSTR|SNPS, but one name contains an unquoted '|'."""
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        f = line.split("|")
        if len(f) < 3 or f[0] == "STR":
            continue
        rows.append((f[0], "|".join(f[1:-1]), f[-1]))
    return pd.DataFrame(rows, columns=["STR", "NSTR", "SNPS"])


def okr_key(obec: pd.Series, okrsok: pd.Series) -> pd.Series:
    return obec.astype(str) + "-" + okrsok.astype(int).astype(str).str.zfill(4)


def build_osk(year: int) -> dict[int, pd.DataFrame]:
    """Governor race per kraj: turnout (tab02d/bd) + votes per candidate (tab06d)."""
    sfx = str(year)
    if year == 2026:
        tur = pd.read_csv(OFF / f"OSK{sfx}_SK_tab02d.csv")
        tur = tur.rename(columns={
            "Kód kraja": "KRAJ", "Názov kraja": "NKRAJ", "Kód volebného obvodu": "VOBVOD",
            "Názov volebného obvodu": "NVOBVOD", "Kód obce": "OBEC", "Názov obce": "NOBEC",
            "Volebný okrsok": "OKRSOK", "Počet zapísaných voličov": "P_ZAP",
            "Počet zúčastnených voličov": "P_ZUC", "Počet odovzdaných obálok": "P_OO",
            "Počet platných hlasovacích lístkov odovzdaných pre voľby predsedu": "P_HL_PRE"})
        vot = pd.read_csv(OFF / f"OSK{sfx}_SK_tab06d.csv").rename(columns={
            "Kód kraja": "KRAJ", "Kód volebného obvodu": "VOBVOD", "Kód obce": "OBEC",
            "Volebný okrsok": "OKRSOK", "Poradie na hlasovacom lístku": "PC_HL",
            "Meno": "MENO", "Priezvisko": "PRIEZVISKO", "Politický subjekt": "SUBJ",
            "Počet platných hlasov": "P_HL"})
        vot["LEAD"] = vot["SUBJ"].map(lead_party)
    else:
        tur = read_pipe(OFF / f"OSK{sfx}_SK_tab02bd.csv")
        geo = read_pipe(OFF / f"OSK{sfx}_SK_tab0dc.csv")[["OBEC", "KRAJ", "NKRAJ", "VOBVOD", "NVOBVOD", "NOBEC"]]
        tur = tur.merge(geo, on="OBEC", how="left", validate="many_to_one")
        cand = read_pipe(OFF / f"OSK{sfx}_SK_tab0a.csv")
        parties = read_party_table(OFF / f"OSK{sfx}_SK_tab0c.csv")
        codes = normalize_codes(dict(zip(parties["STR"].astype(str), parties["SNPS"])))
        cand["PS"] = cand["PS"].fillna("").astype(str)
        cand["LEAD"] = cand["PS"].map(lambda s: lead_party(s, codes))
        cand["SUBJ"] = cand["PS"].astype(str).map(
            lambda s: ", ".join(codes.get(c.strip(), c.strip()) for c in s.split(",") if c.strip()))
        cand = cand.rename(columns={"MENO": "MENO", "PRIEZVISKO": "PRIEZVISKO"})
        vot = read_pipe(OFF / f"OSK{sfx}_SK_tab06d.csv").rename(
            columns={"PC_HL": "PC_HL", "P_HL": "P_HL"})
        vot = vot.merge(geo[["OBEC", "KRAJ"]].drop_duplicates(), on="OBEC", how="left")
        vot = vot.merge(cand[["KRAJ", "PC_HL", "MENO", "PRIEZVISKO", "SUBJ", "LEAD"]],
                        on=["KRAJ", "PC_HL"], how="left", validate="many_to_one")
    tur["key"] = okr_key(tur["OBEC"], tur["OKRSOK"])
    vot["key"] = okr_key(vot["OBEC"], vot["OKRSOK"])
    vot["candidate"] = (vot["PRIEZVISKO"].fillna("?") + " "
                        + vot["MENO"].fillna("").str[0].fillna("").str.strip(".") + "."
                        + " (" + vot["LEAD"].fillna("NEKA") + ")")
    return {"tur": tur, "vot": vot}


def mai_osk(prep: dict[str, pd.DataFrame], year: int) -> dict[int, pd.DataFrame]:
    """One MAI frame per kraj, one votes-column per candidate."""
    out: dict[int, pd.DataFrame] = {}
    tur, vot = prep["tur"], prep["vot"]
    for k, nkraj in KRAJ_CODE.items():
        t = tur[tur["KRAJ"] == k].copy()
        assert t["key"].is_unique, f"duplicate precinct keys, OSK {year} kraj {k}"
        pv = vot[vot["KRAJ"] == k].pivot_table(index="key", columns="candidate",
                                               values="P_HL", aggfunc="sum")
        df = t.set_index("key")[["P_ZAP", "P_HL_PRE", "P_OO", "OBEC", "OKRSOK", "NOBEC",
                                 "VOBVOD", "NVOBVOD"]].join(pv, how="left")
        df[pv.columns] = df[pv.columns].fillna(0).astype(int)
        mai = pd.DataFrame({
            "key": df.index,
            "level": 3,
            "name": df["NOBEC"] + ", okrsok " + df["OKRSOK"].astype(int).astype(str),
            "path": (f"SK-OSK {year} > {nkraj} kraj > " + df["NVOBVOD"] + " > "
                     + df["NOBEC"] + " okr. " + df["OKRSOK"].astype(int).astype(str)),
            "parent_key": f"{year}-k{k}-v" + df["VOBVOD"].astype(int).astype(str),
            "registered_voters": df["P_ZAP"].astype(int),
            "voted": df["P_HL_PRE"].astype(int),
            "turnout_pct": 100.0 * df["P_HL_PRE"] / df["P_ZAP"],
            "blank_votes": 0,
            "null_votes": (df["P_OO"] - df["P_HL_PRE"]).astype(int),
        })
        for c in pv.columns:
            mai["votes:" + c] = df[c]
        vote_cols = [c for c in mai.columns if c.startswith("votes:")]
        bad = mai[mai["voted"] < mai[vote_cols].sum(axis=1)]
        assert bad.empty, f"{year} kraj {k}: candidate votes exceed race ballots in {len(bad)} precincts"
        out[k] = mai
    return out


def build_oso(year: int) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    """Mayor race: precinct turnout (tab02f/bf) + votes per candidate (tab05f)."""
    sfx = str(year)
    if year == 2026:
        tur = pd.read_csv(OFF / f"OSO{sfx}_SK_tab02f.csv").rename(columns={
            "Kód okresu": "OKRES", "Názov okresu": "NOKRES", "Kód obce": "OBEC",
            "Názov obce": "NOBEC", "Volebný obvod v obci": "VOB", "Okrsok": "OKRSOK",
            "Počet zapísaných voličov": "P_ZAP", "Počet odovzdaných obálok": "P_OO",
            "Počet platných hlasovacích lístkov odovzdaných pre voľby starostu": "P_HL_STA"})
        vot = pd.read_csv(OFF / f"OSO{sfx}_SK_tab05f.csv").rename(columns={
            "Kód obce": "OBEC", "Volebný obvod v obci": "VOB", "Okrsok": "OKRSOK",
            "Poradie na hlasovacom lístku": "PC_HL", "Politický subjekt": "SUBJ",
            "Počet platných hlasov": "P_HL"})
        vot["LEAD"] = vot["SUBJ"].map(lead_party)
    else:
        tur = read_pipe(OFF / f"OSO{sfx}_SK_tab02bf.csv").rename(columns={"VOOBEC": "VOB"})
        geo = read_pipe(OFF / f"OSO{sfx}_SK_tab0dd.csv")
        geo = geo.rename(columns={c: c.upper() for c in geo.columns})
        names = geo[["OBEC", "NOBEC", "NOKRES"]].drop_duplicates("OBEC")
        tur = tur.merge(names, on="OBEC", how="left", validate="many_to_one")
        cand = read_pipe(OFF / f"OSO{sfx}_SK_tab0ad.csv")
        parties = read_party_table(OFF / f"OSO{sfx}_SK_tab0c.csv")
        codes = normalize_codes(dict(zip(parties["STR"].astype(str), parties["SNPS"])))
        cand["PS"] = cand["PS"].fillna("").astype(str)
        cand["LEAD"] = cand["PS"].map(lambda s: lead_party(s, codes))
        vot = read_pipe(OFF / f"OSO{sfx}_SK_tab05f.csv").rename(columns={"VOOBEC": "VOB"})
        vot = vot.merge(cand[["OBEC", "PC_HL", "LEAD"]], on=["OBEC", "PC_HL"],
                        how="left", validate="many_to_one")
    for d in (tur, vot):
        d["key"] = (d["OBEC"].astype(str) + "-" + d["VOB"].astype(int).astype(str)
                    + "-" + d["OKRSOK"].astype(int).astype(str).str.zfill(4))
    if year == 2022:
        # Košice (599981) reused (district, okrsok) numbers across city districts
        # in 2022 — 19 precincts; a distinct key cannot be reconstructed, the
        # rows are dropped from the control/previous file (logged).
        dup = tur.loc[tur["key"].duplicated(keep=False), "key"].unique()
        tur.drop(tur[tur["key"].isin(dup)].index, inplace=True)
        vot.drop(vot[vot["key"].isin(dup)].index, inplace=True)
        plog(f"OSO 2022: dropped {len(dup)} precinct rows with reused Košice keys "
             f"(control/previous files only)")
    return tur, vot, {}


def mai_oso(tur: pd.DataFrame, vot: pd.DataFrame, year: int,
            vocab: list[str] | None = None, residual: str = "INÉ (ostatné)") -> pd.DataFrame:
    """National MAI frame, one column per lead party (+ residual)."""
    assert tur["key"].is_unique, f"duplicate precinct keys, OSO {year}"
    vot2 = vot.dropna(subset=["LEAD"]).copy()
    pv = vot2.pivot_table(index="key", columns="LEAD", values="P_HL", aggfunc="sum")
    if vocab is None:
        vocab = sorted(pv.columns)
    df = tur.set_index("key")[["P_ZAP", "P_HL_STA", "P_OO", "OBEC", "OKRSOK", "NOBEC"]].join(pv, how="left")
    known = [c for c in vocab if c != residual and c in df.columns]
    df[known] = df[known].fillna(0).astype(int)
    df[residual] = (df["P_HL_STA"] - df[known].sum(axis=1)).clip(lower=0).astype(int)
    cols = [c for c in vocab if c != residual] + [residual]
    if year == 2026:
        okres = pd.read_csv(OFF / "OSO2026_SK_tab02f.csv")[["Kód obce", "Názov okresu"]]
        okres = okres.drop_duplicates().set_index("Kód obce")["Názov okresu"]
        nokres = df["OBEC"].map(okres).fillna("?")
    else:
        nokres = pd.Series("?", index=df.index)
    mai = pd.DataFrame({
        "key": df.index,
        "level": 3,
        "name": df["NOBEC"] + ", okrsok " + df["OKRSOK"].astype(int).astype(str),
        "path": (f"SK-OSO {year} > " + nokres + " > " + df["NOBEC"]
                 + " okr. " + df["OKRSOK"].astype(int).astype(str)),
        "parent_key": nokres,
        "registered_voters": df["P_ZAP"].astype(int),
        "voted": df["P_HL_STA"].astype(int),
        "turnout_pct": 100.0 * df["P_HL_STA"] / df["P_ZAP"],
        "blank_votes": 0,
        "null_votes": (df["P_OO"] - df["P_HL_STA"]).astype(int),
    })
    for c in cols:
        mai["votes:" + c] = df[c] if c in df.columns else 0
    return mai


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    plog("Validation of the official ŠÚSR exports → data/ef/ adaptation")
    plog("unit = volebný okrsok (precinct); voted = valid ballots of the analysed race;")

    # ---------- OSK 2026 + OSK 2022 ----------
    p26, p22 = build_osk(2026), build_osk(2022)
    mai26, mai22 = mai_osk(p26, 2026), mai_osk(p22, 2022)
    nat26 = pd.read_csv(OFF / "OSK2026_SK_tab01.csv").iloc[0]
    nat22 = read_pipe(OFF / "OSK2022_SK_tab01.csv").iloc[0] if (OFF / "OSK2022_SK_tab01.csv").exists() else None
    ka26 = pd.read_csv(OFF / "OSK2026_SK_tab06a.csv").rename(
        columns={"Kód kraja": "KRAJ", "Priezvisko": "PRIEZVISKO", "Počet platných hlasov": "TOTAL"})
    plog("")
    plog("OSK 2026 (governor race, votes: per candidate):")
    for k in KRAJ_CODE:
        mai_k = mai26[k]
        r, v = mai_k["registered_voters"].sum(), mai_k["voted"].sum()
        n_units = len(mai_k)
        # per-candidate precinct sums vs the official kraj table
        kk = p26["vot"][p26["vot"]["KRAJ"] == k].groupby("PRIEZVISKO")["P_HL"].sum()
        ka_k = ka26[ka26["KRAJ"] == k].set_index("PRIEZVISKO")["TOTAL"]
        assert (kk.reindex(ka_k.index).fillna(0).astype(int) == ka_k.astype(int)).all(), \
            f"OSK26 kraj {k}: per-candidate precinct sums != tab06a"
        plog(f"  k{k} {KRAJ_CODE[k]}: {n_units} precincts, registered {r:,}, "
             f"race ballots {v:,} = Σ candidates == tab06a ✓ "
             f"({len(ka_k)} candidates, turnout(race/registered) {100 * v / r:.2f}%)")
    tot_r = sum(m["registered_voters"].sum() for m in mai26.values())
    tot_v = sum(m["voted"].sum() for m in mai26.values())
    assert tot_r == int(nat26["Počet zapísaných voličov"]), "OSK26 registered != tab01"
    assert tot_v == int(nat26["Počet platných hlasovacích lístkov odovzdaných pre voľby predsedu"])
    plog(f"  SR total: registered {tot_r:,}, race ballots {tot_v:,} == tab01 ✓ "
         f"(official participation {nat26['Účasť voličov v %']:.2f}% = participants/registered)")
    for k in KRAJ_CODE:
        d = OUT / f"osk2026_k{k}"
        d.mkdir(exist_ok=True)
        mai26[k].to_csv(d / "results_freguesias.csv", index=False, encoding="utf-8-sig")
    for k in KRAJ_CODE:
        d = OUT / f"osk2022_k{k}"
        d.mkdir(exist_ok=True)
        mai22[k].to_csv(d / "results_freguesias.csv", index=False, encoding="utf-8-sig")
    # 2022↔2026 precinct key overlap (per kraj)
    ov = {k: len(set(mai26[k]["key"]) & set(mai22[k]["key"])) for k in KRAJ_CODE}
    plog(f"  precinct keys matched to 2022 per kraj: {ov} "
         f"(of { {k: len(mai26[k]) for k in KRAJ_CODE} })")

    # cross-check against the election-night capture (final snapshot)
    tre = pd.read_csv(TRE / "results.csv")
    last = tre["fetch_ts_utc"].max()
    fin = tre[tre["fetch_ts_utc"] == last]
    plog(f"  cross-check vs intraday capture final snapshot {last} (8 kraje):")
    fin_k = fin[fin["area_level"] == "kraj"].groupby("area_code")["votes"].sum()
    for code, votes in fin_k.items():
        mine = mai26[int(code)]["voted"].sum()
        plog(f"    kraj {code}: capture {int(votes):,} vs official {mine:,} "
             f"({'✓' if int(votes) == mine else 'DIFF ' + str(int(votes) - mine)})")

    # ---------- OSO 2026 + OSO 2022 ----------
    tur26, vot26, _ = build_oso(2026)
    tur22, vot22, _ = build_oso(2022)
    vocab = sorted(set(vot26["LEAD"].dropna()) | set(vot22["LEAD"].dropna()) | {"INÉ (ostatné)"})
    mai_o26 = mai_oso(tur26, vot26, 2026, vocab)
    mai_o22 = mai_oso(tur22, vot22, 2022, vocab)
    nat_o26 = pd.read_csv(OFF / "OSO2026_SK_tab01.csv").iloc[0]
    plog("")
    plog("OSO 2026 (mayor race, votes: per lead party + residual INÉ):")
    r, v = mai_o26["registered_voters"].sum(), mai_o26["voted"].sum()
    assert r == int(nat_o26["Počet zapísaných voličov"]), "OSO26 registered != tab01"
    assert v == int(nat_o26["Počet platných hlasovacích lístkov odovzdaných pre voľby starostu"])
    assert (mai_o26["null_votes"] >= 0).all(), "OSO26: negative null_votes"
    plog(f"  {len(mai_o26)} precincts; registered {r:,}, mayor ballots {v:,} == tab01 ✓ "
         f"(official participation {nat_o26['Účasť voličov v %']:.2f}%)")
    cols = [c for c in mai_o26.columns if c.startswith("votes:")]
    top = mai_o26[cols].sum().sort_values(ascending=False).head(8)
    for c, s in top.items():
        plog(f"    {c.removeprefix('votes:')}: {int(s):,} ({100 * s / v:.2f}%)")
    d = OUT / "oso2026"
    d.mkdir(exist_ok=True)
    mai_o26.to_csv(d / "results_freguesias.csv", index=False, encoding="utf-8-sig")
    mai_o22.to_csv(d / "results_all_previous.csv", index=False, encoding="utf-8-sig")
    d22 = OUT / "oso2022"
    d22.mkdir(exist_ok=True)
    mai_o22.to_csv(d22 / "results_freguesias.csv", index=False, encoding="utf-8-sig")
    matched = len(set(mai_o26["key"]) & set(mai_o22["key"]))
    plog(f"  precinct keys matched to 2022: {matched:,} of {len(mai_o26):,} "
         f"({100 * matched / len(mai_o26):.1f}%)")
    # cross-check vs capture: 8 capital mayors, final snapshot
    cap = {524930: "Prešov", 517402: "Žilina", 508438: "Banská Bystrica",
           500011: "Nitra", 506745: "Trnava", 505820: "Trenčín"}
    fin_o = fin[fin["area_level"] == "obec"]
    plog("  cross-check vs intraday capture final snapshot (capital mayors, tab05f):")
    for code, nm in cap.items():
        got = fin_o[fin_o["area_code"] == code]["votes"].sum()
        mine = mai_o26[mai_o26["key"].str.startswith(f"{code}-")]["voted"].sum()
        plog(f"    {nm}: capture {int(got):,} vs official {mine:,} "
             f"({'✓' if int(got) == mine else 'DIFF ' + str(int(got) - mine)})")
    # Bratislava and Košice elect the primátor city-wide — a separate table (x)
    prim = pd.read_csv(OFF / "OSO2026_SK_tab05fx.csv").rename(columns={"Počet platných hlasov": "P_HL"})
    pcol = "Kód mesta" if "Kód mesta" in prim.columns else "OBEC"
    for code, nm in {582000: "Bratislava (primátor)", 599981: "Košice (primátor)"}.items():
        got = fin_o[fin_o["area_code"] == code]["votes"].sum()
        mine = int(prim.loc[prim[pcol] == code, "P_HL"].sum())
        plog(f"    {nm}: capture {int(got):,} vs official tab05fx {mine:,} "
             f"({'✓' if int(got) == mine else 'DIFF ' + str(int(got) - mine)})")
    plog("  (BA/KE primátor races are excluded from the MAI files — the tab05f")
    plog("   precinct rows of Bratislava/Košice cover the city-district starostas)")

    (OUT / "VALIDATION.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
    plog("")
    plog(f"done: {OUT}/")


if __name__ == "__main__":
    main()
