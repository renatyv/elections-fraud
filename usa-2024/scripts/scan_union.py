"""Extract Union County's 20 precinct pages through OpenRouter Luna 6, low reasoning."""
from __future__ import annotations
import base64
import hashlib
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PDF=ROOT/'data/raw/precinct_sources/ms_union2024.pdf'
CACHE=ROOT/'data/source_search/luna_union_precincts.json'


def main() -> None:
    text=subprocess.check_output(['pdftotext','-layout',str(PDF),'-']).decode()
    pages=[i+1 for i,p in enumerate(text.split('\f')) if 'Registered Voters - Total' in p]
    assert len(pages)==20
    if not CACHE.exists():
        key=os.environ.get('OPENROUTER_KEY')
        if not key:
            for line in (ROOT.parent/'.env').read_text().splitlines():
                if line.startswith('OPENROUTER_KEY='):
                    key=line.split('=',1)[1].strip().strip('\"\'');break
        if not key:raise RuntimeError('OPENROUTER_KEY unavailable')
        content=[{'type':'text','text':'Extract these 20 Union County Mississippi November 5 2024 official precinct report pages. JSON only: {"precincts":[{"page":number,"name":"precinct name and code","registered":integer,"ballots":integer,"senate_dem":integer,"senate_rep":integer,"senate_writein":integer,"house_dem":integer,"house_rep":integer,"house_writein":integer}]}. Use TOTAL columns. Senate candidates Ty Pinkins and Roger Wicker; House Dianne Dodson Black and Trent Kelly. A zero must be printed, not inferred; use null for illegible values. Ignore contest totals, presidential and state judicial contests. Do not invent candidates or treat contest totals as write-ins.'}]
        for page in pages:
            prefix=Path('/tmp')/f'union-{page}'
            subprocess.run(['pdftoppm','-f',str(page),'-l',str(page),'-scale-to','1800','-png','-singlefile',str(PDF),str(prefix)],check=True,capture_output=True)
            content.extend([{'type':'text','text':f'PDF page {page}'},{'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(prefix.with_suffix('.png').read_bytes()).decode()}}])
        payload={'model':'openai/gpt-6-luna','reasoning':{'effort':'low'},'messages':[{'role':'user','content':content}],'max_tokens':12000}
        req=urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=600) as response:result=json.load(response)
        output=result['choices'][0]['message']['content']
        parsed=json.loads(re.sub(r'^```(?:json)?\s*|\s*```$','',output.strip()))
        CACHE.write_text(json.dumps({'model':result.get('model'),'reasoning':'low','sha256':hashlib.sha256(PDF.read_bytes()).hexdigest(),'pages':pages,'extraction':parsed,'usage':result.get('usage')},indent=2)+'\n')
    data=json.loads(CACHE.read_text())
    assert data['sha256']==hashlib.sha256(PDF.read_bytes()).hexdigest()
    rows=data['extraction']['precincts']
    assert len(rows)==20 and sorted(r['page'] for r in rows)==pages
    assert len({r['name'] for r in rows})==20
    # Compare every numeric cell with the source's independently extracted text layer.
    labels={'registered':r'Registered Voters\s*-\s*Total','ballots':r'Ballots Cast\s*-\s*Total',
            'senate_dem':r'D Ty P[iIl]nkins','senate_rep':r'R Roger [^\n]*?Wicker',
            'house_dem':r'D Dianne Dodson Black','house_rep':r'R Trent Kelly'}
    for row in rows:
        page=text.split('\f')[row['page']-1]
        for col,label in labels.items():
            match=re.search(label+r'\s+([\d,.]+)',page,re.I)
            assert match and int(re.sub(r'[,\.]','',match[1]))==row[col],(row['page'],col,row[col])
        writeins=[int(v.replace(',','')) for v in re.findall(r'Write-In Totals\s+([\d,]+)',page,re.I)]
        assert len(writeins)>=3 and writeins[1:3]==[row['senate_writein'],row['house_writein']],row
        assert 0<=row['ballots']<=row['registered']
        assert sum(row[c] for c in ['senate_dem','senate_rep','senate_writein'])<=row['ballots']
        assert sum(row[c] for c in ['house_dem','house_rep','house_writein'])<=row['ballots']
    import csv
    with (ROOT/'analysis/ms_union_precincts.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print('Verified',len(rows),'Union precincts')


if __name__=='__main__':main()
