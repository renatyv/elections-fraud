# Slovakia, municipal (OSO) and regional (OSK) elections 24.10.2026 — intraday trend capture

Longitudinal capture of the count from the official ŠÚSR results portal
(statistics.sk, projects OSK/OSO). **36 snapshots** taken 24.10.2026 20:02 UTC
(22:02 SELČ, right after polls closed) through 26.10.2026 07:51 UTC.
Extracted from `election-data-2026-10.zip` (repo root); the scraper itself is
not in this repo — the CSVs here are the normalized capture.

## Races

| Race | Election id | Areas with candidate rows | Units |
|---|---|---|---|
| regional governor (predseda OSK) | SK-2026-OSK | all 8 samosprávne kraje | 6,029 okrsky (precincts) |
| mayor (starosta/primátor OSO) | SK-2026-OSO | 8 regional capitals only: Bratislava, Košice, Prešov, Žilina, Banská Bystrica, Nitra, Trnava, Trenčín | 2,921 obce (municipal returns) |

National count progress (`national.csv`) covers both races in full; per-area
rows are complete for the kraje but only the 8 capitals for mayors.

## Files (`data/trends/`)

Plain UTF-8 CSV, one row per snapshot. Common key columns: `fetch_ts_utc`
(UTC capture time), `source_ts` (timestamp shown by the portal, SELČ),
`election`, `race`.

| File | Grain | Other columns |
|---|---|---|
| `national.csv` | fetch × race | `registered, voters, turnout_pct, votes_total, votes_valid, votes_blank, votes_invalid, units_total, units_counted, pct_counted, units_label` |
| `regions.csv` | fetch × race × area (`area_level`: kraj / obec, `area_code`, `area_name`) | `registered, voters, turnout_pct, units_total, units_counted, pct_counted` |
| `results.csv` | fetch × race × area × candidate (`candidate_id`, `candidate`, `party`) | `votes`, `pct` |

## Final state (last snapshot, 2026-10-26 07:51 UTC, 100% counted)

Turnout: OSK 46.56%, OSO 48.48%. Regional governors (predseda):

| Kraj | Winner | % |
|---|---|---|
| Bratislavský | Juraj Droba | 70.96 |
| Košický | Rastislav Trnka | 32.00 |
| Prešovský | Milan Majerský | 48.77 |
| Žilinský | Erika Jurinová | 52.06 |
| Banskobystrický | Ondrej Lunter | 64.81 |
| Nitriansky | Branislav Becík | 50.47 |
| Trnavský | Jozef Viskupič | 54.04 |
| Trenčiansky | Jaroslav Baška | 57.44 |

(Košický and Prešovský below 50% — check `results.csv` for whether these were
two-round races or simple plurality.)

## Charts (`analysis/trends/charts/`)

`slovakia_overview.png`, `slovakia_regional_governor_predseda_1..8.png`
(kraj codes 1–8), `slovakia_mayor_starosta_prim_tor_<LAU code>.png` for the
8 capitals (582000 Bratislava, 599981 Košice, 524930 Prešov, 517402 Žilina,
508438 Banská Bystrica, 500011 Nitra, 506745 Trnava, 505820 Trenčín).

## Quick start

```python
import pandas as pd
nat = pd.read_csv("data/trends/national.csv", parse_dates=["fetch_ts_utc"])
res = pd.read_csv("data/trends/results.csv", parse_dates=["fetch_ts_utc"])
# count-progress curve per race
nat.pivot_table(index="pct_counted", columns="race", values="turnout_pct")
```
