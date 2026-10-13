"""Загрузка результатов выборов из сводных CSV портала MAI (Португалия).

Формат: key, level, name, path, parent_key, registered_voters, voted,
turnout_pct, blank_votes, null_votes, votes:<PARTY>..., mandates.
Нижний уровень данных — freguesia (приход, level 3).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

# Минимальный размер территории для «цифровых» тестов: в крошечных приходах
# равномерность последних цифр и целые проценты возникают естественно.
MIN_UNITS_FOR_DIGIT_TESTS = 100


@dataclass
class ElectionData:
    """Результаты выборов по территориям одного уровня (обычно freguesias)."""

    name: str
    df: pd.DataFrame
    party_cols: list[str] = field(default_factory=list)

    @property
    def leader_party(self) -> str:
        """Партия-лидер по сумме голосов (аналог «партии власти»)."""
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
        """Явка, % (пересчитанная из голосов, без доверия turnout_pct CSV)."""
        return 100.0 * self.df["voted"] / self.df["registered_voters"]

    def share(self, party: str) -> pd.Series:
        """Доля голосов за партию от числа проголосовавших, %."""
        return 100.0 * self.df[party] / self.df["voted"]


def load_mai_csv(csv_path: str | Path, election_name: str = "") -> ElectionData:
    """Загрузить сводный CSV MAI (results_freguesias.csv или results_all.csv c level=3)."""
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
    """Дерево территорий territory-tree.json: key -> (parent, level, name)."""
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
    """Подмножество достаточно крупных территорий для цифровых тестов."""
    mask = data.df["registered_voters"] >= min_units
    return ElectionData(name=data.name, df=data.df[mask].copy(), party_cols=data.party_cols)


def major_parties(data: ElectionData, top: int = 6, min_total: int = 50_000) -> list[str]:
    """Крупнейшие партии: для графиков и таблиц."""
    totals = {c: int(data.df[c].sum()) for c in data.party_cols if data.df[c].sum() >= min_total}
    ranked = sorted(totals, key=totals.get, reverse=True)
    return ranked[:top]


def merge_parties(data: ElectionData, spec: str) -> ElectionData:
    """Объединить колонки коалиций: 'votes:A<-votes:B,votes:C'.

    В Португалии одна коалиция может идти разными колонками в разных
    округах (AR-2025: AD = PPD/PSD.CDS-PP на материке и PPD/PSD.CDS-PP.PPM
    на Азорах) — без объединения «лидер» обнувается на части территорий.
    Голоса источников прибавляются к целевой колонке, источники исключаются.
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
    """Сводные национальные показатели (сумма по территориям)."""
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
    """Округление как в официальных протоколах (half-up, а не банковское)."""
    arr = np.asarray(x, dtype=float)
    factor = 10**decimals
    return np.floor(arr * factor + 0.5) / factor
