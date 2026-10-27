# Slovakia, municipal (OSO) and regional (OSK) elections 24.10.2026 — data

## Official definitive exports (`data/official/`, ~113 MB, gitignored)

Downloaded 26.10.2026 from the official portals (the 2026 joint elections live
on the new **volbysr.sk** portal, the 2022 ones on **volby.statistics.sk**):

| File | Content |
|---|---|
| `OSK2026_SK_csv.zip` | definitive results, governors + councils, per okrsok |
| `OSO2026_SK_csv.zip` | definitive results, mayors + councils, per okrsok ('x' tables = Bratislava/Košice primátor races) |
| `OSK2022_SK_csv.zip` | the 22.10.2022 control election (same tables) |
| `OSO2022_SK_csv.zip` | the 22.10.2022 control election |

Key tables (separator/encoding differ between years: 2026 = comma-quoted
UTF-8 with long Slovak headers; 2022 = pipe-separated UTF-8 with short
codes; 2022 party codes are zero-padded and '001' = independent):

- turnout per precinct: OSK `tab02d`/`tab02bd` (P_ZAP registered, P_ZUC
  participants, P_OO envelopes, P_HL_PRE/P_HL_POS valid ballots per race);
  OSO `tab02f`/`tab02bf` (… P_HL_STA valid mayor ballots)
- votes per candidate per precinct: governors `tab06d` (+ `tab0a` candidates,
  `tab0c` parties), mayors `tab05f` (+ `tab0ad`)
- mayors elected: OSO 2026 `tab05d` (marker in `Poznámka`; 2022 has no
  obec-level table — aggregate `tab05f`)
- precinct keys: OSK `OBEC-OKRSOK` unique nationally in both years (6,029 in
  2026 / 6,010 in 2022, 96.5–99.5% match per kraj); OSO needs the
  intra-municipal district in the key (`OBEC-VOB-OKRSOK`; in 2022 Košice
  re-used numbers across city districts — 19 rows dropped, and it renumbered
  for 2026 → 90.3% match)

## Analysis-tool adaptation (`data/ef/`)

`scripts/build_ef_csv.py` → MAI-format CSVs (`results_freguesias.csv`),
validation log `data/ef/VALIDATION.txt` (precinct sums = official tables =
election-night capture, to the exact vote):

- `osk2026_k1..k8/` + `osk2022_k1..k8/` — one column per governor candidate,
  per kraj; `voted` = valid governor ballots (P_HL_PRE), `null` = envelopes −
  valid (participants who skipped the race land there; 9.6% in 2026)
- `oso2026/` (incl. `results_all_previous.csv` = 2022) + `oso2022/` —
  mayor candidates aggregated by lead party (first subject of the coalition;
  empty = NEKA) + residual `INÉ`; BA/KE primátor races excluded (separate
  'x' tables; their totals are cross-checked in the validation log)

Reproduce: download the four zips into `data/official/`, then
`analysis-tool/run_forensics_slovakia.sh`.

---

## Intraday trend capture

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
