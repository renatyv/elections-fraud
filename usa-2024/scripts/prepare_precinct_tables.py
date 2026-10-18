"""Export downloaded official workbooks with the bundled openpyxl runtime."""
from pathlib import Path
import csv
import openpyxl

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    raw = ROOT / 'data/raw'
    jobs = [(raw / f'mn{year}_official_precinct.xlsx', 'Precinct-Results',
             raw / f'mn{year}_Precinct-Results.csv') for year in [2020, 2024]]
    jobs += [(raw / f'precinct_sources/id_results/{name}.xlsx', None,
              raw / f'id2024_{name}.csv') for name in ['raw_stats_general', 'raw_races_general']]
    for source, sheet, target in jobs:
        book = openpyxl.load_workbook(source, read_only=True, data_only=True)
        with target.open('w', newline='') as stream:
            csv.writer(stream).writerows(book[sheet or book.sheetnames[0]].values)
        book.close()
        print(target.name)


if __name__ == '__main__':
    main()
