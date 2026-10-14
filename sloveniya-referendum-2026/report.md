# Slovenia: four nationwide referendums — 11 October 2026

**TL;DR.** On Sunday 11.10.2026 Slovenia holds **four referendums simultaneously**: one legislative (on bringing into force amendments to the parliamentary investigation act) and three advisory ones (social assistance, voting rights of foreigners in local elections, abolishing the RTV Slovenija fee). Voting at precincts — 7:00–19:00, preliminary results — **after ~20:00** on the `volitve.dvk-rs.si` portal. DVK publishes machine-readable data (JSON/CSV/XLSX), 8 files per referendum + 88 per-precinct files — a uv project (`uv run sloref fetch --loop`) downloads them every 15 minutes and stores them in `data/`; the trend base is already collected.

---

## 1. What is on the ballot

The National Assembly (Državni zbor) issued on 23 July 2026 the decree on the legislative referendum on ZPPre-B, and on 28 August 2026 three decrees on advisory referendums. All four take place on the same day, each with its own ballot; the voter circles «ZA» (yes) or «PROTI» (no).

1. **Legislative referendum on the Act Amending and Supplementing the Parliamentary Investigation Act (ZPPre-B)** — «Do you consent that the act amending and supplementing the Parliamentary Investigation Act (ZPPre-B), adopted by the National Assembly on 26 May 2026, enters into force?»
2. **Advisory: social assistance** — «Do you consent that the right to monetary social assistance for able-bodied persons without objective obstacles to work is made conditional on their active performance of socially useful work?»
3. **Advisory: voting rights in local elections** — «Do you consent that only citizens of Slovenia or other EU countries — and not citizens of third countries — have the right to vote in local elections in the Republic of Slovenia?»
4. **Advisory: RTV Slovenija** — «Do you consent that the mandatory payment of the Radiotelevizija Slovenija contribution is abolished?»

Advisory referendums have no quorum and their outcome is not legally binding. For the legislative referendum the rule of Art. 90 of the Constitution applies: the act is **rejected** if a majority of valid votes votes «no» **and** at least 1/5 of all voters votes «no» (otherwise the act enters into force).

## 2. How the voting works

- **Day and hours:** Sunday 11.10.2026, precincts open **7:00–19:00**.
- **Who votes:** citizens of Slovenia with active voting rights; voting at the place of permanent residence, upon presenting an identity document.
- **Abroad:** 30 precincts in diplomatic missions (Klagenfurt, Cleveland, Munich, Toronto, Trieste, embassies, etc.) plus voting by post; applications for special forms of voting were accepted until 25.09.2026 through the eUprava portal.
- **Early voting** took place at special precincts; accessible precincts and OMNIA-type precincts are available for people with disabilities.
- **Info line:** 080 28 18 (free of charge, 28.09–11.10, on election day 7:00–19:00).
- **Territorial structure of the count:** 8 electoral units (volilna enota), each with up to 11 districts (okraj), and inside them — precincts (volišče); votes from abroad, by post and at special precincts are counted separately, so district sums may not add up to the national result (DVK officially warns about this).

## 3. Data publication schedule for 11 October (per the official DVK documentation)

| Time | What is published |
|---|---|
| ~11:00 and ~16:00 | turnout — **only** for the legislative referendum |
| 19:00 | turnout for all four referendums |
| after ~20:00 | preliminary results, then periodic updates until the final (the `is_final` flag in the per-precinct files) |

Before the data appears, the `udelezba.json`/`rezultati.json` files contain only the `datum` field — that is how it should be.

## 4. Where to follow online

- **Results portal (official, with charts):** [volitve.dvk-rs.si/referendum-preiskava](https://volitve.dvk-rs.si/referendum-preiskava), […/referendum-socialna-pomoc](https://volitve.dvk-rs.si/referendum-socialna-pomoc), […/referendum-volilna-pravica-tujcev](https://volitve.dvk-rs.si/referendum-volilna-pravica-tujcev), […/referendum-rtv-prispevek](https://volitve.dvk-rs.si/referendum-rtv-prispevek)
- **State Electoral Commission (DVK):** [dvk-rs.si](https://www.dvk-rs.si/) — acts, news, referendum pages (the «Volitve in referendumi → Referendumi» section).
- **volitve.gov.si** — the traditional portal of detailed results (election archives in subfolders `/dz2014/`, `/ep2014/`, etc.). As of 10.10.2026 it serves a «content unavailable» placeholder — probably being updated before the vote; worth checking on election day.
- **Open data:** [data.gov.si](https://data.gov.si/) — 188 datasets for the query «volitve» (precinct lists, presidential, EP elections, etc.).
- Media for a real-time picture: RTV Slovenija (rtvslo.si), STA (sta.si), 24ur.com — they read the same DVK files.

## 5. Machine-readable data (what we scrape)

For each of the 4 referendums (slug: `referendum-preiskava`, `referendum-socialna-pomoc`, `referendum-volilna-pravica-tujcev`, `referendum-rtv-prispevek`) at `https://volitve.dvk-rs.si/<slug>/data/<file>`:

| File | Contents |
|---|---|
| `udelezba.json` / `udelezba.csv` | turnout: registered, voted, % — by country, 8 units, 88 districts, OMNIA special precincts |
| `rezultati.json` / `rezultati.csv` | results: ZA/PROTI (votes and shares), ballots/valid/invalid, over the same hierarchy |
| `izvoz.xlsx` | summary Excel (sheets «Podatki» and «Podatki po voliščih») |
| `volisca_01_01.json … volisca_08_11.json` | results **per precinct** (88 files per referendum), status in the `nastavitve` object (`has_udelezba`, `has_rezultat`, `is_final`) |

Format nuances: percentages are fractions (0.4825); the share of counted ballots = `rezultati.glas / udelezba.slovenija.gl`; timestamps are Slovenian local time in Zulu form (`2026-10-11T19:00:00Z` = 19:00 CET); CSV — `;` separator, decimal comma, first line — `dd;mm;yyyy;hh;nn`. Official field description: [docs/Referendumi_2026_-_datoteke_s_podatki.docx](docs/Referendumi_2026_-_datoteke_s_podatki.docx) (a copy of the DVK instruction for media of 14.09.2026).

## 6. Data of past Slovenian elections

- **DVK referendum archive:** [dvk-rs.si → Referendumi](https://www.dvk-rs.si/volitve-in-referendumi/referendumi/) and «Arhiv referendumov». The page of each past vote has the same `rezultati.json/csv`:
  - legislative 2025: ZPPKŽ, ZDPID;
  - advisory 09.06.2024: euthanasia, preferential voting, cannabis;
  - referendums 2022: on the government, on long-term care, on RTV;
  - ZV-1G 2021 (water act), the repeated vote on ZIUGDT 2018.
- **volitve.gov.si archives** — detailed results of parliamentary (2000–2022), presidential, EP and local elections in subfolders; the site is currently «unavailable», old versions accessible via the Wayback Machine (web.archive.org).
- **data.gov.si** — open data: precinct lists, presidential/EP election results, historical series (ADP).
- An example of the file structure of past years: `data/latest` at the start contained a DVK template with the results of the 2022 RTV referendum (`slovenija` → ZA 13.25% / PROTI 86.75%).

## 7. The data collection project (uv)

A standard uv project: the `src/sloref` package, HTTP client — **httpx2** (the next-gen successor of httpx, same author), **pandas** and **matplotlib** connected for analysis right away, tests — pytest, linter — ruff.

```bash
uv sync                              # install dependencies (.venv, uv.lock)
uv run sloref fetch                  # one poll: 4 referendums × 5 files
uv run sloref fetch --loop           # endless loop, interval 900 s (15 minutes)
uv run sloref fetch --loop --volisca --interval 300   # + precincts, own interval
uv run sloref summary                # summary table of the current figures (pandas)
uv run sloref plot                   # PNG trend plots → data/plots/
```

Modules: `config.py` (referendums/URLs/paths), `httpclient.py` (httpx2: retries, 404 = «no data yet», IPv4-only), `models.py` (nationwide figures from the JSON), `storage.py` (latest/raw snapshots, timeseries.csv, log), `scraper.py` (poll/loop), `analysis.py` (pandas), `plotting.py` (matplotlib), `cli.py`. Tests — `uv run pytest`, linter — `uv run ruff check .`.

What is stored in `data/`:

- `latest/<referendum>/` — latest versions of the files;
- `raw/<date>/<time>/<referendum>/` — snapshots of **only changed** files (by SHA-256), so the update history is kept without duplicates;
- `timeseries.csv` — trend points: a row is appended when the nationwide figures change (the server's `source_datum` stamp, turnout, counted %, ZA/PROTI with shares);
- `plots/<referendum>.png` — trend plots (`sloref plot`);
- `scrape.log` — the log.

The first poll was run on 10.10.2026: all 20 files available, the server returns a zeroed-out structure (waiting for the election-day data).

**To have the data collected automatically:** keep `uv run sloref fetch --loop` running (or via `nohup … &`, cron/launchd — examples in [README.md](README.md)). If ZCode itself should run the collection every 15 minutes — that is configured as a separate automation.

---

## 8. Referendum results and the final data (added 13.10.2026)

During election day the collection loop was not running (local data — only the
empty structures of 10.10), so on 13.10.2026 a full poll `uv run sloref fetch
--volisca` was run: **all 93 files × 4 referendums without errors**, including
88 per-precinct files per referendum. The server stamp —
2026-10-12T18:00:00Z, 99.98% counted, `is_final=false` (the review of votes
cast abroad — 19.10, after which DVK will declare the results final).

### Final figures (DVK, cross-checked with [Wikipedia](https://en.wikipedia.org/wiki/2026_Slovenian_referendum) to the vote)

| Referendum | ZA | PROTI | Invalid | Outcome |
|---|---|---|---|---|
| preiskava (ZPPre-B, legislative) | 449,297 (48.74%) | **472,444 (51.26%)** | 5,191 | act **rejected**, the 1/5 quorum met (472,444 ≫ 339,473) |
| socialna_pomoc | **559,082 (60.54%)** | 364,377 (39.46%) | 3,408 | approved |
| volilna_pravica | **510,484 (55.30%)** | 412,708 (44.70%) | 3,667 | approved |
| rtv_prispevek | 461,753 (49.97%) | **462,299 (50.03%)** | 2,913 | rejected, a margin of **546 votes** |

Turnout — 54.62% (927,066–927,151 voters per ballot out of 1,697,366
registered); intermediate points: 14.2% by 11:00, 35.53%
(603,057) by 16:00.

### Per-precinct data

- `data/latest/<referendum>/volisca_01_01.json … volisca_08_11.json` — results
  of the **3,083 regular precincts** (8 units × 11 districts), each with turnout
  (registered/voted/%), ballots/valid/invalid,
  ZA/PROTI with shares, counted share 1.0.
- `data/derived/volisca_all.csv` — everything in one CSV (12,332 rows),
  assembled by the `scripts/build_volisca_csv.py` script; it also verifies
  the arithmetic: at **all** precincts `ZA+PROTI = valid`,
  `valid+invalid = total` — agrees to the vote.
- Decomposition of the national result: precincts 918,566–918,594 + special
  voting at the district level ~1,224 (post, diplomatic missions, mobile
  commissions) + OMNIA precincts ~7,142–7,190, whose results DVK includes only
  in the national sum (that is why district sums need not agree — this is
  official, the «Pozor!» note in the DVK documentation).

### Dynamics of election day and the counting night

The scraper's time series was not running on election day, and the web archives
of the DVK files preserved nothing; reconstruction from the media (RTV SLO, STA, 24ur, Dnevnik, Svet24,
Siol) — [data/wikipedia/counting_night_dynamics.md](data/wikipedia/counting_night_dynamics.md).
In short: after the first fifth of the ballots «ZA» led on all
four questions (preiskava up to ~53% «ZA»), then both contested questions
flipped as the rural districts were counted; the RTV fee was «for abolition»
with ~99% counted (50.13–50.15%) and finally fell with a margin of 546
votes. Ballots by post from Slovenia (counted 12.10) did not change the results.

### Wikipedia

- `data/wikipedia/2026_Slovenian_referendum.wikitext` — the source wikitext;
- `data/wikipedia/results_wikipedia_and_dvk_crosscheck.md` — the article's table and
  the per-vote cross-check with DVK: **an exact match** on all four
  referendums (ZA, PROTI, invalid, total).
