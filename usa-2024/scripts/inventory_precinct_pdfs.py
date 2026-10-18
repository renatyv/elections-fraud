"""Inventory every downloaded precinct PDF without treating OCR text as verified data."""
from __future__ import annotations
import csv
import hashlib
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def inspect(pdf: Path) -> dict:
    result=subprocess.run(['pdftotext','-layout',str(pdf),'-'],capture_output=True)
    text=result.stdout.decode(errors='replace')
    return {'file':str(pdf.relative_to(ROOT)), 'bytes':pdf.stat().st_size,
            'sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(), 'text_extraction_ok':result.returncode==0,
            'pages':text.count('\f'), 'alphanumeric_characters':sum(c.isalnum() for c in text),
            'registration_mentions':len(re.findall(r'registered\s+voters|registration',text,re.I)),
            'ballots_mentions':len(re.findall(r'ballots\s+cast|total\s+ballots|times\s+counted',text,re.I)),
            'senate_mentions':len(re.findall(r'senat',text,re.I)),
            'limit':'Text-layer availability only; values, precinct geometry and final/corrected status not validated.'}


def main() -> None:
    files=sorted((ROOT/'data/raw/precinct_sources').rglob('*.pdf'))
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(inspect,files))
    with (ROOT/'analysis/precinct_pdf_inventory.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    assert len(rows)==len(files) and len({r['file'] for r in rows})==len(rows)
    print(len(rows),'PDFs,',sum(r['pages'] for r in rows),'pages;',sum(r['registration_mentions']>0 and r['ballots_mentions']>0 for r in rows),'have both registration and ballot text mentions')


if __name__=='__main__':main()
