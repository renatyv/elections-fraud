"""Audit official precinct denominators and run descriptive congressional screens.

Run after prepare_precinct_tables.py, using analysis-tool/.venv/bin/python.
No statistical flag is interpreted as a fraudulent vote count.
"""
from __future__ import annotations

import json
import sys
import zipfile
from dataclasses import asdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from sklearn.ensemble import IsolationForest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'analysis-tool/src'))
from election_forensics.data import ElectionData
from election_forensics.correlations import weighted_pearson
from election_forensics.digit_tests import digit_test
from election_forensics.integer_peaks import integer_peaks
from election_forensics.fingerprints import fingerprint_mixture
from election_forensics.shpilkin import shpilkin_estimate

RAW = ROOT / 'data/raw'
OUT = ROOT / 'analysis'
VOTES = ['votes:DEM', 'votes:REP', 'votes:OTHER']


def bh(pvalues: pd.Series) -> np.ndarray:
    p = pvalues.to_numpy()
    order = np.argsort(p)
    result = np.empty(len(p))
    result[order] = np.minimum(1, np.minimum.accumulate((p[order] * len(p) / np.arange(1, len(p)+1))[::-1])[::-1])
    return result


def minnesota(year: int) -> pd.DataFrame:
    d = pd.read_csv(RAW / f'mn{year}_Precinct-Results.csv', dtype={'VTDID': str, 'CONGDIST': str})
    d = d[d.VTDID.str.fullmatch(r'\d{9}', na=False)].copy()
    frames = []
    for office, prefix in [('SENATE', 'USSEN'), ('HOUSE', 'USREP')]:
        g = pd.DataFrame({'key': d.VTDID, 'county': d.COUNTYNAME, 'name': d.PCTNAME,
                          'registered_voters': d.REG7AM + d.EDR, 'voted': d.TOTVOTING,
                          'votes:DEM': d[prefix+'DFL'], 'votes:REP': d[prefix+'R'],
                          'votes:OTHER': d[prefix+'TOTAL'] - d[prefix+'DFL'] - d[prefix+'R'],
                          'district': d.CONGDIST if office == 'HOUSE' else 'STATEWIDE',
                          'denominator_before_edr': d.REG7AM})
        g['sample'] = 'MN'+str(year)+' '+office
        frames.append(g)
    return pd.concat(frames, ignore_index=True)


def idaho() -> pd.DataFrame:
    stats = pd.read_csv(RAW / 'id2024_raw_stats_general.csv', dtype={'Precinct': str})
    stats = stats[~stats.Precinct.str.casefold().eq('total')].copy()
    assert not stats.duplicated(['County', 'Precinct']).any()
    assert (stats['Total Registered Voters'] == stats['Registration at Cutoff'] + stats['Election Day Registrations']).all()
    races = pd.read_csv(RAW / 'id2024_raw_races_general.csv', dtype={'Precinct': str})
    races = races[races.Race.str.startswith('United States Representative District')].copy()
    races = races[~races.Candidate.str.fullmatch('Overvotes|Undervotes', case=False)].copy()
    races['bloc'] = races.Party.map({'Democratic': 'votes:DEM', 'Republican': 'votes:REP'}).fillna('votes:OTHER')
    votes = races.pivot_table(index=['County', 'Precinct', 'Race'], columns='bloc', values='Votes', aggfunc='sum', fill_value=0).reset_index()
    d = stats.merge(votes, on=['County', 'Precinct'], how='outer', validate='one_to_one', indicator=True)
    d['key'] = d.County + '|' + d.Precinct
    d['county'], d['name'] = d.County, d.Precinct
    d['registered_voters'], d['voted'] = d['Total Registered Voters'], d['Ballots Cast']
    d['district'] = d.Race.str.extract(r'(\d+)$')[0]
    d['sample'] = 'ID2024 HOUSE'
    return d


def california() -> pd.DataFrame:
    with zipfile.ZipFile(RAW / 'precinct_sources/ca_swdb/state_g24_sov_data_by_g24_srprec.zip') as z:
        d = pd.read_csv(z.open(next(n for n in z.namelist() if n.endswith('.csv'))), dtype=str)
    assert d.GEO_TYPE.eq('srprec').all() and not d.SRPREC_KEY.duplicated().any()
    frames = []
    for office, prefix in [('SENATE', 'USS'), ('HOUSE', 'CNG')]:
        cols = [c for c in d if c.startswith(prefix)]
        n = d[cols+['TOTREG', 'TOTVOTE']].apply(pd.to_numeric, errors='coerce')
        # Preserve masked cells as unknown; never let sum skip them.
        g = pd.DataFrame({'key': d.SRPREC_KEY, 'county': d.FIPS, 'name': d.SRPREC,
                          'registered_voters': n.TOTREG, 'voted': n.TOTVOTE,
                          'district': d.CDDIST if office == 'HOUSE' else 'STATEWIDE'})
        for party in ['DEM', 'REP']:
            g['votes:'+party] = n[[c for c in cols if party in c]].sum(axis=1, skipna=False)
        g['votes:OTHER'] = n[[c for c in cols if 'DEM' not in c and 'REP' not in c]].sum(axis=1, skipna=False)
        g['source_exclusion'] = d.FIPS.eq('06039')
        g['sample'] = 'CA2024 '+office
        frames.append(g)
    return pd.concat(frames, ignore_index=True)


def king() -> pd.DataFrame:
    d = pd.read_csv(RAW / 'wa_king2024_official_final.csv')
    d = d[d.Race.eq('United States Senator United States Senator')]
    assert d.CounterGroup.eq('Total').all() and not d.duplicated(['Precinct', 'CounterType']).any()
    d = d.pivot(index='Precinct', columns='CounterType', values='SumOfCount').reset_index()
    d = d.rename(columns={'Precinct': 'key', 'Registered Voters': 'registered_voters',
                          'Times Counted': 'voted', 'Maria Cantwell': 'votes:DEM',
                          'Dr Raul Garcia': 'votes:REP', 'Write-in': 'votes:OTHER'})
    d['county'], d['name'], d['sample'], d['district'] = 'King', d.key, 'WA-King2024 SENATE', 'STATEWIDE'
    d['ballot_balance_error'] = d.voted - d[VOTES+['Times Under Voted', 'Times Over Voted']].sum(axis=1, skipna=False)
    assert d.ballot_balance_error.eq(0).all()
    return d


def maryland() -> pd.DataFrame:
    d = pd.read_csv(RAW / 'md2024_official_precinct_turnout.csv', dtype={'PRECINCT': str})
    keys = ['LBE', 'PRECINCT']
    # Party and district splits are disjoint rows, including split residential precincts.
    d['voted'] = d[['POLLS', 'EARLY_VOTING', 'VBM', 'PROVISIONAL']].sum(axis=1, skipna=False)
    d = d.groupby(keys, as_index=False)[['ELIGIBLE_VOTERS', 'voted']].sum(min_count=1)
    d['county'] = d.LBE.str.upper()
    d['key'] = d.county + '|' + d.PRECINCT
    results = pd.read_csv(ROOT / 'data/congress_candidate_units.csv.gz', keep_default_na=False, dtype=str)
    results = results[(results.state_po == 'MD') & (results.office == 'US SENATE') & results.special.str.upper().eq('FALSE')].copy()
    results = results[~results.candidate.str.contains('UNDER|OVER|BLANK|TOTAL|NO CANDIDATE|^CAST VOTES$|^$', regex=True)]
    results['votes'] = pd.to_numeric(results.votes, errors='coerce')
    results['key'] = results.county_name + '|' + results.precinct
    results['bloc'] = results.party.map({'DEMOCRAT': 'votes:DEM', 'REPUBLICAN': 'votes:REP'}).fillna('votes:OTHER')
    tallies = results.groupby(['key', 'bloc']).votes.agg(lambda x: x.sum() if x.notna().all() else np.nan).unstack('bloc')
    d = d.merge(tallies, on='key', how='outer', validate='one_to_one', indicator=True)
    d['registered_voters'], d['name'] = d.ELIGIBLE_VOTERS, d.PRECINCT
    d['sample'], d['district'] = 'MD2024 SENATE', 'STATEWIDE'
    # Voter-history turnout includes rejected ballots and later registry updates.
    d['source_exclusion'] = True
    return d


def union() -> pd.DataFrame:
    d = pd.read_csv(OUT/'ms_union_precincts.csv')
    assert d.registered.sum() == 17084 and d.ballots.sum() == 12533
    frames = []
    for office, prefix in [('SENATE','senate'),('HOUSE','house')]:
        g = pd.DataFrame({'key':d.name, 'county':'Union', 'name':d.name,
                          'registered_voters':d.registered, 'voted':d.ballots,
                          'votes:DEM':d[prefix+'_dem'], 'votes:REP':d[prefix+'_rep'],
                          'votes:OTHER':d[prefix+'_writein'],
                          'sample':'MS-Union2024 '+office, 'district':'001' if office=='HOUSE' else 'STATEWIDE'})
        frames.append(g)
    return pd.concat(frames,ignore_index=True)


def validate(frame: pd.DataFrame) -> pd.DataFrame:
    d = frame.copy()
    assert not d.duplicated(['sample', 'district', 'key']).any()
    numbers = ['registered_voters', 'voted'] + VOTES
    n = d[numbers]
    d['unknown'] = n.isna().any(axis=1)
    d['noninteger_or_negative'] = ((n < 0) | (n % 1 != 0)).any(axis=1)
    d['zero_denominator'] = (d.registered_voters <= 0) | (d.voted <= 0)
    d['over_registration'] = d.voted > d.registered_voters
    d['contest_over_ballots'] = d[VOTES].sum(axis=1, skipna=False) > d.voted
    if 'source_exclusion' not in d: d['source_exclusion'] = False
    d['source_exclusion'] = d.source_exclusion.fillna(False).astype(bool)
    d['eligible'] = ~d[['unknown', 'noninteger_or_negative', 'zero_denominator', 'over_registration', 'contest_over_ballots', 'source_exclusion']].any(axis=1)
    return d


def selfcheck() -> None:
    assert np.allclose(bh(pd.Series([.01, .04, .03])), [.03, .04, .04])
    f = pd.DataFrame({'sample':['T']*4, 'district':['X']*4, 'key':list('abcd'),
                      'registered_voters':[100]*4, 'voted':[80, 101, 80, 80],
                      'votes:DEM':[40, 40, np.nan, 90], 'votes:REP':[20]*4, 'votes:OTHER':[0]*4})
    assert validate(f).eligible.tolist() == [True, False, False, False]


def main() -> None:
    selfcheck()
    audit = validate(pd.concat([minnesota(2024), minnesota(2020), idaho(), california(), king(), maryland(), union()], ignore_index=True))
    audit.to_csv(OUT / 'precinct_join_audit.csv.gz', index=False)
    coverage = audit.groupby('sample').agg(rows=('key','size'), eligible=('eligible','sum'),
        unknown=('unknown','sum'), zero_denominator=('zero_denominator','sum'),
        over_registration=('over_registration','sum'), contest_over_ballots=('contest_over_ballots','sum'),
        source_exclusion=('source_exclusion','sum')).reset_index()
    coverage.to_csv(OUT / 'precinct_coverage.csv', index=False)
    analyze(audit, OUT)
    plot_fingerprints(audit)
    print(coverage.to_string(index=False))


def analyze(audit: pd.DataFrame, output: Path) -> None:
    """Run one jointly adjusted diagnostic family on validated reporting units."""
    digit_rows, peak_rows, metrics, outliers, duplicate_rows = [], [], [], [], []
    for (sample, district), frame in audit[audit.eligible].groupby(['sample', 'district']):
        if len(frame) < 100 or frame['votes:DEM'].sum() == 0 or frame['votes:REP'].sum() == 0: continue
        frame = frame.reset_index(drop=True)
        election = ElectionData(sample+' '+str(district), frame, VOTES)
        leader = election.leader_party
        r = weighted_pearson(election.turnout.to_numpy(), election.share('votes:REP').to_numpy(), election.voted.to_numpy())
        residuals = pd.DataFrame({'t': election.turnout, 's': election.share('votes:REP'), 'county':frame.county})
        residuals[['t','s']] -= residuals.groupby('county')[['t','s']].transform('mean')
        within = pearsonr(residuals.t, residuals.s).statistic if residuals.t.std() > 0 and residuals.s.std() > 0 else np.nan
        mix = fingerprint_mixture(election, leader)
        tail = shpilkin_estimate(election, leader)
        metrics.append({'sample':sample, 'district':district, 'n':len(frame), 'registered':int(election.registered.sum()),
                        'ballots':int(election.voted.sum()), 'turnout':100*election.voted.sum()/election.registered.sum(),
                        'leader':leader, 'weighted_r_rep':r, 'county_demeaned_r_rep':within,
                        'tail':asdict(tail), 'mixture':asdict(mix)})
        for metric in ['turnout', 'share:votes:DEM', 'share:votes:REP']:
            peak_rows.append(dict(asdict(integer_peaks(election, metric, n_sim=1000)), sample=sample, district=district))
        for party in VOTES[:2]:
            for test, minimum in [('last',100),('benford2',10)]:
                if (frame[party] >= minimum).sum() >= 100:
                    digit_rows.append(dict(asdict(digit_test(election, party, test, n_sim=400)),sample=sample,district=district))
        vector = ['registered_voters','voted']+VOTES
        repeated = frame[frame.duplicated(vector, keep=False)].copy()
        if len(repeated): duplicate_rows.append(repeated[['sample','district','key']+vector])
        features = np.column_stack([election.turnout, election.share(leader), np.log1p(election.registered)])
        model = IsolationForest(contamination=.01, random_state=42, n_estimators=200).fit(features)
        near = frame[['sample','district','key','county','name']].copy()
        near['turnout'], near['leader_share'] = election.turnout, election.share(leader)
        near['isolation_score'], near['isolation_flag'] = -model.score_samples(features), model.predict(features) == -1
        for col in ['turnout','leader_share']:
            med = near.groupby('county')[col].transform('median')
            dev = (near[col]-med).abs()
            mad = dev.groupby(near.county).transform('median')
            near['z_'+col] = (near[col]-med)/(1.4826*mad.replace(0,np.nan))
        near['mad_flag'] = near[['z_turnout','z_leader_share']].abs().max(axis=1) > 4
        outliers.append(near)
        print(sample,district,len(frame),flush=True)
    digits = pd.DataFrame(digit_rows)
    digits['q_bh'] = bh(digits.p_value)
    digits['q_mc_bh'] = bh(digits.p_null_mc)
    digits.to_csv(output/'precinct_digits.csv',index=False)
    pd.DataFrame(peak_rows).to_csv(output/'precinct_integer_peaks.csv',index=False)
    pd.concat(outliers).to_csv(output/'precinct_outliers.csv.gz',index=False)
    (pd.concat(duplicate_rows) if duplicate_rows else pd.DataFrame(columns=['sample','district','key']+vector)).to_csv(output/'precinct_duplicate_vectors.csv',index=False)
    (output/'precinct_metrics.json').write_text(json.dumps(metrics,indent=2,default=float)+'\n')



def plot_fingerprints(audit: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(12,7))
    for ax, sample in zip(axes.flat, ['MN2024 SENATE','MN2020 SENATE','CA2024 SENATE','MS-Union2024 SENATE','WA-King2024 SENATE','ID2024 HOUSE']):
        f=audit[(audit['sample']==sample)&audit.eligible]
        if f.empty:
            ax.text(.5,.5,'Excluded: voter-history turnout\nis not accepted ballots',ha='center',va='center',transform=ax.transAxes)
            ax.set_title(sample)
            continue
        if len(f) < 100:
            ax.scatter(100*f.voted/f.registered_voters,100*f['votes:REP']/f.voted,s=25,color='#26639b')
        else:
            ax.hexbin(100*f.voted/f.registered_voters,100*f['votes:REP']/f.voted,gridsize=45,mincnt=1,cmap='Blues',bins='log')
        ax.set(title=f'{sample}: {len(f):,} units',xlabel='Ballots / registered (%)',ylabel='Republican votes / ballots (%)',xlim=(0,100),ylim=(0,100))
    fig.tight_layout();fig.savefig(ROOT.parent/'site/usa-2024/img/precinct_fingerprints.png',dpi=160);plt.close(fig)


if __name__ == '__main__':
    main()
