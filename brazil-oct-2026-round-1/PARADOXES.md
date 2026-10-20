# Vote aggregation and conditional scenarios: Brazil, 04.10.2026

*Interpretation revised 20 October 2026; numerical outputs have not been recomputed.*

This analysis uses section-level totals. It describes geographic groupings,
estimates transfers between vote categories in 2022, and constructs conditional
2026 scenarios. It does not observe individual preferences or establish cloning,
strategic desertion, a Condorcet outcome, or a no-show paradox. The 2026 candidate
is **Flávio Bolsonaro**; the 2022 candidate is **Jair Bolsonaro**. Mapping one to
the other is a modelling assumption, not an identity of candidates or voters.

Data: `data/secoes_presidente_2026.csv`, `data/secoes_presidente_2022.csv`,
`data/secoes_deputado_2026_parties.csv`. Outputs: `analysis/paradox/`.

## 1. Geographic grouping and arithmetic aggregation

Clustering section-share profiles by Spearman correlation and average linkage
(distance 1−ρ) groups the five candidates below together. The label “anti-Lula”
is an analytical label, not proof of a common transferable electorate.

| Bloc | Members | Votes | % of valid |
|---|---|---|---|
| anti-Lula right | BOLSONARO + CURY + FERREIRA + CAIADO + ZEMA | 65,160,595 | **54.62** |
| Lula | LULA alone | 53,879,538 | 45.16 |

Their totals sum to 54.62% of valid votes. This arithmetic does not show that a
joint candidate would retain all those votes: turnout and preferences could
change. Geographic correlations do not establish interchangeable candidates or
make the actual runoff unnecessary. The bloc sum is a counterfactual holding
votes fixed, not a demonstrated voting paradox.

## 2. Reaggregation by territory

Under the illustrative winner-take-all rule, territories are weighted by
registered voters. The reported result assigns Flávio Bolsonaro 65.9% of this
constructed college, versus 51.0% of votes for the two leading candidates.
This calculation holds existing votes fixed; it does not estimate behaviour
under a different electoral system. Territory-count summaries should be checked
against the output tables before reuse, including treatment of ties and abroad.

## 3. Estimated transfers between the 2022 rounds

For 472,075 matched sections, non-negative least squares fits destination weights
to aggregate origin totals; rows are normalized. The 80/20 section validation
reports MAE 3.5 votes and R² 0.976. The held-out aggregate Lula share is 51.56%
versus an observed 50.86% in that sample, a +0.70 percentage-point discrepancy.

These are **ecological estimates**, not observed individual transitions. Good
prediction of section totals does not identify the transfer matrix uniquely or
validate each rate. A section split also does not establish spatial independence
or out-of-election performance. The two-round comparison is not a causal natural
experiment tracking voters.

| R1 2022 → R2 | Lula | Bolsonaro | blank | null | stayed home |
|---|---|---|---|---|---|
| Lula | **96.8%** | 0.0 | 0.3 | 1.2 | 1.6 |
| Bolsonaro | 0.0 | **99.8%** | 0.1 | 0.0 | 0.2 |
| Ciro | 58.1 | 30.0 | 6.7 | 5.1 | 0.0 |
| Tebet | 27.9 | **49.9** | 10.1 | 12.1 | 0.0 |
| Soraya | 0.0 | **59.1** | 10.1 | 30.8 | 0.0 |
| D'Ávila | 15.0 | **78.5** | 6.3 | 0.3 | 0.0 |
| Manzano / Vera / Péricles | 62–84 | 0–21 | 7–9 | 3–10 | 0 |
| blank | 0.0 | **46.1** | 39.0 | 14.9 | 0.0 |
| null | 26.7 | 0.2 | 3.5 | **69.6** | 0.0 |
| NEW (R2-only voters) | 48.1 | 47.3 | 1.6 | 3.0 | 0.0 |

For Tebet’s category, the fitted rates assign 49.9% to Jair Bolsonaro, 27.9% to
Lula and 22.2% to blank/null ballots. Do not describe the latter as observed
abstention. The model’s “NEW” category is likewise an aggregate construction,
not individually identified entrants. Bootstrap outputs (200 resamples):
`transfers_2022_matrix.csv`, `transfers_2022_bootstrap_ci.csv`.

## 4. Conditional application to 2026

The mapping matches 2026 candidates to 2022 vote categories by section-profile
similarity: Flávio→Jair Bolsonaro (ρ = 0.963), Lula→Lula (0.954),
Cury/Ferreira/Caiado→Tebet (0.35–0.49), Zema→D’Ávila (0.378).
Holding estimated transfer rates fixed yields Lula 47.43% and Flávio Bolsonaro
about 52.6% of the two-candidate total. This is a **conditional scenario**, not a
calibrated election forecast or proof that a bloc will reassemble.

The reported 95% bootstrap interval for Lula (47.39–47.45%) covers resampling of
the fitted transfer model only. It excludes uncertainty in candidate mapping,
changes in turnout and preferences between elections, and model misspecification.
The +0.70 pp validation discrepancy within 2022 is not a complete forecast error
bound and is not a justified automatic bias correction for 2026.

The script also reports candidate-removal scenarios:

| Candidate out | votes | → Lula | → Bolsonaro | Lula two-way without them |
|---|---|---|---|---|
| none (actual) | — | — | — | 47.43% |
| Cury | 3.45M | 27.9% | 49.9% | 48.68% |
| Ferreira | 2.68M | 27.9% | 49.9% | 48.74% |
| Caiado | 2.61M | 27.9% | 49.9% | 48.75% |
| Zema | 0.33M | 15.0% | 78.5% | 48.90% |

These are model-dependent outputs, not observed effects of withdrawal or evidence
that any candidate is (or is not) a decisive spoiler. The redistribution logic
and denominators need separate validation before using these numbers for public
claims about voting paradoxes. The former narrative’s 2.2M “gap to displacing
Lula” was the gap between the two leaders, not Lula’s gap to third place; that
argument is withdrawn. No monotonicity or no-show conclusion follows from it.

## 5. Presidential and legislative vote totals

Compare presidential votes and party federal-deputy votes in matched sections.
These are aggregate counts for different offices, not linked individual ballots.

| Party (candidate) | presidential | party deputy votes | pres ÷ dep | sections where deputy > presidential |
|---|---|---|---|---|
| PT (Lula) | 53.72M | 14.80M | **3.63** | 0.2% |
| PL (Bolsonaro) | 55.96M | 25.83M | **2.17** | 3.7% |
| AVANTE (Cury) | 3.44M | 1.84M | 1.87 | 13.6% |
| PTB (Ferreira) | 2.67M | 1.22M | 2.18 | 7.4% |
| PSD (Caiado) | 2.60M | **9.40M** | **0.28** | **68.9%** |
| NOVO (Zema) | 0.32M | **2.91M** | **0.11** | **79.7%** |

Caiado’s presidential total is about 28% of PSD’s deputy total; Zema’s is about
11% of NOVO’s. The complements 72% and 89% describe relative shortfalls between
totals, not measured individual desertion rates. Party totals do not identify
which people split their votes, where they went, or whether their motives were
strategic. The final column is the share of sections with deputy totals greater
than presidential totals, not a share of voters abandoning a candidate.

## 6. Limits and reproducibility

Ranked preferences and individual transitions are not observed. Establishing
Condorcet properties, strategic motives or candidate-removal effects requires
additional evidence or explicit behavioural assumptions. Geographic similarity
and aggregate predictive fit are insufficient on their own.

Run from the repository root:

```bash
cd analysis-tool
uv run python ../brazil-oct-2026-round-1/scripts/run_paradox_analysis.py
```

Outputs include `cloning_clusters.csv`, `cloning_corr_spearman.csv`,
`transfers_2022_matrix.csv`, `transfers_2022_bootstrap_ci.csv`,
`mapping_2026_to_2022.csv`, `desertion_parties.csv`, `paradox_results.json`.
Legacy output filenames are retained; they do not imply that cloning or desertion
has been identified. The 472,075-section match is between the two 2022 rounds;
the separate 2022–2026 forensic comparison uses 461,218 matched sections.
