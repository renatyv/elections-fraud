"""Explain the published Ohio second-digit finding without rerunning the tests."""
from __future__ import annotations

import numpy as np
import pandas as pd
from build_site_figures import ROOT, SITE, INK, BLUE, GOLD, plt, save
from election_forensics.digit_tests import BENFORD_2ND, digit_freqs, digit_null_band


def main() -> None:
    audit = pd.read_csv(ROOT / 'analysis/expanded/precinct_join_audit.csv.gz', low_memory=False)
    counts = audit.loc[audit.eligible & audit['sample'].eq('OH2024 SENATE'), 'votes:REP'].to_numpy()
    counts = counts[counts >= 10]
    results = pd.read_csv(ROOT / 'analysis/expanded/precinct_digits.csv')
    result = results.loc[results['sample'].eq('OH2024 SENATE') & results.party.eq('REP') & results.test.eq('benford2')].squeeze()
    frequencies = digit_freqs(counts, 'benford2')
    statistic = float(np.sum((frequencies * len(counts) - BENFORD_2ND * len(counts)) ** 2 / (BENFORD_2ND * len(counts))))
    assert len(counts) == result.n_numbers == 8798
    assert np.isclose(statistic, result.chi2)
    assert np.isclose(frequencies.sum(), 1)
    assert np.array_equal(np.array([int(str(n)[1]) for n in [12, 123, 1234]]), [2, 2, 2])

    fig, ax = plt.subplots(figsize=(8, 4.3))
    ax.axis('off')
    ax.set_title('What is a second-digit check?', fontsize=20, color=INK, pad=18)
    for x, digits in zip([.18, .5, .82], ['12', '123', '1234']):
        for i, digit in enumerate(digits):
            ax.text(x + (i - (len(digits)-1)/2)*.047, .72, digit, transform=ax.transAxes,
                    ha='center', fontsize=32, weight='bold', color=GOLD if i == 1 else INK)
        ax.text(x, .49, 'Second digit: 2', transform=ax.transAxes, ha='center', fontsize=13, color=GOLD)
    ax.text(.5, .24, 'Do this for each local vote total, then count the 0s, 1s, 2s … 9s.',
            transform=ax.transAxes, ha='center', fontsize=12, color=INK)
    ax.text(.5, .08, 'Illustration only. These three numbers are not Ohio results.',
            transform=ax.transAxes, ha='center', fontsize=10, color='#526578')
    save(fig, 'ohio_second_digit_explainer.png')

    band = digit_null_band(counts, 'benford2', n_sim=2000, seed=314159) * 100
    fig, ax = plt.subplots(figsize=(8, 5.2))
    digits = np.arange(10)
    ax.bar(digits, frequencies * 100, width=.58, color=BLUE, label='Ohio Republican vote totals', zorder=2)
    ax.errorbar(digits + .32, band.mean(axis=0), yerr=(band[1]-band[0])/2,
                fmt='s', markersize=3, capsize=4, color=GOLD,
                label='Middle 95% of simulated frequencies', zorder=3)
    ax.plot(digits, BENFORD_2ND * 100, color=INK, marker='o', markersize=4,
            linewidth=1.5, label='Benford reference pattern', zorder=4)
    ax.set(title='Ohio Senate: how often did each second digit appear?',
           xlabel='Second digit of the local Republican vote total',
           ylabel='Share of the 8,798 vote totals (%)', xticks=digits, ylim=(0, 16))
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(axis='y', alpha=.15)
    ax.set_axisbelow(True)
    ax.legend(loc='upper center', bbox_to_anchor=(.5, -.18), frameon=False, fontsize=10)
    fig.subplots_adjust(bottom=.29)
    save(fig, 'ohio_second_digit_counts.png')
    pd.DataFrame({'second_digit':digits, 'observed_count':np.rint(frequencies * len(counts)).astype(int),
                  'observed_pct':frequencies * 100, 'benford_pct':BENFORD_2ND * 100,
                  'simulated_low_pct':band[0], 'simulated_high_pct':band[1]}).to_csv(
                      SITE / 'analysis/expanded/ohio_second_digit_frequencies.csv', index=False)


if __name__ == '__main__':
    main()
