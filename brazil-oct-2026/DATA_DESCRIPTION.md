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
with polling-place address also allows neighbor analysis. Data covers the 1st round only;
2nd-round results (25.10.2026) will appear in the TSE dataset later — re-running
`download_votacao_secao.sh` will fetch them (curl `-C -`).

## Statistical fraud analysis (12.10.2026)

The full run of all analysis methods on this data is in **`REPORT_statistical_fraud_analysis.md`**
(tool `analysis-tool/`, output in `analysis/`): conclusion — no systematic traces of fraud
found. Building the section dataset — `scripts/build_sections_csv.py`
→ `data/secoes_presidente_2026.csv` (499,248 sections, ElectionData format, cross-checks
against detalhe — 0 mismatches); running the methods — `scripts/run_forensics.py`; an extra
binomial null for the digit tests — `scripts/digit_binomial_null.py`. Run from `analysis-tool/`
via `uv run python ../brazil-oct-2026/scripts/<script>`.
