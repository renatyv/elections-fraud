"""Digit-based tests: second digit (Benford's law) and last digit (Beber-Scacco).

- Benford: in "natural" counted numbers the second digits 0-9 follow Benford's
  law; hand-crafted numbers deviate (Mebane 2006; Deckert et al. 2011). The
  method is contentious — interpret it together with the null.
- Last digit: in honest tallies the last digits of large numbers are uniform
  (Beber, Scacco, Political Analysis 2012). The test applies only to counts
  >= 100 (at least three digits): for small numbers the "last digit" is the
  number itself, and uniformity fails for natural reasons.

The null model of both tests is "smooth counts": vote counts are simulated
from a lognormal distribution fitted to the observed counts. The digits of
honest counts must not depend on which particular parish got which count, so
swapping the structure between parishes must not change the digit
distribution.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
from scipy import stats

from .data import ElectionData

# P(second digit = d) = Σ_{d1=1..9} log10(1 + 1/(10·d1 + d))
BENFORD_2ND = np.array(
    [sum(np.log10(1 + 1.0 / (10 * d1 + d)) for d1 in range(1, 10)) for d in range(10)]
)

MIN_COUNT = {"benford2": 10, "last": 100}


@dataclass
class DigitTestResult:
    test: str  # 'benford2' | 'last'
    party: str
    n_numbers: int
    min_count: int
    chi2: float | None
    dof: int
    p_value: float | None  # against the theoretical digit distribution
    p_null_mc: float | None  # empirical p-value against the smooth (lognormal) null
    max_dev: float | None  # maximum deviation of a frequency from expectation, p.p.

    def to_dict(self) -> dict:
        return asdict(self)


def _digits(counts: np.ndarray, test: str) -> np.ndarray:
    s = counts.astype(int).astype(str)
    if test == "last":
        return np.array([int(x[-1]) for x in s])
    return np.array([int(x[1]) if len(x) > 1 else -1 for x in s])


def _chi2_uniform(obs_digits: np.ndarray, expected: np.ndarray) -> tuple[float, float, float]:
    obs = np.bincount(obs_digits, minlength=10).astype(float)
    n = obs.sum()
    exp = expected * n
    chi2 = float(((obs - exp) ** 2 / exp).sum())
    p = float(stats.chi2.sf(chi2, 9))
    max_dev = float(np.max(np.abs(obs / n - expected)) * 100)
    return chi2, p, max_dev


def _fit_lognormal(counts: np.ndarray) -> tuple[float, float]:
    return stats.norm.fit(np.log(counts))


def _sim_counts(mu: float, sigma: float, n: int, rng: np.random.Generator) -> np.ndarray:
    sim = np.round(np.exp(rng.normal(mu, sigma, n))).astype(int)
    return sim[sim > 0]


def _expected(test: str) -> np.ndarray:
    return BENFORD_2ND if test == "benford2" else np.full(10, 0.1)


def digit_test(
    data: ElectionData,
    party: str,
    test: str = "last",
    n_sim: int = 400,
    seed: int = 42,
) -> DigitTestResult:
    """Digit-based test for party votes across all territories.

    test='benford2': second digit of numbers >= 10 against Benford's law;
    test='last': last digit of numbers >= 100 against uniform.
    """
    rng = np.random.default_rng(seed)
    min_count = MIN_COUNT[test]
    counts = data.df[party].to_numpy()
    counts = counts[counts >= min_count]
    expected = _expected(test)
    if not len(counts):
        return DigitTestResult(test, party.removeprefix("votes:"), 0, min_count,
                               None, 9, None, None, None)
    chi2, p, max_dev = _chi2_uniform(_digits(counts, test), expected)

    mu, sigma = _fit_lognormal(counts)
    stat_null = np.empty(n_sim)
    for s in range(n_sim):
        sim = _sim_counts(mu, sigma, len(counts) * 2, rng)
        sim = sim[sim >= min_count]
        stat_null[s] = _chi2_uniform(_digits(sim[: len(counts)], test), expected)[0]
    p_mc = float((np.sum(stat_null >= chi2) + 1) / (n_sim + 1))

    return DigitTestResult(
        test=test,
        party=party.removeprefix("votes:"),
        n_numbers=len(counts),
        min_count=min_count,
        chi2=chi2,
        dof=9,
        p_value=p,
        p_null_mc=p_mc,
        max_dev=max_dev,
    )


def digit_freqs(counts: np.ndarray, test: str) -> np.ndarray:
    """Observed digit frequencies (for the plot)."""
    d = _digits(counts[counts >= MIN_COUNT[test]], test)
    return np.bincount(d, minlength=10) / len(d)


def digit_null_band(
    counts: np.ndarray, test: str, n_sim: int = 300, seed: int = 42
) -> np.ndarray:
    """95% interval of digit frequencies under the smooth lognormal null."""
    rng = np.random.default_rng(seed)
    min_count = MIN_COUNT[test]
    counts = counts[counts >= min_count]
    mu, sigma = _fit_lognormal(counts)
    freqs = np.empty((n_sim, 10))
    for i in range(n_sim):
        sim = _sim_counts(mu, sigma, len(counts) * 2, rng)
        sim = sim[sim >= min_count][: len(counts)]
        d = _digits(sim, test)
        freqs[i] = np.bincount(d, minlength=10) / len(d)
    return np.percentile(freqs, [2.5, 97.5], axis=0)
