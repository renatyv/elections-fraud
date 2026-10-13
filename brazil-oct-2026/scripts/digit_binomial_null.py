#!/usr/bin/env python3
"""Дополнительный нуль для цифровых тестов: биномиальная модель секций.

Логнормальный нуль digit_tests не учитывает структуру данных (счётчики
минорных кандидатов сосредоточены в узком диапазоне 10–30, где вторая цифра
не может быть равномерной по construction). Здесь нуль строится как в
integer_peaks: для каждой секции голоса кандидата симулируются
Binomial(явка_секции, доля_кандидата_в_секции) — сохраняет размеры и
структуру секций, честно воспроизводя шум пересчёта.

Выход: analysis/tables/digit_binomial_null.csv + digit_profiles.csv.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

BR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "analysis-tool" / "src"))

from election_forensics.digit_tests import BENFORD_2ND  # noqa: E402

TAB = BR / "analysis" / "tables"
N_SIM = 200
RNG = np.random.default_rng(2026)


def digits_last(x: np.ndarray) -> np.ndarray:
    return x % 10


def digits_2nd(x: np.ndarray) -> np.ndarray:
    d = np.floor(np.log10(np.maximum(x, 1))).astype(np.int64)
    return (x // np.power(10, np.maximum(d - 1, 0), dtype=np.int64)) % 10


def chi2_vs(d: np.ndarray, expected: np.ndarray) -> float:
    obs = np.bincount(d, minlength=10).astype(float)
    n = obs.sum()
    exp = expected * n
    return float(((obs - exp) ** 2 / exp).sum())


def main() -> None:
    df = pd.read_csv(BR / "data" / "secoes_presidente_2026.csv")
    parties = ["votes:BOLSONARO", "votes:LULA", "votes:CURY",
               "votes:FERREIRA", "votes:CAIADO"]
    V = df["voted"].to_numpy()
    rows, prof_rows = [], []
    for p in parties:
        c = df[p].to_numpy()
        prob = np.clip(c / V, 0, 1)
        for test, min_count, expected, digf in (
            ("benford2", 10, BENFORD_2ND, digits_2nd),
            ("last", 100, np.full(10, 0.1), digits_last),
        ):
            ok = c >= min_count
            if ok.sum() < 1000:
                continue
            chi2_obs = chi2_vs(digf(c[ok]), expected)
            sim = np.empty(N_SIM)
            for s in range(N_SIM):
                cs = RNG.binomial(V[ok], prob[ok])
                cs = cs[cs >= min_count]
                sim[s] = chi2_vs(digf(cs), expected)
            pval = float((np.sum(sim >= chi2_obs) + 1) / (N_SIM + 1))
            rows.append({
                "party": p.removeprefix("votes:"), "test": test,
                "n_numbers": int(ok.sum()),
                "chi2_obs": chi2_obs,
                "chi2_null_median": float(np.median(sim)),
                "chi2_null_p95": float(np.percentile(sim, 95)),
                "p_binomial_null": pval,
            })
            print(f"{p.removeprefix('votes:')[:12]:12s} {test:8s} chi2={chi2_obs:9.1f} "
                  f"null med={np.median(sim):9.1f} p95={np.percentile(sim, 95):9.1f} p={pval:.3f}")
        # профиль последних цифр (>=100) для отчёта
        ok = c >= 100
        if ok.sum() >= 1000:
            obs = np.bincount(digits_last(c[ok]), minlength=10) / ok.sum()
            prof_rows.append({"party": p.removeprefix("votes:"), **{
                f"d{d}": round(100 * obs[d], 3) for d in range(10)}})
    pd.DataFrame(rows).to_csv(TAB / "digit_binomial_null.csv", index=False)
    pd.DataFrame(prof_rows).to_csv(TAB / "digit_profiles.csv", index=False)


if __name__ == "__main__":
    main()
