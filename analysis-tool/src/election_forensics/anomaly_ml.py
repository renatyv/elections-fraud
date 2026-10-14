"""Finding anomalous units with ML methods (after Zhang, Alvarez, Levin, 2019).

Isolation Forest on territory features: turnout, leader share, ballot share
(blank/invalid), log size. An anomaly is not proof of fraud but a candidate
for manual inspection.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from .data import ElectionData


def isolation_forest_anomalies(
    data: ElectionData,
    party: str,
    contamination: float = 0.01,
    seed: int = 42,
) -> pd.DataFrame:
    """Ranking of territories by anomalousness (lower score — more anomalous)."""
    df = pd.DataFrame(
        {
            "key": data.df["key"],
            "name": data.df["name"],
            "concelho": data.df["path"].str.split(" > ").str[-2],
            "registered": data.df["registered_voters"],
            "turnout": data.turnout.to_numpy(),
            "share_leader": data.share(party).to_numpy(),
            "blank_pct": 100.0 * data.df["blank_votes"].to_numpy() / data.df["voted"].to_numpy(),
            "null_pct": 100.0 * data.df["null_votes"].to_numpy() / data.df["voted"].to_numpy(),
        }
    )
    df["log_size"] = np.log1p(df["registered"])
    feats = ["turnout", "share_leader", "blank_pct", "null_pct", "log_size"]
    X = df[feats].to_numpy()
    ok = np.isfinite(X).all(axis=1)
    X_scaled = StandardScaler().fit_transform(X[ok])
    iso = IsolationForest(contamination=contamination, random_state=seed, n_estimators=400)
    labels = iso.fit_predict(X_scaled)
    df["anomaly_score"] = np.nan
    df.loc[ok, "anomaly_score"] = -iso.score_samples(X_scaled)  # higher — more anomalous
    df["is_anomaly"] = False
    df.loc[ok, "is_anomaly"] = labels == -1
    return df.sort_values("anomaly_score", ascending=False)
