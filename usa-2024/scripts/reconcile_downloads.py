"""Normalize supplemental precinct tables and preserve every failed reconciliation.

Run extract_downloads.py first with the bundled Python runtime.
Outputs supplement, rather than overwrite, the published forensic sample.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/precinct_sources'
EXT = ROOT / 'data/extracted/precinct_sources'
OUT = ROOT / 'analysis'
VOTES = ['votes:DEM', 'votes:REP', 'votes:OTHER']


@dataclass
class Check:
    source: str
    measure: str
    extracted: float | None
    reference: float | None
    difference: float | None
    note: str


CHECKS: list[Check] = []


def compare(source: str, measure: str, actual: float, reference: float, note: str = '') -> None:
    CHECKS.append(Check(source, measure, float(actual), float(reference), float(actual-reference), note))


def read(relative: str, **kwargs: object) -> pd.DataFrame:
    return pd.read_csv(EXT / relative, **kwargs)


def standard(d: pd.DataFrame, sample: str, office: str, key: str, reg: str | None,
             ballots: str, dem: list[str], rep: list[str], other: list[str]) -> pd.DataFrame:
    g = pd.DataFrame({'key': d[key].astype(str), 'registered_voters': d[reg] if reg else np.nan,
                      'voted': d[ballots], 'sample': sample, 'office': office})
    for bloc, cols in zip(VOTES, [dem, rep, other]):
        g[bloc] = d[cols].apply(pd.to_numeric, errors='coerce').sum(axis=1, skipna=False)
    return g


def washington(year: int) -> pd.DataFrame:
    directory = f'expansion_20261018/wa{year}_precinct_results.zip/'
    if year == 2024:
        d = read(directory+'2024Gen_Precinct_Results_GIS-Ready_Federal.csv', dtype={'St_Code': str})
        t = read(directory+'2024Gen_Precinct_Turnout_GIS-Ready.csv', dtype={'St_Code': str})
        key, reg, ballot = 'St_Code', 'G24TREGVOT', 'G24TBALCST'
        assert not t[key].duplicated().any() and not d[key].duplicated().any()
        d = d.merge(t, on=key, how='outer', validate='one_to_one', indicator=True)
        clerk=pd.read_csv(OUT/'clerk_candidate_totals.csv',dtype={'district':str})
        clerk=clerk[clerk.state_po.eq('WA') & ~clerk.special]
        specs=[];candidate_checks=[]
        for office,prefix in [('SENATE','G24SEN'),('HOUSE',r'G24C\d\d')]:
            blocs={'DEM':[],'REP':[],'OTHER':[]}
            for field in [c for c in d if re.match(prefix,c)]:
                district=field[4:6].zfill(3) if office=='HOUSE' else 'STATEWIDE'
                suffix=field[6:]
                # Publisher's GOWI column carries Schrier's totals; retain the anomalous code in the audit.
                suffix={'GOWI':'SCHR'}.get(suffix,suffix)
                candidates=clerk[clerk.office.eq('US '+office) & clerk.district.eq(district)]
                match=candidates[candidates.candidate.map(lambda name:
                    name.casefold()=='write-in' if suffix=='W-I' else
                    any(word.startswith(suffix) for word in re.findall(r'[A-Z]+',name.upper())))]
                assert len(match)==1,(field,match.candidate.tolist())
                row=match.iloc[0]
                bloc='DEM' if 'Democrat' in row.labels else 'REP' if 'Republican' in row.labels else 'OTHER'
                blocs[bloc].append(field)
                observed=d[field].sum()
                candidate_checks.append({'field':field,'office':office,'district':district,'candidate':row.candidate,
                    'bloc':bloc,'extracted':observed,'clerk':row.votes,'difference':observed-row.votes})
            specs.append((office,blocs['DEM'],blocs['REP'],blocs['OTHER']))
        pd.DataFrame(candidate_checks).to_csv(OUT/'wa2024_candidate_reconciliation.csv',index=False)
        codes = read('expansion_20261018/wa2024_precinct_associations.xlsx/Sheet1.csv.gz', dtype=str)
        counties = codes[['CountyCode','County']].drop_duplicates()
        assert not counties.CountyCode.duplicated().any()
        d['CountyCode'] = d[key].str[:2]
        d = d.merge(counties, on='CountyCode', how='left', validate='many_to_one')
        assert d.County.notna().all()
        rec = read('expansion_20261018/wa2024_reconciliation.xlsx/Sheet1.csv.gz')
        county = d.groupby('County')[[reg,ballot]].sum().reset_index().merge(rec, left_on='County',right_on='County',how='outer',validate='one_to_one')
        county['registration_difference'] = county[reg]-county['Active Voters']
        county['ballots_difference'] = county[ballot]-county['Ballots Counted']
        county.to_csv(OUT/'wa2024_county_reconciliation.csv',index=False)
        for col, ref in [(reg, 'Active Voters'),(ballot, 'Ballots Counted')]:
            compare('WA2024',col,d[col].sum(),rec[ref].sum(),'County reconciliation workbook; registration is active voters.')
        compare('WA2024','registration versus published statewide turnout table',d[reg].sum(),5017620,
                'Previously recorded official summary in TURNOUT_EXPANSION.md; not a newly fetched certification.')
        old = pd.read_csv(ROOT/'data/raw/wa_king2024_official_final.csv')
        old = old[old.Race.eq('United States Senator United States Senator')]
        old = old.groupby('CounterType').SumOfCount.sum()
        king = d[d.County.eq('King')]
        for col, counter in [(reg,'Registered Voters'),(ballot,'Times Counted'),('G24SENCANT','Maria Cantwell'),('G24SENGARC','Dr Raul Garcia'),('G24SENW-I','Write-in')]:
            compare('WA2024 King overlap', col, king[col].sum(),old[counter],'Overlap; never append King County twice.')
    else:
        d = read(directory+'2020Gen_Precinct_Results_GIS-Ready/FINAL.csv.gz',dtype={'PrecinctCode':str})
        t = read(directory+'2020Gen_Precinct_Turnout_GIS-Ready/FINAL.csv.gz',dtype={'PrecCode':str})
        key = d.columns[0]
        reg, ballot = 'G20TREGVOT', 'G20TBALCST'
        assert not d[key].duplicated().any() and not t.PrecCode.duplicated().any()
        d = d.rename(columns={reg:'results_registered',ballot:'results_ballots'})
        d = d.merge(t, left_on=key,right_on='PrecCode',how='outer',validate='one_to_one',indicator=True)
        d[key] = d[key].fillna(d.PrecCode)
        both = d._merge.eq('both')
        compare('WA2020','turnout-versus-results registration',d.loc[both,reg].sum(),d.loc[both,'results_registered'].sum())
        compare('WA2020','turnout-versus-results ballots',d.loc[both,ballot].sum(),d.loc[both,'results_ballots'].sum())
        specs = [('PRESIDENT',['G20PRSBIDE'],['G20PRSTRUM'],[c for c in d if c.startswith('G20PRS') and c not in {'G20PRSBIDE','G20PRSTRUM'}]),
                 ('HOUSE',[],[],[])]
        # Party coding for historical House columns is supplied by the publisher's codebook.
        code = read(directory+'2020Gen_Precinct_Results_GIS-Ready/Candidate_Codes.csv.gz')
        code.to_csv(OUT/'wa2020_candidate_codebook.csv',index=False)
        specs = specs[:1]
    frames = []
    for office, dem, rep, other in specs:
        g = standard(d, f'WA{year} {office}',office,key,reg,ballot,dem,rep,other)
        g['county'], g['join_status'] = d.County,d._merge.astype(str)
        frames.append(g)
    return pd.concat(frames,ignore_index=True)


def minnesota() -> pd.DataFrame:
    d = read('expansion_20261018/mn2016_official_precinct.xlsx/Results.csv.gz',dtype={'VTDID':str})
    d = d[d.VTDID.str.fullmatch(r'\d{9}',na=False)].copy()
    d['registered'] = d.REG7AM+d.EDR
    frames = []
    for office,prefix in [('HOUSE','USREP'),('PRESIDENT','USPRS')]:
        g = standard(d,'MN2016 '+office,office,'VTDID','registered','TOTVOTING',[prefix+'DFL'],[prefix+'R'],[])
        g['votes:OTHER'] = d[prefix+'TOTAL']-d[prefix+'DFL']-d[prefix+'R']
        g['county'] = d.COUNTYNAME
        g['join_status'] = 'same_source'
        frames.append(g)
    return pd.concat(frames,ignore_index=True)


def california() -> pd.DataFrame:
    d = read('expansion_20261018/ca2020_srprec_sov.zip/state_g20_sov_data_by_g20_srprec.csv',dtype={'SRPREC_KEY':str,'FIPS':str})
    frames = []
    for office,prefix in [('HOUSE','CNG'),('PRESIDENT','PRS')]:
        cols = [c for c in d if c.startswith(prefix)]
        g = standard(d,'CA2020 '+office,office,'SRPREC_KEY','TOTREG','TOTVOTE',
                     [c for c in cols if 'DEM' in c],[c for c in cols if 'REP' in c],
                     [c for c in cols if 'DEM' not in c and 'REP' not in c])
        g['county'],g['join_status'] = d.FIPS,'same_source'
        frames.append(g)
    sr = read('ca_swdb/state_g24_sov_data_by_g24_srprec.zip/state_g24_sov_data_by_g24_srprec.csv',dtype=str)
    sv = read('ca_swdb/state_g24_sov_data_by_g24_svprec.zip/state_g24_sov_data_by_g24_svprec.csv',dtype=str)
    aggregates = sv.SVPREC.str.contains(r'TOT$|^SOV',na=False)
    sv[aggregates].to_csv(OUT/'ca2024_sv_aggregate_rows.csv.gz',index=False)
    sv = sv[~aggregates].copy()
    cols = ['TOTREG','TOTVOTE']+[c for c in sr if c.startswith(('CNG','USS','USP','PRS'))]
    a = sr[cols].apply(pd.to_numeric,errors='coerce').groupby(sr.FIPS).sum(min_count=1)
    b = sv[cols].apply(pd.to_numeric,errors='coerce').groupby(sv.FIPS).sum(min_count=1)
    audit = a.join(b,lsuffix='_sr',rsuffix='_sv',how='outer')
    for c in cols:
        audit[c+'_difference'] = audit[c+'_sr']-audit[c+'_sv']
        missing_sr = pd.to_numeric(sr[c],errors='coerce').isna().sum()
        missing_sv = pd.to_numeric(sv[c],errors='coerce').isna().sum()
        compare('CA2024 SR versus SV',c,a[c].sum(),b[c].sum(),
                f'Observed numeric sums, not complete totals when masked; {missing_sr} unknown SR cells, {missing_sv} unknown SV cells. Aggregate rows excluded.')
    audit.to_csv(OUT/'ca2024_sr_sv_reconciliation.csv')
    for name in ['registration','voters']:
        aux = read(f'ca_swdb/state_g24_{name}_by_g24_srprec.zip/state_g24_{name}_by_g24_srprec.csv',dtype=str)
        assert not sr.SRPREC_KEY.duplicated().any() and not aux.SRPREC_KEY.duplicated().any()
        joined = sr[['SRPREC_KEY','FIPS','TOTREG','TOTVOTE']].merge(aux[['SRPREC_KEY','TOTREG_R']],on='SRPREC_KEY',how='outer',indicator=True,validate='one_to_one')
        joined['difference'] = pd.to_numeric(joined.TOTREG_R,errors='coerce')-pd.to_numeric(joined.TOTREG if name=='registration' else joined.TOTVOTE,errors='coerce')
        joined.to_csv(OUT/f'ca2024_{name}_join_audit.csv.gz',index=False)
    return pd.concat(frames,ignore_index=True)


def wyoming() -> pd.DataFrame:
    directory = EXT/'wy_results/2024_Wyoming_General_Results.zip'
    if not directory.exists():
        directory = next(EXT.rglob('2024_Wyoming_General_Results.zip'))
    frames=[]
    for path in sorted((directory/'2024_County_General_PbP_-_OFFICIAL').glob('*.csv.gz')):
        county = path.name.removesuffix('.csv.gz').replace('_',' ')
        d = pd.read_csv(path,header=None,dtype=str).dropna(how='all')
        header = d.index[d[0].eq('Precinct')][0]
        labels = d.loc[header].fillna('').str.replace(r'\s+',' ',regex=True)
        races = d.loc[header-1].ffill()
        body = d.loc[header+1:].copy()
        # Printed total/absentee aggregates remain separate from polling precinct rows.
        body['key'] = body[0]
        body = body[body.key.notna() & ~body.key.str.contains('total',case=False,na=False)].copy()
        body = body[body[list(labels.index[1:])].apply(pd.to_numeric,errors='coerce').notna().any(axis=1)].copy()
        body['original_key'] = body.key
        # Excel stored some precinct codes as 2022 dates; require the reconstructed key to match TBC.
        body['key'] = body.key.str.replace(r'^\d{4}-(\d\d)-(\d\d) 00:00:00$',r'\1-\2',regex=True)
        t = pd.read_csv(directory/'2024_County_General_PbP_TBC_-_OFFICIAL'/path.name,header=None,dtype=str)
        t = t[pd.to_numeric(t[1],errors='coerce').notna() & ~t[0].str.contains('total',case=False,na=False)].copy()
        assert not t[0].duplicated().any()
        body = body.merge(t[[0,1]].rename(columns={0:'key',1:'ballots'}),on='key',how='outer',indicator=True,validate='one_to_one')
        body['ballots'] = pd.to_numeric(body.ballots.str.replace(',',''),errors='coerce')
        for office,title in [('SENATE','United States Senator'),('HOUSE','United States Representative')]:
            cols = [i for i in labels.index if races[i]==title and labels[i] not in {'Overvotes','Undervotes'}]
            dem = [i for i in cols if '(D)' in labels[i]]
            rep = [i for i in cols if '(R)' in labels[i]]
            assert len(dem)==len(rep)==1
            g = standard(body,f'WY2024 {office}',office,'key',None,'ballots',dem,rep,[i for i in cols if i not in dem+rep])
            g['county'] = county
            g['original_key'] = body.original_key
            g['key'] = county+'|'+g.key
            g['join_status'] = body._merge.astype(str)
            balance_cols = [i for i in labels.index if races[i]==title]
            g['ballot_balance_error'] = body[balance_cols].apply(pd.to_numeric,errors='coerce').sum(axis=1,skipna=False)-body.ballots
            frames.append(g)
    return pd.concat(frames,ignore_index=True)


def supplemental() -> None:
    pa = RAW/'pa_bulk'
    reg = pd.read_csv(next(pa.glob('vrstat*.txt')),header=None,dtype=str,keep_default_na=False)
    assert set(reg[5]) == {'DEM'} and set(reg[8]) == {'REP'}
    reg['registered_voters'] = reg[[6,9,12,15,18,21]].apply(pd.to_numeric,errors='raise').sum(axis=1)
    reg['key'] = reg[2]+'|'+reg[3]
    assert not reg.key.duplicated().any()
    results = pd.read_csv(next(pa.glob('erstat*.txt')),header=None,dtype=str,keep_default_na=False)
    results['key'] = results[2]+'|'+results[3]
    results['votes'] = pd.to_numeric(results[15],errors='raise')
    results['office'] = results[8].map({'USS':'SENATE','USC':'HOUSE'})
    results = results[results.office.notna()].copy()
    results['bloc'] = results[9].map({'DEM':'votes:DEM','REP':'votes:REP'}).fillna('votes:OTHER')
    votes = results.groupby(['key','office','bloc']).votes.sum().unstack('bloc').reset_index()
    joined = votes.merge(reg[['key','registered_voters']],on='key',how='outer',validate='many_to_one',indicator=True)
    joined['voted'] = np.nan
    joined['note'] = 'No precinct ballots downloaded; field positions inferred from headerless file and checked against Clerk totals.'
    joined.to_csv(OUT/'pa2024_registration_results_join.csv.gz',index=False)
    for office,g in results.groupby('office'):
        clerk_check('PA2024 '+office,'PA',office,g.votes.sum())
    county = read('pa_bulk/voter%20registration%20-%20vote%20history%20summary%20-%202024%20general.xlsx/By_county.csv.gz')
    county = county[~county.County.str.contains('TOTAL',case=False,na=False)]
    compare('PA2024 registration','precinct-versus-county registration',reg.registered_voters.sum(),county['Registered voters'].sum(),'Vote history is not precinct ballots.')
    nc = read('nc_registration/voter_stats_20241105.zip/voter_stats_20241105.txt',sep='\t',dtype=str)
    assert nc.stats_type.eq('voter').all()
    nc['registered_voters'] = pd.to_numeric(nc.total_voters,errors='raise')
    n = nc.groupby(['county_desc','precinct_abbrv'],dropna=False).registered_voters.sum().reset_index()
    n.to_csv(OUT/'nc2024_precinct_registration.csv.gz',index=False)
    de = pd.read_csv(RAW/'de_results/GE2024.csv')
    compare('DE2024','mode sum versus total',de[['machinevotessum','absenteevotessum','earlyvotessum']].sum().sum(),de.totalvotessum.sum(),'State/district summary; no precinct identifier.')
    for office,pattern in [('SENATE',r'^U\.S\. Senator$'),('HOUSE','Representative in Congress')]:
        g=de[de.office.str.contains(pattern,case=False)]
        if len(g):clerk_check('DE2024 '+office,'DE',office,g.totalvotessum.sum())


def north_dakota() -> pd.DataFrame:
    html=(RAW/'nd2024_precinct_turnout.html').read_text()
    rows=re.findall(r'<div class="county-precinct (?:odd|even)">(\d+)</div>\s*<div[^>]*></div>\s*<div class="county-cast (?:odd|even)">([\d,]+)</div>',html)
    t=pd.DataFrame(rows,columns=['key','voted'])
    t['voted']=t.voted.str.replace(',','').astype(int)
    t['key']=t.key.str.zfill(6)
    state=int(re.search(r'Voter Turnout<span>([\d,]+)</span>',html)[1].replace(',',''))
    assert len(t)==385 and not t.key.duplicated().any()
    compare('ND2024','precinct ballots versus statewide HTML',t.voted.sum(),state)
    t.to_csv(OUT/'nd2024_precinct_ballots.csv',index=False)
    r=pd.read_csv(ROOT/'data/congress_candidate_units.csv.gz',dtype=str,keep_default_na=False)
    r=r[r.state_po.eq('ND') & r.special.eq('FALSE') & r.date.eq('2024-11-05')].copy()
    r=r[~r.candidate.str.contains('UNDER|OVER|BLANK|TOTAL|NO CANDIDATE|^CAST VOTES$|^$',regex=True)]
    r['key']=r.precinct.str.zfill(6)
    r['votes']=pd.to_numeric(r.votes,errors='coerce')
    r['bloc']=r.party.map({'DEMOCRAT':'votes:DEM','REPUBLICAN':'votes:REP'}).fillna('votes:OTHER')
    v=r.groupby(['key','office','bloc']).votes.agg(lambda x:x.sum(skipna=False)).unstack('bloc').reset_index()
    frames=[]
    for office,g in v.groupby('office'):
        g=g.merge(t,on='key',how='outer',validate='one_to_one',indicator=True)
        g['registered_voters']=np.nan
        g['sample']='ND2024 '+office.removeprefix('US ')
        g['office']=office.removeprefix('US ')
        g['join_status']=g._merge.astype(str)
        g['denominator_note']='No voter registration; statewide Census eligible population is not a precinct denominator.'
        frames.append(g)
    return pd.concat(frames,ignore_index=True)


def maryland_official() -> pd.DataFrame:
    r=pd.read_csv(ROOT/'data/raw/md2024_official_results.csv',dtype=str)
    r=r[r['Office Name'].isin(['U.S. Senator','U.S. Congress'])].copy()
    columns=['Early Votes','Election Night Votes','Mail-In Ballot 1 Votes','Provisional Votes','Mail-In Ballot 2 Votes']
    r['votes']=r[columns].apply(pd.to_numeric,errors='coerce').sum(axis=1,skipna=False)
    r['county']=r['County Name'].str.replace(r' County$','',regex=True).str.upper()
    r['key']=r.county+'|'+r['Election District - Precinct']
    r['office']=r['Office Name'].map({'U.S. Senator':'SENATE','U.S. Congress':'HOUSE'})
    r['bloc']=r.Party.map({'DEM':'votes:DEM','REP':'votes:REP'}).fillna('votes:OTHER')
    v=r.groupby(['key','office','bloc']).votes.agg(lambda s:s.sum(skipna=False)).unstack('bloc').reset_index()
    t=pd.read_csv(ROOT/'data/raw/md2024_official_precinct_turnout.csv',dtype={'PRECINCT':str})
    t['key']=t.LBE.str.upper()+'|'+t.PRECINCT
    t['voted']=t[['POLLS','EARLY_VOTING','VBM','PROVISIONAL']].sum(axis=1,skipna=False)
    t=t.groupby('key')[['ELIGIBLE_VOTERS','voted']].sum(min_count=1).reset_index()
    t=t.rename(columns={'ELIGIBLE_VOTERS':'registered_voters'})
    frames=[]
    for office,g in v.groupby('office'):
        g=g.merge(t,on='key',how='outer',validate='one_to_one',indicator=True)
        g['sample']='MD-official2024 '+office
        g['office']=office
        g['join_status']=g._merge.astype(str)
        g['source_comparability_exclusion']=True
        g['denominator_note']='Administrative voter-history participation includes rejected ballots/later registry changes; not accepted-ballot turnout.'
        frames.append(g)
    return pd.concat(frames,ignore_index=True)


def clerk_check(source: str,state: str,office: str,total: float) -> None:
    clerk = pd.read_csv(OUT/'clerk_candidate_totals.csv')
    c = clerk[(clerk.state_po==state)&(clerk.office=='US '+office)&~clerk.special]
    compare(source,'candidate votes versus House Clerk',total,c.votes.sum(),'All candidate/write-in totals; excludes undervotes and overvotes. Statewide sum, not proof of precinct geography.')


def existing_samples() -> None:
    d=pd.read_csv(OUT/'precinct_join_audit.csv.gz',low_memory=False)
    for sample,g in d[d['sample'].str.match(r'^(?:MN|ID|CA|MD)2024 ')].groupby('sample'):
        office=sample.split()[-1]
        totals=g[VOTES].sum(axis=1,skipna=False)
        clerk_check(sample,sample[:2],office,totals.sum(min_count=1))
        CHECKS[-1].note += f' {totals.isna().sum()} units have unknown candidate totals; extracted sum is a lower bound if nonzero.'


def validate(d: pd.DataFrame) -> pd.DataFrame:
    assert not d.duplicated(['sample','key']).any()
    n = d[['registered_voters','voted']+VOTES]
    d['unknown'] = n.isna().any(axis=1)
    d['noninteger_or_negative'] = ((n<0)|(n%1!=0)).any(axis=1)
    d['zero_denominator'] = (d.registered_voters<=0)|(d.voted<=0)
    d['over_registration'] = d.voted>d.registered_voters
    d['contest_over_ballots'] = d[VOTES].sum(axis=1,skipna=False)>d.voted
    d['eligible_arithmetic_only'] = ~d[['unknown','noninteger_or_negative','zero_denominator','over_registration','contest_over_ballots']].any(axis=1)
    return d


def selfcheck() -> None:
    d=pd.DataFrame({'sample':['T']*5,'key':list('abcde'),'registered_voters':[100,100,np.nan,100,100],
                    'voted':[80,101,80,80,80],'votes:DEM':[40,40,40,90,-1],'votes:REP':[30]*5,'votes:OTHER':[0]*5})
    assert validate(d).eligible_arithmetic_only.tolist()==[True,False,False,False,False]


def main() -> None:
    selfcheck()
    frames = [washington(2024),washington(2020),minnesota(),california(),wyoming(),north_dakota(),maryland_official()]
    d = validate(pd.concat(frames,ignore_index=True))
    d.to_csv(OUT/'supplemental_precinct_join_audit.csv.gz',index=False)
    coverage = d.groupby('sample').agg(rows=('key','size'),eligible_arithmetic_only=('eligible_arithmetic_only','sum'),
        unknown=('unknown','sum'),over_registration=('over_registration','sum'),contest_over_ballots=('contest_over_ballots','sum'),
        registered=('registered_voters',lambda s:s.sum(min_count=1)),ballots=('voted',lambda s:s.sum(min_count=1)))
    coverage.to_csv(OUT/'supplemental_precinct_coverage.csv')
    for (sample,office),g in d[d['sample'].str.contains('2024')].groupby(['sample','office']):
        clerk_check(sample,sample[:2],office,g[VOTES].sum(axis=1,skipna=False).sum())
    supplemental()
    existing_samples()
    pd.DataFrame(CHECKS).to_csv(OUT/'download_reconciliation.csv',index=False)
    print(coverage.to_string())
    print(f'{len(CHECKS)} reconciliations; {sum(c.difference==0 for c in CHECKS)} exact agreements')


if __name__=='__main__':
    main()
