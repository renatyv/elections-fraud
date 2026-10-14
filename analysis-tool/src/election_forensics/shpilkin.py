"""The Shpilkin method: turnout distribution, "honest core", estimate of anomalous votes.

The idea (section 2 of the survey document):
1. Histogram of party votes as a function of turnout (weighted by the number
   of voters, not by the number of units).
2. The "honest core" — a smooth model of the main body of the distribution;
   assumption: manipulations only add turnout and votes.
3. The anomalous component is the mass of the distribution to the right of the
   boundary of natural ("honest") decline; integrating it yields an estimate of
   the number of anomalous votes for the party and allows recomputing the result.

Anomalous-turnout boundary. For heterogeneous data (Portugal: a broad mix of
urban/rural parishes) a single parametric kernel is unstable, so the boundary
is set by an external reference — the upper percentile of the weighted turnout
distribution of CONTROL elections over the same territories (the "control
countries/elections" logic from section 4 of the survey). Without controls,
the q99.5 of the data themselves is used.
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
    tail_voters: int  # voters at turnout above the boundary
    tail_votes_party: int  # party votes at turnout above the boundary
    tail_share_of_party: float  # the same as % of the party's votes
    observed_share_pct: float
    honest_share_pct: float  # the party's result without the anomalous zone

    def to_dict(self) -> dict:
        return asdict(self)


def votes_by_turnout(
    data: ElectionData,
    weight_col: str | None = None,
    bin_width: float = 0.5,
) -> tuple[np.ndarray, np.ndarray]:
    """Histogram: sum of weight_col over turnout bins.

    weight_col=None → number of voters (the turnout distribution weighted by
    the electorate), otherwise — votes for the party.
    """
    turnout = data.turnout.to_numpy()
    w = data.df[weight_col].to_numpy() if weight_col else data.df["voted"].to_numpy()
    edges = np.arange(0.0, 100.0 + bin_width, bin_width)
    h, _ = np.histogram(turnout, bins=edges, weights=w)
    centers = 0.5 * (edges[:-1] + edges[1:])
    return centers, h


def suggest_t_cut(controls: list[ElectionData], q: float = 99.5) -> float:
    """Anomalous-turnout boundary: the maximum q-percentile across control elections."""
    qs = []
    for c in controls:
        t = c.turnout.to_numpy()
        w = c.registered.to_numpy()
        qs.append(float(np.percentile(np.repeat(t, np.round(w).astype(int)), q)))
    return max(qs)


def smooth_mode_sigma(centers: np.ndarray, h: np.ndarray, smooth_bins: float = 2.0) -> tuple[float, float]:
    """Mode and σ of the smooth approximation of the distribution (for reference and plots)."""
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
    """Estimate of anomalous votes for the party: the mass to the right of the honest-decline boundary."""
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
    """Data for the "turnout × result" scatter plot (the comet tail)."""
    return pd.DataFrame(
        {
            "turnout": data.turnout,
            "share": data.share(party),
            "voters": data.df["registered_voters"],
            "name": data.df["name"],
        }
    )
