# Intraday trend capture — Bulgaria, president 25.10.2026 (BG-pvr202610)

Normalized captures of results.cik.bg — the same portal `../../scrape_cik.py`
polls every 15 min. Extracted from `election-data-2026-10.zip` (repo root).

- `national.csv`, `results.csv` — **10 snapshots** (results pages), 25.10.2026
  22:07 UTC through 26.10.2026 07:03 UTC. Count progress is measured in СИК
  (section protocols received), not precincts; the first snapshot has empty
  totals — the portal had no numbers yet.
- `intraday_turnout.csv` — the official **intraday turnout page**
  (`/pvr202610/aktivnost/`): official times 11:00 and 16:00 EET, country row
  from the page itself + 31 MIR rows from the site's mapData, captured at 22
  fetch times (values repeat between refreshes — dedupe on
  `area × as_of_local`).

Common key columns: `fetch_ts_utc` (UTC capture time), `source_ts`, `election`,
`race` (= president). `results.csv` grain: fetch × area (`country` / `mir`) ×
candidate pair, columns `votes`, `pct` (of protocols received).

## State at last snapshot (2026-10-26 07:03 UTC, 98.99% protocols)

Йотова 34.70%, Гюров 31.98%, Костадинов 12.57% — no one above 50%, runoff
pending.

## Quick start

```python
import pandas as pd
tu = pd.read_csv("intraday_turnout.csv")
tu[(tu.area_level == "country")].drop_duplicates("as_of_local")  # official hourly turnout
```
