"""County turnout diagnostics: EAVS participation joined to congressional returns."""
from __future__ import annotations

import json
import sys
import zipfile
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'analysis-tool/src'))
from election_forensics.data import ElectionData
from election_forensics.correlations import turnout_result_correlations
from election_forensics.integer_peaks import integer_peaks
from election_forensics.fingerprints import fingerprint_mixture
from election_forensics.shpilkin import shpilkin_estimate
from sklearn.ensemble import IsolationForest


def main() -> None:
    out = ROOT / 'analysis'
    with zipfile.ZipFile(ROOT / 'data/raw/eavs2024.zip') as z:
        eavs = pd.read_csv(z.open(z.namelist()[0]), dtype={'FIPSCode': str},
                           usecols=['FIPSCode', 'Jurisdiction_Name', 'State_Abbr', 'A1a', 'A1b', 'F1a'])
    # Only county-wide EAVS jurisdictions; never truncate municipal FIPS into a county.
    county = eavs.FIPSCode.str.len().eq(10) & eavs.FIPSCode.str.endswith('00000')
    eavs = eavs[county].copy()
    eavs['county_fips'] = eavs.FIPSCode.str[:5]
    assert not eavs.county_fips.duplicated().any()
    eavs = eavs.rename(columns={'A1a': 'registered_voters', 'F1a': 'voted'})
    senate = pd.read_csv(ROOT / 'data/raw/2024-senate-county.csv', dtype={'county_fips': str}, keep_default_na=False)
    cross = senate[['state_po', 'county_name', 'county_fips']].drop_duplicates()
    assert not cross.duplicated(['state_po', 'county_name']).any()
    data = pd.read_csv(ROOT / 'data/congress_candidate_units.csv.gz', keep_default_na=False,
                       dtype={'district': str, 'special': str})
    data['votes'] = pd.to_numeric(data.votes, errors='coerce')
    for party in ['DEMOCRAT', 'REPUBLICAN']:
        other = 'REPUBLICAN' if party == 'DEMOCRAT' else 'DEMOCRAT'
        mask = data.party.str.split('|').map(lambda x: party in x and other not in x)
        data.loc[mask, 'party'] = party
    data = data[data.special.str.upper().eq('FALSE') & data.date.eq('2024-11-05')]
    data = data[~data.candidate.str.contains('UNDER|OVER|BLANK|TOTAL|NO CANDIDATE|^CAST VOTES$|^$', regex=True)]
    # Neither impute suppressed precincts nor use known overlapping/incomplete states.
    data = data[~data.state_po.isin(['IN', 'NJ', 'LA', 'AK', 'ME', 'OR', 'RI'])]
    data = data.merge(cross, on=['state_po', 'county_name'], how='inner', validate='many_to_one')
    keys = ['state_po', 'office', 'county_fips', 'county_name']
    unknown = data.votes.isna().groupby([data[k] for k in keys]).transform('any')
    data = data[~unknown].copy()
    data['bloc'] = data.party.where(data.party.isin(['DEMOCRAT', 'REPUBLICAN']), 'OTHER')
    counts = data.pivot_table(index=keys, columns='bloc', values='votes', aggfunc='sum', fill_value=0).reset_index()
    for party in ['DEMOCRAT', 'REPUBLICAN', 'OTHER']:
        if party not in counts: counts[party] = 0
    counts['valid_votes'] = counts[['DEMOCRAT', 'REPUBLICAN', 'OTHER']].sum(axis=1)
    joined = counts.merge(eavs[['county_fips', 'registered_voters', 'voted', 'A1b']], on='county_fips', validate='many_to_one')
    joined['eligible'] = ((joined.registered_voters > 0) & (joined.voted > 0) &
                          (joined.voted <= joined.registered_voters) &
                          (joined.valid_votes <= joined.voted) & (joined.valid_votes > 0))
    joined.to_csv(out / 'county_turnout_join_audit.csv', index=False)
    records, correlations, peaks, neighbors = [], [], [], []
    for (state, office), group in joined[joined.eligible].groupby(['state_po', 'office']):
        if len(group) < 20: continue
        frame = group.reset_index(drop=True).copy()
        frame['key'] = frame.county_fips
        frame['name'] = frame.county_name
        frame['path'] = state + ' > ' + frame.county_name
        frame['parent_key'] = state
        for party in ['DEMOCRAT', 'REPUBLICAN', 'OTHER']:
            frame['votes:' + party] = frame[party].astype(int)
        election = ElectionData(f'{state} {office}', frame, ['votes:DEMOCRAT', 'votes:REPUBLICAN', 'votes:OTHER'])
        leader = election.leader_party
        corr = turnout_result_correlations(election, election.party_cols)
        corr['state'], corr['office'] = state, office
        correlations.append(corr)
        for metric in ['turnout', f'share:{leader}']:
            peaks.append(dict(asdict(integer_peaks(election, metric)), state=state, office=office))
        # Tail is a descriptive upper-tail mass, not an estimate of fraudulent ballots.
        tail = shpilkin_estimate(election, leader)
        mixture = fingerprint_mixture(election, leader)
        records.append({'state': state, 'office': office, 'n_counties': len(group),
                        'leader': leader, 'turnout_tail': asdict(tail), 'mixture': asdict(mixture)})
        near = frame[['key', 'name']].copy()
        for col, values in [('turnout', election.turnout), ('share', election.share(leader))]:
            mad = (values - values.median()).abs().median()
            near['z_' + col] = (values - values.median()) / (1.4826 * mad) if mad else np.nan
        near['flag'] = near[['z_turnout', 'z_share']].abs().max(axis=1) > 4
        near['state'], near['office'] = state, office
        features = np.column_stack([election.turnout, election.share(leader), np.log1p(election.registered)])
        model = IsolationForest(contamination=.01, random_state=42, n_estimators=200).fit(features)
        near['isolation_score'] = -model.score_samples(features)[near.index]
        near['isolation_flag'] = (model.predict(features) == -1)[near.index]
        neighbors.append(near)
        fig, ax = plt.subplots(figsize=(6, 4))
        for party in ['DEMOCRAT', 'REPUBLICAN']:
            ax.scatter(election.turnout, election.share('votes:'+party), s=12, alpha=.55, label=party)
        ax.set(xlabel='Participation / total registered (%)', ylabel='Party votes / all participants (%)',
               title=f'{state}: {office}, {len(group)} matched counties')
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out / f'{state}_{office.replace(" ", "_")}_turnout.png', dpi=120)
        plt.close(fig)
    pd.concat(correlations).to_csv(out / 'county_correlations.csv', index=False)
    pd.DataFrame(peaks).to_csv(out / 'county_integer_peaks.csv', index=False)
    pd.concat(neighbors).to_csv(out / 'county_within_state_outliers.csv', index=False)
    (out / 'county_metrics.json').write_text(json.dumps(records, indent=2, default=float)+'\n')
    print(f'{len(joined)} county-office joins; {joined.eligible.sum()} eligible; {len(records)} state-office analyses')


if __name__ == '__main__':
    main()
