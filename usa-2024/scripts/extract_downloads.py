"""Inventory local downloads and losslessly export downloaded spreadsheet tables.

Use the bundled Python runtime (openpyxl). Does not modify raw sources.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import re
import shutil
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw'
OUT = ROOT / 'data/extracted'


@dataclass
class Table:
    source: str
    member: str
    sheet: str
    output: str
    rows: int
    columns: int


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe_name(name: str) -> str:
    return re.sub(r'[^\w.-]', '_', name)


def workbook(source: Path, origin: str, member: str, target: Path) -> list[Table]:
    book = openpyxl.load_workbook(source, read_only=True, data_only=True)
    assert len({safe_name(s.title) for s in book}) == len(book.sheetnames)
    tables = []
    for sheet in book:
        output = target / (safe_name(sheet.title) + '.csv.gz')
        output.parent.mkdir(parents=True, exist_ok=True)
        count, columns = 0, 0
        with gzip.open(output, 'wt', newline='') as stream:
            writer = csv.writer(stream)
            for row in sheet.values:
                writer.writerow(row)
                count += 1
                columns = max(columns, len(row))
        tables.append(Table(origin, member, sheet.title, str(output.relative_to(ROOT)), count, columns))
    book.close()
    return tables


def check_manifests() -> None:
    expected = []
    with (ROOT/'data/manifest.csv').open() as stream:
        expected.extend(dict(r, source='data/raw/'+r['file']) for r in csv.DictReader(stream))
    with (ROOT/'data/source_search/download_manifest.csv').open() as stream:
        expected.extend(dict(r, source=r['file'].removeprefix('usa-2024/')) for r in csv.DictReader(stream))
    with (ROOT/'data/source_search/precinct_download_manifest.csv').open() as stream:
        expected.extend(dict(r, source=r['path']) for r in csv.DictReader(stream) if r['status']=='downloaded')
    expected.extend(dict(r, source=r['name']) for r in json.loads(
        (ROOT/'data/source_search/turnout_expansion_20261018.json').read_text()) if r['status']=='downloaded')
    expected.extend(dict(r, source='data/raw/'+r['file']) for r in json.loads(
        (ROOT/'data/source_search/analysis_extra_downloads.json').read_text()))
    expected.extend(dict(r, source='data/raw/'+r['file']) for r in json.loads(
        (ROOT/'data/supplemental_sources.json').read_text()))
    rows=[]
    for record in expected:
        path=ROOT/record['source']
        rows.append({'source':record['source'],'exists':path.is_file(),
            'bytes_match':path.is_file() and ('bytes' not in record or path.stat().st_size==int(record['bytes'])),
            'sha256_match':path.is_file() and digest(path)==record['sha256']})
    with (ROOT/'analysis/download_integrity.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['source','exists','bytes_match','sha256_match'])
        writer.writeheader();writer.writerows(rows)
    assert all(r['exists'] and r['bytes_match'] and r['sha256_match'] for r in rows), 'See download_integrity.csv'


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    inventory, tables, archives = [], [], []
    # Only downloaded sources, not the derived CSVs beside them.
    sources = sorted((RAW / 'precinct_sources').rglob('*'))
    sources += sorted(p for p in RAW.iterdir() if p.suffix.lower() in {'.xlsx', '.pdf', '.zip', '.csv'})
    for source in sources:
        if not source.is_file():
            continue
        origin = str(source.relative_to(ROOT))
        sha = digest(source)
        inventory.append({'source': origin, 'bytes': source.stat().st_size, 'sha256': sha})
        if source.suffix in {'.zip','.xlsx'}:
            with zipfile.ZipFile(source) as archive:
                bad=archive.testzip()
            archives.append({'source':origin,'crc_ok':bad is None})
            if bad:
                raise ValueError(f'Corrupt ZIP: {origin}: {bad}')
        if 'precinct_sources' not in source.parts and source.suffix != '.xlsx':
            continue
        target = OUT / source.relative_to(RAW)
        if source.suffix == '.xlsx':
            tables.extend(workbook(source, origin, '', target))
        elif source.suffix == '.zip':
            with zipfile.ZipFile(source) as archive:
                members=[i.filename for i in archive.infolist() if not i.is_dir()]
                assert len({safe_name(n) for n in members})==len(members), origin
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    # Flatten members; never permit archive paths to escape the output directory.
                    output = target / safe_name(info.filename)
                    output.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(info) as src, output.open('wb') as dst:
                        shutil.copyfileobj(src, dst)
                    if output.suffix == '.xlsx':
                        tables.extend(workbook(output, origin, info.filename, output.with_suffix('')))
                    elif output.suffix in {'.csv', '.txt'}:
                        with output.open(errors='replace', newline='') as stream:
                            reader = csv.reader(stream, delimiter='\t' if output.suffix == '.txt' and 'voter_stats' in output.name else ',')
                            count, columns = 0, 0
                            for row in reader:
                                count += 1
                                columns = max(columns, len(row))
                        tables.append(Table(origin, info.filename, '', str(output.relative_to(ROOT)), count, columns))
        print(origin, flush=True)
    assert len({r['source'] for r in inventory}) == len(inventory)
    with (ROOT / 'analysis/download_inventory.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['source', 'bytes', 'sha256'])
        writer.writeheader()
        writer.writerows(inventory)
    (ROOT / 'analysis/extracted_tables.json').write_text(json.dumps([asdict(t) for t in tables], indent=2) + '\n')
    with (ROOT/'analysis/download_archive_checks.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['source','crc_ok'])
        writer.writeheader();writer.writerows(archives)
    check_manifests()
    print(f'{len(inventory)} files inventoried; {len(tables)} tables exported')


if __name__ == '__main__':
    main()
