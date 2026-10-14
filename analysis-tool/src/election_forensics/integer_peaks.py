"""Integer peaks of turnout and result (Kobak, Shpilkin, Pshenichnikov, 2016).

The idea: if protocols are "drawn" by people, turnout/result values gravitate
towards round numbers — exactly 60%, 70%, 75%, 80%. In honest data the
frequency of integer percentages matches the natural probability of a
discrete quantity falling into a narrow rounding window.

The null model is Monte Carlo: for each territory, voting is modelled with a
binomial distribution at the observed turnout, after which the rounded
percentages are recomputed. This accounts for territory size (in small
parishes integer percentages are more likely).
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
    """Number of territories with an integer percentage and with a multiple-of-5 percentage."""
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
    """Integer-peaks test with a binomial Monte Carlo null model.

    metric: 'turnout' or 'share:<party>'.
    """
    rng = np.random.default_rng(seed)
    N = data.registered.to_numpy()
    V = data.voted.to_numpy()
    P = data.df[metric.removeprefix("share:")] if metric.startswith("share:") else V

    obs_int, obs_m5 = _integer_stats(
        _share_values(data, metric.removeprefix("share:")) if metric.startswith("share:") else 100.0 * V / N
    )
    # points with a zero denominator are excluded by the data loader

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
    """Turnout histogram by number of territories (for visualising the peaks)."""
    t = data.turnout.to_numpy()
    edges = np.arange(0.0, 100.0 + bin_width, bin_width)
    h, _ = np.histogram(t, bins=edges)
    return 0.5 * (edges[:-1] + edges[1:]), h
