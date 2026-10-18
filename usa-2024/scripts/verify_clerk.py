"""Verify all ten spoiler-bound rows plus rejected Arizona Senate against rendered PDF pages."""
from __future__ import annotations
import base64
import hashlib
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


def main() -> None:
    pdf=ROOT/'data/raw/clerk_statistics2024.pdf'
    races=pd.read_csv(ROOT/'analysis/clerk_race_screens.csv',dtype={'district':str})
    wanted=races[(races.plurality_eligible&races.spoiler_capacity)|((races.state_po=='AZ')&races.office.eq('US SENATE'))]
    candidates=pd.read_csv(ROOT/'analysis/clerk_candidate_totals.csv',dtype={'district':str,'pdf_pages':str})
    selected=candidates.merge(wanted[['state_po','office','district']],on=['state_po','office','district'])
    pages=sorted({int(p) for item in selected.pdf_pages for p in item.split(',')})
    cache=ROOT/'data/source_search/luna_clerk_verification.json'
    if not cache.exists():
        key=os.environ.get('OPENROUTER_KEY')
        if not key:
            for line in (ROOT.parent/'.env').read_text().splitlines():
                if line.startswith('OPENROUTER_KEY='):key=line.split('=',1)[1].strip().strip('\"\'');break
        if not key:raise RuntimeError('OPENROUTER_KEY unavailable')
        targets=wanted[['state_po','office','district']].to_dict('records')
        content=[{'type':'text','text':'Read these official House Clerk 2024 election pages. For ONLY the following contests, independently calculate the two largest candidate totals, their positive margin, and the SUM of all other candidate/write-in/miscellaneous votes. Exclude blanks, void and Nevada None of These Candidates. Fusion party lines immediately under a candidate belong to that candidate. Do not include presidential votes or recapitulation totals. Return JSON only {"races":[{"state_po":"XX","office":"US HOUSE or US SENATE","district":"three digits or STATEWIDE","winner_votes":integer,"runner_up_votes":integer,"margin":integer,"other_votes":integer}]}. Targets: '+json.dumps(targets)}]
        for page in pages:
            prefix=Path('/tmp')/f'clerk24-{page}'
            subprocess.run(['pdftoppm','-f',str(page),'-l',str(page),'-scale-to','2200','-png','-singlefile',str(pdf),str(prefix)],check=True,capture_output=True)
            content.extend([{'type':'text','text':f'PDF page {page}'},{'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(prefix.with_suffix('.png').read_bytes()).decode()}}])
        payload={'model':'openai/gpt-6-luna','reasoning':{'effort':'low'},'messages':[{'role':'user','content':content}],'max_tokens':8000}
        req=urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=600) as response:result=json.load(response)
        parsed=json.loads(re.sub(r'^```(?:json)?\s*|\s*```$','',result['choices'][0]['message']['content'].strip()))
        cache.write_text(json.dumps({'model':result.get('model'),'reasoning':'low','sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'pages':pages,'extraction':parsed,'usage':result.get('usage')},indent=2)+'\n')
    output=json.loads(cache.read_text())
    assert output['sha256']==hashlib.sha256(pdf.read_bytes()).hexdigest()
    verify=pd.DataFrame(output['extraction']['races'])
    merged=wanted.merge(verify,on=['state_po','office','district'],validate='one_to_one',suffixes=('','_luna'))
    assert len(merged)==len(wanted)==11
    for col in ['winner_votes','runner_up_votes','margin','other_votes']:
        assert merged[col].eq(merged[col+'_luna']).all(),merged.loc[merged[col]!=merged[col+'_luna'],['state_po','office',col,col+'_luna']].to_dict('records')
    print('Luna verified all 11 target races on',len(pages),'pages')


if __name__=='__main__':main()
