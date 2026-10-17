#!/usr/bin/env python3
"""Build the per-section federal-deputy votes by party (election 6259, CD_CARGO=6).

Reads the 27 state files data/votacao_secao/votacao_secao_2026_<UF>/ and pivots
(section × party): the party of a deputy vote is the 2-digit prefix of NR_VOTAVEL
(federal-deputy ballot numbers are 4 digits; 2-digit NR_VOTAVEL rows are legend
votes and map to the party itself); 95/96 are blank/null and kept as totals.

Output: data/secoes_deputado_2026_parties.csv — one row per section
(key as in secoes_presidente_2026.csv, uf, dep_valid, dep_blank, dep_null,
votes_p<NN> for every party, minor parties lumped into votes_p00) and
data/secoes_deputado_2026_parties_checks.json.

Run from analysis-tool/: uv run python ../brazil-oct-2026-round-1/scripts/build_deputy_parties_csv.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

BR = Path(__file__).resolve().parents[1]
SRC = BR / "data" / "votacao_secao"
OUT_CSV = BR / "data" / "secoes_deputado_2026_parties.csv"
OUT_JSON = BR / "data" / "secoes_deputado_2026_parties_checks.json"

KEY_COLS = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"]
UF_CODES = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
}
MIN_PARTY_VOTES = 100_000  # below this nationally -> lumped into votes_p00


def read_state(uf: str) -> pd.DataFrame:
    path = SRC / f"votacao_secao_2026_{uf}" / f"votacao_secao_2026_{uf}.csv"
    df = pd.read_csv(
        path, encoding="latin-1", sep=";", quoting=1, dtype=str,
        usecols=KEY_COLS + ["CD_ELEICAO", "CD_CARGO", "NR_VOTAVEL", "QT_VOTOS"],
    )
    df = df[(df.CD_ELEICAO == "6259") & (df.CD_CARGO == "6")]
    df["QT_VOTOS"] = pd.to_numeric(df.QT_VOTOS).astype("int64")
    for c in KEY_COLS:
        df[c] = df[c].str.strip()
    return df.drop(columns=["CD_ELEICAO", "CD_CARGO"])


def party_of(nr_votavel: pd.Series) -> pd.Series:
    """Map NR_VOTAVEL to a party code; 95/96 pass through as blank/null."""
    n = nr_votavel.str.strip()
    return n.where(n.isin(["95", "96"]), n.str[:2])


def main() -> None:
    frames = []
    for uf in sorted(UF_CODES):
        f = read_state(uf)
        print(f"{uf}: {len(f):,} deputy rows", flush=True)
        frames.append(f)
    vot = pd.concat(frames, ignore_index=True)

    vot["party"] = party_of(vot.NR_VOTAVEL)
    totals = vot.groupby("party").QT_VOTOS.sum().sort_values(ascending=False)
    keep = totals[(totals >= MIN_PARTY_VOTES) & ~totals.index.isin(["95", "96"])].index
    vot["party_col"] = vot.party.where(vot.party.isin(keep), "00")
    vot.loc[vot.party.isin(["95", "96"]), "party_col"] = vot.party

    votes = vot.pivot_table(
        index=KEY_COLS, columns="party_col", values="QT_VOTOS",
        aggfunc="sum", fill_value=0,
    )

    df = votes.reset_index()
    df["key"] = (df.SG_UF + "-" + df.CD_MUNICIPIO + "-z" + df.NR_ZONA + "-s" + df.NR_SECAO)
    df["dep_valid"] = df[[c for c in votes.columns if c not in ("00", "95", "96")]].sum(axis=1)
    out = df[["key", "SG_UF", "dep_valid"]].copy()
    out = out.rename(columns={"SG_UF": "uf"})
    if "95" in df.columns:
        out["dep_blank"] = df["95"]
    if "96" in df.columns:
        out["dep_null"] = df["96"]
    for p in sorted(c for c in votes.columns if c not in ("95", "96")):
        out[f"votes_p{p}"] = df[p]

    checks: dict = {
        "n_rows_votacao": int(len(vot)),
        "n_sections": int(len(out)),
        "duplicate_keys": int(out.key.duplicated(keep=False).sum()),
        "parties_kept": {p: int(totals[p]) for p in keep},
        "parties_lumped_00": {
            p: int(t) for p, t in totals.items()
            if p not in keep and p not in ("95", "96") and t > 0
        },
        "totals": {
            "dep_valid": int(out.dep_valid.sum()),
            "dep_blank": int(out.dep_blank.sum()),
            "dep_null": int(out.dep_null.sum()),
            "all_rows": int(vot.QT_VOTOS.sum()),
        },
    }
    out.to_csv(OUT_CSV, index=False)
    OUT_JSON.write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(checks["totals"], indent=2))
    print(f"written: {OUT_CSV} ({OUT_CSV.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    sys.exit(main())
