# Brazil, general elections 04.10.2026 — TSE polling-station data

Downloaded on 12.10.2026 by the `download_votacao_secao.sh` script from the TSE open-data
portal (dataset [resultados-2026](https://dadosabertos.tse.jus.br/dataset/resultados-2026),
CDN `cdn.tse.jus.br/estatistica/sead/odsele`). These are the **final 1st-round results**
(files generated 05–06.10.2026) at the level of an individual ballot station (seção).

On disk in total: **29 zips (~2.9 GB) + 58 unpacked CSVs (~23 GB)**, each folder contains
a `leiame.pdf` with the official field descriptions. Encoding **latin-1**, separator `;`,
quoted rows. The files are huge — open them with pandas and explicit `dtype`, not in Excel.

## The three sets of files (`data/votacao_secao/`)

| Set | Files | Contents |
|---|---|---|
| `votacao_secao_2026_BR` | 1 file (zip 162 MB, CSV 1.05 GB, 3.8M rows) | **President** (election 6257, office 1) for every station in the country, including abroad (ZZ, 12,035 rows) |
| `votacao_secao_2026_<UF>` | 27 states | **State-level offices** (election 6259): governor (3), senator (5), federal deputy (6), state legislature deputy (7; in DF — district deputy 8). Largest: SP 767 MB, RJ 288 MB, MG 255 MB |
| `detalhe_votacao_secao_2026` | 30 files: per UF + BR + BRASIL + ZZ | **Turnout and counting details** per station (see below); `BRASIL` — everything combined, `BR` — president only, `ZZ` — empty (header only, the abroad rows are already in BR) |

## Row format

**`votacao_secao_*`** — one row = (station × candidate). Key fields:
`SG_UF`, `CD_MUNICIPIO`/`NM_MUNICIPIO`, `NR_ZONA`, `NR_SECAO` (station),
`CD_CARGO`/`DS_CARGO` (office), `NR_VOTAVEL`/`NM_VOTAVEL` (candidate; also includes
`VOTO BRANCO`/`VOTO NULO` rows), `QT_VOTOS`, plus the polling-place address
(`NR/NM_LOCAL_VOTACAO`, `DS_LOCAL_VOTACAO_ENDERECO`).

**`detalhe_votacao_secao_*`** — one row = (station × office), the part needed for
turnout and forensics: `QT_APTOS` (station electorate), `QT_COMPARECIMENTO` (showed up),
`QT_ABSTENCOES`, nominal/blank/null/party/annulled votes, time the BU reached the TSE,
"station installed/annulled" flags,
`CD_MODELO_URNA`/`DS_MODELO_URNA` (ballot machine model).

Election identifiers: **6257** — federal (president); **6259** — state-level;
**6261** — Fernando de Noronha district council (10 stations, PE). All `NR_TURNO=1`.

## 1st-round results in this data

President, valid votes 119,306,034 (.valid = all − null − blank):

| Candidate | Votes | % of valid |
|---|---|---|
| FLAVIO NANTES BOLSONARO | 56 104 503 | 47.03 |
| LUIZ INÁCIO LULA DA SILVA | 53 879 538 | 45.16 |
| AUGUSTO JORGE CURY | 3 448 569 | 2.89 |
| RENAN ANTONIO FERREIRA DOS SANTOS | 2 675 887 | 2.24 |
| RONALDO RAMOS CAIADO | 2 605 148 | 2.18 |
| ROMEU ZEMA NETO | 326 488 | 0.27 |

Nobody reached 50% → **2nd round on 25.10.2026** (Bolsonaro × Lula).

Overall figures (from `detalhe_..._BRASIL`, election 6257):

- stations: **499,248** (across 5,757 municipality codes, including abroad);
- electorate: **158,745,502**; showed up: **125,275,835** (turnout **78.92%**); abstentions: 33.5M;
- blank: 2,300,798, null: 3,669,003.

The vote total of the `votacao_secao_2026_BR` file matches the "showed up" figure from
`detalhe` to the last vote (125,275,835) — the data is self-consistent.

## For election forensics

The analysis base is `detalhe_votacao_secao_2026_BRASIL.csv` (president: 499,248 stations
with electorate and turnout) + votes from `votacao_secao_2026_BR.csv`; the station level
with polling-place address also allows neighbor analysis. After each turno the TSE
regenerates the same files with both rounds included (`NR_TURNO` = 1/2 in one CSV); the
portal states files are updated at the end of each round. Do **not** resume a changed zip
with `curl -C -` — it corrupts the archive; `scripts/download_votacao_secao_T2.sh` does a
fresh download of the two BR files once the 2nd round is published.

## Statistical fraud analysis (12.10.2026)

The full run of all analysis methods on this data is in **`REPORT_statistical_fraud_analysis.md`**
(tool `analysis-tool/`, output in `analysis/`): conclusion — no systematic traces of fraud
found. Building the section dataset — `scripts/build_sections_csv.py`
→ `data/secoes_presidente_2026.csv` (499,248 sections, ElectionData format, cross-checks
against detalhe — 0 mismatches); running the methods — `scripts/run_forensics.py`; an extra
binomial null for the digit tests — `scripts/digit_binomial_null.py`. Run from `analysis-tool/`
via `uv run python ../brazil-oct-2026-round-1/scripts/<script>`.

## Intraday trend capture — 2nd round (25.10.2026)

`data/trends/` — 13 snapshots of the TSE results portal, 20:07 UTC 25.10 (17:07 BRT,
minutes after polls closed) → 07:52 UTC 26.10; file schema and capture notes in
`data/trends/README.md`. This election-night stream did not exist for the 1st round.

`scripts/analyze_trends.py` → `analysis/trends/`:

- `trends_summary.json` — president share trajectory vs % counted (country ticker:
  58.59% Lula at 0.21% counted → 51.79% final, −6.8 pp), full snapshot timeline with
  turnout-of-counted-sections and blank/null shares, early- vs late-reporting states
  (11 states that crossed 50% counted first: mean Lula two-way 46.69% vs 54.02% in the
  other 17), governor-runoff margins and intraday lead changes (no flips in any of the 6);
- `swing_decomposition.csv` + `swing_by_uf` — exact per-step decomposition of the
  national two-way share into state-batch contributions
  (contribution_u = ΔV_u/V_t · (s_u − S_prev), anchored at the 1.56%-counted snapshot
  where the portal's UF table reaches ~85% coverage of the country ticker; from that
  anchor the net move is −1.26 pp: PR −2.23, SC −1.27, SP −1.24, RS −1.12 down,
  BA +1.94, PE +1.30, CE +1.19, MA +1.12, PB +0.90 back up);
- `uf_final_twoway.csv` — per-UF final two-way shares, 50%-counted crossing times,
  early/late reporter flags.

The final captured totals (turnout 80.78%, Lula 51.79% two-candidate valid) are the
cross-check reference for the per-section 2nd-round dataset built by
`scripts/build_sections_csv_T2.py` (`vs_trends_portal` block must match to the vote).
