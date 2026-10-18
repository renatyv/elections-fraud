"""Reconcile cached Luna transcriptions without promoting them to certified data."""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from extract_precinct_pdfs import Batch, batches

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'analysis'
NUMBERS=['registered','ballots','dem','rep','other','under','over']
KEYS=['source','unit','level','office','district','mode']


def unique_value(values: pd.Series) -> float:
    found=values.dropna().unique()
    return found[0] if len(found)==1 else np.nan


def state_for(source: str) -> str:
    for text,state in [('ms_county/','MS'),('ut_counties/','UT'),('hi_results/','HI'),
                       ('de2024_','DE'),('wa_island','WA'),('nh_','NH')]:
        if text in source:return state
    raise ValueError(source)


def county_for(source: str) -> str:
    name=Path(source).stem
    if 'ms_county/' in source:
        return name.removesuffix('_Updated').replace('_',' ').upper().replace('JEFF DAVIS','JEFFERSON DAVIS')
    if 'ut_counties/' in source:
        return name.removeprefix('G24_Canvass_').removesuffix('_No-Precinct').replace('-',' ').upper()
    if 'wa_island' in source:return 'ISLAND'
    return ''


def selfcheck() -> None:
    assert np.isnan(unique_value(pd.Series([1,2])))
    assert unique_value(pd.Series([1,1,np.nan]))==1
    assert county_for('ms_county/Coahoma_Updated.pdf')=='COAHOMA'
    assert county_for('ut_counties/G24_Canvass_Utah_No-Precinct.pdf')=='UTAH'


def main() -> None:
    selfcheck()
    saved=OUT/'pdf_extraction_plan.json'
    plan=[Batch(ROOT/r['source'],r['sha256'],tuple(r['pages']),()) for r in json.loads(saved.read_text())] if saved.exists() else batches()
    status=json.loads((OUT/'pdf_extraction_status.json').read_text())
    repaired=[]
    if (OUT/'pdf_repair_status.json').exists():
        repairs=json.loads((OUT/'pdf_repair_status.json').read_text())
        repaired=[r for r in repairs if not r['error']]
        sources={r['source'] for r in repaired}
        status=[r for r in status if r['source'] not in sources]+repaired
        plan=[j for j in plan if str(j.source.relative_to(ROOT)) not in sources]
        for record in repaired:
            cached=json.loads((ROOT/record['cache']).read_text())
            plan.append(Batch(ROOT/record['source'],cached['sha256'],tuple(record['pages']),()))
    expected={(str(j.source.relative_to(ROOT)),j.pages) for j in plan}
    actual={(r['source'],tuple(r['pages'])) for r in status}
    assert actual<=expected
    selection=pd.DataFrame([{'source':str(j.source.relative_to(ROOT)),'pages':','.join(map(str,j.pages))} for j in plan])
    selection.to_csv(OUT/'pdf_selected_pages.csv',index=False)
    rows=[]
    for record in status:
        if record['error']:continue
        cached=json.loads((ROOT/record['cache']).read_text())
        for row in cached['extraction']['rows']:
            rows.append(dict(row,source=record['source'],sha256=cached['sha256']))
    d=pd.DataFrame(rows)
    d['state']=d.source.map(state_for)
    for col in ['unit','level','office','district','mode']:
        d[col]=d[col].fillna('').astype(str).str.strip()
    d[NUMBERS]=d[NUMBERS].apply(pd.to_numeric,errors='raise')
    d.to_csv(OUT/'pdf_extracted_rows.csv.gz',index=False)
    # Anonymous continuation rows remain unlocated, never joined to each other as one precinct.
    d['unit_missing']=d.unit.eq('')
    position=d.groupby(['source','page']).cumcount().astype(str)
    d.loc[d.unit_missing,'unit']='__UNLOCATED_PAGE_'+d.page.astype(str)+'_ROW_'+position
    # Identical repeated tables coalesce; differing readings remain a visible conflict.
    groups=d.groupby(KEYS,dropna=False)
    g=groups[NUMBERS].agg(unique_value).reset_index()
    conflicts=groups[NUMBERS].nunique().gt(1).any(axis=1).rename('conflicting_readings').reset_index()
    g=g.merge(conflicts,on=KEYS,validate='one_to_one')
    missing=groups.unit_missing.max().reset_index()
    g=g.merge(missing,on=KEYS,validate='one_to_one')
    pages=groups.page.agg(lambda s:','.join(map(str,sorted(set(s))))).rename('pages').reset_index()
    g=g.merge(pages,on=KEYS,validate='one_to_one')
    turnout_keys=['source','unit','level','mode']
    turnout=d.groupby(turnout_keys)[['registered','ballots']].agg(unique_value).reset_index()
    turnout_conflicts=d.groupby(turnout_keys)[['registered','ballots']].nunique().gt(1).any(axis=1).rename('unit_turnout_conflict').reset_index()
    g=g.merge(turnout,on=turnout_keys,how='left',validate='many_to_one',suffixes=('','_unit'))
    g=g.merge(turnout_conflicts,on=turnout_keys,how='left',validate='many_to_one')
    g['conflicting_readings']=g.conflicting_readings | g.unit_turnout_conflict
    for col in ['registered','ballots']:
        g[col]=g[col].fillna(g[col+'_unit'])
    g['state']=g.source.map(state_for)
    g['county']=g.source.map(county_for)
    g['unknown']=g[['registered','ballots','dem','rep','other']].isna().any(axis=1)
    g['over_registration']=g.ballots>g.registered
    g['candidate_total']=g[['dem','rep','other']].sum(axis=1,skipna=False)
    g['contest_over_ballots']=g.candidate_total>g.ballots
    g['ballot_balance_error']=g.candidate_total+g.under+g.over-g.ballots
    g['eligible_arithmetic_only']=(g.level.eq('precinct') & g.office.isin(['SENATE','HOUSE']) &
        g['mode'].str.upper().eq('TOTAL') & ~g.unit_missing & ~g.unknown & ~g.conflicting_readings &
        (g.registered>0) & (g.ballots>0) & ~g.over_registration & ~g.contest_over_ballots &
        (g.ballot_balance_error.isna() | g.ballot_balance_error.eq(0)))
    g.to_csv(OUT/'pdf_precinct_join_audit.csv.gz',index=False)
    coverage=g.groupby(['state','source','office']).agg(rows=('unit','size'),
        precincts=('level',lambda s:s.eq('precinct').sum()),
        eligible_arithmetic_only=('eligible_arithmetic_only','sum'),
        conflicting_readings=('conflicting_readings','sum'),unknown=('unknown','sum'),
        unlocated_rows=('unit_missing','sum'),
        over_registration=('over_registration','sum'),contest_over_ballots=('contest_over_ballots','sum'))
    coverage.to_csv(OUT/'pdf_extraction_coverage.csv')
    results=pd.read_csv(ROOT/'data/congress_candidate_units.csv.gz',dtype=str,keep_default_na=False)
    results=results[results.special.eq('FALSE') & results.date.eq('2024-11-05')].copy()
    results=results[~results.candidate.str.contains('UNDER|OVER|BLANK|TOTAL|NO CANDIDATE|^CAST VOTES$|^$',regex=True)]
    results['votes']=pd.to_numeric(results.votes,errors='coerce')
    refs=results.groupby(['state_po','county_name','office']).votes.agg(lambda s:s.sum(skipna=False))
    party_refs=results.groupby(['state_po','county_name','office','party']).votes.agg(lambda s:s.sum(skipna=False))
    clerk=pd.read_csv(OUT/'clerk_candidate_totals.csv')
    clerk=clerk[~clerk.special]
    checks=[]
    for (source,office),frame in g[g.office.isin(['SENATE','HOUSE'])].groupby(['source','office']):
        state=state_for(source);county=county_for(source)
        units=frame[frame.level.isin(['precinct','other']) & frame['mode'].str.upper().eq('TOTAL')]
        # A statewide/table total is never added to its constituent precincts.
        observed=units.candidate_total.sum(min_count=1)
        complete=units.candidate_total.notna().all() and not units.conflicting_readings.any()
        reference=refs.get((state,county,'US '+office),np.nan) if county else np.nan
        scope='MEDSL county' if county else 'No external reference for this geography'
        printed=unique_value(frame.loc[frame.level.isin(['county_total','state_total']) & frame['mode'].str.upper().eq('TOTAL'),'candidate_total'])
        printed_only=units.empty and pd.notna(printed)
        if printed_only:
            observed=printed
            complete=not frame.conflicting_readings.any()
        if state=='HI':
            c=clerk[clerk.state_po.eq(state) & clerk.office.eq('US '+office)]
            reference=c.votes.sum(min_count=1)
            scope='House Clerk statewide'
        elif not county and pd.notna(printed):
            reference=printed
            scope='Printed source total (internal arithmetic only)'
        planned=[j for j in plan if str(j.source.relative_to(ROOT))==source]
        finished=[r for r in status if r['source']==source and not r['error']]
        checks.append({'source':source,'state':state,'county':county,'office':office,
            'total_mode_units':len(units),'unknown_unit_totals':int(units.candidate_total.isna().sum()),
            'observed_candidate_sum':observed,'reference_candidate_sum':reference,'reference_scope':scope,
            'observation_level':'printed_total_only' if printed_only else 'precinct_and_pool_sum',
            'printed_candidate_total':printed,'printed_total_difference':observed-printed,
            'difference':observed-reference,'all_selected_batches_extracted':len(planned)==len(finished),
            'complete_unit_values':complete,'exact_source_total_agreement':bool(complete and observed==reference and len(planned)==len(finished)),
            'limit':'Exact aggregate agreement does not verify unit geography or OCR cells; other-level pools included, printed totals excluded.'})
        for col,party in [('dem','DEMOCRAT'),('rep','REPUBLICAN')]:
            checks[-1][col+'_observed_sum']=units[col].sum(min_count=1)
            if printed_only:
                checks[-1][col+'_observed_sum']=unique_value(frame.loc[frame.level.isin(['county_total','state_total']) & frame['mode'].str.upper().eq('TOTAL'),col])
            checks[-1][col+'_unknown_units']=int(units[col].isna().sum())
            checks[-1][col+'_reference_sum']=party_refs.get((state,county,'US '+office,party),np.nan) if county else np.nan
            if state=='HI':
                label='Democrat' if col=='dem' else 'Republican'
                checks[-1][col+'_reference_sum']=c.loc[c.labels.str.contains(label),'votes'].sum(min_count=1)
            checks[-1][col+'_difference']=checks[-1][col+'_observed_sum']-checks[-1][col+'_reference_sum']
    present={(r['source'],r['office']) for r in checks}
    for source in sorted({j.source for j in plan}):
        name=str(source.relative_to(ROOT));state=state_for(name)
        offices=['TURNOUT'] if state=='DE' or 'Voter_Turnout' in name else ['HOUSE'] if state=='NH' else ['HOUSE','SENATE']
        for office in offices:
            if office=='TURNOUT' or (name,office) in present:continue
            checks.append({'source':name,'state':state,'county':county_for(name),'office':office,
                'total_mode_units':0,'exact_source_total_agreement':False,
                'limit':'No rows for expected congressional office; source absence or extraction omission remains unresolved.'})
    pd.DataFrame(checks).to_csv(OUT/'pdf_source_reconciliation.csv',index=False)
    summary={'planned_batches':len(plan),'finished_batches':len(status),'successful_batches':sum(not r['error'] for r in status),
        'failed_batches':sum(bool(r['error']) for r in status),'pending_batches':len(expected-actual),
        'selected_pages':sum(len(j.pages) for j in plan),'transcribed_rows':len(d),'coalesced_rows':len(g),
        'source_documents':len({j.source for j in plan}),'unlocated_rows':int(g.unit_missing.sum()),
        'arithmetic_eligible_congress_rows':int(g.eligible_arithmetic_only.sum()),
        'repaired_documents':len(repaired),
        'source_office_comparisons':len(checks),
        'exact_source_total_agreements':sum(r['exact_source_total_agreement'] for r in checks),
        'limit':'Provisional model extraction; no changes to published forensic sample. Relevant text pages and all scanned pages selected; local-only text pages excluded. Wyoming uses equivalent Excel; corrected MS PDFs supersede originals.'}
    (OUT/'pdf_extraction_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
