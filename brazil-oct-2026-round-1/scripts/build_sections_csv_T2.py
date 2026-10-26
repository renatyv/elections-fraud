#!/usr/bin/env python3
"""Build the BR-2026 president 2nd-round (25.10.2026) section dataset, MAI format.

Same schema as build_sections_csv.py (1st round), but filters NR_TURNO=2 from the
TSE export updated after the runoff (dataset "resultados-2026", files regenerated
at the end of each turno — re-download votacao_secao_2026_BR.zip and
detalhe_votacao_secao_2026.zip fresh, they are NOT resumable):

  - detalhe_votacao_secao_2026_BRASIL.csv — electorate/turnout per section
    (CD_CARGO=1 president, NR_TURNO=2);
  - votacao_secao_2026_BR.csv — votes per (section × votável), NR_TURNO=2:
    two finalists 13 LULA / 22 BOLSONARO + BRANCO 95 / NULO 96.

Output: data/secoes_presidente_2026_T2.csv (+ _checks.json with cross-checks
against the totals captured from the TSE results portal on election night).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BR = Path(__file__).resolve().parents[1]
DATA = BR / "data" / "votacao_secao"

SHORT = {"13": "LULA", "22": "BOLSONARO"}
KEY_COLS = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"]

# final totals from the TSE results portal, snapshot 26.10.2026 07:52 UTC
# (data/trends/national.csv + results.csv) — the build must match these exactly
TRENDS_FINAL = {
    "voted": 128_236_074,
    "blank": 1_430_496,
    "null": 2_723_305,
    "LULA": 64_256_232,
    "BOLSONARO": 59_826_041,
}


def read_detalhe() -> pd.DataFrame:
    usecols = KEY_COLS + [
        "CD_ELEICAO", "CD_CARGO", "NR_TURNO", "NM_MUNICIPIO",
        "QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES",
        "QT_VOTOS_NOMINAIS", "QT_VOTOS_BRANCOS", "QT_VOTOS_NULOS",
        "QT_VOTOS_ANULADOS_APU_SEP", "ST_SECAO_INSTALADA", "ST_SECAO_ANULADA",
        "CD_MODELO_URNA", "DS_MODELO_URNA", "DS_ORIGEM_VOTO",
    ]
    df = pd.read_csv(
        DATA / "detalhe_votacao_secao_2026" / "detalhe_votacao_secao_2026_BRASIL.csv",
        encoding="latin-1", sep=";", quoting=1, dtype=str, usecols=usecols,
    )
    df = df[(df.CD_CARGO == "1") & (df.NR_TURNO == "2")]
    for c in df.columns:
        if c.startswith("QT_"):
            df[c] = pd.to_numeric(df[c]).astype("int64")
    for c in KEY_COLS:
        df[c] = df[c].str.strip()
    df["NM_MUNICIPIO"] = df["NM_MUNICIPIO"].str.strip()
    return df.drop(columns=["CD_CARGO", "NR_TURNO"])


def read_votacao() -> pd.DataFrame:
    usecols = KEY_COLS + ["CD_CARGO", "NR_TURNO", "NR_VOTAVEL", "QT_VOTOS"]
    df = pd.read_csv(
        DATA / "votacao_secao_2026_BR" / "votacao_secao_2026_BR.csv",
        encoding="latin-1", sep=";", quoting=1, dtype=str, usecols=usecols,
    )
    df = df[(df.CD_CARGO == "1") & (df.NR_TURNO == "2")]
    df["QT_VOTOS"] = pd.to_numeric(df["QT_VOTOS"]).astype("int32")
    for c in KEY_COLS:
        df[c] = df[c].str.strip()
    return df.drop(columns=["CD_CARGO", "NR_TURNO"])


def main() -> None:
    det = read_detalhe()
    vot = read_votacao()
    print(f"detalhe: {len(det)} sections; votacao: {len(vot)} rows")
    checks: dict = {"n_rows_votacao": int(len(vot)),
                    "detalhe_cd_eleicao": sorted(det.CD_ELEICAO.unique().tolist())}

    vot["votavel"] = vot.NR_VOTAVEL.map(
        lambda n: {"95": "BRANCO", "96": "NULO"}.get(n) or SHORT.get(n, f"X{n}")
    )
    votes = vot.pivot_table(
        index=KEY_COLS, columns="votavel", values="QT_VOTOS",
        aggfunc="sum", fill_value=0,
    )
    df = det.merge(votes, left_on=KEY_COLS, right_index=True, how="left", validate="1:1")
    vote_cols = [c for c in votes.columns if c not in ("BRANCO", "NULO")]
    df[vote_cols] = df[vote_cols].fillna(0).astype("int64")

    # --- self-consistency checks -----------------------------------------
    checks["duplicate_section_keys"] = int(df.duplicated(subset=KEY_COLS, keep=False).sum())
    nominal = df[vote_cols].sum(axis=1)
    checks["nominal_vs_QT_VOTOS_NOMINAIS_mismatch"] = int((nominal != df.QT_VOTOS_NOMINAIS).sum())
    residual = df.QT_COMPARECIMENTO - nominal - df.QT_VOTOS_BRANCOS - df.QT_VOTOS_NULOS
    checks["residual_vs_anulados_apu_sep_mismatch"] = int(
        (residual != df.QT_VOTOS_ANULADOS_APU_SEP).sum())
    checks["blank_vs_detalhe_mismatch"] = int((df.BRANCO != df.QT_VOTOS_BRANCOS).sum())
    checks["null_vs_detalhe_mismatch"] = int((df.NULO != df.QT_VOTOS_NULOS).sum())
    checks["voted_gt_aptos"] = int((df.QT_COMPARECIMENTO > df.QT_APTOS).sum())
    checks["not_installed"] = int((df.ST_SECAO_INSTALADA != "Sim").sum())
    checks["annulled"] = int((df.ST_SECAO_ANULADA != "Não").sum())

    # --- final dataset ------------------------------------------------------
    key = df.SG_UF + "-" + df.CD_MUNICIPIO + "-z" + df.NR_ZONA + "-s" + df.NR_SECAO
    out = pd.DataFrame({
        "key": key,
        "level": 3,
        "name": df.NM_MUNICIPIO + " z" + df.NR_ZONA + " s" + df.NR_SECAO,
        "path": "BR > " + df.SG_UF + " > " + df.NM_MUNICIPIO,
        "parent_key": df.SG_UF + "-" + df.CD_MUNICIPIO,
        "registered_voters": df.QT_APTOS,
        "voted": df.QT_COMPARECIMENTO,
        "blank_votes": df.QT_VOTOS_BRANCOS,
        "null_votes": df.QT_VOTOS_NULOS,
        "uf": df.SG_UF,
        "urna_model": df.DS_MODELO_URNA,
        "origem_voto": df.DS_ORIGEM_VOTO,
        "instalada": df.ST_SECAO_INSTALADA,
    })
    for c in vote_cols:
        out[f"votes:{c}"] = df[c]
    out["turnout_pct"] = 100.0 * out.voted / out.registered_voters.replace(0, np.nan)

    totals = {
        "sections": int(len(out)),
        "registered": int(out.registered_voters.sum()),
        "voted": int(out.voted.sum()),
        "turnout_pct": round(100.0 * out.voted.sum() / out.registered_voters.sum(), 3),
        "blank": int(out.blank_votes.sum()),
        "null": int(out.null_votes.sum()),
        "candidates": {c: int(out[f"votes:{c}"].sum()) for c in vote_cols},
    }
    checks["totals"] = totals
    # cross-check against the election-night portal capture (exact votes)
    checks["vs_trends_portal"] = {
        name: ("match" if totals.get(name.lower(), totals.get(name)) == want
               else f"MISMATCH {totals.get(name.lower(), totals.get(name))} != {want}")
        for name, want in TRENDS_FINAL.items()
    }

    out_file = BR / "data" / "secoes_presidente_2026_T2.csv"
    out.to_csv(out_file, index=False)
    (BR / "data" / "secoes_presidente_2026_T2_checks.json").write_text(
        json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    print(f"written: {out_file} ({out_file.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    sys.exit(main())
