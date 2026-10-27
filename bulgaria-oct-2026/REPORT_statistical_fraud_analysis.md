# Bulgaria 2026 presidential first round: statistical screening

Checked **27 October 2026**. National source stamp: **26 October, 15:00 EET**, **100%** of section-commission protocols processed. This does not imply certification.

**The available screening does not establish ballot stuffing. It does identify protocol-balance discrepancies and digit-distribution flags for follow-up.** There is no comparable historical control in this run, so the conclusion is exploratory. Count-night stability cannot establish a clean election.

## Updated official result

[CIK national table](https://results.cik.bg/pvr202610/rezultati/index.html):

| Item | Votes | Displayed share |
|---|---:|---:|
| Yotova | 528,929 | 34.759% |
| Gyurov | 486,214 | 31.952% |
| Kostadinov | 190,894 | 12.545% |
| Do not support anyone | 67,353 | 4.426% |
| All 27 candidate pairs plus nobody | 1,521,711 | 100.002% after rounding |

The last saved night snapshot ended at 98.99% and 1,512,779 listed votes. The updated table adds **8,932 net listed votes**, including Yotova +4,016 and Gyurov +2,368. The displayed-share margin grows from 2.715 to **2.807 percentage points**, a 0.092-point change. Net differences can include corrections; they are not a reconstruction of the ballots in newly processed sections.

The possible runoff is scheduled for **1 November 2026**, per [CIK decision 415-ПВР](https://www.cik.bg/bg/decisions/415/2026-10-26). The earlier page and night report had incorrectly stated 8 November.

## Source validation and exclusions

The bulk [open-data page](https://results.cik.bg/pvr202610/opendata/index.html), `opendata/export.zip` and `opendata/spreadsheet.zip` returned **404**. However, the [numeric-protocol index](https://results.cik.bg/pvr202610/protokoli/data.js) links **12,719 individual sections**, all successfully captured. Where aggregate form `0` exists, it is used once; component forms are not added again. Otherwise form `1` is used. Each section's identifier and all 27 candidate rows are validated.

**All 27 candidate totals and the nobody total reconcile exactly with the national table.** Nevertheless, **22 sections** have an internal voter/signature balance discrepancy: candidate votes plus nobody exceed signatures, or signatures exceed the opening register plus election-day additions. Nineteen are domestic and three abroad. These are discrepancies in published numerical fields, not proof of fabricated ballots. The parser preserves them instead of silently repairing them.

Example: [section 321320600, aggregate protocol](https://results.cik.bg/pvr202610/protokoli/256/32/321320600.0.html) lists 77 opening electors, 192 additions, 56 signatures and 248 machine votes (244 candidate votes + 4 nobody). The section is excluded from turnout screening. The discrepancy could reflect source-entry or field-definition issues and needs protocol review.

| Sequential selection | Sections |
|---|---:|
| All indexed protocols | 12,719 |
| Exclude abroad (includes 3 balance discrepancies) | −613 |
| Exclude remaining domestic balance discrepancies | −19 |
| Exclude registers below 100 | −1,471 |
| Eligible domestic sections | **10,616** |

Eligible sections contain **6,532,472 registered electors**, **1,399,546 signatures**, **490,916 Yotova votes**. The turnout denominator is **opening register + election-day additions**; candidate shares use signatures/ballots cast, not the national table's listed-vote denominator. Yotova therefore has **35.0768% in this subset**, not 34.759% nationally. The nobody category occupies the toolkit's `blank_votes` field solely as an explicit non-candidate category; it is not a blank ballot. `null_votes` is the residual signatures minus candidate and nobody votes, not an independently verified invalid-ballot count.

A size filter does not identify every mobile, institutional or special section. Ordinary/special and paper/machine stratification remains incomplete. Local comparisons group sections by the first four digits of their official identifier (district + municipality); no geographic nearest-neighbor distances are used.

## Method results

### 1. Shpilkin-style high-turnout tail

The toolkit uses the electorate-weighted **99.5th percentile of this same dataset**, **50.4823% turnout**, as a cutoff. It counts candidate votes in 0.5-point turnout bins whose centers lie above the cutoff. This is an endogenous tail diagnostic, not an externally calibrated excess-vote model.

There are **7,845 Yotova votes** in that tail, **1.598% of her eligible-subset votes**. Excluding the entire tail would change her share from **35.0768% to 35.1025%** (+0.0257 points). This is a descriptive counterfactual; those 7,845 votes must not be described as proven fraudulent votes. The weighted section turnout–Yotova-share correlation is **−0.140**, versus **+0.420** for Gyurov.

| Endogenous percentile | Turnout cutoff | Yotova votes in tail | Share of her subset votes |
|---|---:|---:|---:|
| 99 | 45.531% | 13,303 | 2.710% |
| 99.5 | 50.482% | 7,845 | 1.598% |
| 99.9 | 99.296% | 2,445 | 0.498% |

The large cutoff shift demonstrates sensitivity to the selected reference percentile and the extreme-turnout sections. No historical control or fraud total is inferred.

### 2. Comet scatter and Klimek-style fingerprints

The two-component Gaussian mixture does **not** meet the toolkit's separation criterion. Its second-component weight is **0.676**; this is a fitted cluster weight, not a fraud fraction. The components differ mainly in turnout (means 24.22% vs 15.59%) while Yotova shares are 35.48% vs 36.91%. Geographic heterogeneity and special sections remain plausible contributors; a pooled mixture is not an election-integrity verdict.

### 3. Kobak-style integer peaks

Under the toolkit's section-size-aware binomial Monte Carlo null (200 simulations, seed 42), **1.884%** of section turnout values round to an integer at two decimal places, versus **1.855%** expected: **z = 0.25**. Integer Yotova shares: **z = 1.55**; multiples of five: turnout **z = 0.01**, Yotova share **z = 1.72**. These diagnostics do not show a large integer-percentage excess under that particular null model.

### 4. Second digit and last digit

Five candidates meet the toolkit's 50,000-vote threshold. Second digits use counts ≥10; last digits use counts ≥100. We report both the theoretical reference and the fitted smooth-lognormal Monte Carlo reference (400 simulations, seed 42), then apply **Holm correction across seven candidate/test combinations with at least 50 usable counts**. This is an exploratory family, not a preregistered analysis. The last-digit chi-square result for Vasilev (only two eligible tallies) is not interpreted; Kostadinov and Mihaylov have no ≥100 tallies.

- Yotova second digit: theoretical Benford p ≈ 5.0×10⁻⁷, but **smooth-null p = 0.693**. The theoretical rejection does not survive the count-distribution comparison.
- Yotova last digit: **189 tallies**, raw Monte Carlo p = **0.0224**, Holm-adjusted **0.1122**. It does not reject at 5% after the stated adjustment.
- Vasilev and Mihaylov second digits: Monte Carlo p = **1/401 = 0.00249**, Holm-adjusted **0.01746** each. These remain model-relative flags. Small, truncated vote counts and an imperfect lognormal reference can contribute; inspect tally ranges, voting modes, geography and a historical control before interpreting them as manipulation.
- Other sufficiently sized digit tests have Holm-adjusted p = 1. Raw p-values and sample sizes are preserved in the outputs.

### 5. Local outliers and machine learning

The robust within-municipality screen flags **388 sections** with |z| > 4 in turnout or leader share. These are comparisons within an administrative group, not proof about individual stations. Isolation Forest flags **107 sections**, using a configured **1% contamination**. The count is largely set by that parameter and must not be presented as an estimated fraud rate. Flag lists are provided for inspection.

### 6. Synthetic injection

Adding **100,376 synthetic Yotova votes** in the toolkit's injection scenario increases the tail statistic from 7,845 to **61,077** (**7.79×**). A separate rounded-turnout injection changes the self-test's integer-peak z from **0.45 to 3.07** (self-test simulation settings differ from the main test). This checks sensitivity to those synthetic patterns, not specificity to real fraud or authenticity of the source data.

### 7. Controls and remaining limits

**No 2021 presidential control is included.** Neither matched-section historical swings nor control-calibrated Shpilkin cutoffs have been computed. There is no assessment here of coercion, vote buying, registration integrity, physical ballots or campaign conditions. The 22 source balance discrepancies and the surviving digit flags merit inspection, while the aggregate and precinct diagnostics do not establish a mechanism or quantity of manipulation.

## Reproduction and outputs

Raw HTML is cached under `data/official_20261027/` (gitignored); all indexed section totals are saved in `sections.json`, with national reconciliation and discrepant IDs in `summary.json`. The adapter writes `data/ef/results_freguesias.csv`, `exclusions.csv` and `audit.json`. The static page bundles the analysis CSV, summary, exclusions, metrics, sensitivity outputs and an archive of toolkit tables/figures.

```bash
bulgaria-oct-2026/.venv/bin/python bulgaria-oct-2026/scripts/check_official_results.py --sections
bulgaria-oct-2026/.venv/bin/python bulgaria-oct-2026/scripts/build_ef_csv.py
MPLCONFIGDIR=/tmp/bulgaria-mpl analysis-tool/.venv/bin/ef-analyze \
  --data bulgaria-oct-2026/data/ef --out bulgaria-oct-2026/analysis/ef \
  --title 'Bulgaria 2026 R1 — domestic sections, exploratory'
analysis-tool/.venv/bin/python bulgaria-oct-2026/scripts/summarize_forensics.py
MPLCONFIGDIR=/tmp/bulgaria-mpl analysis-tool/.venv/bin/python bulgaria-oct-2026/scripts/build_site_figures.py
```

The capture intentionally retains its dated cache. To check a later publication, use a new cache directory in the capture script; do not overwrite the archived observation.
