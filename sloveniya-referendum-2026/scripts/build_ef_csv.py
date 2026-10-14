"""Adapting the referendum results to the analysis-tool format (MAI export).

Reads data/derived/volisca_all.csv (scripts/build_volisca_csv.py) and builds,
for each referendum, a data/ef/<referendum>/results_freguesias.csv directory —
the same format as the MAI exports in portugal-2025 (key, level, name, path,
parent_key, registered_voters, voted, turnout_pct, blank_votes, null_votes,
votes:ZA, votes:PROTI). The standard analysis-tool pipeline runs on top:

    cd ../analysis-tool && uv run ef-analyze \
        --data ../sloveniya-referendum-2026/data/ef/preiskava \
        --out ../sloveniya-referendum-2026/analysis/preiskava \
        --title "Slovenia, ZPPre-B referendum 11.10.2026 (precincts)" \
        --controls <directories of the other three referendums>

The precinct key follows the MAI LOCAL-0XYZAB scheme (12 chars, district_key =
the district by chars [6:8]): LOCAL-0<enota><sequence number within enota>;
district_correlations then groups by the 8 electoral units. For the neighbors
test parent_key = «enota-okraj» (88 groups of ~34 precincts). Path:
«referendum > enota > okraj > precinct» ([-2] = okraj — outlier labels).

Early-voting points (precinct numbers ≥ 900, upr = 0 — electorate undefined)
are not converted to the turnout format and do not pass through the pipeline:
scripts/analyze_extra.py checks them (digit tests). Here they are used only
in completeness cross-checks.

The adaptation is validated at the same time (log — data/ef/VALIDATION.txt):
row arithmetic, agreement of electorate and turnout across the four
referendums (same precincts), coverage of the DVK national result.

Run (from sloveniya-referendum-2026/):

    ../analysis-tool/.venv/bin/python scripts/build_ef_csv.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]  # sloveniya-referendum-2026/
SRC = BASE / "data" / "derived" / "volisca_all.csv"
NAC = BASE / "data" / "derived" / "nacionalni_pregled.csv"
OUT = BASE / "data" / "ef"
LOG = OUT / "VALIDATION.txt"

REF_TITLE = {
    "preiskava": "preiskava (ZPPre-B, legislative)",
    "socialna_pomoc": "socialna_pomoc (social assistance)",
    "volilna_pravica": "volilna_pravica (non-citizen voting rights)",
    "rtv_prispevek": "rtv_prispevek (RTV Slovenija fee)",
}


def adapt(ref: str, df: pd.DataFrame) -> pd.DataFrame:
    """Precincts of one referendum → results_freguesias.csv (MAI) format."""
    df = df.sort_values(["enota_st", "okraj_rpeid", "volisce_rpeid"]).copy()
    seq = df.groupby("enota_st").cumcount() + 1  # numbering within enota (< 10 000)
    out = pd.DataFrame(
        {
            "key": "LOCAL-0" + df["enota_st"].astype(str) + seq.astype(str).str.zfill(4),
            "level": 3,
            "name": df["volisce_naz"],
            "path": REF_TITLE[ref] + " > " + df["enota_naz"] + " > "
                    + df["okraj_naz"] + " > " + df["volisce_naz"],
            "parent_key": df["enota_st"].astype(str) + "-" + df["okraj_rpeid"].astype(str),
            "registered_voters": df["upr"].astype(int),
            "voted": df["glas"].astype(int),
            "turnout_pct": 100.0 * df["glas"] / df["upr"],
            "blank_votes": 0,  # referendums have no «blank» category
            "null_votes": df["nev"].astype(int),
            "votes:ZA": df["za"].astype(int),
            "votes:PROTI": df["proti"].astype(int),
            # service columns (tracing back to volisca_all.csv; analysis-tool ignores them)
            "okraj_rpeid": df["okraj_rpeid"],
            "volisce_rpeid": df["volisce_rpeid"],
            "okraj_naz": df["okraj_naz"],
            "prestetih_glasov": df["prestetih_glasov"],
        }
    )
    assert out["key"].is_unique, f"duplicate keys in {ref}"
    assert (seq <= 9999).all()
    return out


def main() -> None:
    raw = pd.read_csv(SRC)
    raw["station"] = (raw["okraj_rpeid"].astype(str) + "_"
                      + raw["volisce_rpeid"].astype(str).str.zfill(3))
    reg = raw[raw["volisce_rpeid"] < 900].copy()
    early = raw[raw["volisce_rpeid"] >= 900].copy()
    nac = pd.read_csv(NAC)
    nat = nac[nac["nivo"] == "slovenija"].set_index("referendum")

    OUT.mkdir(parents=True, exist_ok=True)
    log: list[str] = [
        "Validation of the volisca_all.csv → data/ef/<referendum>/results_freguesias.csv adaptation",
        f"source: {SRC.name}; regular precincts — numbers < 900, early-voting points — >= 900",
        "",
    ]

    adapted: dict[str, pd.DataFrame] = {}
    for ref in REF_TITLE:
        d = adapt(ref, reg[reg.referendum == ref])
        adapted[ref] = d
        (OUT / ref).mkdir(parents=True, exist_ok=True)
        d.to_csv(OUT / ref / "results_freguesias.csv", index=False, encoding="utf-8-sig")

        # row arithmetic on the raw DVK numbers
        g = reg[reg.referendum == ref]
        d_bal = (g["za"] + g["proti"] - g["velj"]).abs().max()
        d_tot = (g["velj"] + g["nev"] - g["glas"]).abs().max()
        n_early = int((early.referendum == ref).sum())
        log += [
            f"[{ref}] {REF_TITLE[ref]}",
            f"  precincts: {len(d)} (early-voting points listed separately: {n_early}); "
            f"enota: {g.enota_st.nunique()}, okraj: {g.okraj_rpeid.nunique()}",
            f"  ZA+PROTI=valid: max discrepancy {d_bal}; "
            f"valid+invalid=ballots: {d_tot}",
            f"  electorate {g.upr.sum():,}, ballots {g.glas.sum():,} "
            f"(turnout {100 * g.glas.sum() / g.upr.sum():.2f}%), "
            f"ZA {100 * g.za.sum() / g.velj.sum():.2f}% of valid votes",
            f"  coverage of the DVK national result: electorate "
            f"{100 * g.upr.sum() / nat.loc[ref, 'upr']:.1f}%, ballots "
            f"{100 * g.glas.sum() / nat.loc[ref, 'glas']:.2f}% "
            f"(the rest — early voting, OMNIA, postal, embassies)",
        ]
        # discrepancy between the adapted sums and the volisca precinct totals
        for col_a, col_r in (("votes:ZA", "za"), ("votes:PROTI", "proti"),
                             ("null_votes", "nev"), ("voted", "glas")):
            assert int(d[col_a].sum()) == int(g[col_r].sum()), ref
        log.append("  sums of the adapted CSV = sums of volisca_all.csv: yes")
        log.append("")

    # cross-referendum checks: the same precincts in all four ballots
    piv_upr = reg.pivot_table(index="station", columns="referendum", values="upr", aggfunc="first")
    bad_upr = piv_upr[piv_upr.nunique(axis=1) > 1]
    log += ["Precinct electorate (upr) identical across all four referendums:"]
    if len(bad_upr) == 0:
        log.append("  yes, all 2 984 precincts")
    else:
        log.append(f"  NO for {len(bad_upr)} precincts:")
        for st, row in bad_upr.iterrows():
            log.append(f"    {st}: " + ", ".join(f"{r}={v:g}" for r, v in row.items()))

    piv_gl = reg.pivot_table(index="station", columns="referendum", values="gl", aggfunc="first")
    dmax = piv_gl.max(axis=1) - piv_gl.min(axis=1)
    log += [
        "",
        "Precinct turnout (gl, ballots issued) across the four referendums:",
        f"  exactly identical: {int((dmax == 0).sum())}; 1–2 ballot gap: "
        f"{int(((dmax >= 1) & (dmax <= 2)).sum())}; 3–5: {int(((dmax >= 3) & (dmax <= 5)).sum())}; "
        f"more than 5: {int((dmax > 5).sum())} (max {int(dmax.max())})",
        "  precincts with a gap > 2 ballots:",
    ]
    for st, row in piv_gl.loc[dmax[dmax > 2].index].iterrows():
        log.append(f"    {st}: " + ", ".join(f"{r}={v:g}" for r, v in row.items()))

    gg = reg[reg["glas"] > reg["gl"]]
    if len(gg):
        log += ["", "More ballots counted than recorded by turnout (glas > gl):"]
        for _, r in gg.iterrows():
            log.append(f"    {r.station} [{r.referendum}]: gl={r.gl}, glas={r.glas}")

    # early-voting points: summary by referendum
    log += ["", "Early-voting points (numbers >= 900, upr = 0), by referendum:"]
    for ref, g in early.groupby("referendum"):
        log.append(f"  {ref}: {g.station.nunique()} points, {g.glas.sum():,} ballots, "
                   f"ZA {100 * g.za.sum() / g.velj.sum():.2f}% of valid votes")

    log_text = "\n".join(log) + "\n"
    LOG.write_text(log_text, encoding="utf-8")
    print(log_text)
    print(f"done: {OUT}/<referendum>/results_freguesias.csv; log — {LOG}")


if __name__ == "__main__":
    main()
