#!/usr/bin/env python3
"""Сборка секционного датасета президента BR-2026 в формат ElectionData.

Читает выгрузку TSE (data/votacao_secao/):
  - detalhe_votacao_secao_2026_BRASIL.csv — электорат/явка по секциям
    (фильтр: CD_ELEICAO=6257 федеральные, CD_CARGO=1 президент, NR_TURNO=1);
  - votacao_secao_2026_BR.csv — голоса по (секция × votável), пивот в колонки
    votes:<NR>-<ИМЯ>; VOTO BRANCO (95) -> blank_votes, VOTO NULO (96) -> null_votes.

Выход: data/secoes_presidente_2026.csv (UTF-8, MAI-подобные колонки
key/level/name/path/parent_key/registered_voters/voted/blank_votes/null_votes/
votes:* + бразильские поля uf/urna_model/origem_voto/instalada) и
data/secoes_presidente_2026_checks.json — проверки самосогласованности.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BR = Path(__file__).resolve().parents[1]
DATA = BR / "data" / "votacao_secao"

# короткие имена кандидатов для колонок votes:
SHORT = {
    "13": "LULA", "22": "BOLSONARO", "70": "CURY", "14": "FERREIRA",
    "55": "CAIADO", "30": "ZEMA", "80": "SAMARA", "16": "HERTZ",
    "27": "CLARIANA", "21": "EDMILSON", "35": "GRASSI", "29": "RUI",
    "28": "LEONARDO",
}

KEY_COLS = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"]


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
    df = df[(df.CD_ELEICAO == "6257") & (df.CD_CARGO == "1") & (df.NR_TURNO == "1")]
    for c in df.columns:
        if c.startswith("QT_"):
            df[c] = pd.to_numeric(df[c]).astype("int64")
    for c in KEY_COLS:
        df[c] = df[c].str.strip()
    df["NM_MUNICIPIO"] = df["NM_MUNICIPIO"].str.strip()
    return df.drop(columns=["CD_ELEICAO", "CD_CARGO", "NR_TURNO"])


def read_votacao() -> pd.DataFrame:
    usecols = KEY_COLS + ["CD_ELEICAO", "CD_CARGO", "NR_VOTAVEL", "QT_VOTOS"]
    df = pd.read_csv(
        DATA / "votacao_secao_2026_BR" / "votacao_secao_2026_BR.csv",
        encoding="latin-1", sep=";", quoting=1, dtype=str, usecols=usecols,
    )
    df = df[(df.CD_ELEICAO == "6257") & (df.CD_CARGO == "1")]
    df["QT_VOTOS"] = pd.to_numeric(df["QT_VOTOS"]).astype("int32")
    for c in KEY_COLS:
        df[c] = df[c].str.strip()
    return df.drop(columns=["CD_ELEICAO", "CD_CARGO"])


def main() -> None:
    det = read_detalhe()
    vot = read_votacao()
    print(f"detalhe: {len(det)} секций; votacao: {len(vot)} строк")

    # пивот голосов: секция × votável
    vot["votavel"] = vot.NR_VOTAVEL.map(
        lambda n: {"95": "BRANCO", "96": "NULO"}.get(n) or SHORT.get(n, f"X{n}")
    )
    votes = vot.pivot_table(
        index=KEY_COLS, columns="votavel", values="QT_VOTOS",
        aggfunc="sum", fill_value=0,
    )
    checks: dict = {"n_rows_votacao": int(len(vot))}

    df = det.merge(votes, left_on=KEY_COLS, right_index=True, how="left", validate="1:1")
    checks["sections_without_vote_rows"] = int(
        df[[c for c in votes.columns if c not in ("BRANCO", "NULO")]].isna().all(axis=1).sum()
    )
    vote_cols = [c for c in votes.columns if c not in ("BRANCO", "NULO")]
    df[vote_cols] = df[vote_cols].fillna(0).astype("int64")

    # --- проверки самосогласованности -----------------------------------
    dup = df.duplicated(subset=KEY_COLS, keep=False).sum()
    checks["duplicate_section_keys"] = int(dup)
    nominal = df[vote_cols].sum(axis=1)
    checks["nominal_vs_QT_VOTOS_NOMINAIS_mismatch"] = int((nominal != df.QT_VOTOS_NOMINAIS).sum())
    residual = df.QT_COMPARECIMENTO - nominal - df.QT_VOTOS_BRANCOS - df.QT_VOTOS_NULOS
    checks["residual_vs_anulados_apu_sep_mismatch"] = int(
        (residual != df.QT_VOTOS_ANULADOS_APU_SEP).sum()
    )
    checks["residual_nonzero"] = int((residual != 0).sum())
    checks["blank_vs_detalhe_mismatch"] = int((df.BRANCO != df.QT_VOTOS_BRANCOS).sum())
    checks["null_vs_detalhe_mismatch"] = int((df.NULO != df.QT_VOTOS_NULOS).sum())
    checks["voted_gt_aptos"] = int((df.QT_COMPARECIMENTO > df.QT_APTOS).sum())
    checks["not_installed"] = int((df.ST_SECAO_INSTALADA != "Sim").sum())
    checks["annulled"] = int((df.ST_SECAO_ANULADA != "Não").sum())
    checks["aptos_zero"] = int((df.QT_APTOS == 0).sum())
    checks["comparecimento_zero"] = int((df.QT_COMPARECIMENTO == 0).sum())

    # --- финальный датасет -------------------------------------------------
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

    checks["totals"] = {
        "sections": int(len(out)),
        "registered": int(out.registered_voters.sum()),
        "voted": int(out.voted.sum()),
        "turnout_pct": round(100.0 * out.voted.sum() / out.registered_voters.sum(), 3),
        "blank": int(out.blank_votes.sum()),
        "null": int(out.null_votes.sum()),
        "anulados_apu_sep": int(df.QT_VOTOS_ANULADOS_APU_SEP.sum()),
        "candidates": {c: int(out[f"votes:{c}"].sum()) for c in vote_cols},
    }

    out_file = BR / "data" / "secoes_presidente_2026.csv"
    out.to_csv(out_file, index=False)
    (BR / "data" / "secoes_presidente_2026_checks.json").write_text(
        json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    print(f"written: {out_file} ({out_file.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    sys.exit(main())
