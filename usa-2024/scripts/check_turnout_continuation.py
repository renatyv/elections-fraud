from pathlib import Path
from collections import Counter
import csv, json, hashlib, zipfile
import xml.etree.ElementTree as E
root=Path('usa-2024'); base=root/'data/raw/precinct_sources/continuation_20261018'
manifest=json.loads((root/'data/source_search/turnout_continuation_20261018.json').read_text())
additional=json.loads((root/'data/source_search/turnout_continuation_additional_20261018.json').read_text())
artifacts=[r['attempts'][-1] for r in manifest['counties']+additional]
for a in artifacts:
 p=root/a['name']; assert a['status']=='downloaded'; assert p.stat().st_size==a['bytes']; assert hashlib.sha256(p.read_bytes()).hexdigest()==a['sha256']
checks={'files':len(artifacts),'bytes':sum(a['bytes'] for a in artifacts),'provenance':dict(Counter('mirror' if 'github' in a['url'] else 'official' for a in artifacts)),'states':{}}
for state,expected in [('ia',99),('wv',55)]:
 files=list((base/f'{state}-2024-county-detailxml-reports').glob('*/detailxml.zip')); assert len(files)==expected
 rows=[]
 for f in files:
  with zipfile.ZipFile(f) as z:
   assert z.testzip() is None
   for name in z.namelist():
    if name.endswith('.xml'):
     r=E.fromstring(z.read(name)); assert r.findtext('ElectionDate')=='11/5/2024'
     rows.extend(r.findall('.//VoterTurnout/Precincts/Precinct'))
 checks['states'][state.upper()]={'counties':len(files),'turnout_rows':len(rows),'ballots_cast':sum(int(r.attrib['ballotsCast']) for r in rows),'registered_voters':sum(int(r.attrib['totalVoters']) for r in rows)}
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(base/'oh-2024-statewide-races-precinct-level.xlsx') as z:
 assert z.testzip() is None
 strings=[''.join(t.itertext()) for t in E.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',ns)]
 rows=E.fromstring(z.read('xl/worksheets/sheet3.xml')).findall('s:sheetData/s:row',ns)
 def values(row: E.Element) -> dict:
  return {''.join(filter(str.isalpha,c.attrib['r'])):strings[int(c.findtext('s:v','0',ns))] if c.attrib.get('t')=='s' else c.findtext('s:v','',ns) for c in row}
 data=[values(r) for r in rows[4:]]
 assert len(data)==8878 and len({(r['A'],r['C']) for r in data})==8878
 checks['states']['OH']={'turnout_rows':len(data),'registered_voters':sum(int(r['F']) for r in data),'ballots_cast':sum(int(r['G']) for r in data)}
 assert checks['states']['OH']['registered_voters']==8159946 and checks['states']['OH']['ballots_cast']==5851387
with (base/'va-2024-enr-election-turnout.csv').open(encoding='utf-8-sig') as f:
 rows=list(csv.DictReader(f))
 assert len({(r['locality'],r['precinct']) for r in rows})==len(rows)==2669
 checks['states']['VA']={'turnout_rows':len(rows),'registered_voters':sum(int(r['TotalRegisteredVoters']) for r in rows if r['TotalRegisteredVoters']),'ballots_cast':sum(int(r['TotalVoteTurnout']) for r in rows if r['TotalVoteTurnout'])}
checks['states']['VA']['missing_registered_rows'] = sum(not r['TotalRegisteredVoters'] for r in rows)
checks['states']['VA']['missing_turnout_rows'] = sum(not r['TotalVoteTurnout'] for r in rows)
with (base/'sc-2024-election-history/voter-statistics-7075.csv').open() as f:
 rows=list(csv.reader(f))
checks['states']['SC']={'csv_rows_including_headers':len(rows),'first_rows':rows[:7],'status':'candidate; totals and denominator discrepancy versus VREMS unresolved'}
rows=json.loads((base/'vt-2024-official-sources/2024-general-turnout.json').read_text())['d']
checks['states']['VT']={'town_rows':len(rows),'registered_voters':sum(r['tvr'] for r in rows),'voters_cast':sum(r['tvc'] for r in rows),'status':'town geography; denominator timing unresolved'}
checks['states']['KY']={'pdf_files':4,'status':'PDF magic checked; not transcribed in this pass; publisher unofficial turnout caveat retained'}
(root/'data/source_search/turnout_continuation_checks_20261018.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(checks,indent=2))
