"""Analyze the 18 October downloads as a new, jointly adjusted diagnostic family.

Preserve the earlier snapshot. Run with analysis-tool/.venv/bin/python.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from precincts import VOTES, analyze, bh, selfcheck, validate
from reconcile_downloads import read

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/expanded'
SITE = ROOT.parent / 'site/usa-2024'
RAW = ROOT / 'data/raw/precinct_sources/continuation_20261018'


def county_xml(state: str) -> pd.DataFrame:
    rows = []
    for path in sorted(RAW.glob(state.lower()+'*/**/detailxml.zip')):
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None
            names = [n for n in archive.namelist() if n.endswith('.xml')]
            assert len(names) == 1
            root = ET.fromstring(archive.read(names[0]))
        county = root.findtext('Region')
        assert root.findtext('ElectionDate') == '11/5/2024'
        turnout = {p.attrib['name']: p.attrib for p in root.findall('./VoterTurnout/Precincts/Precinct')}
        assert len(turnout) == len(root.findall('./VoterTurnout/Precincts/Precinct'))
        for contest in root.findall('Contest'):
            name = contest.attrib['text']
            if re.search(r'^(U\.?S\.?|United States).*Senat', name, re.I):
                office, district = 'SENATE', 'STATEWIDE'
            elif re.search(r'^(U\.?S\.?|United States).*?(Represent|Congress)', name, re.I):
                office = 'HOUSE'
                numbers = re.findall(r'\d+', name)
                assert len(numbers) == 1, name
                district = numbers[0].zfill(3)
            else:
                continue
            choices = []
            for choice in contest.findall('Choice'):
                counts: dict[str, int] = {}
                modes = choice.findall('VoteType')
                assert len({v.attrib['name'] for v in modes}) == len(modes)
                for mode in modes:
                    precincts = mode.findall('Precinct')
                    assert len({p.attrib['name'] for p in precincts}) == len(precincts)
                    assert sum(int(p.attrib['votes']) for p in precincts) == int(mode.attrib['votes'])
                    for p in precincts:
                        key = p.attrib['name']
                        counts[key] = counts.get(key, 0) + int(p.attrib['votes'])
                assert sum(counts.values()) == int(choice.attrib['totalVotes'])
                bloc = 'votes:'+choice.attrib.get('party', 'OTHER')
                choices.append((bloc if bloc in VOTES else 'votes:OTHER', counts))
            keys = set().union(*(set(c) for _, c in choices))
            for key in sorted(keys):
                t = turnout.get(key, {})
                row = dict(sample=f'{state}2024 {office}', district=district, key=f'{county}|{key}',
                           county=county, name=key, registered_voters=t.get('totalVoters', np.nan),
                           voted=t.get('ballotsCast', np.nan), source_exclusion=False)
                for bloc in VOTES:
                    cs = [c for b, c in choices if b == bloc]
                    row[bloc] = sum(c[key] for c in cs) if all(key in c for c in cs) else np.nan
                rows.append(row)
    assert rows, state
    d = pd.DataFrame(rows)
    d[['registered_voters','voted']] = d[['registered_voters','voted']].apply(pd.to_numeric)
    return d


def ohio() -> pd.DataFrame:
    # Read cached XLSX values with the standard library; no new Excel dependency.
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(RAW/'oh-2024-statewide-races-precinct-level.xlsx') as archive:
        strings = [''.join(e.itertext()) for e in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('s:si', ns)]
        raw = ET.fromstring(archive.read('xl/worksheets/sheet5.xml')).findall('s:sheetData/s:row', ns)
        data = []
        for row in raw:
            data.append({re.sub(r'\d', '', c.attrib['r']): strings[int(c.findtext('s:v','0',ns))]
                         if c.attrib.get('t') == 's' else c.findtext('s:v','',ns) for c in row})
    headers, labels = data[0], data[1]
    groups: dict[str, list[str]] = {}
    current = ''
    for col, text in headers.items():
        if text.strip(): current = text.strip()
        if col not in list('ABCDEFGH'): groups.setdefault(current, []).append(col)
    d = pd.DataFrame(data[4:])
    assert len(d) == 8878 and not d.duplicated(['A','C']).any()
    rows = []
    for name, cols in groups.items():
        if name.startswith('U.S. Senator'): office, district = 'SENATE', 'STATEWIDE'
        elif name.startswith('Representative to Congress'):
            office, district = 'HOUSE', re.findall(r'\d+',name)[0].zfill(3)
        else: continue
        n = d[cols].apply(pd.to_numeric,errors='raise')
        active = n.sum(axis=1) > 0
        g = pd.DataFrame({'sample':'OH2024 '+office,'district':district,'key':d.A+'|'+d.C,
                          'county':d.A,'name':d.B,'registered_voters':pd.to_numeric(d.F),
                          'voted':pd.to_numeric(d.G)})
        for bloc, suffix in [('votes:DEM','(D)'),('votes:REP','(R)')]:
            g[bloc] = n[[c for c in cols if labels[c].endswith(suffix)]].sum(axis=1)
        g['votes:OTHER'] = n.sum(axis=1)-g['votes:DEM']-g['votes:REP']
        g['incomplete_writeins'] = True
        rows.append(g[active])
    return pd.concat(rows, ignore_index=True)


def vermont() -> pd.DataFrame:
    towns = json.loads((RAW/'vt-2024-official-sources/2024-general-turnout.json').read_text())['d']
    rows = []
    for town in towns:
        for group in town['hl']:
            for office in group['o']:
                if office['on'] not in {'REPRESENTATIVE TO CONGRESS', 'US SENATOR'}: continue
                # Sanders is independent: do not silently relabel him as a Democrat.
                if office['on'] == 'US SENATOR': continue
                for contest in office['cs']:
                    candidates = contest['rc'] + contest['wc']
                    row = dict(sample='VT2024 HOUSE', district='001', key=str(town['tid']),
                               county='STATEWIDE', name=town['tn'], registered_voters=town['tvr'], voted=town['tvc'])
                    for bloc in VOTES: row[bloc] = 0
                    for candidate in candidates:
                        party = candidate.get('pn') or ''
                        bloc = 'DEM' if party == 'DEMOCRATIC' else 'REP' if party == 'REP/LBRT' else 'OTHER'
                        row['votes:'+bloc] += candidate['vc']
                    row['source_exclusion'] = True  # Partial district results in multi-district towns; statewide totals incomplete.
                    rows.append(row)
    return pd.DataFrame(rows)


def supplemental() -> pd.DataFrame:
    d = pd.read_csv(ROOT/'analysis/supplemental_precinct_join_audit.csv.gz',dtype={'key':str,'county':str},low_memory=False)
    d = d[d['sample'].isin(['WA2024 SENATE','WA2020 PRESIDENT','MN2016 HOUSE','CA2020 HOUSE','CA2020 PRESIDENT'])].copy()
    d['district'] = 'STATEWIDE'
    for sample, file, key, district in [
        ('MN2016 HOUSE','expansion_20261018/mn2016_official_precinct.xlsx/Results.csv.gz','VTDID','CONGDIST'),
        ('CA2020 HOUSE','expansion_20261018/ca2020_srprec_sov.zip/state_g20_sov_data_by_g20_srprec.csv','SRPREC_KEY','CDDIST')]:
        source = read(file,dtype=str)
        mapping = source.set_index(key)[district]
        selected = d['sample'].eq(sample)
        d.loc[selected,'district'] = d.loc[selected,'key'].map(mapping).str.zfill(3)
        assert d.loc[selected,'district'].notna().all()
    d['name'] = d.key
    # WA full-state Senate replaces overlapping King; House needs district-specific fields.
    source = read('expansion_20261018/wa2024_precinct_results.zip/2024Gen_Precinct_Results_GIS-Ready_Federal.csv',dtype={'St_Code':str})
    senate = d[d['sample'].eq('WA2024 SENATE')].copy()
    codes = pd.read_csv(ROOT/'analysis/wa2024_candidate_reconciliation.csv',dtype={'district':str})
    house = []
    district_sums = pd.DataFrame({district:source[g.field].sum(axis=1) for district,g in codes[codes.office.eq('HOUSE')].groupby('district')})
    for district, columns in codes[codes.office.eq('HOUSE')].groupby('district'):
        g = senate.copy().set_index('key')
        g['district'], g['sample'] = district, 'WA2024 HOUSE'
        for bloc in VOTES:
            fields = columns[columns.bloc.eq(bloc.removeprefix('votes:'))].field.tolist()
            g[bloc] = source.set_index('St_Code')[fields].sum(axis=1,skipna=False)
        active = source.loc[district_sums[district]>0,'St_Code']
        split = source.loc[(district_sums>0).sum(axis=1)>1,'St_Code']
        g['source_exclusion'] = g.index.isin(split)
        house.append(g.loc[g.index.isin(active)].reset_index())
    return pd.concat([d,*house],ignore_index=True)


def turnout_joins() -> pd.DataFrame:
    """Join exact normalized publisher names; retain every unmatched reporting key."""
    va = pd.read_csv(RAW/'va-2024-enr-election-turnout.csv',dtype=str)
    va['county'] = va.locality.str.upper().str.replace(r' COUNTY$', '',regex=True)
    va['name'] = va.precinct
    va['registered_voters'] = pd.to_numeric(va.TotalRegisteredVoters,errors='coerce')
    va['voted'] = pd.to_numeric(va.TotalVoteTurnout,errors='coerce')
    sc = pd.read_csv(RAW/'sc-2024-election-history/voter-statistics-7075.csv',skiprows=2,header=None,
                     names=['level','name','voted','registered_voters'])
    sc['county'] = sc['name'].where(sc.level.eq('County')).ffill().str.upper()
    state_total = sc[sc.level.eq('State')][['voted','registered_voters']].iloc[0]
    sc = sc[sc.level.eq('Precinct')].copy()
    assert (sc[['voted','registered_voters']].sum() == state_total).all()
    results = pd.read_csv(ROOT/'data/congress_candidate_units.csv.gz',dtype=str,keep_default_na=False)
    frames = []
    for state, turnout in [('VA',va),('SC',sc)]:
        # Remove numeric padding only, with collision checks on both sides of the join.
        def key(county: pd.Series, name: pd.Series) -> pd.Series:
            return county.str.upper()+'|'+name.str.upper().str.replace(r'\b0+(\d)',r'\1',regex=True).str.strip()
        turnout['key'] = key(turnout.county,turnout['name'])
        assert not turnout.key.duplicated().any()
        source = results[results.state_po.eq(state)&results.special.str.upper().eq('FALSE')].copy()
        source = source[~source.candidate.str.contains('UNDER|OVER|BLANK|TOTAL|NO CANDIDATE|^CAST VOTES$|^$',regex=True)]
        source['key'] = key(source.county_name,source.precinct)
        source['votes'] = pd.to_numeric(source.votes,errors='coerce')
        source['bloc'] = source.party.map({'DEMOCRAT':'votes:DEM','REPUBLICAN':'votes:REP'}).fillna('votes:OTHER')
        for office, candidates in source.groupby('office'):
            tallies = candidates.groupby(['key','district','bloc']).votes.agg(lambda v:v.sum() if v.notna().all() else np.nan).unstack('bloc',fill_value=0).reset_index()
            g = tallies.merge(turnout[['key','county','name','registered_voters','voted']],on='key',how='outer',validate='many_to_one',indicator=True)
            g['sample'] = state+'2024 '+office.removeprefix('US ')
            g['district'] = g.district.fillna('UNMATCHED').str.zfill(3)
            g['join_status'] = g._merge.astype(str)
            g = g.drop(columns='_merge')
            for col in VOTES:
                if col not in g: g[col] = 0
            frames.append(g)
    return pd.concat(frames,ignore_index=True)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    selfcheck()
    old = pd.read_csv(ROOT/'analysis/precinct_join_audit.csv.gz',dtype={'key':str,'county':str},low_memory=False)
    old = old[~old['sample'].eq('WA-King2024 SENATE')]
    frames = [old,supplemental(),county_xml('IA'),county_xml('WV'),ohio(),vermont(),turnout_joins()]
    audit = pd.concat(frames,ignore_index=True)
    audit['source_exclusion'] = audit.source_exclusion.fillna(False).astype(bool)
    # Full precinct turnout cannot be assigned to each fragment of a split House precinct.
    house = audit['sample'].str.endswith('HOUSE')
    split = audit[house].duplicated(['sample','key'],keep=False)
    audit.loc[audit[house].index[split], 'source_exclusion'] = True
    audit = validate(audit)
    audit.to_csv(OUT/'precinct_join_audit.csv.gz',index=False)
    coverage = audit.groupby('sample').agg(rows=('key','size'),eligible=('eligible','sum'),unknown=('unknown','sum'),
        zero_denominator=('zero_denominator','sum'),over_registration=('over_registration','sum'),
        contest_over_ballots=('contest_over_ballots','sum'),source_exclusion=('source_exclusion','sum')).reset_index()
    coverage.to_csv(OUT/'precinct_coverage.csv',index=False)
    # Compare major blocs and all candidate votes to the complete official-source inventory.
    clerk = pd.read_csv(ROOT/'analysis/clerk_candidate_totals.csv',dtype={'district':str})
    clerk = clerk[~clerk.special].copy()
    clerk['bloc'] = np.where(clerk.labels.str.contains('Democrat',na=False),'votes:DEM',np.where(clerk.labels.str.contains('Republican',na=False),'votes:REP','votes:OTHER'))
    comparisons = []
    for (sample,district), g in audit[audit['sample'].str.match(r'(IA|WV|OH|VT|WA|VA|SC)2024')].groupby(['sample','district']):
        office = 'US '+sample.split()[-1]
        ref = clerk[clerk.state_po.eq(sample[:2])&clerk.office.eq(office)&clerk.district.eq(district)]
        for bloc in VOTES:
            expected = ref.loc[ref.bloc.eq(bloc),'votes'].sum(min_count=1)
            observed = g[bloc].sum(min_count=1)
            comparisons.append(dict(sample=sample,district=district,bloc=bloc,observed=observed,clerk=expected,difference=observed-expected))
    pd.DataFrame(comparisons).to_csv(OUT/'clerk_bloc_reconciliation.csv',index=False)
    analyze(audit,OUT)
    peaks = pd.read_csv(OUT/'precinct_integer_peaks.csv')
    # Toolkit provides z-scores, so label the normal-tail adjustment as approximate.
    peaks['p_normal_approx'] = norm.sf(peaks.z_score)
    peaks['q_bh_normal_approx'] = bh(peaks.p_normal_approx)
    peaks['p_mult5_normal_approx'] = norm.sf(peaks.z_mult5)
    joint = pd.concat([peaks.p_normal_approx,peaks.p_mult5_normal_approx],ignore_index=True)
    adjusted = bh(joint)
    peaks['q_joint_normal_approx'] = adjusted[:len(peaks)]
    peaks['q_mult5_joint_normal_approx'] = adjusted[len(peaks):]
    peaks.to_csv(OUT/'precinct_integer_peaks.csv',index=False)
    print(coverage.to_string(index=False))


if __name__ == '__main__':
    main()
