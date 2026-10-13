"""Метод Шпилькина: распределение явки, «честное ядро», оценка аномальных голосов.

Идея (раздел 2 обзорного документа):
1. Гистограмма числа голосов за партию в зависимости от явки (взвешивание
   по числу проголосовавших, а не по числу участков).
2. «Честное ядро» — гладкая модель основной части распределения;
   допущение: манипуляции только добавляют явку и голоса.
3. Аномальная составляющая — масса распределения правее границы
   естественного («честного») спада; интеграл даёт оценку числа
   аномальных голосов за партию и позволяет пересчитать итог.

Граница аномальной явки. Для неоднородных данных (Португалия: широкое
смесь городских/сельских приходов) параметрическое одиночное ядро
неустойчиво, поэтому граница задаётся внешним ориентиром — верхним
перцентилем взвешенного распределения явки КОНТРОЛЬНЫХ выборов тех же
территорий (логика «контрольных стран/выборов» из раздела 4 обзора).
Без контролов берётся q99.5 самих данных.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d

from .data import ElectionData


@dataclass
class ShpilkinResult:
    party: str
    t_cut: float
    t_cut_source: str  # 'controls' | 'own_q995'
    mode: float
    sigma: float
    total_votes_party: int
    tail_voters: int  # проголосовавших на явке выше границы
    tail_votes_party: int  # голосов за партию на явке выше границы
    tail_share_of_party: float  # то же в % от голосов партии
    observed_share_pct: float
    honest_share_pct: float  # итог партии без аномальной зоны

    def to_dict(self) -> dict:
        return asdict(self)


def votes_by_turnout(
    data: ElectionData,
    weight_col: str | None = None,
    bin_width: float = 0.5,
) -> tuple[np.ndarray, np.ndarray]:
    """Гистограмма: сумма weight_col по корзинам явки.

    weight_col=None → число проголосовавших (распределение явки,
    взвешенное по электорату), иначе — голоса за партию.
    """
    turnout = data.turnout.to_numpy()
    w = data.df[weight_col].to_numpy() if weight_col else data.df["voted"].to_numpy()
    edges = np.arange(0.0, 100.0 + bin_width, bin_width)
    h, _ = np.histogram(turnout, bins=edges, weights=w)
    centers = 0.5 * (edges[:-1] + edges[1:])
    return centers, h


def suggest_t_cut(controls: list[ElectionData], q: float = 99.5) -> float:
    """Граница аномальной явки: максимальный q-перцентиль контрольных выборов."""
    qs = []
    for c in controls:
        t = c.turnout.to_numpy()
        w = c.registered.to_numpy()
        qs.append(float(np.percentile(np.repeat(t, np.round(w).astype(int)), q)))
    return max(qs)


def smooth_mode_sigma(centers: np.ndarray, h: np.ndarray, smooth_bins: float = 2.0) -> tuple[float, float]:
    """Мода и σ гладкой аппроксимации распределения (для справки и графика)."""
    hs = gaussian_filter1d(h.astype(float), smooth_bins)
    i_mode = int(np.argmax(hs))
    mode = float(centers[i_mode])
    total = hs.sum()
    mean = float((centers * hs).sum() / total)
    var = float(((centers - mean) ** 2 * hs).sum() / total)
    return mode, float(np.sqrt(var))


def shpilkin_estimate(
    data: ElectionData,
    party: str,
    controls: list[ElectionData] | None = None,
    bin_width: float = 0.5,
    q: float = 99.5,
) -> ShpilkinResult:
    """Оценка аномальных голосов за партию: масса правее границы честного спада."""
    centers, h_voted = votes_by_turnout(data, None, bin_width)
    _, h_party = votes_by_turnout(data, party, bin_width)
    if controls:
        t_cut = suggest_t_cut(controls, q)
        source = "controls"
    else:
        t = data.turnout.to_numpy()
        w = data.registered.to_numpy()
        t_cut = float(np.percentile(np.repeat(t, np.round(w).astype(int)), q))
        source = "own_q995"

    mask = centers > t_cut
    tail_voted = float(h_voted[mask].sum())
    tail_party = float(h_party[mask].sum())
    mode, sigma = smooth_mode_sigma(centers, h_voted)

    total_party = float(data.df[party].sum())
    total_voted = float(data.df["voted"].sum())
    obs_share = 100.0 * total_party / total_voted
    honest_share = 100.0 * (total_party - tail_party) / max(total_voted - tail_voted, 1)

    return ShpilkinResult(
        party=party.removeprefix("votes:"),
        t_cut=t_cut,
        t_cut_source=source,
        mode=mode,
        sigma=sigma,
        total_votes_party=int(total_party),
        tail_voters=int(tail_voted),
        tail_votes_party=int(tail_party),
        tail_share_of_party=100.0 * tail_party / max(total_party, 1),
        observed_share_pct=obs_share,
        honest_share_pct=honest_share,
    )


def comet_scatter_data(data: ElectionData, party: str) -> pd.DataFrame:
    """Данные для скаттерплота «явка × результат» (хвост кометы)."""
    return pd.DataFrame(
        {
            "turnout": data.turnout,
            "share": data.share(party),
            "voters": data.df["registered_voters"],
            "name": data.df["name"],
        }
    )
