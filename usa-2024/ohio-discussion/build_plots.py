"""Reproduce Ohio's second-digit screen and plots from the bundled CSV files.

Run: python build_plots.py (numpy, pandas, scipy, matplotlib required).
No network access or repository-specific imports are used.
"""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import chi2

ROOT = Path(__file__).resolve().parent


def bh(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values)
    adjusted = np.empty(len(values))
    adjusted[order] = np.minimum(1, np.minimum.accumulate(
        (values[order] * len(values) / np.arange(1, len(values) + 1))[::-1])[::-1])
    return adjusted


def main() -> None:
    frame = pd.read_csv(ROOT / 'data/ohio_senate_precincts.csv')
    assert len(frame) == 8878 and frame.key.is_unique
    counts = frame.loc[frame['votes:REP'] >= 10, 'votes:REP'].to_numpy(dtype=np.int64)
    assert len(counts) == 8798 and (counts >= 10).all()
    digits = np.array([int(str(x)[1]) for x in counts])
    observed = np.bincount(digits, minlength=10)
    expected = np.array([sum(np.log10(1 + 1 / (10 * first + d)) for first in range(1, 10)) for d in range(10)])
    statistic = float(((observed - len(counts) * expected) ** 2 / (len(counts) * expected)).sum())
    p = float(chi2.sf(statistic, 9))
    family = pd.read_csv(ROOT / 'data/full_digit_test_family.csv')
    selected = family['sample'].eq('OH2024 SENATE') & family.party.eq('REP') & family.test.eq('benford2')
    assert len(family) == 694 and selected.sum() == 1
    result = family.loc[selected].iloc[0]
    assert np.isclose(statistic, result.chi2) and np.isclose(p, result.p_value, rtol=1e-9, atol=0)
    assert np.allclose(bh(family.p_value.to_numpy()), family.q_bh)
    assert np.allclose(bh(family.p_mc_refined.to_numpy()), family.q_mc_refined_bh)
    mu, sigma = np.log(counts).mean(), np.log(counts).std()
    rng = np.random.default_rng(314159)
    simulated = np.empty((20000, 10))
    exceed = 0
    for start in range(0, 20000, 32):
        draws = np.rint(np.exp(rng.normal(mu, sigma, (min(32, 20000-start), 2*len(counts))))).astype(np.int64)
        for offset, row in enumerate(draws):
            row = row[row >= 10][:len(counts)]
            assert len(row) == len(counts)
            sd = (row // (10 ** (np.floor(np.log10(row)).astype(int)-1))) % 10
            obs = np.bincount(sd, minlength=10)
            simulated[start+offset] = obs / len(row)
            exceed += ((obs-len(row)*expected)**2/(len(row)*expected)).sum() >= statistic
    p_mc = (int(exceed)+1)/20001
    assert np.isclose(p_mc, result.p_mc_refined)
    low, high = np.percentile(simulated, [2.5, 97.5], axis=0) * 100
    table = pd.DataFrame({'second_digit':range(10), 'observed_count':observed,
        'observed_pct':observed/len(counts)*100, 'benford_expected_count':expected*len(counts),
        'benford_pct':expected*100, 'lognormal_mean_pct':simulated.mean(axis=0)*100,
        'lognormal_low_pct':low, 'lognormal_high_pct':high,
        'pearson_residual':(observed-len(counts)*expected)/np.sqrt(len(counts)*expected)})
    table.to_csv(ROOT/'data/second_digit_frequencies.csv', index=False)
    summary = {'n_rows':len(frame),'n_tested':len(counts),'excluded_below_10':len(frame)-len(counts),
        'chi2':statistic,'degrees_of_freedom':9,'p_theoretical':p,'q_theoretical':float(result.q_bh),
        'p_lognormal':p_mc,'q_lognormal':float(result.q_mc_refined_bh),
        'simulations':20000,'exceedances':int(exceed),'seed':314159,
        'log_count_mu':float(mu),'log_count_sigma_population':float(sigma),'family_tests':len(family)}
    (ROOT/'data/result.json').write_text(json.dumps(summary,indent=2)+'\n')
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig, ax = plt.subplots(figsize=(9,5))
    x = np.arange(10)
    ax.bar(x-.15, table.observed_pct, width=.55, color='#307aa5', label='Observed Ohio Republican totals')
    mean = table.lognormal_mean_pct.to_numpy()
    ax.errorbar(x+.23,mean,yerr=[mean-low, high-mean],fmt='s',color='#b57414',capsize=3,
                label='Fitted lognormal: pointwise 95% ranges')
    ax.plot(x,expected*100,'o-',color='#18314b',label='Benford reference')
    ax.set(xlabel='Second digit',ylabel='Reporting units (%)',xticks=x,ylim=(0,16),
           title='Ohio Senate 2024: Republican second digits (n = 8,798)')
    ax.legend(loc='upper center',bbox_to_anchor=(.5,-.16),frameon=False,fontsize=9)
    fig.subplots_adjust(bottom=.26)
    fig.savefig(ROOT/'figures/second_digits.png',dpi=180); plt.close(fig)
    fig, axes = plt.subplots(1,2,figsize=(9,4))
    axes[0].bar(x,table.pearson_residual,color='#307aa5'); axes[0].axhline(0,color='#18314b',lw=1)
    axes[0].set(xticks=x,xlabel='Second digit',ylabel='Pearson residual',title='Departure from Benford')
    axes[1].hist(counts,bins=np.geomspace(counts.min(),counts.max()+1,35),color='#307aa5')
    axes[1].set(xscale='log',xlabel='Republican votes per reporting unit',ylabel='Reporting units',title='Vote-count sizes (tested units)')
    fig.tight_layout(); fig.savefig(ROOT/'figures/residuals_and_sizes.png',dpi=180); plt.close(fig)
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    main()
