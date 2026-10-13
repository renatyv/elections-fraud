"""Целочисленные пики явки и результата (Kobak, Shpilkin, Pshenichnikov, 2016).

Идея: если протоколы «рисуют» люди, значения явки/результата тяготеют
к круглым числам — ровно 60 %, 70 %, 75 %, 80 %. В честных данных частота
целых процентов соответствует естественной вероятности попадания
дискретной величины в узкое окно округления.

Нулевая модель — Монте-Карло: для каждой территории голосование
моделируется биномиальным распределением с наблюдаемой явкой,
после чего пересчитываются округлённые проценты. Это учитывает
размер территорий (в мелких приходах целые проценты вероятнее).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .data import ElectionData, rounder


@dataclass
class IntegerPeaksResult:
    metric: str  # 'turnout' | 'share:<party>'
    n_units: int
    observed_integer: int
    observed_integer_pct: float
    null_mean_pct: float
    null_sd_pct: float
    z_score: float
    observed_mult5: int
    null_mult5_pct: float
    z_mult5: float


def _integer_stats(values_pct: np.ndarray) -> tuple[int, int]:
    """Число территорий с целым процентом и с процентом, кратным 5."""
    rounded = rounder(values_pct, decimals=2)
    is_int = np.abs(rounded - np.round(rounded)) < 1e-9
    is_m5 = is_int & (np.mod(np.round(rounded), 5) == 0) & (np.round(rounded) > 0)
    return int(is_int.sum()), int(is_m5.sum())


def _share_values(data: ElectionData, party: str) -> np.ndarray:
    return 100.0 * data.df[party].to_numpy() / data.df["voted"].to_numpy()


def integer_peaks(
    data: ElectionData,
    metric: str = "turnout",
    n_sim: int = 200,
    seed: int = 42,
) -> IntegerPeaksResult:
    """Тест целочисленных пиков с биномиальной Монте-Карло-моделью.

    metric: 'turnout' или 'share:<партия>'.
    """
    rng = np.random.default_rng(seed)
    N = data.registered.to_numpy()
    V = data.voted.to_numpy()
    P = data.df[metric.removeprefix("share:")] if metric.startswith("share:") else V

    obs_int, obs_m5 = _integer_stats(
        _share_values(data, metric.removeprefix("share:")) if metric.startswith("share:") else 100.0 * V / N
    )
    # точки с нулевым знаменателем исключены загрузчиком данных

    null_int = np.empty(n_sim)
    null_m5 = np.empty(n_sim)
    for s in range(n_sim):
        v_sim = rng.binomial(N.astype(int), V / N)
        p_sim = rng.binomial(v_sim, np.clip(P / np.maximum(V, 1), 0, 1))
        val = 100.0 * p_sim / np.maximum(v_sim, 1) if metric.startswith("share:") else 100.0 * v_sim / N
        val = val[np.isfinite(val)]
        a, b = _integer_stats(val)
        null_int[s] = a
        null_m5[s] = b

    n = len(V)
    mu_int, sd_int = null_int.mean(), max(null_int.std(ddof=1), 0.5)
    mu_m5, sd_m5 = null_m5.mean(), max(null_m5.std(ddof=1), 0.5)
    return IntegerPeaksResult(
        metric=metric,
        n_units=n,
        observed_integer=obs_int,
        observed_integer_pct=100.0 * obs_int / n,
        null_mean_pct=100.0 * mu_int / n,
        null_sd_pct=100.0 * sd_int / n,
        z_score=(obs_int - mu_int) / sd_int,
        observed_mult5=obs_m5,
        null_mult5_pct=100.0 * mu_m5 / n,
        z_mult5=(obs_m5 - mu_m5) / sd_m5,
    )


def turnout_histogram_counts(data: ElectionData, bin_width: float = 0.1) -> tuple[np.ndarray, np.ndarray]:
    """Гистограмма явки по числу территорий (для визуализации пиков)."""
    t = data.turnout.to_numpy()
    edges = np.arange(0.0, 100.0 + bin_width, bin_width)
    h, _ = np.histogram(t, bins=edges)
    return 0.5 * (edges[:-1] + edges[1:]), h
