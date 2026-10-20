"""Resolve coarse Monte Carlo floors for digit flags, retaining the full family."""
from __future__ import annotations

import numpy as np
import pandas as pd
from expanded_analysis import OUT
from precincts import bh
from election_forensics.digit_tests import BENFORD_2ND, _digits


def numerical_digits(counts: np.ndarray, test: str) -> np.ndarray:
    if test == 'last': return counts % 10
    exponent = np.floor(np.log10(counts)).astype(int)-1
    return (counts // (10**exponent)) % 10


def refined_p(counts: np.ndarray, test: str, chi2: float, simulations: int = 20000) -> float:
    minimum = 100 if test == 'last' else 10
    counts = counts[counts >= minimum]
    mu, sigma = np.log(counts).mean(), np.log(counts).std()
    expected = np.full(10,.1) if test == 'last' else BENFORD_2ND
    rng = np.random.default_rng(314159)
    exceed = 0
    for start in range(0,simulations,32):
        draws = np.rint(np.exp(rng.normal(mu,sigma,(min(32,simulations-start),2*len(counts))))).astype(np.int64)
        for row in draws:
            row = row[row >= minimum][:len(counts)]
            observed = np.bincount(numerical_digits(row,test),minlength=10)
            wanted = len(row)*expected
            statistic = ((observed-wanted)**2/wanted).sum()
            exceed += statistic >= chi2
    return (exceed+1)/(simulations+1)


def main() -> None:
    values = np.array([10,11,99,100,101,999,1000,10001,999999])
    for test in ['last','benford2']:
        assert np.array_equal(numerical_digits(values,test),_digits(values,test))
    d = pd.read_csv(OUT/'precinct_digits.csv',dtype={'district':str})
    audit = pd.read_csv(OUT/'precinct_join_audit.csv.gz',dtype={'district':str},low_memory=False)
    d['p_mc_refined'] = 1.0
    d['refined_simulations'] = 0
    # Unselected tests get p=1, so their omission cannot create a rejection.
    selected = (d.q_bh < .05)|(d.p_null_mc <= 1/401+1e-10)
    for index,row in d[selected].iterrows():
        frame = audit[audit.eligible&audit['sample'].eq(row['sample'])&audit.district.eq(row.district)]
        d.loc[index,'p_mc_refined'] = refined_p(frame['votes:'+row.party].to_numpy(),row.test,row.chi2)
        d.loc[index,'refined_simulations'] = 20000
        print(row['sample'],row.district,row.party,row.test,d.loc[index,'p_mc_refined'],flush=True)
    d['q_mc_refined_bh'] = bh(d.p_mc_refined)
    d.to_csv(OUT/'precinct_digits.csv',index=False)


if __name__ == '__main__': main()
