#!/usr/bin/env python3
"""Сборка секционного датасета президента BR-2022 (оба тура) в формат ElectionData.

Контрольные данные для анализа 2026: те же территории/секции, выгрузка TSE
data/votacao_secao_2022/ (датасет resultados-2022; 1-й тур 02.10.2022,
2-й тур 30.10.2022):
  - detalhe_votacao_secao_2022_BRASIL.csv — электорат/явка по секциям
    (фильтр: CD_CARGO=1 президент; CD_ELEICAO=544 → 1-й тур, 545 → 2-й);
  - votacao_secao_2022_BR.csv — голоса по (секция × votável), пивот в колонки
    votes:<NR>-<ИМЯ>; VOTO BRANCO (95) -> blank_votes, VOTO NULO (96) -> null_votes.
    Строки с нулевыми голосами TSE опускает → после пивота недостающие = 0
    (проверяется против QT_VOTOS_NOMINAIS detalhe).

Выход: data/secoes_presidente_2022.csv (колонка turno: 1|2; прочий формат как у
secoes_presidente_2026.csv) и data/secoes_presidente_2022_checks.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BR = Path(__file__).resolve().parents[1]
DATA = BR / "data" / "votacao_secao_2022"

# короткие имена кандидатов для колонок votes: (номера бюллетеня 2022)
SHORT = {
    "13": "LULA", "22": "BOLSONARO", "15": "TEBET", "12": "CIRO",
    "44": "SORAYA", "30": "DAVILA", "14": "KELMON", "80": "PERICLES",
    "21": "MANZANO", "16": "VERA", "27": "EYMAEL",
}
CD_ELEICAO_TURNO = {"544": "1", "545": "2"}  # ELEIÇÃO GERAL FEDERAL 2022, туры 1/2

KEY_COLS = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"]


def read_detalhe() -> pd.DataFrame:
    usecols = KEY_COLS + [
        "CD_ELEICAO", "CD_CARGO", "NR_TURNO", "NM_MUNICIPIO",
        "QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES",
        "QT_VOTOS_NOMINAIS", "QT_VOTOS_BRANCOS", "QT_VOTOS_NULOS",
        "QT_VOTOS_ANULADOS_APU_SEP", "ST_SECAO_INSTALADA", "ST_SECAO_ANULADA",
        "DS_ORIGEM_VOTO",
    ]
    df = pd.read_csv(
        DATA / "detalhe_votacao_secao_2022" / "detalhe_votacao_secao_2022_BRASIL.csv",
        encoding="latin-1", sep=";", quoting=1, dtype=str, usecols=usecols,
    )
    df = df[(df.CD_CARGO == "1") & (df.CD_ELEICAO.isin(CD_ELEICAO_TURNO))]
    assert (df.CD_ELEICAO.map(CD_ELEICAO_TURNO) == df.NR_TURNO).all(), "CD_ELEICAO/NR_TURNO расходятся"
    for c in df.columns:
        if c.startswith("QT_"):
            df[c] = pd.to_numeric(df[c]).astype("int64")
    for c in KEY_COLS:
        df[c] = df[c].str.strip()
    df["NM_MUNICIPIO"] = df["NM_MUNICIPIO"].str.strip()
    return df.drop(columns=["CD_ELEICAO", "CD_CARGO"])


def read_votacao() -> pd.DataFrame:
    usecols = KEY_COLS + ["CD_ELEICAO", "CD_CARGO", "NR_TURNO", "NR_VOTAVEL", "QT_VOTOS"]
    df = pd.read_csv(
        DATA / "votacao_secao_2022_BR" / "votacao_secao_2022_BR.csv",
        encoding="latin-1", sep=";", quoting=1, dtype=str, usecols=usecols,
    )
    df = df[(df.CD_CARGO == "1") & (df.CD_ELEICAO.isin(CD_ELEICAO_TURNO))]
    df["QT_VOTOS"] = pd.to_numeric(df["QT_VOTOS"]).astype("int32")
    for c in KEY_COLS:
        df[c] = df[c].str.strip()
    return df.drop(columns=["CD_ELEICAO", "CD_CARGO"])


def build_turn(det: pd.DataFrame, vot: pd.DataFrame, turno: str, checks: dict) -> pd.DataFrame:
    det = det[det.NR_TURNO == turno].copy()
    vot = vot[vot.NR_TURNO == turno].drop(columns=["NR_TURNO"])
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

    c: dict = {"n_rows_votacao": int(len(vot))}
    c["duplicate_section_keys"] = int(df.duplicated(subset=KEY_COLS, keep=False).sum())
    nominal = df[vote_cols].sum(axis=1)
    c["nominal_vs_QT_VOTOS_NOMINAIS_mismatch"] = int((nominal != df.QT_VOTOS_NOMINAIS).sum())
    residual = df.QT_COMPARECIMENTO - nominal - df.QT_VOTOS_BRANCOS - df.QT_VOTOS_NULOS
    c["residual_vs_anulados_apu_sep_mismatch"] = int((residual != df.QT_VOTOS_ANULADOS_APU_SEP).sum())
    c["residual_nonzero"] = int((residual != 0).sum())
    c["blank_vs_detalhe_mismatch"] = int((df.BRANCO.fillna(0) != df.QT_VOTOS_BRANCOS).sum())
    c["null_vs_detalhe_mismatch"] = int((df.NULO.fillna(0) != df.QT_VOTOS_NULOS).sum())
    c["voted_gt_aptos"] = int((df.QT_COMPARECIMENTO > df.QT_APTOS).sum())
    c["not_installed"] = int((df.ST_SECAO_INSTALADA != "Sim").sum())
    c["annulled"] = int((df.ST_SECAO_ANULADA != "Não").sum())
    c["aptos_zero"] = int((df.QT_APTOS == 0).sum())
    c["comparecimento_zero"] = int((df.QT_COMPARECIMENTO == 0).sum())
    c["totals"] = {
        "sections": int(len(df)),
        "registered": int(df.QT_APTOS.sum()),
        "voted": int(df.QT_COMPARECIMENTO.sum()),
        "turnout_pct": round(100.0 * df.QT_COMPARECIMENTO.sum() / df.QT_APTOS.sum(), 3),
        "blank": int(df.QT_VOTOS_BRANCOS.sum()),
        "null": int(df.QT_VOTOS_NULOS.sum()),
        "anulados_apu_sep": int(df.QT_VOTOS_ANULADOS_APU_SEP.sum()),
        "candidates": {v: int(df[v].sum()) for v in vote_cols},
    }
    checks[f"turno_{turno}"] = c

    key = df.SG_UF + "-" + df.CD_MUNICIPIO + "-z" + df.NR_ZONA + "-s" + df.NR_SECAO
    out = pd.DataFrame({
        "key": key,
        "turno": int(turno),
        "level": 3,
        "name": df.NM_MUNICIPIO + " z" + df.NR_ZONA + " s" + df.NR_SECAO,
        "path": "BR > " + df.SG_UF + " > " + df.NM_MUNICIPIO,
        "parent_key": df.SG_UF + "-" + df.CD_MUNICIPIO,
        "registered_voters": df.QT_APTOS,
        "voted": df.QT_COMPARECIMENTO,
        "blank_votes": df.QT_VOTOS_BRANCOS,
        "null_votes": df.QT_VOTOS_NULOS,
        "uf": df.SG_UF,
        "origem_voto": df.DS_ORIGEM_VOTO,
        "instalada": df.ST_SECAO_INSTALADA,
    })
    for col in vote_cols:
        out[f"votes:{col}"] = df[col]
    out["turnout_pct"] = 100.0 * out.voted / out.registered_voters.replace(0, np.nan)
    return out


def main() -> None:
    det = read_detalhe()
    vot = read_votacao()
    print(f"detalhe: {len(det)} строк президента; votacao: {len(vot)} строк")

    checks: dict = {}
    out1 = build_turn(det, vot, "1", checks)
    out2 = build_turn(det, vot, "2", checks)
    out = pd.concat([out1, out2], ignore_index=True)

    # единый набор колонок голосов по обоим турам (у 2-го тура минорные = 0)
    vote_cols = sorted({c for c in out1.columns if c.startswith("votes:")}
                       | {c for c in out2.columns if c.startswith("votes:")})
    for col in vote_cols:
        if col not in out.columns:
            out[col] = 0

    out_file = BR / "data" / "secoes_presidente_2022.csv"
    out.to_csv(out_file, index=False)
    (BR / "data" / "secoes_presidente_2022_checks.json").write_text(
        json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    print(f"written: {out_file} ({out_file.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    sys.exit(main())
