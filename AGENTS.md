
```
portugal-2025/               — Portugal, legislativas 2021–2026: 11 MAI exports,
                              official CNE results, laws, precinct-level maps of
                              municipalities, reports, parsers; voting-paradox
                              analysis (legislativas 2025 D'Hondt/FPTP,
                              autárquicas 2025, presidenciais 2026 runoff) →
                              PARADOXES.md; site figures —
                              scripts/build_site_figures.py
brazil-oct-2026-round-1/             — Brazil, rounds of 04/25.10.2026: TSE results by precinct
                              (data/votacao_secao, ~23 GB of CSV; description in
                              DATA_DESCRIPTION.md) + the 2022 control election on the
                              same precincts (data/votacao_secao_2022); statistical
                              fraud analysis → REPORT_statistical_fraud_analysis.md
                              ("statistical fraud analysis report"; 2022 control —
                              section 12); voting-paradox analysis (bloc cloning,
                              2022 runoff transfer matrix, 2026 runoff prediction,
                              lesser-evil desertion; scripts/run_paradox_analysis.py)
                              → PARADOXES.md; site figures —
                              scripts/build_site_figures.py
bulgaria-oct-2026/           — Bulgaria, presidential election of 25.10.2026: captures of
                              results.cik.bg (scrape_cik.py + run_every_15min.sh) →
                              REPORT.md
serbia-oct-2026/             — Serbia, National Assembly 25.10.2026: RIK JSON API,
                              captures every 15 minutes → ОТЧЁТ.md ("REPORT.md")
sloveniya-referendum-2026/   — Slovenia, 4 referendums on 11.10.2026: uv project `sloref`
                              (DVK portal): totals and all 3,083 precincts, cross-check
                              against Wikipedia and election-night counting dynamics →
                              README.md, report.md; statistical fraud analysis (2,984
                              precincts, analysis-tool pipeline) →
                              statistical_fraud_analysis.md; voting-paradox analysis
                              (territorial reversals, gerrymander bound, Art. 90
                              quorum) → PARADOXES.md; site figures —
                              scripts/build_site_figures.py
india-2024/                  — India, Lok Sabha 2024: uv project `india2024`;
                              constituency-level results (data/results_pc), turnout
                              (data/turnout), Uttar Pradesh Form20 (data/form20),
                              wayback snapshots (data/wayback); 2014/2019 controls
                              (data/control_*); scripts/ — download and parsing;
                              statistical fraud analysis → REPORT.md (national PC +
                              UP assembly segments + UP booth digit tests, 2014
                              booth-level control); analysis-tool inputs in data/mai_*
                              (scripts/build_mai_datasets.py); publishable booth
                              dataset + provenance → release/ (DATACARD.md; unique —
                              first public PS-level 2024 dataset)
site/                        — public website for Vercel (static, deployed from
                              the site/ root): landing page site/index.html + country
                              sections — Minto pyramid, images swapped from
                              img/<lang>/ by language: Slovenian (5 languages
                              SL/EN/HR/IT/HU), Brazilian (PT/EN/ES/RU),
                              Portuguese (PT/EN), Indian (EN/HI)
                              → README.md in each section
analysis-tool/               — election forensics (pandas/sklearn, uv): Shpilkin,
                              Klimek fingerprints, Kobak integer peaks, Benford/
                              last-digit, outliers vs neighbors, Isolation
                              Forest; CLI `ef-analyze`
методы_выявления_фальсификаций_выборов.md ("methods for detecting election fraud".md) —
                              overview of the methods analysis-tool was written from
```


## analysis-tool

```bash
cd analysis-tool && uv sync
uv run ef-analyze \
  --data ../portugal-2025/data/legislativas2025_mai \
  --out ../portugal-2025/analysis \
  --title "Португалия AR 2025 (freguesias)" \
  --merge "votes:PPD/PSD.CDS-PP<-votes:PPD/PSD.CDS-PP.PPM" \
  --controls ../portugal-2025/data/legislativas2022_mai,../portugal-2025/data/legislativas2024_mai
uv run pytest
```
# code guidelines

- Use type hints at least in method definitions
- prefer
    - strenums to plain 'str'
    - dataclasses instead of plain dicts or tuples
- httpx2 for instead of requests

# Good software architecture principles

- reverse call: a module uses its parent
- parallel call: a module uses another one on the same level
- downstream call: a module uses a function or a module which is at least 2 levels below it
- functions should use simple data classes in and simple data classes out.
- Side effects should be encapsulated in separate modules: one can read from the database, but not directly change it
- a module should not save a history of calls to control its operations
- a module only does one thing, completely
- major decision making should be pushed to the highest possible level. Typically, the main decisions are made by the head module (at the first level). This head module serves as a succinct "summary" of the entire program.
- a lower-level module should not make decisions for higher-level modules. Therefore, a module shouldn't perform actions that directly alter the program's operation.
- errors should bubble up until the level where the control-flow decision can be made

# Parsing PDF and scanned documents

Use openrouter + [GPT-luna-latest](https://openrouter.ai/~openai/gpt-luna-latest), reasoning=off or reasoning=low if the resulting quality is not low.
The key `OPENROUTER_KEY=...` is in `.env`. Never read it, only use it in scripts.
