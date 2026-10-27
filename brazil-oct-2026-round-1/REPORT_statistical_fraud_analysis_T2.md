# Brazil, presidential runoff 25.10.2026 (2nd round): statistical fraud analysis

Report on running the election-forensics methods from the review
[`fraud_detection_methods.md`](../fraud_detection_methods.md) with the
[`analysis-tool/`](../analysis-tool/) tool on official TSE data at the polling-section
level (seção), for the runoff of 25.10.2026 (Lula vs Flávio Bolsonaro). Unlike the
[1st-round report](REPORT_statistical_fraud_analysis.md), this one has **three
references on the same sections**: the honest 2022 runoff (same stage of the cycle,
four years earlier), the 2026 1st round (same election, three weeks earlier), and —
new for this round — a **13-snapshot intraday capture of the TSE results portal**
taken live on election night (section 3).

**Conclusion up front: no systematic statistical traces of fraud were found.**
None of the eleven applicable method families (Shpilkin, fingerprints, integer
peaks, 2D correlations, last digit, neighbours, ML, urna models — with the 2022
runoff and the 2026 first round on the same sections as controls, plus the
intraday portal capture) produced a signal of the kind these methods read as a
sign of manipulation; the self-test confirms that on this data the battery is
sensitive and would "see" stuffing/painting. The digit tests' formal
significances repeat the first round's structural artifact (sections 7–8). The
runoff section export reconciles with the independent election-night capture to
the exact vote.

## Summary table of methods

| № | Method | Result on BR-2026 runoff | Verdict | Section |
|---|---|---|---|---|
| 2 | Shpilkin (turnout tail) | boundary 92.5% (q99.5); tail 0.59% of ballots; Lula 0.71% / Bolsonaro 0.46% of their votes | **clean** | [4](#4-shpilkin-method-turnout-distribution-honest-core) |
| 1 | Klimek fingerprints | both components at 79.8–81.4% turnout, not separated; no corner cluster | **clean** | [5](#5-electoral-fingerprints--comet-tail-klimek-et-al-2012) |
| 3 | Integer peaks | z(turnout)=−0.8; z(leader share)=−1.0; at multiples of 5 \|z\|≤1.6 | **clean** | [6](#6-integer-peaks-kobak-et-al-2016) |
| 4 | Benford-2 | smooth monotone profiles, max dev 2.15 pp; repeats the R1 structural artifact | **not applicable/clean** | [7](#7-benfords-law-second-digit-mebane-2006-deckert-et-al-2011) |
| 5 | Last digit | max dev 0.56 pp; 0/5 excess ≤0.45 pp — flat within noise | **clean** | [8](#8-last-digit-beberscacco-2012) |
| 3-b | 2D correlations | national r +0.04/−0.04; by state −0.48…+0.23, mirrored | **heterogeneity, not fraud** | [9](#9-2d-correlations-by-candidates-and-states-kobak-et-al-2012) |
| 8 | Neighbors | 5,018 outliers (1.005%) — the R1/2022 baseline level; no pattern | **audit candidates** | [10](#10-outliers-vs-neighbors-and-ml) |
| 7 | ML (Isolation Forest) | 4,993 = 1% by construction; extreme small sections | **audit candidates** | [10](#10-outliers-vs-neighbors-and-ml) |
| — | Self-test | 1.87M stuffing visible (×15.5); 5% painting visible (z→9.0) | methods are sensitive | [11](#11-self-test-of-the-methods-synthetic-injections) |
| — | Ballot-machine models | two-candidate split 51.5–53.8% across 4 generations; newest not most pro-government | **clean** | [12](#12-brazilian-specifics-ballot-machine-models) |
| — | Same-stage control (2022 runoff) | control boundary 91.52 ≈ own 92.51; tails at control boundary 1.37/0.95% vs 2022-R2's own 0.57–0.62%; jumps 0.78%, both directions | **clean** | [13](#13-controls-on-the-same-sections) |
| — | Same-election control (2026 R1→R2 jumps) | Δturnout median +1.91 pp, symmetric; 1.12% \|z\|>4 (409 up / 5,156 down — anti-stuffing direction); swing uniform across deciles | **clean** | [13](#13-controls-on-the-same-sections) |
| — | Intraday counting dynamics | two lead flips explained by reporting order; totals reconcile to the section file to the exact vote | **clean** (order effect) | [3](#3-intraday-counting-dynamics-new-for-this-round) |

---

## 1. Result and data

Runoff result (official, final): **Lula 51.79% vs Flávio Bolsonaro 48.21%** of the
two-candidate valid vote (64,256,232 vs 59,826,041), turnout **80.78%**
(128,236,074 of 158,745,502 registered; blank 1,430,496, null 2,723,305),
499,248 sections. Margin: 3.58 pp. Six states held governor runoffs the same day
(AC, AM, DF, ES, RN, TO); the closest — Rio Grande do Norte — ended at 1.54 pp
(Cadu de Lula 50.77% vs Allyson 49.23%).

Section dataset: `data/secoes_presidente_2026_T2.csv`, built by
`scripts/build_sections_csv_T2.py` from `votacao_secao_2026_BR.zip` +
`detalhe_votacao_secao_2026.zip` (rows `NR_TURNO == 2`, `CD_CARGO == 1`).
Self-consistency (`data/secoes_presidente_2026_T2_checks.json`): duplicate
section keys 0; nominal votes vs detail files 0 mismatches; blank/null vs detail
0; residual vs separately-annulled 0; voted > electorate 0; annulled sections 0;
43 zero-vote sections (all abroad, mostly never installed) have no rows in the
votes file and take zeros; 41 sections not installed. The totals were additionally cross-checked
against the independent election-night portal capture (section 3) — every
headline number matches **to the exact vote** (`vs_trends_portal` in
`data/secoes_presidente_2026_T2_checks.json`: match on voted/blank/null and both
candidates).

## 2. The three references

- **2022 runoff control** — `data/secoes_presidente_2022.csv` (turno 2), the same
  sections four years earlier at the same stage of the cycle; the 2022 elections are
  treated as honest per the 1st-round analysis. Supplies the Shpilkin q99.5 boundary
  for the runoff turnout distribution and the same-stage jump comparison.
- **2026 1st round** — `data/secoes_presidente_2026.csv`, the same election three
  weeks earlier: matched-section jumps R1→R2 (turnout change of a real runoff
  campaign vs a stuffing signature), and the origin votes for the transfer matrix
  (section 14).
- **Intraday portal capture** — `data/trends/` (section 3): the sequence in which
  the count actually unfolded, which no per-section file contains.

## 3. Intraday counting dynamics (new for this round)

The 1st-round report had to list "intraday dynamics" among the non-applicable
methods — no data. For the runoff, `data/trends/` holds 13 snapshots of the TSE
results portal taken live, 20:07 UTC 25.10 (17:07 BRT, minutes after polls closed)
through 07:52 UTC 26.10 (final tally, portal time 23:26 BRT 25.10). Schema in
`data/trends/README.md`; analysis in `scripts/analyze_trends.py` →
`analysis/trends/`.

### 3.1. The lead flipped twice — an order effect, not a count effect

National two-candidate share of counted valid votes, by snapshot:

| % counted (BRT) | Lula | Bolsonaro | note |
|---|---|---|---|
| 0.21% (17:05) | **58.59** | 41.41 | first ~300k votes, strongly Lula |
| 1.56% (19:07) | 52.16 | 47.84 | |
| 28.66% (20:06) | 49.54 | **50.46** | Bolsonaro leads |
| 95.33% (21:06) | **51.72** | 48.28 | Lula back ahead |
| 100% (23:26) | **51.79** | 48.21 | final |

Total swing from the first snapshot: **−6.8 pp for Lula**. The line moved for a
banal reason: **who reports when**. The 11 states whose sections crossed 50%
counted first average 46.69% two-way Lula; the other 17 average 54.02%. Turnout
of already-counted sections rose from 48.2% in the first minutes to the final
80.8% — the earliest transmitting sections were also unrepresentative on turnout.

### 3.2. Exact decomposition of the swing by state batches

`analysis/trends/swing_decomposition.csv`: between consecutive snapshots each state
adds a batch of votes with its own two-way share; the identity
`ΔS = Σ_u (ΔV_u/V_t)·(s_u − S_prev)` attributes each move of the national line to
specific states' batches, exactly. The per-state attribution is anchored at the
1.56%-counted snapshot — the first where the portal's per-state table covers ~85%
of the country ticker (before that the state rows lag the headline number and
cannot be decomposed).

From that anchor (Lula 53.05% two-way) to the final 51.79% — a net **−1.26 pp**:

- pulled the line **down**: PR −2.23, SC −1.27, SP −1.24, RS −1.12, MT −0.68 pp —
  the Bolsonaro-leaning South/Southeast, whose big pools dominated the first half
  of the count (the batch counted between 1.56% and 28.66% went 49.34% Lula over
  33.6M two-way votes);
- pulled it **back up**: BA +1.94, PE +1.30, CE +1.19, MA +1.12, PB +0.90 pp — the
  Northeast reporting after ~30% counted (the 28.66%→95.33% batch: 52.64% Lula
  over 83.1M votes; the final tail above 95%: 53.28% over 5.7M).

This is the Brazilian cousin of the "blue shift"/"red mirage" familiar from
absentee-heavy US counts: evidence about the *sequence* of reporting, not about
the integrity of the count. No discontinuity, reversal or jump in any trajectory:
each candidate's share moved monotonically towards its final value as pools
arrived (figure `site/brazil-oct-2026-round-2/img/en/counting.png` and the
decomposition `…/swing.png`).

### 3.3. Blank/null and governor runoffs

Null votes drifted smoothly from 1.46% of counted ballots in the first minutes to
the final 2.12% (blank 1.24%→1.12%) — the earliest sections were again
unrepresentative, no late surge anywhere. In all six governor runoffs the
final leader led in **every** snapshot (no flips): even the 1.54 pp RN race stayed
Cadu de Lula–led all night (margin 6.92 pp at the first snapshot → min 1.42 →
final 1.54). `trends_summary.json → governor_intraday`.

### 3.4. Reconciliation with the section dataset

The last snapshot's national totals — turnout 80.78%; Lula 64,256,232; Bolsonaro
59,826,041; blank 1,430,496; null 2,723,305 — are the `TRENDS_FINAL` reference
baked into `scripts/build_sections_csv_T2.py`; the per-section file built later
from the TSE open-data CSVs must reproduce them **to the exact vote** (and does:
`vs_trends_portal` all "match"). Two independent capture paths of the same
election agreeing at the last digit is itself a cross-check.

## 4. Shpilkin method (turnout distribution, "honest core")

Runoff turnout distribution: one bell, mode **82.75%**, σ 5.67 pp. The sample's
own q99.5 boundary: **92.5%**; the 2022-runoff control's boundary (both 2022
rounds pooled): **91.52%** — nearly the same, i.e. the distribution's shape did
not change between the honest election and this runoff; it shifted up with the
+1.86 pp turnout.

Above the boundary: **749,738 voters = 0.59% of ballots cast**, of which Lula
**453,486 votes (0.71% of his total)** and Bolsonaro **275,583 (0.46%)**. At the
stricter control boundary the tails are 1.37% and 0.95% of the candidates'
votes; the honest 2022 runoff's own tails at its own boundary were 0.57–0.62%.
The winner's tail is larger than the loser's but comparable to what the
reference elections produce — a descriptive count, not identified fraudulent
votes (`analysis_T2/figures/shpilkin_lula.png`, `shpilkin_bolsonaro.png`).

## 5. Electoral fingerprints + comet tail (Klimek et al. 2012)

Two-Gaussian mixtures on (turnout × candidate share), voter-weighted:

| | main component | 2nd component | weight | separated |
|---|---|---|---|---|
| Lula | (79.9; 64.0) | (81.3; 41.3) | 0.608 | no |
| Bolsonaro | (79.8; 33.4) | (81.4; 55.3) | 0.602 | no |

Both components of both candidates sit at normal turnout (≈80–81%); the "second"
component is the same geography seen from the other candidate's side, not an
anomalous cluster. No mass in the 90–100% turnout / 80–100% share corner where
documented extreme-fraud cases land (`fingerprint_lula.png`,
`fingerprint_bolsonaro.png`, against the controls `control_fingerprint_2026r2.png`).
The comet scatter is flat: national weighted turnout–share correlations
**+0.04 (Lula) / −0.04 (Bolsonaro)**, horizontal clouds (`comet_scatter.png`).

## 6. Integer peaks (Kobak et al. 2016)

Whole-percent turnout in **1.68%** of sections vs **1.70%** expected under the
size-adjusted Monte Carlo null: **z = −0.8**. Leader's share on a whole percent:
**z = −1.0**. At multiples of 5 — the stronger prior for hand-crafted numbers —
**|z| ≤ 1.6**. Documented falsification cases reach z of dozens
(`integer_peaks.png`).

## 7. Benford's law, second digit (Mebane 2006; Deckert et al. 2011)

Second digits of both candidates' counts (≈470k and ≈460k numbers ≥ 10):
maximum deviation from Benford's expectation **1.78 pp (Lula) / 2.15 pp
(Bolsonaro)**; theoretical χ² p < 0.01 for both. Against the smooth-count
(lognormal Monte Carlo) null Lula passes at **p = 1.0**; Bolsonaro sits at the
null's resolution floor (0.0025 = 1/401 — above all 400 draws).

This is the same formal rejection with the same smooth monotone profile as in
the 1st round on the same sections (report §5) and in the honest-2022-based
control runs: with hundreds of thousands of small-count sections, minuscule
structural biases (mixtures of section-size populations, truncation at small
counts) swamp the theoretical distribution. The digit profile is smooth with no
standing digit — not the signature of crafted numbers; a better-calibrated null
is needed before this test says anything substantive on data of this shape
(`digit_benford2.png`).

## 8. Last digit (Beber–Scacco 2012)

Last digits of counts ≥ 100: maximum deviation from uniform **0.53 pp (Lula) /
0.56 pp (Bolsonaro)**; combined excess of digits 0 and 5 at most **+0.45 pp** —
psychological rounding concentrates 0/5, this profile does not. The formal χ²
rejections (p ~ 1e-69) again reflect n ≈ 440k numbers × structural digit
asymmetries of small counts; the Monte Carlo smooth-count null is at its floor.
Flat within noise (`digit_last.png`).

## 9. 2D correlations by candidates and states (Kobak et al. 2012)

National weighted turnout–share correlations: **+0.043 (Lula) / −0.044
(Bolsonaro)**. By state, Lula's correlation ranges **−0.48 … +0.23** and
Bolsonaro's mirrors it (two-candidate shares sum to one). The same
heterogeneous-geography pattern the 1st round and 2022 show on these sections;
nationally the correlations collapse to ≈0. Alone they do not distinguish
mobilisation from manipulation (`correlations.png`).

## 10. Outliers vs neighbors and ML

Within-municipality robust-z rule (|z| > 4 on turnout or share): **5,018
sections (1.005%)** flagged, both directions, scattered — the baseline this rule
produces on the 1st round (0.93%) and on clean data of this size
(`neighbors_outliers.png`). Isolation Forest (contamination 1%): **4,993**
sections by construction; the top-scored are ordinary small sections
(`ml_anomalies.png`).

Duplicate identical result vectors: **2,348 rows in 1,172 groups, max group 3**.
In a two-candidate race the vector (voted, Lula, Bolsonaro, blank, null) has few
degrees of freedom, so small sections coincide by chance far more often than in
the 13-candidate first round; no large duplicate clusters. Flags are audit
candidates, not findings.

## 11. Self-test of the methods (synthetic injections)

- **Stuffing**: +1,870,878 synthetic ballots for the leader injected into 10% of
  sections above the threshold → his tail votes grow 453,486 → 7,048,037
  (**×15.5**) — the tail statistic explodes, as it should.
- **Painting**: turnout rounded to whole percentages in 5% of sections (24,772)
  → the integer-peaks statistic moves **z = −0.65 → 9.0**.

The battery demonstrably sees the two specific mechanisms it is built to detect,
on this very data (`analysis_T2/figures/selftest.png`). Sensitivity holds for
these mechanisms and parameters, not for every manipulation of comparable size.

## 12. Brazilian specifics: ballot-machine models

Four urna generations carried the runoff:

| Model | Sections | Registered | Turnout | Lula (two-way) |
|---|---|---|---|---|
| UE2013 | 12,455 | 4.30M | 74.85% | 53.8% |
| UE2015 | 87,500 | 28.24M | 80.76% | 52.0% |
| UE2020 | 200,504 | 63.24M | 80.90% | 51.5% |
| UE2022 | 198,746 | 62.97M | 81.08% | 51.8% |

The two-candidate split stays within a 2.3 pp band; the oldest fleet (2.7% of
the electorate, smaller municipalities) runs *highest* for Lula and the newest
is not the most pro-government — the spread tracks deployment geography and
electorate composition, not machine generation. Unadjusted differences neither
establish a machine effect nor certify machine security
(`analysis_T2/tables/urna_models.csv`).

## 13. Controls on the same sections

Two controls on the same sections: the honest 2022 runoff (same stage of the
cycle four years earlier; 472,027 sections matched) and the 2026 1st round (same
election three weeks earlier; 499,205 matched). Outputs:
`analysis_T2/metrics_control_T2.json`, figures `control_*.png`.

### 13.1. Shpilkin boundary from the 2022 control

The control boundary (q99.5 of the pooled 2022 rounds) is **91.52%**; the
runoff's own is **92.51%** — a 1 pp shift with unchanged distribution shape
(`control_turnout.png`). Runoff tails at the control boundary: **1.37% of
Lula's and 0.95% of Bolsonaro's votes**; the honest 2022 runoff's own tails at
its own boundary: **0.57–0.62%**. Judged at a borrowed boundary the honest
control would look "worse" too; nothing anomalous in relative terms.

### 13.2. Jumps 2026 R1 → 2026 R2 and 2022 R2 → 2026 R2 on matched sections

**2026 R1 → R2** (n = 499,205): Δturnout median **+1.91 pp** (national: +1.86),
MAD 1.59, q01/q99 −7.6/+7.8 — symmetric. Robust |z|>4 jumps: **1.115%** of
sections, **409 up / 5,156 down**: the flagged mass sits where turnout *fell*
between rounds — the opposite of a stuffing signature. ΔLula-share mirrors
ΔBolsonaro-share; the leader's share shows no skew towards the top Δturnout
deciles (`control_jumps_2026.png`).

**2022 R2 → 2026 R2** (n = 472,027): Δturnout median **+1.14 pp**, q01/q99
−7.4/+13.7; jumps **0.784%** (2,864 up / 754 down); Lula's share among flagged
sections ≈ his national share — jump sections favour neither candidate; swing
uniform across turnout deciles (`control_jumps_2022r2.png`).

### 13.3. Fingerprints on the 2026 runoff against the 2022 control

The 2026-runoff fingerprints (both candidates, both components at 79.8–81.4%
turnout, not separated) sit within the envelope the 2022 control elections'
fingerprints define on the same sections (`control_fingerprint_2026r2.png`).
No corner cluster, no high-weight anomalous component.

## 14. Runoff transfer matrix and validation of the round-1 prediction

The [1st-round paradox analysis](PARADOXES.md) fitted an ecological R1→R2 transfer
matrix on the 2022 pair of rounds, mapped 2026 candidates onto 2022 origins, and
produced a conditional scenario: **Lula 47.43%** two-candidate (bootstrap CI
47.39–47.45). The actual runoff came in at **51.79%** — the scenario missed by
**−4.36 pp**. The CI covered model resampling only; mapping and behaviour-change
uncertainty were excluded by construction, and the election had other plans.

Fitting the same model directly on the actual 2026 pair of rounds
(`scripts/run_paradox_analysis_T2.py` → `analysis/paradox/transfers_2026_matrix.csv`,
row-stochastic NNLS on section totals with 80/20 cross-validation and a 200-draw
bootstrap; held-out r² = 0.978, MAE = 3.06 votes/section; all 499,248 sections
matched 1:1). Headline rates (to Lula / to Bolsonaro / to blank+null):

| round-1 origin | votes | → Lula | → Bolsonaro | → blank/null | → stayed home |
|---|---|---|---|---|---|
| Lula | 53.88M | **98.85%** | 0 | 0.2% | 0.96% |
| Bolsonaro | 56.10M | 0 | **99.23%** | 0.6% | 0.16% |
| Cury | 3.45M | **69.28%** | 8.51% | 22.2% | 0 |
| Ferreira | 2.68M | 37.79% | 43.96% | 18.3% | 0 |
| Caiado | 2.61M | 38.17% | 54.03% | 7.8% | 0 |
| Zema | 0.33M | 0 | **88.14%** | 11.9% | 0 |
| Hertz (PSOL) | 0.04M | 89.2% | 0 | 10.8% | 0 |
| blank | 2.30M | **66.75%** | 0.4% | 30.0% | 0 |
| null | 3.67M | **57.48%** | 0.3% | 42.2% | 0 |
| runoff-only (NEW) | 10.69M | 62.38% | 32.75% | 4.9% | — |

For the NEW row the 2022-based scenario had 48.1 / 47.3.

Error decomposition per origin (`prediction_decomposition.csv`, contributions to
the −4.36 pp gap; negative = the scenario underestimated Lula): **blank −1.24,
Cury −1.15, null −0.91, Lula's own base −0.87** (loyalty 96.8% assumed vs 98.85%
observed), Caiado −0.22, Ferreira −0.21, Samara −0.06, Hertz −0.02; Zema +0.04.
The listed origins sum to −4.65 pp; turnout-composition effects offset
+0.29 pp.

**Reading.** The 2022-borrowed rates told a coherent story and still missed by
4.4 pp: runoff re-alignment in 2026 (turnout 80.78% vs 78.92% in R1, +1.86 pp —
2.96M more voters; new runoff-only voters; the eliminated candidates' voters
behaving differently than their 2022 counterparts did) dominates the mapping
noise. An ecological scenario is a baseline, not a forecast — the validation
quantifies exactly how far off a well-fitted one can be.

## 15. Limitations

- Aggregate published results, not a procedural audit of urnas or ballot
  handling; the urna-model comparison is unadjusted.
- The 2022 control is a reference election assumed honest, not a proven
  fraud-free ground truth; "matches the control" is descriptive evidence.
- Statistical non-detection ≠ proof of absence; assumptions, spatial dependence
  and multiple comparisons matter — the digit tests' standing rejections are the
  example (§7–8).
- The Shpilkin tail is a descriptive count; the q99.5 threshold is
  sample-defined.
- Transfer estimates are ecological: good aggregate fit (r² 0.978) does not
  validate individual rates, and the scenario validation (§14) shows a
  well-fitted ecological model can still miss the outcome by 4.4 pp.
- The intraday capture is sparse (13 snapshots, 8 distinct updates); the
  per-state table lags the national ticker early in the night, so the swing
  decomposition is anchored at the first ~85%-coverage snapshot.

## 16. Files and reproduction

- Section dataset + checks: `data/secoes_presidente_2026_T2.csv`,
  `data/secoes_presidente_2026_T2_checks.json` (`scripts/build_sections_csv_T2.py`)
- Intraday capture + analysis: `data/trends/` (`README.md` inside),
  `analysis/trends/{trends_summary.json, uf_final_twoway.csv,
  swing_decomposition.csv}` (`scripts/analyze_trends.py`)
- Forensics run: `analysis_T2/{metrics_T2.json, figures/, tables/}`
  (`scripts/run_forensics_T2.py`, `--lang {en,pt,es,ru}`)
- Controls: `analysis_T2/metrics_control_T2.json` (`scripts/control_forensics_T2.py`)
- Transfer matrix + prediction validation: `analysis/paradox/{transfers_2026_matrix.csv,
  transfers_2026_bootstrap_ci.csv, prediction_decomposition.csv,
  prediction_vs_actual.json}` (`scripts/run_paradox_analysis_T2.py`)
- Site figures (4 languages): `scripts/build_site_figures_T2.py` →
  `site/brazil-oct-2026-round-2/img/<lang>/`
- Everything runs from `analysis-tool/`:
  `uv run python ../brazil-oct-2026-round-1/scripts/<script>.py`
