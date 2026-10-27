"""Two-component Gaussian fit to turnout and list share.

Two components are requested in advance, not inferred as the optimal number.
Registered-elector-weighted resampling approximates weighting in the fit.
The legacy ``separated`` field is a directional screening rule, not a test
of cluster separation or evidence that a component represents fraud.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
from sklearn.mixture import GaussianMixture

from .data import ElectionData


@dataclass
class FingerprintResult:
    party: str
    # mixture component parameters (0 — main, 1 — anomalous, if separated)
    weight_anom: float
    mean_anom: tuple[float, float]
    mean_main: tuple[float, float]
    anom_cluster_voters: int
    anom_cluster_votes_party: int
    total_voters: int
    separated: bool  # directional screening rule; not statistical separation

    def to_dict(self) -> dict:
        return asdict(self)


def fingerprint_mixture(
    data: ElectionData,
    party: str,
    seed: int = 42,
) -> FingerprintResult:
    """Fit two Gaussians; flag higher turnout (>2 pp), higher share, weight >1%."""
    rng = np.random.default_rng(seed)
    x = data.turnout.to_numpy(dtype=float)
    y = data.share(party).to_numpy(dtype=float)
    w = data.registered.to_numpy(dtype=float)
    ok = np.isfinite(y) & (data.df["voted"].to_numpy() > 0)
    x, y, w = x[ok], y[ok], w[ok]

    # sklearn 1.9 does not accept sample_weight in GaussianMixture.fit —
    # weighting by voters is done by resampling the territories
    p = w / w.sum()
    sample_size = min(50_000, max(20_000, 10 * len(x)))
    idx = rng.choice(len(x), size=sample_size, replace=True, p=p)
    gm = GaussianMixture(n_components=2, covariance_type="full", random_state=seed,
                         n_init=3, max_iter=300, reg_covar=1e-3)
    gm.fit(np.column_stack([x[idx], y[idx]]))
    means = gm.means_
    # the anomalous component is the one with the higher turnout
    anom_idx = int(np.argmax(means[:, 0]))
    main_idx = 1 - anom_idx
    weight_anom = float(gm.weights_[anom_idx])

    # clusters by posterior probabilities
    labels = gm.predict(np.column_stack([x, y]))
    anom_mask = labels == anom_idx
    anom_voters = int(w[anom_mask].sum())
    anom_votes_party = int(data.df[party].to_numpy()[ok][anom_mask].sum())

    # the fraud cluster per Klimek et al. is "up and to the right": higher
    # turnout AND a higher result; a split along turnout only or result only
    # is territorial heterogeneity, not a fraud signal
    separated = bool(
        weight_anom > 0.01
        and means[anom_idx, 0] - means[main_idx, 0] > 2.0
        and means[anom_idx, 1] > means[main_idx, 1]
    )
    return FingerprintResult(
        party=party.removeprefix("votes:"),
        weight_anom=weight_anom,
        mean_anom=(float(means[anom_idx, 0]), float(means[anom_idx, 1])),
        mean_main=(float(means[main_idx, 0]), float(means[main_idx, 1])),
        anom_cluster_voters=anom_voters,
        anom_cluster_votes_party=anom_votes_party,
        total_voters=int(w.sum()),
        separated=bool(separated),
    )


def to_dict(res: FingerprintResult) -> dict:
    return res.to_dict()
