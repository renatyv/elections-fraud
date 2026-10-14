# Bulgaria: presidential election of 25 Oct 2026 — open data and scraping

Date confirmed by the CEC: "Избори за президент и вицепрезидент — 25 октомври 2026"
(Elections for President and Vice President — 25 October 2026).
If nobody wins an absolute majority — a second round on **8 November 2026**.
Presidential election only (the early parliamentary election took place on 19 Apr 2026).

## Where the data lives (verified 10 Oct 2026)

| Source | URL | Contents |
|---|---|---|
| CEC election hub | `https://www.cik.bg/bg/pvr2026` | timeline, decisions, FAQ |
| Candidate register | `…/pvr2026/registers/per_candidates` | president+vice-president pairs, 18+ registered (Siderov, Mihaylov/«Величие», Rasate, etc.; the major parties are at the end of the list) |
| **Results portal** | `https://results.cik.bg/` | the primary source of interim results |
| 2026 election portal | will appear as `results.cik.bg/<code>/` (by analogy: `pvrns2021`, `pe202604`) | not yet published as of 10 Oct; the script will find it on its own |
| Turnout/results map | `https://map.cik.bg/<code>/` | interactive map (same data) |

Portal structure (based on the 2016/2021/2024/2026-04 elections): `{round}/rezultati/` — results,
`{round}/aktivnost/` — turnout, `{round}/machine/data.js` — index of machine protocols by section,
`{round}/protokoli/…` and `opendata/export.zip` (";"-separated txt), `opendata/spreadsheet.zip` (xlsx) — published toward the end of processing. Rounds: `tur1/`, `tur2/`.

## How interim results are updated

- Pages are **static HTML, regenerated** as protocols are processed; updates run all night (in April 2026 the first publication was ~21:40, then every few tens of minutes).
- On the page: a status line "Данни към ЧЧ:ММ на ДД.ММ.ГГГГ при обработени **X%** СИК протоколи в РИК" (data as of HH:MM on DD.MM.YYYY with **X%** of district commission protocols processed) + a table "№ / Кандидатска двойка / Гласове / Разпределение" (No. / Candidate pair / Votes / Share) + protocol metrics (voters, voted, valid/invalid).
- Intraday turnout: reports at **11:00, 16:00 and 20:00**.
- `machine/data.js` (a JS index, served without Cloudflare) changes more often than the HTML — it works well as an update detector.
- Limitation: the CEC sites sit behind Cloudflare with an intermittent managed challenge (HTML/zip may return 403 to non-browsers, `*.js` is almost always accessible). The script uses a `requests → curl_cffi (impersonate chrome) → cloudscraper` cascade with retries.

## Scripts

- `scrape_cik.py` — the scraper: auto-detects the 2026 portal in the index, polls `tur1`/`tur2` (results, turnout, machine protocols), raw snapshots + CSV timelines.
- `run_every_15min.sh` — a cron wrapper; `requirements.txt` — dependencies (`pip install -r requirements.txt`, venv already in `.venv/`).

```bash
# loop with a 15-minute interval (default):
.venv/bin/python scrape_cik.py --loop
# one-shot run (for cron):
.venv/bin/python scrape_cik.py --once
# test against the 2021 election (both rounds):
.venv/bin/python scrape_cik.py --once --base https://results.cik.bg/pvrns2021/
```

Output in `data/`: `raw/<timestamp>/` (HTML/JS as-is), `results_timeline.csv` (votes/shares per pair over time), `turnout_timeline.csv`, `stats_timeline.csv`, `machine_sections_timeline.csv`, `state.json` (portal address, VERSION hashes for "unchanged" detection), log in `scrape.log`.

**Verified 10 Oct 2026** against the live site: 2021 round 1 — Radev 49.42%, Gerdzhikov 22.83%; round 2 — 66.72% / 31.80%; turnout 40.23% / 34.84% — everything matched the official results; the flat layout (pe202604) parses too.

## Checklist for 25 Oct 2026

1. Start `scrape_cik.py --loop` in advance (e.g., in the morning) — it will find the portal itself once it appears in the index and start recording the 11:00/16:00/20:00 turnout reports.
2. First results — expected after 21:00–21:45; watch the "обработени X%" (X% processed) line.
3. Final machine-readable data — `opendata/export.zip` (txt) and `spreadsheet.zip`; download manually once processing reaches 100% (the script does not fetch the zip files because of Cloudflare).
4. If Cloudflare is tightened on election night — on 403, keep `results.cik.bg` open in a browser and raise the interval if needed (`--interval 300` or more); as a last resort — FlareSolverr/Playwright.
