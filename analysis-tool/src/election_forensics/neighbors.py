"""Comparison of "similar" territories and neighbours (Myagkov, Ordeshook, Shakin, 2009).

Two tests:
1. Outlier relative to one's own municipality (concelho): robust z-scores of
   turnout and the leader's share against the median of neighbouring parishes
   of the same concelho.
2. Jump relative to the previous election in the same territory: change in
   turnout and party share between two elections (results_all_previous.csv).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .data import ElectionData


def robust_z_outliers(data: ElectionData, party: str, threshold: float = 4.0) -> pd.DataFrame:
    """Robust outliers of turnout and party share relative to one's own concelho."""
    df = data.df[["key", "name", "path", "parent_key", "registered_voters", "voted"]].copy()
    df["turnout"] = data.turnout.to_numpy()
    df["share"] = data.share(party).to_numpy()

    def _z(g: pd.DataFrame, col: str) -> pd.Series:
        med = g[col].median()
        mad = (g[col] - med).abs().median()
        z = (g[col] - med) / (1.4826 * mad) if mad > 0 else g[col] * 0
        return z

    df["z_turnout"] = df.groupby("parent_key", group_keys=False).apply(
        lambda g: _z(g, "turnout"), include_groups=False
    )
    df["z_share"] = df.groupby("parent_key", group_keys=False).apply(
        lambda g: _z(g, "share"), include_groups=False
    )
    df["n_concelho"] = df.groupby("parent_key")["key"].transform("count")
    df["concelho"] = df["path"].str.split(" > ").str[-2]
    small = df["n_concelho"] < 4
    df.loc[small, ["z_turnout", "z_share"]] = np.nan
    df["flag"] = df[["z_turnout", "z_share"]].abs().max(axis=1) > threshold
    return df.sort_values("z_share", key=lambda s: s.abs(), ascending=False)


def swing_vs_previous(
    current: ElectionData,
    previous: ElectionData,
    party: str,
    turnout_jump: float = 15.0,
    share_jump: float = 15.0,
) -> pd.DataFrame:
    """Change in turnout and party share between two elections over the same territories."""
    cur = current.df.set_index("key")
    prev = previous.df.set_index("key")
    keys = cur.index.intersection(prev.index)
    out = pd.DataFrame(index=keys)
    out["name"] = cur.loc[keys, "name"]
    out["concelho"] = cur.loc[keys, "path"].str.split(" > ").str[-2]
    out["registered"] = cur.loc[keys, "registered_voters"]
    out["turnout_now"] = 100.0 * cur.loc[keys, "voted"] / cur.loc[keys, "registered_voters"]
    out["turnout_prev"] = 100.0 * prev.loc[keys, "voted"] / prev.loc[keys, "registered_voters"]
    out["d_turnout"] = out["turnout_now"] - out["turnout_prev"]
    out["share_now"] = 100.0 * cur.loc[keys, party] / cur.loc[keys, "voted"]
    out["share_prev"] = 100.0 * prev.loc[keys, party] / prev.loc[keys, "voted"]
    out["d_share"] = out["share_now"] - out["share_prev"]
    out["flag"] = (out["d_turnout"].abs() > turnout_jump) & (out["d_share"].abs() > share_jump)
    out["flag_turnout_only"] = out["d_turnout"].abs() > turnout_jump
    return out.reset_index()
