"""2D-корреляционный анализ «явка ↔ результат» (Kobak et al., arXiv:1205.0741).

Совместный анализ корреляций явки с результатами всех крупных партий,
взвешенно по числу избирателей: национально и по округам (círculos).
Признак перелива голосов: у «партии власти» корреляция положительная
и растёт с аномальной явкой, у оппонентов — отрицательная.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .data import ElectionData


def weighted_pearson(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    xm = np.average(x, weights=w)
    ym = np.average(y, weights=w)
    cov = np.average((x - xm) * (y - ym), weights=w)
    sx = np.sqrt(np.average((x - xm) ** 2, weights=w))
    sy = np.sqrt(np.average((y - ym) ** 2, weights=w))
    return float(cov / (sx * sy)) if sx > 0 and sy > 0 else float("nan")


def turnout_result_correlations(data: ElectionData, parties: list[str]) -> pd.DataFrame:
    """Национальные корреляции явка × доля партии (Пирсон и Спирмен)."""
    t = data.turnout.to_numpy()
    w = data.registered.to_numpy(dtype=float)
    rows = []
    for p in parties:
        s = data.share(p).to_numpy()
        ok = np.isfinite(s) & np.isfinite(t)
        rho_s = stats.spearmanr(t[ok], s[ok]).statistic
        rows.append(
            {
                "party": p.removeprefix("votes:"),
                "pearson_w": weighted_pearson(t[ok], s[ok], w[ok]),
                "spearman": rho_s,
            }
        )
    return pd.DataFrame(rows)


def district_key(key: str) -> str:
    """Ключ округа (círculo) из ключа freguesia: LOCAL-0XYZAB -> LOCAL-0X0000."""
    if key.startswith("LOCAL-") and len(key) == 12:
        return f"LOCAL-{key[6:8]}0000"
    return ""


def district_correlations(data: ElectionData, parties: list[str]) -> pd.DataFrame:
    """Корреляции явка × доля партии по округам (взвешенный Пирсон)."""
    df = data.df.copy()
    df["turnout"] = data.turnout.to_numpy()
    df["district_key"] = df["key"].map(district_key)
    names = (
        df.groupby("district_key")["path"]
        .first()
        .str.split(" > ")
        .str[1]
        .rename("district")
    )
    out = []
    for dkey, g in df.groupby("district_key"):
        if len(g) < 30:
            continue
        w = g["registered_voters"].to_numpy(dtype=float)
        row: dict = {"district_key": dkey, "district": names.get(dkey, dkey), "n": len(g)}
        for p in parties:
            s = 100.0 * g[p].to_numpy() / g["voted"].to_numpy()
            row[p.removeprefix("votes:")] = weighted_pearson(g["turnout"].to_numpy(), s, w)
        out.append(row)
    res = pd.DataFrame(out)
    # Азорские острова представлены несколькими округами с одинаковым именем —
    # различаем их кодом территории
    dup = res["district"].duplicated(keep=False)
    res.loc[dup, "district"] = res.loc[dup, "district"] + " (" + res.loc[dup, "district_key"].str[6:8] + ")"
    return res.sort_values("district").reset_index(drop=True)
