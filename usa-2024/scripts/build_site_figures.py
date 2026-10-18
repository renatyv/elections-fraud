"""Build the static U.S. page's figures and downloadable analysis snapshot."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT.parent / 'site/usa-2024'
INK, BLUE, GOLD = '#16324f', '#3b82c4', '#b7791f'
sys.path.insert(0, str(ROOT.parent / 'analysis-tool/src'))
from election_forensics.data import ElectionData
from election_forensics.shpilkin import votes_by_turnout, shpilkin_estimate
from election_forensics.selftest import inject_additive_fraud
from election_forensics.digit_tests import digit_freqs, BENFORD_2ND


def save(fig: plt.Figure, name: str) -> None:
    fig.tight_layout()
    fig.savefig(SITE / 'img' / name, dpi=160, facecolor='white', bbox_inches='tight')
    plt.close(fig)


def election(rows: pd.DataFrame) -> ElectionData:
    frame = rows.copy()
    for party in ['DEMOCRAT', 'REPUBLICAN', 'OTHER']:
        frame['votes:' + party] = frame[party].astype(int)
    return ElectionData('Matched counties', frame, ['votes:DEMOCRAT', 'votes:REPUBLICAN', 'votes:OTHER'])


def diagnostic_figures() -> None:
    county = pd.read_csv(ROOT / 'analysis/county_turnout_join_audit.csv', dtype={'county_fips': str})
    county = county[county.eligible].copy()
    records = json.loads((ROOT / 'analysis/county_metrics.json').read_text())
    panels = [('FL', 'US SENATE'), ('PA', 'US SENATE'), ('MI', 'US SENATE'), ('WA', 'US HOUSE')]
    fig_tail, axes_tail = plt.subplots(2, 2, figsize=(11, 7))
    fig_fp, axes_fp = plt.subplots(2, 2, figsize=(10, 8))
    for i, (state, office) in enumerate(panels):
        group = county[(county.state_po == state) & (county.office == office)]
        result = next(x for x in records if (x['state'], x['office']) == (state, office))
        assert len(group) == result['n_counties']
        data = election(group)
        leader = result['leader']
        tail = result['turnout_tail']
        centers, voters = votes_by_turnout(data)
        _, party = votes_by_turnout(data, leader)
        ax = axes_tail.flat[i]
        ax.plot(centers, voters / 1000, color=BLUE, label='All participants')
        ax.plot(centers, party / 1000, color=GOLD, label='Leading-party votes')
        ax.axvline(tail['t_cut'], color='#b45345', linestyle='--', label='Own-data 99.5th percentile')
        ax.set(title=f"{state} {office} · {len(group)} counties", xlabel='Turnout (%)', ylabel='Votes per 0.5 pp bin (thousands)', xlim=(30, 100))
        ax.text(.02, .94, f"Tail: {tail['tail_votes_party']:,} votes ({tail['tail_share_of_party']:.2f}%)", transform=ax.transAxes, va='top', fontsize=9)
        if i == 0: ax.legend(fontsize=7, loc='upper left', bbox_to_anchor=(0, .82))
        ax = axes_fp.flat[i]
        ax.hist2d(data.turnout, data.share(leader), bins=[np.arange(0, 102, 2), np.arange(0, 102, 2)], cmap='Blues', cmin=1)
        mixture = result['mixture']
        for key, marker, color in [('mean_main', 'o', GOLD), ('mean_anom', 'x', '#b45345')]:
            ax.scatter(*mixture[key], marker=marker, color=color, s=70)
        ax.set(title=f"{state} {office} · {leader.removeprefix('votes:').title()}", xlabel='Turnout (%)', ylabel='Party votes / participants (%)', xlim=(30,100), ylim=(0,100))
    save(fig_tail, 'shpilkin.png')
    save(fig_fp, 'fingerprints.png')
    peaks = pd.read_csv(ROOT / 'analysis/county_integer_peaks.csv')
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for ax, is_turnout, title in zip(axes, [True, False], ['Integer turnout percentages', 'Integer leading-party shares']):
        z = peaks.loc[peaks.metric.eq('turnout') == is_turnout, 'z_score']
        ax.hist(z, bins=np.arange(-4, 4.51, .5), color=BLUE, edgecolor='white')
        ax.set(title=title, xlabel='Monte Carlo z-score (unadjusted)', ylabel='State–office samples')
        ax.axvline(1.96, color=GOLD, linestyle='--')
        ax.axvline(-1.96, color=GOLD, linestyle='--')
    save(fig, 'integer_peaks.png')
    corr = pd.read_csv(ROOT / 'analysis/county_correlations.csv')
    matrix = corr[corr.party.eq('REPUBLICAN')].pivot(index='state', columns='office', values='pearson_w')
    fig, ax = plt.subplots(figsize=(6.5, 7))
    im = ax.imshow(matrix, vmin=-1, vmax=1, cmap='RdBu_r', aspect='auto')
    ax.set(xticks=range(len(matrix.columns)), xticklabels=matrix.columns, yticks=range(len(matrix)), yticklabels=matrix.index)
    for i in range(len(matrix)):
        for j in range(len(matrix.columns)):
            v = matrix.iloc[i,j]
            ax.text(j, i, f'{v:+.2f}' if pd.notna(v) else '—', ha='center', va='center', color='white' if abs(v)>.65 else INK)
    fig.colorbar(im, ax=ax, label='Weighted turnout–Republican-share correlation')
    save(fig, 'correlations.png')
    candidates = pd.read_csv(ROOT / 'data/congress_candidate_units.csv.gz', dtype=str, keep_default_na=False)
    candidates['votes'] = pd.to_numeric(candidates.votes, errors='coerce')
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, state, office, test in zip(axes, ['MA','MO'], ['US HOUSE','US SENATE'], ['benford2','last']):
        counts = candidates.loc[candidates.state_po.eq(state) & candidates.office.eq(office) &
                                candidates.special.eq('FALSE') & candidates.party.eq('DEMOCRAT'), 'votes'].dropna().to_numpy()
        minimum = 10 if test == 'benford2' else 100
        expected_n = pd.read_csv(ROOT / 'analysis/digit_tests.csv').query(
            'state == @state and office == @office and party == "DEMOCRAT" and test == @test').n_numbers.item()
        assert int((counts >= minimum).sum()) == expected_n
        observed = digit_freqs(counts, test)
        assert np.isclose(observed.sum(), 1)
        expected = BENFORD_2ND if test == 'benford2' else np.full(10,.1)
        ax.bar(np.arange(10), observed*100, color=BLUE, label='Observed')
        ax.plot(np.arange(10), expected*100, 'o--', color=GOLD, label='Theoretical reference')
        ax.set(title=f'{state} {office} · Democrats · {test}', xlabel='Digit', ylabel='Share of eligible counts (%)', xticks=range(10))
        ax.text(.02,.97,f'n = {(counts >= minimum).sum():,}',transform=ax.transAxes,va='top',fontsize=9)
        ax.legend(fontsize=8,loc='lower right')
    save(fig, 'digit_frequencies.png')
    outliers = pd.read_csv(ROOT / 'analysis/county_within_state_outliers.csv')
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for flag, label, color in [(False, 'Not flagged', BLUE), (True, 'Median/MAD flag', GOLD)]:
        group = outliers[outliers.flag.eq(flag)]
        axes[0].scatter(group.z_turnout, group.z_share, s=9, alpha=.5, label=label, color=color)
    axes[0].set(xlabel='Turnout robust z', ylabel='Party-share robust z', title='Within-state county outliers', xscale='symlog', yscale='symlog')
    axes[0].legend(fontsize=8)
    flags = outliers.groupby('state')[['flag', 'isolation_flag']].sum()
    flags.plot.bar(ax=axes[1], color=[GOLD, BLUE])
    axes[1].set(title='Flag counts across both offices', xlabel='State', ylabel='County–office observations')
    axes[1].legend(['Median/MAD', 'Isolation Forest'], fontsize=8)
    save(fig, 'outliers_ml.png')
    vectors = []
    for item in records:
        group = county[(county.state_po == item['state']) & (county.office == item['office'])]
        columns = ['registered_voters', 'voted', 'DEMOCRAT', 'REPUBLICAN', 'OTHER']
        vectors.append({'state':item['state'], 'office':item['office'], 'n':len(group), 'repeats':int(group.duplicated(columns).sum())})
    duplicate_total = sum(x['repeats'] for x in vectors)
    assert sum(x['n'] for x in vectors) == len(outliers)
    pd.DataFrame(vectors).to_csv(ROOT / 'analysis/county_duplicate_vectors.csv', index=False)
    fig, ax = plt.subplots(figsize=(8, 3.5))
    sizes = pd.DataFrame(vectors).groupby('state')[['n','repeats']].sum()
    ax.bar(sizes.index, sizes.n, color=BLUE, label='County–office records checked')
    ax.set(ylabel='Records', xlabel='State', title=f'{duplicate_total} repeated complete county vectors in {len(outliers):,} records')
    ax.tick_params(axis='x', rotation=45)
    save(fig, 'duplicates.png')
    data = election(county[(county.state_po == 'PA') & (county.office == 'US SENATE')])
    leader = 'votes:REPUBLICAN'
    baseline = shpilkin_estimate(data, leader, controls=[data])
    injected, added = inject_additive_fraud(data, leader)
    response = shpilkin_estimate(injected, leader, controls=[data])
    assert int((injected.df[leader]-data.df[leader]).sum()) == added
    assert (injected.voted <= injected.registered).all()
    fig, ax = plt.subplots(figsize=(8, 3.7))
    ax.bar(['Original data', 'Synthetic injection'], [baseline.tail_votes_party, response.tail_votes_party], color=[BLUE, GOLD])
    ax.set(ylabel='Party votes beyond the fixed turnout boundary', title=f'Pennsylvania Senate · fixed cutoff {baseline.t_cut:.2f}%')
    for i, value in enumerate([baseline.tail_votes_party, response.tail_votes_party]):
        ax.annotate(f'{value:,}', (i, value), ha='center', va='bottom', xytext=(0,4), textcoords='offset points')
    ax.margins(y=.15)
    save(fig, 'selftest.png')
    summary = {'duplicate_vectors':duplicate_total, 'duplicate_records_checked':len(outliers), 'selftest_state':'PA',
               'selftest_office':'US SENATE', 'selftest_added_party_votes':added, 'selftest_cutoff':baseline.t_cut,
               'selftest_original_tail':baseline.tail_votes_party, 'selftest_injected_tail':response.tail_votes_party}
    (ROOT / 'analysis/site_diagnostics.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(summary)


def main() -> None:
    (SITE / 'img').mkdir(parents=True, exist_ok=True)
    (SITE / 'analysis').mkdir(exist_ok=True)
    (SITE / 'data').mkdir(exist_ok=True)
    tests = pd.read_csv(ROOT / 'analysis/digit_tests.csv')
    races = pd.read_csv(ROOT / 'analysis/clerk_race_screens.csv', dtype={'district': str})
    selected = races[races.plurality_eligible & races.spoiler_capacity].copy()
    metrics = json.loads((ROOT / 'analysis/metrics.json').read_text())
    assert len(tests) == metrics['digit_tests']
    assert int((tests.q_bh < .05).sum()) == metrics['digit_tests_q_below_005']
    assert len(selected) == json.loads((ROOT / 'analysis/clerk_summary.json').read_text())['spoiler_bounds']
    assert (selected.other_votes > selected.margin).all()
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'text.color': INK,
                         'axes.labelcolor': INK, 'axes.spines.top': False,
                         'axes.spines.right': False, 'font.size': 11})
    fig, ax = plt.subplots(figsize=(8, 3.6))
    sizes = tests.groupby('test').size().reindex(['benford2', 'last'])
    flags = tests[tests.q_bh < .05].groupby('test').size().reindex(sizes.index, fill_value=0)
    ax.barh(['Second-digit Benford', 'Last digits'], sizes, color='#e3e8ee', label='All tests')
    ax.barh(['Second-digit Benford', 'Last digits'], flags, color=GOLD, label='Flagged (BH q < 0.05)')
    for i, (flag, total) in enumerate(zip(flags, sizes)):
        ax.text(total+3, i, f'{flag} / {total}', va='center', color=INK)
    ax.set(xlabel='State × office × major-party tests', xlim=(0, sizes.max()+35))
    ax.invert_yaxis()
    ax.legend(loc='lower right', frameon=False, fontsize=9)
    save(fig, 'digits.png')
    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.barh(['House', 'Regular Senate'], [435, 33], color='#e3e8ee', label='Seats contested')
    usable = races[races.plurality_eligible].groupby('office').size()
    for i, (office, total) in enumerate([('US HOUSE', 435), ('US SENATE', 33)]):
        value = int(usable[office])
        ax.barh(i, value, color=BLUE)
        ax.text(value+5, i, f'{value} / {total}', va='center', color=INK)
    ax.set(xlim=(0, 500), xlabel='Contests included in the vote-splitting screen')
    ax.invert_yaxis()
    save(fig, 'coverage.png')
    labels = [f'{x.state_po} · '+('Senate' if x.office == 'US SENATE' else f'House {int(x.district)}')
              for x in selected.itertuples()]
    y = np.arange(len(selected))
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(y-.17, selected.margin, height=.32, color=BLUE, label='Top-two margin')
    ax.barh(y+.17, selected.other_votes, height=.32, color=GOLD, label='Other candidate / write-in votes')
    ax.set(yticks=y, yticklabels=labels, xlabel='Votes compiled from official sources by the House Clerk')
    ax.invert_yaxis()
    ax.ticklabel_format(axis='x', style='plain')
    ax.legend(frameon=False, fontsize=9)
    save(fig, 'spoilers.png')
    diagnostic_figures()
    for path in (ROOT / 'analysis').iterdir():
        if path.suffix in {'.csv', '.json', '.gz'} or path.name in {'PA_US_SENATE_turnout.png', 'WA_US_HOUSE_turnout.png'}:
            shutil.copy2(path, SITE / 'analysis' / path.name)
    for name in ['REPORT.md', 'PARADOXES.md', 'README.md', 'PRECINCT_REPORT.md', 'PRECINCT_DATA_SOURCES.md', 'PRECINCT_DOWNLOADS.md']:
        target = 'DATA.md' if name == 'README.md' else name
        text = (ROOT / name).read_text().replace('(README.md)', '(DATA.md)')
        (SITE / target).write_text(text)
    for name in ['manifest.csv', 'download_urls.txt', 'source_tree.json', 'supplemental_sources.json']:
        shutil.copy2(ROOT / 'data' / name, SITE / 'data' / name)
    (SITE / 'data/source_search').mkdir(exist_ok=True)
    for name in ['download_manifest.csv', 'precinct_download_manifest.csv', 'precinct_downloads.json', 'downloaded_table_schemas.json']:
        shutil.copy2(ROOT / 'data/source_search' / name, SITE / 'data/source_search' / name)
    print(f'Built site figures and copied the analysis snapshot to {SITE}')


if __name__ == '__main__':
    main()
