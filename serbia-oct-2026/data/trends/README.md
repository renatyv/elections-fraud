# Intraday trend capture — Serbia, National Assembly 25.10.2026

**14 snapshots**, 25 October 21:04:02 UTC (22:04 CET) through
26 October 20:19:23 UTC (21:19 CET); latest RIK source stamp **21:15 CET**.
The first 11 captures come from the archived election-night export; later
ones are parsed from `../raw/680072/` and `../checks/680072/` by
`scripts/analyze_trends.py`. Capture time and official source time differ.
Serbia was on CET (UTC+1) during this election night.

| File | Grain |
|---|---|
| `national.csv` | Capture: register, voters, turnout, valid/invalid ballots, station coverage |
| `regions.csv` | Capture × region, including prisons (100) and abroad (101) |
| `results.csv` | Capture × country/region × list: absolute votes and displayed percentage |

Keys: `fetch_ts_utc`, `source_ts`, `election`, `race`, plus `area_level`,
`area_code` and `candidate_id` where applicable. Turnout uses the register of
processed stations; displayed list percentages use valid + invalid ballots.
`voters` can exceed `votes_valid + votes_invalid`; retain that accounting gap.

At the latest check 8,191/8,392 stations are counted, turnout is 68.83%,
Students 52.71%, Vučić 39.17%. See the
[trend report](../../analysis/trends/README.md) for findings and limitations.
The forensics use the separately reconciled 16:55 CET station snapshot.
