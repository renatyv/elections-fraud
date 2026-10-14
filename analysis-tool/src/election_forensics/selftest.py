"""Synthetic validation of the methods: we "inject" fraud into honest data
and check that the methods detect it and that the scale estimate grows with
the intensity.

Two injections:
1. "Ballot stuffing" (the Shpilkin method): in a random fraction of
   territories turnout is increased by 5-35 p.p., with the added ballots
   60-95% for the leader.
2. "Protocol drawing" (integer peaks): in a random fraction of territories
   the vote count is fitted to exactly an integer turnout percentage.

Convention caveat (as in Shpilkin): ALL leader votes at anomalous turnout are
counted as anomalous — including honest votes that "moved" into the tail
along with the inflated turnout, so the estimate may exceed the number of
added ballots; on clean data the estimate is ≈ 0.
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
    signal_growth: float  # by how many times the anomaly estimate grew
    peaks_z_clean: float
    peaks_z_rounded: float
    n_rounded_units: int

    def to_dict(self) -> dict:
        return asdict(self)


def inject_additive_fraud(
    data: ElectionData, party: str, frac_units: float = 0.10, seed: int = 7
) -> tuple[ElectionData, int]:
    """Add turnout and party votes in a fraction of territories."""
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
    return ElectionData(name=data.name + " + injection", df=df, party_cols=data.party_cols), int(add_party.sum())


def inject_rounded_turnout(
    data: ElectionData, frac_units: float = 0.05, seed: int = 11
) -> tuple[ElectionData, int]:
    """Fit turnout to an integer percentage in a fraction of territories ("drawing")."""
    rng = np.random.default_rng(seed)
    df = data.df.copy()
    N = df["registered_voters"].to_numpy()
    t = df["voted"].to_numpy() / N
    hit = rng.random(len(df)) < frac_units
    t_rounded = np.clip(np.round(t * 100) / 100.0, 0, 1)
    V2 = np.round(np.where(hit, t_rounded, t) * N).astype(int)
    # redistribute the difference proportionally between parties and blanks
    diff = V2 - df["voted"].to_numpy()
    party_cols = list(data.party_cols)
    party_tot = df[party_cols].to_numpy()
    denom = party_tot.sum(axis=1) + df["blank_votes"].to_numpy() + df["null_votes"].to_numpy()
    for j, c in enumerate(party_cols):
        share = np.divide(party_tot[:, j], denom, out=np.zeros(len(df)), where=denom > 0)
        df[c] = np.maximum(party_tot[:, j] + np.round(diff * share).astype(int), 0)
    df["voted"] = V2
    return ElectionData(name=data.name + " + rounded turnout", df=df, party_cols=data.party_cols), int(hit.sum())


def run_selftest(data: ElectionData, leader: str, seed: int = 7) -> SelftestReport:
    """Run both injections and evaluate the methods' response."""
    # the anomalous-turnout boundary is fixed on the CLEAN data before injection
    clean_est = shpilkin_estimate(data, leader, controls=[data])
    injected, added = inject_additive_fraud(data, leader, seed=seed)
    inj_est = shpilkin_estimate(injected, leader, controls=[data])  # t_cut from clean data

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
