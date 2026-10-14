# analysis-tool: election forensics

Statistical methods for detecting election fraud — an implementation of the
methods from the survey "The Shpilkin method and other statistical methods
for detecting election fraud" (repository root).

## Methods

| Module | Method | Source |
|---|---|---|
| `shpilkin` | turnout histogram, "honest core", estimate of anomalous votes | Shpilkin |
| `fingerprints` | electoral fingerprints, 2D Gaussian mixture | Klimek et al., PNAS 2012 |
| `integer_peaks` | integer peaks of turnout/result (MC null) | Kobak et al., AOAS 2016 |
| `correlations` | 2D turnout × result correlations by party and district | Kobak et al., arXiv:1205.0741 |
| `digit_tests` | second digit (Benford) and last digit | Mebane 2006; Beber–Scacco 2012 |
| `neighbors` | outliers vs neighbours + jumps vs the previous election | Myagkov–Ordeshook–Shakin 2009 |
| `anomaly_ml` | Isolation Forest, ranking of anomalous territories | Zhang et al., PLOS ONE 2019 |
| `selftest` | synthetic validation: "stuffing" and "rounded turnouts" | — |

## Run

```bash
uv sync
uv run ef-analyze --data ../portugal-2025/data/legislativas2025_mai \
                  --out ../portugal-2025/analysis \
                  --title "Portugal AR 2025 (freguesias)" \
                  --controls ../portugal-2025/data/legislativas2022_mai,../portugal-2025/data/legislativas2024_mai
```

Output: `analysis/figures/*.png`, `analysis/tables/*.csv`, `analysis/metrics.json`.

The input is a MAI portal export (`results_freguesias.csv` +
`results_all_previous.csv`); the analysis level is parishes (freguesias),
the lowest available official level.

Plot labels default to English; other languages are set with
`--lang <code>` (`ru|en|pt|es|sl|hr|it|hu`).

## Tests

```bash
uv run pytest
```
