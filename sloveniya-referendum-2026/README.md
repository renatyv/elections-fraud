# Slovenia — referendums of 11.10.2026: monitoring and analysis

A Python project (uv) for regularly downloading the official data of the four
nationwide referendums of Slovenia of 11 October 2026 from the portal of the
State Electoral Commission (DVK): `https://volitve.dvk-rs.si`,
and analysing the trends (pandas, matplotlib).

Context and a walkthrough of the sources — in [report.md](report.md); the official
description of the DVK data formats — in [docs/Referendumi_2026_-_datoteke_s_podatki.docx](docs/Referendumi_2026_-_datoteke_s_podatki.docx).

## Quick start

You need [uv](https://docs.astral.sh/uv/). Dependencies install with one command:

```bash
uv sync
```

Commands (the `sloref` console script):

```bash
uv run sloref fetch                 # one poll: 4 referendums × 5 files
uv run sloref fetch --loop          # a loop every 15 minutes
uv run sloref fetch --loop --interval 300 --volisca   # own interval + precincts
uv run sloref summary               # summary table of the current figures (pandas)
uv run sloref plot                  # PNG trend plots → data/plots/
```

Background collection on election day:

```bash
nohup uv run sloref fetch --loop > /dev/null 2>&1 &
```

or cron (`crontab -e`):

```
*/15 * * * * cd "/Users/renatyuldashev/Documents/elections analysis/sloveniya-referendum-2026" && uv run sloref fetch
```

## What is downloaded

For each referendum (slug: `referendum-preiskava`,
`referendum-socialna-pomoc`, `referendum-volilna-pravica-tujcev`,
`referendum-rtv-prispevek`) — the `udelezba.json/csv` (turnout),
`rezultati.json/csv` (ZA/PROTI results), `izvoz.xlsx` files; optionally
`--volisca` — results per precinct (`volisca_01_01.json … volisca_08_11.json`,
88 files per referendum).

Format nuances: percentages in JSON are fractions (0.4825); the share of counted
ballots = `rezultati.glas / udelezba.slovenija.gl`; timestamps are Slovenian local
time in Zulu form; CSV — `;` separator and decimal comma; before publication the
files contain only the `datum` field — that is normal.

## Where the data is stored

| Path | Contents |
|---|---|
| `data/latest/<referendum>/` | latest versions of the files (overwritten) |
| `data/raw/<date>/<time>/<referendum>/` | snapshots of **only changed** files |
| `data/timeseries.csv` | timeline of the nationwide figures (a row — when the figures change) |
| `data/derived/volisca_all.csv` | combined per-precinct dataset: 3,083 precincts × 4 referendums, 12,332 rows (`scripts/build_volisca_csv.py`) |
| `data/derived/nacionalni_pregled.csv` | DVK aggregates: country / 8 units / 88 districts per referendum |
| `data/ef/<referendum>/` | precincts in the analysis-tool format (`results_freguesias.csv`) + validation log |
| `data/wikipedia/` | Wikipedia data: article wikitext, results table + per-vote cross-check with DVK, reconstructed counting-night dynamics |
| `data/plots/` | PNG trend plots (`sloref plot`) |
| `analysis/` | election forensics: figures/tables/metrics.json per referendum + `analysis/cross/` |
| `data/scrape.log` | poll log |

Referendum keys: `preiskava` (legislative, on ZPPre-B), `socialna_pomoc`,
`volilna_pravica`, `rtv_prispevek`. The data directory can be overridden
with the `SLOREF_DATA_DIR` variable.

## Project structure

```
src/sloref/
  config.py      referendums, files, URLs, paths
  httpclient.py  httpx2 client: retries, 404 = "no data yet", IPv4-only
  models.py      Aggregates — nationwide figures from the JSON
  storage.py     Store: latest/raw snapshots, timeseries.csv, log
  scraper.py     poll_once / run_loop
  analysis.py    pandas: loading trends, summary table
  plotting.py    matplotlib: PNG trend plots
  cli.py         argparse CLI (fetch / summary / plot)
scripts/
  build_ef_csv.py     adapting precincts to the analysis-tool format (results_freguesias.csv)
                      + validation (data/ef/VALIDATION.txt)
  analyze_extra.py    cross-referendum checks, the second option (PROTI),
                      early-voting points, duplicate protocols
tests/           pytest: extracting figures, snapshot and trend deduplication
```

## Statistical analysis of election fraud

Election forensics on the per-precinct results (2,984 precincts × 4 referendums) —
the standard [`analysis-tool`](../analysis-tool/) pipeline; report —
[statistical_fraud_analysis.md](statistical_fraud_analysis.md),
output — `analysis/<referendum>/` and `analysis/cross/`. The full cycle in one
command:

```bash
../analysis-tool/run_forensics_slovenia.sh
# or step by step:
cd ../analysis-tool && uv sync
uv run python ../sloveniya-referendum-2026/scripts/build_ef_csv.py     # adaptation + validation
uv run ef-analyze --data ../sloveniya-referendum-2026/data/ef/preiskava \
  --out ../sloveniya-referendum-2026/analysis/preiskava \
  --title "Slovenia, ZPPre-B referendum 11.10.2026 (precincts)" \
  --controls ../sloveniya-referendum-2026/data/ef/socialna_pomoc,../sloveniya-referendum-2026/data/ef/volilna_pravica,../sloveniya-referendum-2026/data/ef/rtv_prispevek
uv run python ../sloveniya-referendum-2026/scripts/analyze_extra.py    # cross-checks
```

The control elections for the Shpilkin method — the other three referendums (same
precincts, same turnout distribution). Early-voting points (numbers ≥ 900, `upr` = 0)
are not part of the turnout pipeline: `analyze_extra.py` checks them (digit tests).

## Development

```bash
uv run pytest        # tests
uv run ruff check .  # linter
uv lock --upgrade    # upgrade dependencies
PYTHONPATH=src uv run python scripts/build_volisca_csv.py  # combined per-precinct CSV + cross-check
```
