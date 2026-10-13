"""Синтетическая валидация методов: «вбрасываем» фальсификации в честные данные
и проверяем, что методы их находят и оценка масштаба растёт с интенсивностью.

Две инъекции:
1. «Вброс/приписка» (метод Шпилькина): в случайной доле территорий явка
   увеличивается на 5–35 п.п., добавленные бюллетени на 60–95 % за лидера.
2. «Рисование протоколов» (целочисленные пики): в случайной доле территорий
   число голосов подгоняется под ровно целый процент явки.

Оговорка конвенции (как у Шпилькина): аномальными считаются ВСЕ голоса
лидера на аномальной явке — включая честные голоса, «переехавшие» в хвост
вместе с накруткой явки, поэтому оценка может превышать число добавленных
бюллетеней; на чистых данных оценка ≈ 0.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

from .data import ElectionData
from .integer_peaks import integer_peaks
from .shpilkin import shpilkin_estimate


@dataclass
class SelftestReport:
    t_cut: float
    clean_tail_party: int
    injected_added_ballots_party: int
    injected_tail_party: int
    signal_growth: float  # во сколько раз выросла оценка аномалии
    peaks_z_clean: float
    peaks_z_rounded: float
    n_rounded_units: int

    def to_dict(self) -> dict:
        return asdict(self)


def inject_additive_fraud(
    data: ElectionData, party: str, frac_units: float = 0.10, seed: int = 7
) -> tuple[ElectionData, int]:
    """Добавить явку и голоса за партию в доле территорий."""
    rng = np.random.default_rng(seed)
    df = data.df.copy()
    N = df["registered_voters"].to_numpy()
    V = df["voted"].to_numpy()
    hit = rng.random(len(df)) < frac_units
    delta = rng.uniform(0.05, 0.35, size=len(df)) * hit
    add_ballots = np.round(delta * N).astype(int)
    add_party = np.round(add_ballots * rng.uniform(0.60, 0.95, size=len(df))).astype(int)
    V2 = np.minimum(V + add_ballots, N)
    scale = np.where(add_ballots > 0, (V2 - V) / np.maximum(add_ballots, 1), 0)
    add_party = np.round(add_party * scale).astype(int)
    df["voted"] = V2
    df[party] = df[party].to_numpy() + add_party
    return ElectionData(name=data.name + " + инъекция", df=df, party_cols=data.party_cols), int(add_party.sum())


def inject_rounded_turnout(
    data: ElectionData, frac_units: float = 0.05, seed: int = 11
) -> tuple[ElectionData, int]:
    """Подогнать явку под целый процент в доле территорий («рисование»)."""
    rng = np.random.default_rng(seed)
    df = data.df.copy()
    N = df["registered_voters"].to_numpy()
    t = df["voted"].to_numpy() / N
    hit = rng.random(len(df)) < frac_units
    t_rounded = np.clip(np.round(t * 100) / 100.0, 0, 1)
    V2 = np.round(np.where(hit, t_rounded, t) * N).astype(int)
    # перераспределяем разницу пропорционально между партиями и бланками
    diff = V2 - df["voted"].to_numpy()
    party_cols = list(data.party_cols)
    party_tot = df[party_cols].to_numpy()
    denom = party_tot.sum(axis=1) + df["blank_votes"].to_numpy() + df["null_votes"].to_numpy()
    for j, c in enumerate(party_cols):
        share = np.divide(party_tot[:, j], denom, out=np.zeros(len(df)), where=denom > 0)
        df[c] = np.maximum(party_tot[:, j] + np.round(diff * share).astype(int), 0)
    df["voted"] = V2
    return ElectionData(name=data.name + " + круглые явки", df=df, party_cols=data.party_cols), int(hit.sum())


def run_selftest(data: ElectionData, leader: str, seed: int = 7) -> SelftestReport:
    """Прогнать обе инъекции и оценить отклик методов."""
    # граница аномальной явки фиксируется по ЧИСТЫМ данным до инъекции
    clean_est = shpilkin_estimate(data, leader, controls=[data])
    injected, added = inject_additive_fraud(data, leader, seed=seed)
    inj_est = shpilkin_estimate(injected, leader, controls=[data])  # t_cut от чистых данных

    rounded, n_rounded = inject_rounded_turnout(data, seed=seed + 4)
    peaks_clean = integer_peaks(data, "turnout", n_sim=100, seed=seed)
    peaks_rounded = integer_peaks(rounded, "turnout", n_sim=100, seed=seed)

    return SelftestReport(
        t_cut=clean_est.t_cut,
        clean_tail_party=clean_est.tail_votes_party,
        injected_added_ballots_party=added,
        injected_tail_party=inj_est.tail_votes_party,
        signal_growth=inj_est.tail_votes_party / max(clean_est.tail_votes_party, 1),
        peaks_z_clean=peaks_clean.z_score,
        peaks_z_rounded=peaks_rounded.z_score,
        n_rounded_units=n_rounded,
    )
