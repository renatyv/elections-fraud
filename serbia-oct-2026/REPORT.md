# Elections to the National Assembly of Serbia — 25 October 2026

**Latest analysis:** [trends](analysis/trends/README.md),
[statistical forensics](REPORT_statistical_fraud_analysis.md), and
[voting paradoxes](PARADOXES.md), updated 26 October 2026.

**Report:** open data sources + scripts that poll interim results every 15 minutes.
Prepared 10 Oct 2026. The scripts were validated against real 2023 election data (RIK round 341140) — the numbers match the official outcome.

## 1. Open data sources

| Source | What it provides | Format | When available |
|---|---|---|---|
| **RIK — JSON API of the results portal** `rik.parlament.gov.rs` | **Interim results on election night**: country / 7 regions / ~180 municipalities / 8,273 polling stations; turnout, processed stations, votes and % per list | JSON (POST) | from the close of polls ~20:00 on 25 Oct until the final count |
| RIK — same API, polling-station level | Links to **station PDF protocols** (Form RG-2, RG-11) with upload date | JSON → PDF | as protocols are entered |
| RIK — news feed `rik.parlament.gov.rs/rss/` | Decisions, announcements, final acts | RSS | continuous |
| CeSID + Ipsos `cesid.rs/u-fokusu/rezultati-izbora/` | Statistical **projections** of results and turnout (not machine-readable — articles) | HTML | election evening |
| Statistical Office `stat.gov.rs` → "Izbori", database `data.stat.gov.rs` | Final official statistics | DB/files | after the results are announced |
| RIK — "Анализа тренутно проглашених листа" (analysis of currently proclaimed lists), complaints register | Lists of admitted parties, complaints | HTML | before the election |

The campaign **is already registered in the RIK API**: round `680072` "Парламентарни 2026" (Parliamentary 2026) — this was the setup status on 10 October; captured results are analysed below.

## 2. RIK API (reverse-engineered from the official portal frontend)

All requests are POST with the header `X-Requested-With: XMLHttpRequest`:

- `/get-elections/` `{election_type: 2}` → rounds: `{"680072": "Парламентарни 2026"}`
- `/get-regions/` `{election_type, election_round}` → regions (+ NUTS2 codes)
- `/get-municipalities/` `{..., election_region}` → HTML `<option>` list of municipalities
- `/get-election-stations/` `{..., election_municipality}` → polling stations
- `/get_results/` `{type=2, election_round, region, municipality, election_station}` → response:

```
stat_sum_numbers: total_voters, available (votes cast), processed_stations,
                  number_of_stations, datetime (RIK data timestamp), election_title
table_data:       [{list_name, won_number, won_percent}, ...]
sum_config:       pie-chart data → valid/invalid ballots
```

Quirks: dot-grouped numbers ("3.820.746"), Cyrillic script, `datetime` serves as the update stamp (used for deduplication), the `available` field = number of voters who voted.

## 3. Scripts (capture uses stdlib; analysis uses analysis-tool dependencies)

| File | Purpose |
|---|---|
| `scripts/rik_api.py` | API client: requests, number/date parsing, normalization |
| `scripts/scrape_rik.py` | scraper: raw-JSON snapshots + CSV timelines, `--loop` mode |
| `scripts/capture_stations.py` | polling-station-level capture into a wide CSV (resume-safe; used for the 2026 election and the 2023 control) |
| `scripts/latest_summary.py` | summary: current standings, Δ from the previous snapshot (`--html` → md) |
| `scripts/dump_municipality_index.py` | preserves the municipality index (official unit codes + names) of a round as JSON |
| `scripts/build_ef_csv.py` | builds the forensics (MAI-format) CSVs at municipality/station grain, 2026 + 2023 control → `data/ef/` |
| `scripts/analyze_trends.py` | count-night trend charts + metrics → `analysis/trends/` |
| `scripts/analyze_diagnostics.py` | matched station comparison, ballot accounting gaps and incumbent-focused tests → `analysis/diagnostics/` |
| `scripts/analyze_paradoxes.py` | voting-paradox analysis → `PARADOXES.md` outputs in `analysis/paradoxes/` |
| `scripts/run_scraper.sh` | wrapper for cron (single pass) |
| `scripts/com.user.serbia-rik-scraper.plist` | macOS LaunchAgent running every 15 minutes |

**Running (every 15 minutes):**

```bash
# option A — built-in loop
python3 scripts/scrape_rik.py --loop --interval 900

# option B — cron
*/15 * * * * "<path>/scripts/run_scraper.sh" >> "<path>/data/cron.log" 2>&1

# option C — macOS launchd
cp scripts/com.user.serbia-rik-scraper.plist ~/Library/LaunchAgents/ && \
launchctl load ~/Library/LaunchAgents/com.user.serbia-rik-scraper.plist
```

Levels: default `--levels national,regions`; add municipalities with `--levels national,regions,municipalities` (~180 requests per pass). End-of-day summary: `python3 scripts/latest_summary.py --html`.

**Data:** `data/raw/<round>/<date_time>/*.json` (raw responses), `data/timeline/<round>/snapshots_national.csv` (turnout/stations per snapshot), `results_long.csv` (list votes across all levels). A snapshot is written only when the RIK `datetime` stamp changes — there will be no empty duplicates. `data/` already contains a validation sample for round 341140 (2023 election).

## 4. Notes

- The API is not officially documented — it is the internal protocol of the RIK results portal; the format is stable (unchanged since 2020), but it is worth running a test pass before election night.
- RIK has no robots.txt; a 15-minute interval with pauses between requests is a deliberately polite load.
- Timestamps in the data are local Serbian time (CET/CEST). The electoral threshold for lists is 3%. 250 mandates; the country is a single constituency.
- For history/archiving: RIK's final Excel exports traditionally appear in the "Документа" (Documents) section after the results are announced; RG-2 protocols are available per polling station via the API.

## 5. Findings, updated 26 October 2026

The latest independent RIK API check has source stamp **21:15 CET**, captured
at 20:19 UTC: **8,191/8,392 stations (97.60%)**, 4,248,886 valid ballots,
Students **52.71%**, Vučić's list **39.17%**, SPS **2.17%** on the portal's
displayed denominator. Turnout is **68.83% of the covered register**;
abroad remains 8/93 processed. Raw check:
`data/checks/680072/20261026_201923/`.

- **Trends:** Vučić led the initial 9.38%-counted sample by 6.13 points;
  Students first lead between the 23:07 and 00:08 CET captures
  (25.45–41.35% counted). The margin reaches 13.62 points at 16:55 and
  narrows to 13.54 at 21:15. The full series is not monotonic.
- **Forensics:** the separate reconciled 16:55 snapshot covers 8,124
  territorial stations and 189 municipalities. The completed 2023 control
  covers all 8,273 stations (8,163 territorial), with exact per-list
  reconciliation at both grains. No convergent statistical evidence of
  large-scale stuffing is established; mixture/digit signals and a
  **2,650-voter ballot-accounting gap** remain documented for investigation.
- **Historical comparison:** 7,935 matched station keys show turnout
  58.63 → 68.83% and incumbent valid share 47.92 → 39.83%. Keys alone do
  not establish unchanged boundaries or identify voter transfers.
- **Electoral rules:** at the 16:55 snapshot, the corrected legal model
  projects **140 Students, 104 Vučić, six minority seats**. It includes
  the 35% minority quotient bonus and all nine exempt lists. Students'
  majority survives all tested allocation alternatives. These are
  projections, not final official mandates.

Read the [trend report](analysis/trends/README.md),
[full forensic report](REPORT_statistical_fraud_analysis.md), and
[paradox analysis](PARADOXES.md) for methods, figures and limitations.

## 6. Reproduce the analysis

From the repository root:

```bash
zsh analysis-tool/run_forensics_serbia.sh
```

This rebuilds adapted data, six trend charts, paradox tables/figures, five
forensic runs, and incumbent/matched-station diagnostics, then runs tests.
It does not fetch live data or change scraper scheduling. Keep the local
source data (gitignored) for reproducibility. The completed 2023 station
archive is `data/timeline/341140/stations_complete.csv`; the original
resume-safe capture is retained separately.
