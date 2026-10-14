# Elections to the National Assembly of Serbia — 25 October 2026

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

The campaign **is already registered in the RIK API**: round `680072` "Парламентарни 2026" (Parliamentary 2026) — no results yet, which is expected with voting on 25 Oct.

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

## 3. Scripts (stdlib Python 3 only, no dependencies)

| File | Purpose |
|---|---|
| `scripts/rik_api.py` | API client: requests, number/date parsing, normalization |
| `scripts/scrape_rik.py` | scraper: raw-JSON snapshots + CSV timelines, `--loop` mode |
| `scripts/latest_summary.py` | summary: current standings, Δ from the previous snapshot (`--html` → md) |
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
