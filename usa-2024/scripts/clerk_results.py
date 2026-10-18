"""Parse the House Clerk's official-source 2024 candidate totals and spoiler bounds."""
from __future__ import annotations
import json
import re
import subprocess
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
STATES='Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming'.split('|')
CODES='AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split()
NAMES=dict(zip([s.upper() for s in STATES],CODES))


def main() -> None:
    text=subprocess.check_output(['pdftotext','-layout',str(ROOT/'data/raw/clerk_statistics2024.pdf'),'-']).decode()
    state,office,district,special=None,None,'001',False
    last_candidate=''
    rows=[]
    for page_num,page in enumerate(text.split('\f'),1):
        for line in page.splitlines():
            s=line.strip()
            head=re.split(r'—|–',s)[0]
            if head in NAMES:
                if NAMES[head]!=state:office=None
                state=NAMES[head]
                continue
            if 'Recapitulation of Votes Cast' in s or 'FOR PRESIDENTIAL ELECTORS' in s:
                office=None
            if 'FOR UNITED STATES SENATOR' in s:
                office,district,special='US SENATE','STATEWIDE',False
            if 'FOR UNITED STATES REPRESENTATIVE' in s:
                if 'Continued' not in s:district='001'
                office,special='US HOUSE',False
            if 'For unexpired term' in s:special=True
            if 'For full term' in s:special=False
            if state and office:
                m=re.fullmatch(r'(?:(\d+)\.\s*)?(.+?)\s*\.{3,}\s*([\d,]+|\(1\))',s)
                if not m:continue
                if m[1]:district=f'{int(m[1]):03d}'
                label=m[2].strip()
                compact=label.lower().replace(' ','')
                if compact.startswith(('total','blanks','blank','overvote','undervote','void','noneofthese','continuingballots','exhaustedballots')):continue
                if label in {'Conservative','Working Families','Independent','Common Sense','Common Sense Suffolk'}:
                    assert last_candidate
                    candidate=last_candidate
                else:
                    candidate=label.split(',')[0].strip()
                    last_candidate=candidate
                rows.append({'state_po':state,'office':office,'district':district,'special':special,
                             'label':label,'candidate':candidate,
                             'votes':int(m[3].replace(',','')) if m[3]!='(1)' else None,'pdf_page':page_num})
    d=pd.DataFrame(rows)
    # Fusion candidates repeat on multiple party lines, which are additive.
    keys=['state_po','office','district','special','candidate']
    totals=d.groupby(keys,as_index=False).agg(votes=('votes',lambda s:s.sum(min_count=1)),labels=('label',lambda s:' | '.join(s)),pdf_pages=('pdf_page',lambda s:','.join(map(str,sorted(set(s))))))
    totals.to_csv(ROOT/'analysis/clerk_candidate_totals.csv',index=False)
    races=[]
    for key,g in totals[~totals.special].groupby(['state_po','office','district']):
        g=g.sort_values('votes',ascending=False)
        if len(g)<2 or g.votes.isna().any():continue
        a,b=g.iloc[0],g.iloc[1]
        margin=int(a.votes-b.votes); other=int(g.votes.sum()-a.votes-b.votes)
        races.append(dict(zip(['state_po','office','district'],key),winner=a.candidate,runner_up=b.candidate,
                     winner_votes=int(a.votes),runner_up_votes=int(b.votes),total=int(g.votes.sum()),margin=margin,other_votes=other,
                     plurality_eligible=key[0] not in {'AK','ME','LA'},below_majority=2*a.votes<g.votes.sum(),spoiler_capacity=other>margin,
                     minimum_transfer_if_rest_abstain=margin+1,minimum_transfer_if_rest_back_leader=(other+margin)//2+1))
    race=pd.DataFrame(races)
    race.to_csv(ROOT/'analysis/clerk_race_screens.csv',index=False)
    counts=totals[~totals.special].groupby('office').apply(lambda g:g[['state_po','district']].drop_duplicates().shape[0]).to_dict()
    assert counts=={'US HOUSE':435,'US SENATE':33},counts
    assert not totals.duplicated(keys).any()
    selected=race[race.plurality_eligible & race.spoiler_capacity]
    medsl=pd.read_csv(ROOT/'analysis/race_screens.csv',dtype={'district':str},keep_default_na=False)
    numeric=medsl.district.str.fullmatch(r'\d+') & medsl.office.eq('US HOUSE')
    medsl.loc[numeric,'district']=medsl.loc[numeric,'district'].str.zfill(3)
    at_large=medsl.office.eq('US HOUSE') & medsl.state_po.isin(['AK','DE','ND','SD','VT','WY'])
    medsl.loc[at_large,'district']='001'
    reconciliation=race.merge(medsl,on=['state_po','office','district'],how='outer',suffixes=('_clerk','_medsl'),indicator=True,validate='one_to_one')
    for col in ['winner_votes','runner_up_votes','margin','other_votes']:
        reconciliation['difference_'+col]=reconciliation[col+'_medsl']-reconciliation[col+'_clerk']
    reconciliation.to_csv(ROOT/'analysis/clerk_medsl_race_reconciliation.csv',index=False)
    print(counts);print(selected.to_string(index=False))
    (ROOT/'analysis/clerk_summary.json').write_text(json.dumps({'regular_contests':counts,'plurality_eligible_with_two_records':int(race.plurality_eligible.sum()),'spoiler_bounds':len(selected),'nonmajority_plurality':int((race.plurality_eligible&race.below_majority).sum()),'source':'https://clerk.house.gov/member_info/electionInfo/2024/statistics2024.pdf','limit':'Candidate totals and pooled write-ins; Alaska/Maine ranked choice and Louisiana majority rule excluded from plurality claims; Clerk PDF totals do not supply ranked preferences.'},indent=2)+'\n')


if __name__=='__main__':main()
