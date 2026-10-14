# Portugal's 2025 Parliamentary Elections: Open Data

**Election:** snap elections to the Assembly of the Republic (Assembleia da República), **18 May 2025** — the most recent parliamentary elections as of now (the next ones no earlier than 2028; the presidential election was in January 2026).

## TL;DR — what is open and downloaded

| Level of detail | Are official data available? | Where |
|---|---|---|
| Country / districts (círculos, 22) | ✅ XLSX/ODS + PDF | CNE |
| Municipalities (concelhos, 308) | ✅ JSON | MAI results portal |
| Parishes (freguesias, **3092**) | ✅ JSON — **the most detailed official level** | MAI results portal |
| Abroad: countries and consulates | ✅ JSON (Europe / outside Europe) | MAI results portal |
| **Voting sections (secções de votação)** | ⚠️ **not** available centrally, but available from municipalities (PDF "MAPA GLOBAL POR SECÇÃO DE VOTO") | câmara municipal websites — see the section "Section data: where to download" |

At the section level: MAI/SGMAI publishes results only down to the parish — verified on our AR-2025 download (3092 freguesias, the leaves of the tree), on the portal's newest API (presidential 2026: freguesia `final: true`, no children), and on the official SGMAI spreadsheet `AR_2025_Globais.xlsx` (sheets down to Freguesia/Consulado, no sections). Section-level data are public **at the municipality level** — câmaras publish a "MAPA GLOBAL POR SECÇÃO DE VOTO" for each vote; for AR-2025 this was verified on a live example (Alcácer do Sal, downloaded and parsed). Where exactly to download — see the section "Section data (secções): what and where to download" below. Under the law, the count itself is done precisely at the section level — legal basis and LEAR articles: see the section "Legal framework of the vote count" below.

## Sources

### 1. Official MAI/SGMAI results portal (main source)
- Portal: <https://www.eleicoes.mai.gov.pt/> — all elections from 1979 to 2026 (AR, presidential, European, municipal, regional, referendums)
- AR 2025 section: <https://www.eleicoes.mai.gov.pt/legislativas2025/>
- It is an Angular SPA; the data are exposed as open JSON following this scheme:
  - `…/legislativas2025/assets/static/territory-results/territory-results-<KEY>-AR.json` — results for a territory (country/district/municipality/parish, overseas districts and consulates), including `previousResults` (2024 results for comparison)
  - `…/assets/static/territory-children/territory-children-<KEY>.json` — the territory tree
  - `…/assets/static/configurations.json`, `affluences.json` (turnout over time), `results-available.json`
- Territory keys: `GLOBAL-990000` (final result), `LOCAL-500000` (country), `LOCAL-0X0000` (districts), `LOCAL-0XYZ00` (municipalities), `LOCAL-0XYZAB` (parishes), `FOREIGN-8xxxxx/9xxxxx` (Europe / outside Europe → countries → consulates)
- SGMAI publishes **official spreadsheets (XLSX) by year** on the page
  <https://www.sg.mai.gov.pt/pt/AdministracaoEleitoral/Resultadoseleitorais/> —
  AR-2025: [AR_2025_Globais.xlsx](https://www.sg.mai.gov.pt/pt/AdministracaoEleitoral/EleicoesReferendos/AssembleiaRepublica/Documents/AR2025/AR_2025_Globais.xlsx)
  (sheets: Global / Distrito-RA / Concelho / Freguesia / País / Consulado — **down to the freguesia, no sections**);
  the same page has XLS/XLSX files for 1999–2024 and similar sections for the presidential and municipal elections.
  The same file is saved locally: `data/seccoes_test/AR_2025_Globais.xlsx`.
- ⚠️ Newer elections (verified on the 2026 presidential) use a different URL template — numeric ids instead of KEY:
  `…/<slug>/assets/static/territory/children-electionId=61-territoryId=<ID>.json` and
  `…/assets/static/result/territory-electionId=61-territoryId=<ID>-organId=3.json` (freguesia ids are leaves, no sections).
- ⚠️ The CDN (Akamai) aggressively blocks bulk downloads: keep to ≤2–3 requests/sec; on "Access Denied" — pause for 1–2 minutes. The script below accounts for this.

### 2. CNE (National Election Commission) — official results
- AR 2025 results page: <https://www.cne.pt/content/eleicoes-referendos-resultados-oficiais>
- **Excel/ODS by district (the official "mapa"):** <https://www.cne.pt/sites/default/files/dl/eleicoes/2025_ar/docs_geral/2025_ar_mapa_resultados.zip> (xlsx+ods; sheet: 22 districts × parties, inscritos/votantes/brancos/nulos)
- **Official results map (PDF, Diário da República, Mapa Oficial n.º 2-A/2025):** <https://www.cne.pt/sites/default/files/dl/eleicoes/2025_ar/2025_ar_mapa_oficial_dr.pdf>
- Note: the CNE results differ slightly from the MAI portal (the CNE accounts for a correction in the Viana do Castelo district; e.g. AD: 1 971 602 per CNE vs 1 971 558 on the portal).

### 3. dados.gov.pt (government open data)
- Searching for "eleições": only Arquivo.pt web archives and INE turnout series — **the AR 2025 results themselves are not there** (verified via the API `dados.gov.pt/api/1/datasets/?q=…`). The old CKAN portal (before the migration) had "resultados eleitorais" datasets for 1976–2009 — now only in the Wayback Machine.

### 4. Other
- INE (turnout statistics by municipality, long series): <https://dados.gov.pt> → datasets instituto-nacional-de-estatistica
- Arquivo.pt (web archive of the 2025 campaigns): <https://arquivo.pt>

## Legal framework of the vote count (verified against the official texts of the laws)

The basic law is **Lei n.º 14/79, de 16 de maio "Lei Eleitoral para a Assembleia da República" (LEAR)**,
consolidated version dated 23-07-2026 (PDF, 53 pp., downloaded to `data/legislacao/`).
Voter registration — **Lei n.º 13/99** (the old law 13/79 was repealed long ago — a common confusion).

- LEAR, consolidated PDF (CNE): <https://www.cne.pt/sites/default/files/dl/legis_lear_consolidada_2026-07.pdf>
- LEAR, original 1979 text in the Diário da República (ELI link): <https://data.dre.pt/eli/lei/14/1979/05/16/p/dre/pt/html>
- Lei 13/99, consolidated PDF (CNE): <https://www.cne.pt/sites/default/files/dl/legis_13_99_re_2024-02-08.pdf>
- CNE summary page of electoral legislation: <https://www.cne.pt/content/legislacao-eleitoral>

### The counting chain under the law (LEAR articles, quotes translated)

| Step | Article | What it establishes |
|---|---|---|
| Voting sections | Art. 40.º | "Each freguesia corresponds to one assembleia de voto"; when the number of registered voters is **noticeably above ~1000**, it is divided into **secções de voto** (a decision of the municipality) |
| Count at the section | Art. 100.º–102.º | After closing: count of voters against the rolls, opening of the ballot box, recount of ballots; every ballot is **read aloud**; the chairperson performs a cross-check; the results are published immediately as an **edict on the door** of the section (votes for each lista, blank, invalid) |
| Section minutes | Art. 105.º | The **Acta das operações eleitorais** must contain: all inscritos and votantes; votes for each lista; blank; invalid; the numbers of early voters; disagreements in the count |
| Passing upward | Art. 106.º | Within 24 hours the minutes of all sections are passed to the district **assembleia de apuramento geral** |
| District count | Art. 108.º–111.º | The district commission (chaired by a judge, plus 2 lawyers, plus 2 professors of mathematics, plus 6 section chairpersons) consolidates the **section minutes**, reviews contested ballots, allocates seats; the deadline is the 10th day after the election. **There is no freguesia stage in the count here** |
| National map | Art. 115.º | The **CNE** publishes the official map by district in the Diário da República. Our `2025_ar_mapa_oficial_dr.pdf` (Mapa Oficial n.º 2-A/2025 of 31-05-2025) opens verbatim: "Nos termos do artigo 115.º da Lei n.º 14/79… a Comissão Nacional de Eleições faz publicar…" |
| Early voting | Art. 79.º-C-15/16, 87.º | Early voting envelopes (including "mobile" voting 7 days before the election) are delivered to the **section of the voter's registration** and dropped into its ballot box on election day → counted in that section's minutes |
| Abroad | Art. 101.º-A, 106.º-B–J | Votes from abroad are cast mostly by post; envelopes are counted by separate "assembleias de recolha e contagem" **on the 10th day after the election** at SGMAI premises in Portugal, then by the overseas district apuramento geral. Hence the ~10-day wait for the final results |

Corrections to widespread inaccuracies (including in my first version): the threshold for splitting into sections is
**~1000** registered voters (not 1600); the national map is issued by the **CNE** ("CNAP" is an outdated name of
an abolished body); the district body in the current version of the law is the **assembleia de apuramento geral**
(historically called CTAP).

### Empirical cross-check against our data (`results_all.csv`)

- All **20 districts on the national territory: the district total equals the sum of its parishes exactly** (Δ = 0 for
  registered voters, turnout, blank, invalid).
- National total = parishes + overseas districts, votes cast:
  5 965 446 (freguesias) + 255 305 (Europa) + 97 198 (Fora da Europa) = **6 317 949**.
- Conclusion: the portal's freguesia-level data cover 100% of the votes cast within the country, while overseas
  votes do not flow through the freguesias — exactly as the law prescribes (a separate count).

### What this means for the question of sections (secções)

Legally, the minimal unit of the count is the **voting section**: each has a public count, an edict on the door, and
minutes with the full results (Art. 100–105). A "count within freguesias" as a separate procedure does not
exist — the freguesia is merely the geography of a section and the portal's publication level. The state necessarily has
data for every section (district totals are compiled precisely from the section minutes, Art. 106 and
109) — a strong argument when requesting a section-level data export from SGMAI (Lei 26/2016).

## Discussions of "why there are no section data" and access attempts (verified 09.10.2026)

**In short: no public discussions of the "lockdown" or an official explanation were found; instead, a
workaround was found — municipal section-level maps.**

- **Reddit** (r/portugal and neighboring subreddits, search of the pullpush.io archive, phrases "secções de voto",
  "resultados por secção", "dados eleitorais secção"): no discussions of access to section-level data.
  The closest relevant item is a 2026 complaint that the portal lacks the second-round results
  ([thread](https://www.reddit.com/r/portugal/comments/1r1fg8k/)). Caveat: the archive does not cover everything;
  recent threads (2024–2026) may be missing.
- **YouTube** (parsing search results for "resultados por secção eleições", "secção de voto Portugal"):
  only videos about the voting procedure and news items; the topic of data publication is absent.
- **Forums**: no specialized Portuguese forums on electoral data were found —
  discussions live on Facebook/X, which are not retrospectively accessible.
- **CADA** (opinions on complaints — a direct check of "who tried"): search on cada.pt does not work for
  automated requests (redirect to the home page), and the old request platform pedidos.sgc.ma.gov.pt is
  dead and was not preserved in the archives. So far it has not been possible to check whether there were requests about sections.
- **Municipal section-level maps (the main find).** Câmara Municipal publish their own
  "MAPA GLOBAL POR SECÇÃO DE VOTO" — officially, broken down as freguesia × section × party. Example —
  Sabugal (Guarda district):
  - AR-2024 (10.03.2024): [section map](https://arquivo.pt/wayback/20240513201654/https://cm-sabugal.pt/wp-content/uploads/2024/03/mapa_global_seccao_voto-9.pdf);
  - presidential 2021: [map](https://arquivo.pt/wayback/20210923115136/https://cm-sabugal.pt/wp-content/uploads/2021/01/mapa-global-por-seccoes-de-voto-7.pdf);
  - municipal 2009–2021: [2009](https://arquivo.pt/wayback/20091219115212/https://web.cm-sabugal.pt/files/2009_09/eleicoes09/mapa_global_seccoes_voto.pdf), [final 2021](https://arquivo.pt/wayback/20210930170925/https://cm-sabugal.pt/wp-content/uploads/2021/09/mapaderesultadosdefinitivos_por_seccao_de_voto.pdf).
  I.e. section-level data have in fact been public at the municipal level for a long time, without any
  requests; for AR-2025 they must be collected across the 308 câmaras (websites/archives or a request — câmaras are also
  subject to Lei 26/2016).
- **Correction of the earlier claim** ("old portals up to 2015 contained sections in HTML"): the archive does
  NOT confirm this. The structure of the old MAI portals — [autarquicas2001](https://arquivo.pt/wayback/20141007173534/http://www.eleicoes.mai.gov.pt/)
  (38 thousand URLs) and [legislativas2015](https://arquivo.pt/wayback/20210928140659/https://eleicoes.mai.gov.pt/legislativas2015/territorio-nacional.html)
  (6.5 thousand URLs, format `D####/C####/F####.html`) — ends at the freguesia level; there are no "secc" URLs,
  and the archived freguesia page (autárquicas2001, C010100/010100_AF.html) has no sections.
  Centralized publication of sections apparently never existed; what was "lost" in the redesign was at most
  access to the old static sites, not the level of detail.

## Section data (secções): what and where to download (verified 09.10.2026)

**In short: the only working source of section-level results is the municipalities' own websites
(PDF "MAPA GLOBAL POR SECÇÃO DE VOTO" and analogues). The AR-2025 example has been downloaded and parsed;
the central sources do not provide sections (verified against all of them, see below).**

### Verified live links (AR-2025 and adjacent elections)

| Who | What | Link | Format/contents |
|---|---|---|---|
| **CM Alcácer do Sal** (Setúbal) | **AR-2025, results by section** — working example | <https://cm-alcacerdosal.pt/wp-content/uploads/2025/05/LEGISLATIVAS-2025-Resultados-no-concelho-de-Alcacer-do-Sal.pdf> | PDF table: freguesia × section (number, place) × all 18 lists + inscritos, brancos, nulos, turnout, abstenções; totals by freguesia/concelho. Downloaded to `data/seccoes_test/` |
| **CM Sabugal** (Guarda) | section maps for **every** election since 2017 | sections like <https://www.cm-sabugal.pt/eleicoes-autarquicas-2021>; files in `/uploads/YYYY/MM/…` (AR-2019, PE-2019, municipal 2017/2021/2025, presidential 2021/2026 — all in Google results for the exact phrase) | the same standard "MAPA GLOBAL POR SECÇÃO DE VOTO" template |
| **Junta de Freguesia de Benfica** (Lisbon) | AR-2025: "Eleitores – distribuição por secção de voto · Resultados" | <https://bairrobenfica.pt/2025/05/06/eleicoes-legislativas-2025/> | parish councils (juntas) publish these too, not only câmaras |
| CM Vila Nova de Gaia | pre-election "Mapa da Assembleia e Secções de Voto" | <https://www.cm-gaia.pt/pt/autarquicas-2025> | ⚠️ this is a map of where to vote, not results; the final maps of large cities must be looked for in their Eleições sections |
| SGMAI (central) | official AR-2025 spreadsheet | `AR_2025_Globais.xlsx` — see the "Sources" section | down to the freguesia; useful as a reference for cross-checking |

Searching for other municipalities: Google with the exact phrases `"mapa global por secção de voto" legislativas 2025`,
`"TOTAL URNA" "ABSTENÇÕES" legislativas 2025 filetype:pdf` (a marker of the final table), `site:cm-<city>.pt eleições`.
⚠️ Google's indexing of these PDFs is poor (only a handful are found by the "TOTAL URNA" marker) — for full coverage
one needs to crawl the 308 câmara websites using the concelho list from `results_concelhos.csv` (the domains are mostly `cm-<name>.pt`,
but not all; some have their documents in separate systems — e.g. Porto uses the APEX portal `bme.cm-porto.pt`).

### Central sources do NOT provide sections — verified (09.10.2026)

- MAI portal, AR-2025: the `territory-tree.json` tree — 4 levels, 3092 freguesias as leaves; nothing below.
- MAI portal, new API (the presidential-2026 template): descending district→concelho→freguesia; the freguesia
  has `typeId=7, final=true`, 0 children — even the newest elections stop at the freguesia.
- Official SGMAI XLSX `AR_2025_Globais.xlsx`: sheets Global/Distrito/Concelho/Freguesia/País/Consulado.
- By law (LEAR Art. 115) the national map is issued by district; there is no obligation to publish sections
  centrally — the câmaras do it themselves (custom, not a requirement).
- No aggregators found: no GitHub datasets on sections; the "dadosabertos.mai.gov.pt" portal does not exist
  (the domain does not resolve — it appears only in the hallucinations of search assistants).

### How to collect (methodology, if we go after all 308)

1. The list of concelhos — from `results_concelhos.csv`; match the câmara domains (manually / via Google `camera municipal <nome> site:.pt`).
2. On each website, find the Eleições/Resultados section (site search, sitemap, Google `site:`).
3. Download the PDF/XLSX for AR-2025; for dead links the alternative is arquivo.pt (Sabugal 2009–2024 was done that way).
4. Parsing: `pdftotext -layout` gives clean columns (verified on Alcácer do Sal); for complex layouts use pdfplumber.
5. Quality control: the section sums per freguesia must match `results_freguesias.csv` (MAI).
6. To match sections across elections / georeference them — the pre-election "Mapa definitivo das assembleias
   e secções de voto" (the câmaras are required to publish them; see Trofa, Gaia, Mafra).

Sample files are saved in `data/seccoes_test/`: `alcacerdosal_legislativas2025.pdf` (results by section,
parsed), `AR_2025_Globais.xlsx` (the official SGMAI spreadsheet down to the freguesia).

## Election results (18.05.2025, source: official JSON of the MAI portal)

- Turnout: **58.23%** (6 317 949 of 10 850 215; within the territory of Portugal — 64.38%)
- 230 mandates: **AD (PPD/PSD.CDS-PP) 88 (31.2%, 1 971 558 votes)**, Chega 60 (22.8%), PS 58 (22.8%), IL 9, LIVRE 6, PCP-PEV 3, PPD/PSD.CDS-PP.PPM (Azores) 3, B.E. 1, PAN 1, JPP (Madeira) 1
- Blank votes 87 654, invalid ballots 172 994 (CNE data)

## What has been downloaded (this folder)

```
data/
  cne/                          — official CNE results
    2025_ar_mapa_resultados.xlsx / .ods / .zip   (for the 22 districts)
    2025_ar_mapa_oficial_dr.pdf                  (official map, 5 pp.)
  legislativas2025_mai/         — full download from the MAI portal (27 MB)
    territory-results/*.json    — results for ALL 3458 territories (0 missed):
                                   22 districts + 325 municipalities + 3092 parishes
                                   + overseas districts (countries/consulates) + totals;
                                   inside each file — votes/% by party,
                                   turnout, blank/invalid, mandates,
                                   previousResults (the 2024 election)
    territory-children/*.json   — the territory tree
    territory-tree.json         — the assembled tree (parent/level/name)
    configurations.json, affluences.json, links.json, …
    results_all.csv             — consolidated: all levels, votes by party (wide format)
    results_circulos.csv / results_concelhos.csv / results_freguesias.csv
    results_all_previous.csv    — the same territories, results of the previous election (2024)
  <election>_mai/ (10 directories) — the same downloads for previous years, see the section below
  legislacao/                   — official texts of the laws:
    lei14-79_LEAR_consolidada_CNE_2026-07.pdf        — the AR election law
                                   (Lei 14/79, consolidated version 23-07-2026, 53 pp.)
    lei13-99_recenseamento_consolidada_CNE_2024-02.pdf — the voter registration
                                   law (Lei 13/99, consolidated version 2024)
  seccoes_test/                 — samples for the section-level direction (see the section
                                 "Section data: what and where to download"):
    alcacerdosal_legislativas2025.pdf  — MAPA GLOBAL POR SECÇÃO DE VOTO (AR-2025,
                                   Alcácer do Sal): freguesia × section × parties
    AR_2025_Globais.xlsx          — official SGMAI spreadsheet (sheets down to the freguesia)
```

Integrity check: the sums over all 3092 parishes (registered voters, turnout, blank,
party votes) match the national total to the last vote; the totals of all
20 "continental" districts equal the sums of their parishes, and the national total =
parishes + Europa + Fora da Europa (5 965 446 + 255 305 + 97 198 = 6 317 949).

## Elections of previous years (2021–2026): the full collection (downloaded 09.10.2026)

All nationwide elections in Portugal over the last 5 years have been downloaded from the MAI portal using the same
method (down to the freguesia/consulate level inclusive). Each `<slug>_mai/`
directory has the same structure as `legislativas2025_mai/` (territory-results, territory-tree,
results_all.csv and per-level CSVs + results_all_previous.csv).

| Election | Date | Directory `data/…_mai` | Suffix/organ | Territories |
|---|---|---|---|---|
| Presidential, 1st round (one round was enough) | 24.01.2021 | presidenciais2021 | PR | 3585 |
| Municipal (câmara) | 26.09.2021 | autarquicas2021 | CM | 3422 |
| Parliamentary (AR) | 30.01.2022 | legislativas2022 | AR | 3472 |
| Regional, Azores | 04.02.2024 | regionais2024 | **RA** | 186 |
| Parliamentary (AR) | 10.03.2024 | legislativas2024 | AR | 3464 |
| Regional, Madeira | 26.05.2024 | regionais-madeira2024 | **RM** | 68 |
| European Parliament | 09.06.2024 | europeias2024 | PE | 3602 |
| Parliamentary (AR) | 18.05.2025 | legislativas2025 | AR | 3458 |
| Municipal (câmara) | 12.10.2025 | autarquicas2025 | organ 4 (CM) | 3588 |
| Presidential, 1st round | 18.01.2026 | presidenciais2026_1S | organ 3 (PR) | 3771 |
| Presidential, 2nd round | 08.02.2026 | presidenciais2026_2S | organ 3 (PR) | 3767 |

Specifics:
- **The regional suffixes differ**: the Azores — `RA`, Madeira — `RM`
  (determined by the `electionDefaultId` in the election's configurations.json).
- **Since autumn 2025 the portal has changed its format** (autarquicas2025 and older do not have this): numeric
  ids of territories and "organs" instead of the `LOCAL-*` keys; files like
  `assets/static/result/territory-electionId=<E>-territoryId=<ID>-organId=<O>.json`;
  the electionId is taken from `app-settings.json`. For these, `scripts/fetch_mai_results_v2.py` is used. organId: PR=3; municipal CM=4/AM=5/AF=6
  (for the full municipal triads: `--organs 4,5,6`).
- The internal structure of the result files has not changed (currentResults/previousResults
  under the `data` key), so `build_csv.py` works with both formats.
- The portal's new tree (2025/2026) is smaller: ~3590–3770 nodes vs ~3460 (the overseas
  part is structured differently; the mainland has the same 3092 freguesias).

Verification (`python3 scripts/verify_downloads.py`): all 11 downloads — the sums of votes
and registered voters over the leaves = 100.00% of the national total; no missing files.
The control points match the official results: PS 41.4% (absolute majority, 2022);
the near-tie AD 28.0% / PS 28.0% (2024); Marcelo Rebelo de Sousa 59.5% in the 1st round (2021);
the 2026 2nd round — Seguro 66.8% vs Ventura 33.2%.

## Scripts for reuse (`scripts/`)

```bash
# Old portal format (elections up to 2025; rate ~5 req/s, automatic pause on a CDN ban):
python3 scripts/fetch_mai_results.py legislativas2024          # parliamentary
python3 scripts/fetch_mai_results.py europeias2024 --suffix PE # European
python3 scripts/fetch_mai_results.py autarquicas2021 --suffix CM,AM,AF  # municipal
python3 scripts/fetch_mai_results.py regionais2024 --suffix RA # the Azores (Madeira — RM!)
python3 scripts/fetch_mai_results.py legislativas2024 --leaf-level 3     # do not check freguesias for children (faster)

# New portal format (autarquicas2025, presidenciais2026_*):
python3 scripts/fetch_mai_results_v2.py presidenciais2026_1S --organs 3
python3 scripts/fetch_mai_results_v2.py autarquicas2025 --organs 4,5,6  # CM+AM+AF

# Build the consolidated CSVs from a download (both formats):
python3 scripts/build_csv.py data/legislativas2024_mai

# Verify the integrity of all downloads (leaf sums against the national total):
python3 scripts/verify_downloads.py
```

The scripts can resume downloads (re-running is safe) and wait by themselves when the CDN blocks them.
The election slugs come from the portal URL `eleicoes.mai.gov.pt/<slug>/`; the suffixes: AR (parliament), PE (European Parliament), PR (presidential), CM/AM/AF (municipal triads).

**If the CDN bans curl** (Access Denied on bulk downloads — as happened in 2025):
a fallback path via a real browser, whose requests Akamai lets through:
1. `python3 scripts/local_receiver.py <download_dir> 8765` — a local file receiver;
2. open the election page on the portal in the browser and run `scripts/browser_loader.js` in its console
   (substituting the list of keys and the suffix) — it will download everything
   at a rate of ~1.5 req/s with automatic pauses and pass the files to the receiver.
