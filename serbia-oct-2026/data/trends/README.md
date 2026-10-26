# Intraday trend capture — Serbia, National Assembly 25.10.2026 (RS-680072)

**11 snapshots** of the RIK results portal, roughly hourly: 25.10.2026 21:04 UTC
(23:04 local, first numbers) through 26.10.2026 07:04 UTC. Extracted from
`election-data-2026-10.zip` (repo root); normalized counterpart to the raw JSON
snapshots in `../raw/` and the timeline in `../timeline/`.

## Files

Common key columns: `fetch_ts_utc` (UTC capture time), `source_ts` (RIK's own
timestamp), `election`, `race` (= parliament).

| File | Grain | Other columns |
|---|---|---|
| `national.csv` | fetch | `registered, voters, turnout_pct, votes_total/valid/blank/invalid, units_total, units_counted, pct_counted, units_label` (units = birackih mesta) |
| `regions.csv` | fetch × region | same turnout/count columns; regions + Заводи за извршење кривичних санкција (prisons, area_code 100), in Cyrillic |
| `results.csv` | fetch × area × electoral list | `votes`, `pct`; `area_level` = country / region |

## State at last snapshot (2026-10-26 07:04 UTC)

96.25% of polling stations counted, turnout 68.78%. Among counted votes:
СТУДЕНТСКА ЛИСТА 53.22%, Вучић's УЈЕДИЊЕНА СРБИЈА 39.81%, Дачић 2.21%.

## Quick start

```python
import pandas as pd
res = pd.read_csv("results.csv", parse_dates=["fetch_ts_utc"])
# list trend by snapshot
res[res.area_level == "country"].pivot(index="fetch_ts_utc", columns="candidate_id", values="pct")
```
