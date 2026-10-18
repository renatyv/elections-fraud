"""Parse every Minnesota review table; verify selected rendered pages with Luna 6.

Uses OPENROUTER_KEY in the root .env without displaying it. Model outputs are
cached with source/page provenance; numerical parsing remains reproducible offline.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / 'data/raw/mn2024_post_election_review.pdf'
OUT = ROOT / 'analysis'
MODEL = 'openai/gpt-6-luna'


def main() -> None:
    text = subprocess.check_output(['pdftotext','-layout',str(PDF),'-']).decode()
    records = []
    for part in re.split(r'(?=Precinct:)', text)[1:]:
        head = re.search(r'Precinct:\s*(.*?)\s{2,}(\S.*? County)',part)
        office = re.search(r'Office:\s*(.+)',part)
        totals = re.search(r'^\s*Totals\s+([\d,]+)\s+([\d,]+)\s+(-?[\d,]+)\s+(-?[\d,]+)\s+(-?[\d,]+)',part,re.M)
        status = re.search(r'Final Results[^\n]*?\b(ACCEPTABLE|NOT ACCEPTABLE|UNACCEPTABLE)\s*$',part,re.M)
        assert head and office and totals and status, part[:250]
        nums=[int(v.replace(',','')) for v in totals.groups()]
        # Report totals sum candidate absolute differences, not net ballot changes.
        assert nums[2] >= abs(nums[1]-nums[0]) and nums[2]-nums[3] == nums[4]
        records.append({'county':head[2], 'precinct':head[1], 'office':office[1].strip(),
                        'machine':nums[0],'hand':nums[1],'raw_difference':nums[2],
                        'explained_difference':nums[3],'adjusted_difference':nums[4],'status':status[1]})
    import csv
    with (OUT/'mn_hand_review.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    pages=text.split('\f')
    discrepant=[i+1 for i,p in enumerate(pages) if re.search(r'^\s*Totals\s+[\d,]+\s+[\d,]+\s+(?:-?[1-9][\d,]*)\s',p,re.M)]
    selected=list(dict.fromkeys([1]+discrepant[:2]))
    cache=ROOT/'data/source_search/luna_mn_audit_verification.json'
    if not cache.exists():
        key=os.environ.get('OPENROUTER_KEY')
        if not key:
            for line in (ROOT.parent/'.env').read_text().splitlines():
                if line.startswith('OPENROUTER_KEY='):
                    key=line.split('=',1)[1].strip().strip('\"\'');break
        if not key: raise RuntimeError('OPENROUTER_KEY is unavailable')
        content=[{'type':'text','text':'Transcribe the Totals row and Final Results status of EVERY review table in these Minnesota 2024 hand-count report page images. Return JSON only: {"pages":[{"page":number,"tables":[{"precinct":"...","county":"...","office":"...","machine":integer,"hand":integer,"raw_difference":integer,"explained_difference":integer,"adjusted_difference":integer,"status":"..."}]}]}. Preserve negative signs. Do not infer missing entries. Each image is preceded by its page number.'}]
        for page in selected:
            prefix=Path('/tmp')/f'mn-review-{page}'
            subprocess.run(['pdftoppm','-f',str(page),'-l',str(page),'-scale-to','1800','-png','-singlefile',str(PDF),str(prefix)],check=True,capture_output=True)
            content.extend([{'type':'text','text':f'PDF page {page}'},{'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(prefix.with_suffix('.png').read_bytes()).decode()}}])
        payload={'model':MODEL,'reasoning':{'effort':'low'},'messages':[{'role':'user','content':content}],'max_tokens':6000}
        request=urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=240) as response:
            result=json.load(response)
        output=result['choices'][0]['message']['content']
        parsed=json.loads(re.sub(r'^```(?:json)?\s*|\s*```$','',output.strip()))
        cache.write_text(json.dumps({'requested_model':MODEL,'returned_model':result.get('model'), 'reasoning':'low','source_sha256':hashlib.sha256(PDF.read_bytes()).hexdigest(),'pages':selected,'extraction':parsed,'usage':result.get('usage')},indent=2)+'\n')
    verification=json.loads(cache.read_text())
    assert verification['source_sha256'] == hashlib.sha256(PDF.read_bytes()).hexdigest()
    checked=0
    for page in verification['extraction']['pages']:
        page_text=pages[page['page']-1]
        for row in page['tables']:
            values=[row[k] for k in ['machine','hand','raw_difference','explained_difference','adjusted_difference']]
            pattern=r'Totals\s+'+r'\s+'.join(re.escape(f'{v:,}').replace(',',',?') for v in values)
            assert re.search(pattern,page_text), (page['page'],values)
            checked+=1
    summary={'source_url':'https://www.sos.mn.gov/media/ixzn1dkx/2024-post-election-review-results.pdf',
             'pages':len(pages)-1,'tables':len(records),'unique_county_precincts':len({(r['county'],r['precinct']) for r in records}),
             'statuses':{s:sum(r['status']==s for r in records) for s in sorted({r['status'] for r in records})},
             'tables_nonzero_raw_total':sum(r['raw_difference']!=0 for r in records),
             'tables_nonzero_adjusted_total':sum(r['adjusted_difference']!=0 for r in records),
             'sum_abs_raw_total_difference':sum(abs(r['raw_difference']) for r in records),
             'sum_abs_adjusted_total_difference':sum(abs(r['adjusted_difference']) for r in records),
             'luna_pages':selected,'luna_verified_tables':checked,
             'limit':'Report difference totals sum candidate/category discrepancies, so the same ballot can affect more than one difference and more than one contest. Selected page verification is not a full OCR audit.'}
    (OUT/'mn_hand_review_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
