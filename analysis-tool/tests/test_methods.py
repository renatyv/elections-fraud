"""Quick checks of the key components (uv run pytest)."""

import numpy as np
import pandas as pd
import pytest

from election_forensics.data import ElectionData, rounder
from election_forensics.digit_tests import BENFORD_2ND, digit_test
from election_forensics.integer_peaks import integer_peaks
from election_forensics.shpilkin import shpilkin_estimate, votes_by_turnout


def _synthetic_data(n=400, seed=0):
    rng = np.random.default_rng(seed)
    registered = rng.integers(500, 5000, n)
    turnout = np.clip(rng.normal(0.6, 0.06, n), 0.2, 0.95)
    voted = np.round(registered * turnout).astype(int)
    leader_share = np.clip(rng.normal(0.55, 0.05, n), 0.2, 0.8)
    df = pd.DataFrame(
        {
            "key": [f"L-{i:06d}" for i in range(n)],
            "level": 3,
            "name": [f"u{i}" for i in range(n)],
            "path": ["a > b > c"] * n,
            "parent_key": ["P"] * n,
            "registered_voters": registered,
            "voted": voted,
            "turnout_pct": 100 * voted / registered,
            "blank_votes": np.round(voted * 0.01).astype(int),
            "null_votes": np.round(voted * 0.01).astype(int),
            "votes:X": np.round(voted * leader_share).astype(int),
            "votes:Y": np.round(voted * (1 - leader_share) * 0.9).astype(int),
        }
    )
    return ElectionData(name="synthetic", df=df, party_cols=["votes:X", "votes:Y"])


def test_benford_second_digit_distribution():
    assert abs(BENFORD_2ND.sum() - 1.0) < 1e-9
    assert BENFORD_2ND[0] > BENFORD_2ND[9]


def test_rounder_half_up():
    assert rounder(np.array([0.5, 1.5, 2.45]), 0).tolist() == [1.0, 2.0, 2.0]
    assert rounder(np.array([74.995]), 2).tolist() == [75.0]


def test_leader_party():
    d = _synthetic_data()
    assert d.leader_party == "votes:X"


def test_shpilkin_clean_synthetic_zero_tail():
    d = _synthetic_data(seed=1)
    res = shpilkin_estimate(d, "votes:X", controls=[d])
    assert res.tail_share_of_party < 1.0  # clean data — the tail is negligible


def test_integer_peaks_clean_synthetic():
    d = _synthetic_data(seed=2)
    res = integer_peaks(d, "turnout", n_sim=40)
    assert abs(res.z_score) < 4


def test_integer_peaks_detects_rounding():
    d = _synthetic_data(seed=3)
    n = len(d.df)
    hit = np.random.default_rng(4).random(n) < 0.2
    t = d.df["voted"] / d.df["registered_voters"]
    d.df["voted"] = np.round(np.where(hit, np.round(t * 100) / 100, t) * d.df["registered_voters"]).astype(int)
    res = integer_peaks(d, "turnout", n_sim=40)
    assert res.z_score > 5


def test_digit_test_last_digit_uniform():
    rng = np.random.default_rng(5)
    d = _synthetic_data(n=800, seed=5)
    counts = rng.integers(100, 5000, 2000)
    d.df["votes:X"] = counts[: len(d.df)]
    res = digit_test(d, "votes:X", "last", n_sim=100)
    assert res.p_null_mc > 0.01
