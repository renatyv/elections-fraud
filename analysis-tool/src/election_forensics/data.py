"""Loading election results from MAI portal summary CSVs (Portugal).

Format: key, level, name, path, parent_key, registered_voters, voted,
turnout_pct, blank_votes, null_votes, votes:<PARTY>..., mandates.
The lowest data level is freguesia (parish, level 3).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

# Minimum unit size for the digit-based tests: in tiny parishes, last-digit
# uniformity and integer percentages arise naturally.
MIN_UNITS_FOR_DIGIT_TESTS = 100


@dataclass
class ElectionData:
    """Election results across territories of one level (usually freguesias)."""

    name: str
    df: pd.DataFrame
    party_cols: list[str] = field(default_factory=list)

    @property
    def leader_party(self) -> str:
        """Leading party by total votes (the "party of power" analogue)."""
        totals = {c: int(self.df[c].sum()) for c in self.party_cols}
        return max(totals, key=totals.get)

    @property
    def n(self) -> int:
        return len(self.df)

    @property
    def registered(self) -> pd.Series:
        return self.df["registered_voters"]

    @property
    def voted(self) -> pd.Series:
        return self.df["voted"]

    @property
    def turnout(self) -> pd.Series:
        """Turnout, % (recomputed from votes, without trusting turnout_pct from the CSV)."""
        return 100.0 * self.df["voted"] / self.df["registered_voters"]

    def share(self, party: str) -> pd.Series:
        """Party vote share of ballots cast, %."""
        return 100.0 * self.df[party] / self.df["voted"]


def load_mai_csv(csv_path: str | Path, election_name: str = "") -> ElectionData:
    """Load a MAI summary CSV (results_freguesias.csv or results_all.csv with level=3)."""
    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    if "level" in df.columns and (df["level"] != 3).any():
        df = df[df["level"] == 3].copy()
    df = df.dropna(subset=["registered_voters", "voted"]).copy()
    for col in df.columns:
        if col.startswith("votes:"):
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    party_cols = [c for c in df.columns if c.startswith("votes:")]
    if not election_name:
        election_name = csv_path.parent.name
    return ElectionData(name=election_name, df=df, party_cols=party_cols)


def load_territory_tree(mai_dir: str | Path) -> dict:
    """Territory tree territory-tree.json: key -> (parent, level, name)."""
    tree_file = Path(mai_dir) / "territory-tree.json"
    with open(tree_file, encoding="utf-8") as f:
        raw = json.load(f)
    flat: dict[str, dict] = {}

    def walk(node: dict) -> None:
        flat[node["key"]] = {
            "parent": node.get("parent"),
            "level": node.get("level"),
            "name": node.get("name"),
        }
        for child in node.get("children", []) or []:
            walk(child)

    if isinstance(raw, dict) and "children" in raw:
        walk(raw)
    elif isinstance(raw, list):
        for root in raw:
            walk(root)
    return flat


def subset_for_digit_tests(data: ElectionData, min_units: int = MIN_UNITS_FOR_DIGIT_TESTS) -> ElectionData:
    """Subset of sufficiently large territories for the digit-based tests."""
    mask = data.df["registered_voters"] >= min_units
    return ElectionData(name=data.name, df=data.df[mask].copy(), party_cols=data.party_cols)


def major_parties(data: ElectionData, top: int = 6, min_total: int = 50_000) -> list[str]:
    """Largest parties: for plots and tables."""
    totals = {c: int(data.df[c].sum()) for c in data.party_cols if data.df[c].sum() >= min_total}
    ranked = sorted(totals, key=totals.get, reverse=True)
    return ranked[:top]


def merge_parties(data: ElectionData, spec: str) -> ElectionData:
    """Merge coalition columns: 'votes:A<-votes:B,votes:C'.

    In Portugal a single coalition may run under different columns in
    different districts (AR-2025: AD = PPD/PSD.CDS-PP on the mainland and
    PPD/PSD.CDS-PP.PPM in the Azores) — without merging, the "leader" is
    zeroed on part of the territories. Source votes are added to the target
    column and the sources are dropped.
    """
    target, _, rest = spec.partition("<-")
    target = target.strip()
    df = data.df.copy()
    party_cols = list(data.party_cols)
    for src in [s.strip() for s in rest.split(",") if s.strip()]:
        if src in df.columns and target in df.columns and src != target:
            df[target] = df[target] + df[src]
            if src in party_cols:
                party_cols.remove(src)
    return ElectionData(name=data.name, df=df, party_cols=party_cols)


def national_totals(data: ElectionData) -> dict:
    """National summary metrics (sum over territories)."""
    valid = data.df[["blank_votes", "null_votes"]].sum().sum() * 0  # placeholder type
    total_votes = data.df["voted"].sum()
    out = {
        "n_units": data.n,
        "registered": int(data.registered.sum()),
        "voted": int(data.voted.sum()),
        "turnout_pct": 100.0 * data.voted.sum() / data.registered.sum(),
        "blank_pct": 100.0 * data.df["blank_votes"].sum() / total_votes,
        "null_pct": 100.0 * data.df["null_votes"].sum() / total_votes,
    }
    for c in data.party_cols:
        s = data.df[c].sum()
        if s > 0:
            out[f"share:{c.removeprefix('votes:')}"] = 100.0 * s / total_votes
    return out


def rounder(x: np.ndarray | pd.Series, decimals: int = 0) -> np.ndarray:
    """Rounding as in official protocols (half-up, not banker's)."""
    arr = np.asarray(x, dtype=float)
    factor = 10**decimals
    return np.floor(arr * factor + 0.5) / factor
