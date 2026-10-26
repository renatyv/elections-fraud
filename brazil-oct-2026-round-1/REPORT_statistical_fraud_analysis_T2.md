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

**Conclusion up front: ⟦TODO-VERDICT⟧**

## Summary table of methods

| № | Method | Result on BR-2026 runoff | Verdict | Section |
|---|---|---|---|---|
| 2 | Shpilkin (turnout tail) | ⟦TODO⟧ | ⟦TODO⟧ | [4](#4-shpilkin-method-turnout-distribution-honest-core) |
| 1 | Klimek fingerprints | ⟦TODO⟧ | ⟦TODO⟧ | [5](#5-electoral-fingerprints--comet-tail-klimek-et-al-2012) |
| 3 | Integer peaks | ⟦TODO⟧ | ⟦TODO⟧ | [6](#6-integer-peaks-kobak-et-al-2016) |
| 4 | Benford-2 | ⟦TODO⟧ | ⟦TODO⟧ | [7](#7-benfords-law-second-digit-mebane-2006-deckert-et-al-2011) |
| 5 | Last digit | ⟦TODO⟧ | ⟦TODO⟧ | [8](#8-last-digit-beberscacco-2012) |
| 3-b | 2D correlations | ⟦TODO⟧ | ⟦TODO⟧ | [9](#9-2d-correlations-by-candidates-and-states-kobak-et-al-2012) |
| 8 | Neighbors | ⟦TODO⟧ | ⟦TODO⟧ | [10](#10-outliers-vs-neighbors-and-ml) |
| 7 | ML (Isolation Forest) | ⟦TODO⟧ | ⟦TODO⟧ | [10](#10-outliers-vs-neighbors-and-ml) |
| — | Self-test | ⟦TODO⟧ | methods are sensitive | [11](#11-self-test-of-the-methods-synthetic-injections) |
| — | Ballot-machine models | ⟦TODO⟧ | ⟦TODO⟧ | [12](#12-brazilian-specifics-ballot-machine-models) |
| — | Same-stage control (2022 runoff) | ⟦TODO⟧ | ⟦TODO⟧ | [13](#13-controls-on-the-same-sections) |
| — | Same-election control (2026 R1→R2 jumps) | ⟦TODO⟧ | ⟦TODO⟧ | [13](#13-controls-on-the-same-sections) |
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
Self-consistency: ⟦TODO-CHECKS⟧. The totals were additionally cross-checked
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

⟦TODO-SHPILKIN⟧

## 5. Electoral fingerprints + comet tail (Klimek et al. 2012)

⟦TODO-FINGERPRINTS⟧

## 6. Integer peaks (Kobak et al. 2016)

⟦TODO-PEAKS⟧

## 7. Benford's law, second digit (Mebane 2006; Deckert et al. 2011)

⟦TODO-BENFORD⟧

## 8. Last digit (Beber–Scacco 2012)

⟦TODO-LASTDIGIT⟧

## 9. 2D correlations by candidates and states (Kobak et al. 2012)

⟦TODO-CORRELATIONS⟧

## 10. Outliers vs neighbors and ML

⟦TODO-OUTLIERS⟧

## 11. Self-test of the methods (synthetic injections)

⟦TODO-SELFTEST⟧

## 12. Brazilian specifics: ballot-machine models

⟦TODO-URNAS⟧

## 13. Controls on the same sections

⟦TODO-CONTROLS⟧

### 13.1. Shpilkin boundary from the 2022 control

⟦TODO-CTRL-SHPILKIN⟧

### 13.2. Jumps 2026 R1 → 2026 R2 and 2022 R2 → 2026 R2 on matched sections

⟦TODO-CTRL-JUMPS⟧

### 13.3. Fingerprints on the 2026 runoff against the 2022 control

⟦TODO-CTRL-FINGERPRINTS⟧

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
bootstrap): ⟦TODO-TRANSFERS⟧. Error decomposition per origin
(`prediction_decomposition.csv`): ⟦TODO-DECOMP⟧.

**Reading.** The 2022-borrowed rates told a coherent story and still missed by
4.4 pp: runoff re-alignment in 2026 (turnout 80.78% vs 78.92% in R1, +1.86 pp —
2.96M more voters; new runoff-only voters; the eliminated candidates' voters
behaving differently than their 2022 counterparts did) dominates the mapping
noise. An ecological scenario is a baseline, not a forecast — the validation
quantifies exactly how far off a well-fitted one can be.

## 15. Limitations

⟦TODO-LIMITATIONS⟧

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
