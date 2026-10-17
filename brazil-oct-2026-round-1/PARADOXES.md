# Voting paradoxes in the Brazilian presidential election of 04.10.2026

*Which items of the catalogue [`paradoxes.md`](../paradoxes.md) are testable on this
data — and what they show. Brazil elects the president by plurality with runoff:
a candidate needs 50% of valid votes in round 1, otherwise the top two repeat
head-to-head. There are no ranked ballots, so the ranked-only part of the catalogue
(Condorcet cycles, best-is-worst, later-no-harm/help, truncation, twin) is out of
scope; but the splitting family (cloning, spoiler, frustrated majority), the runoff
family (center squeeze, lesser-evil) and the aggregation family (multiple-district)
are all live — and the 2022 election, with both rounds on the very same 472,075
sections, provides a natural experiment for measuring what runoff voters actually
do. Data: TSE section-level exports (`data/secoes_presidente_2026.csv`,
`data/secoes_presidente_2022.csv`, `data/secoes_deputado_2026_parties.csv`);
outputs in `analysis/paradox/`.*

## 1. Cloning — the runoff exists because a 54.6% majority ran as five candidates

Clustering the six candidates above 200k votes by the geographic profiles of their
section shares (Spearman correlation, average linkage at distance 1−ρ) produces
exactly two blocs — and the split is the story:

| Bloc | Members | Votes | % of valid |
|---|---|---|---|
| anti-Lula right | BOLSONARO + CURY + FERREIRA + CAIADO + ZEMA | 65,160,595 | **54.62** |
| Lula | LULA alone | 53,879,538 | 45.16 |

Every member of the five-candidate bloc is negatively correlated with Lula's
geography (ρ from −0.19 for Cury to −0.98 for Bolsonaro) and positively with each
other (ρ 0.11–0.34): they fish in the same electorate. Jointly that electorate is
a **majority — 54.62% of valid votes, 5.5M votes above the 50% line — yet no
member crossed 50% (Bolsonaro 47.03%), so the rule sends the election to a runoff.**
That is the *cloning paradox* in the catalogue's sense: five near-clones split a
winning coalition into a forced second round. Had the bloc run as one candidate on
exactly the same votes, it would have won outright on 4 October. The seven
remaining candidates (0.32% combined, all under 200k votes) sit below the
clustering threshold.

## 2. Multiple-district paradox — absent at every level

Counting territories instead of votes does not change the answer here (unlike the
Slovenian referendums, where it flips two outcomes): Bolsonaro leads in the
national vote, in **15 of 28** units (27 states + abroad; Lula 13, Amapá an exact
two-way tie) and in **3,009 of 5,757 municipalities** (Lula 2,748) — the same
order at every level, in round 1 and in the two-way count alike. An
electoral-college rule (winner-take-all by state, weighted by registered voters)
would amplify, not reverse: Bolsonaro's 51.0% two-way national share becomes
65.9% of the college, because Lula's margins concentrate in small-voter states
of the Northeast (Piauí 74.7%, Bahia 69.9% two-way) while Bolsonaro carries the
populous South/Southeast narrowly.

## 3. The 2022 runoff as a natural experiment — transfers measured, not assumed

Round 1 → round 2 of 2022 on 472,075 matched sections: for each origin (2022 R1
vote type, plus "NEW" = round-2-only voters) a row-stochastic destination vector
is fitted by non-negative least squares over all sections simultaneously. The
model reproduces the held-out sections (80/20 cross-validation: section MAE
3.5 votes, R² 0.976) and the national two-way share of the actual 2022 runoff to
+0.70 pp (predicted 51.56% vs observed 50.86% on held-out sections) — a small,
consistent pro-Lula bias, carried into §4 as an explicit error bar.

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

The runoff's *center squeeze* anatomy: Simone Tebet — the eliminated center —
split almost 2:1 to Bolsonaro (49.9 : 27.9 of her electorate, with another 22.2%
blank/null), while Ciro's centrist-left electorate went 2:1 to Lula. Full matrix
with bootstrap CIs (200 resamples): `analysis/paradox/transfers_2022_matrix.csv`,
`transfers_2022_bootstrap_ci.csv`.

## 4. Predicting the 2026 head-to-head — the runoff re-assembles the bloc

Mapping every 2026 candidate to the 2022 origin with the most similar precinct
profile (Spearman ρ; Bolsonaro→Bolsonaro 0.963, Lula→Lula 0.954, Cury/Ferreira/
Caiado→Tebet 0.35–0.49, Zema→D'Ávila 0.378, minors→Tebet/Manzano/blank) and
applying the 2022 transfer matrix to the 2026 round-1 vote totals:

- **predicted two-way Lula share 47.43%** (95% CI 47.39–47.45 over transfer-model
  resampling; add the §3 model bias of ≈ +0.7 pp pro-Lula, and the mapping's own
  uncertainty is not in the interval) — i.e. **Bolsonaro ≈ 52.6%**, a ~5-pp
  runoff margin, consistent with the bloc arithmetic of §1: the fragmented 54.6%
  majority re-assembles behind one name in round 2.

So the *frustrated majority* is present in round 1 (a majority of voters voted
against the runoff loser's opponent structure — the bloc held a majority no
member had) but does **not** survive into the predicted result: the round-1
leader is also the predicted pairwise winner; no reversal occurs.

**Spoiler counterfactuals** (candidate removed from round 1, votes redistributed
along the fitted transfer row of their origin; effect on the Lula two-way share):

| Candidate out | votes | → Lula | → Bolsonaro | Lula two-way without them |
|---|---|---|---|---|
| none (actual) | — | — | — | 47.43% |
| Cury | 3.45M | 27.9% | 49.9% | 48.68% |
| Ferreira | 2.68M | 27.9% | 49.9% | 48.74% |
| Caiado | 2.61M | 27.9% | 49.9% | 48.75% |
| Zema | 0.33M | 15.0% | 78.5% | 48.90% |

Every clone's exit *helps* Lula — but by 1.3–1.5 pp at most: none of the minor
candidates is a decisive spoiler, and the runoff *pair* is out of reach:
displacing Bolsonaro from the top two would have required a 52.7M-vote swing
(he led third-place Cury by 52,655,934), displacing Lula a 2.2M swing.

**No-show / perverse response: no room to fire.** The catalogue flags plurality
with runoff for non-monotonicity (a candidate harmed by receiving more votes, by
pushing a stronger rival into — or out of — the final). In 2026 the top-two
gaps (2.22M and 52.66M votes) make every such scenario unreachable; the 2022
data shows the behavioral side — between rounds, blank ballots tripled in
relative terms among eliminated candidates' electorates (Tebet 22.2%, Soraya
40.9% of their voters going blank/null or staying home) — lesser-evil pressure
dissolving into abstention and spoiled ballots rather than into transfers.

## 5. Lesser-evil desertion — the same section, two ballots, one hour apart

The presidential and federal-deputy votes are cast simultaneously on the same
machine. Comparing, per section, a candidate's presidential votes with the
deputy votes received by his own party:

| Party (candidate) | presidential | party deputy votes | pres ÷ dep | sections where deputy > presidential |
|---|---|---|---|---|
| PT (Lula) | 53.72M | 14.80M | **3.63** | 0.2% |
| PL (Bolsonaro) | 55.96M | 25.83M | **2.17** | 3.7% |
| AVANTE (Cury) | 3.44M | 1.84M | 1.87 | 13.6% |
| PTB (Ferreira) | 2.67M | 1.22M | 2.18 | 7.4% |
| PSD (Caiado) | 2.60M | **9.40M** | **0.28** | **68.9%** |
| NOVO (Zema) | 0.32M | **2.91M** | **0.11** | **79.7%** |

For the two finalists the presidential race *multiplies* their parties' chamber
vote (coattails + concentration). For Caiado and Zema it *divides* it: **72% of
the PSD electorate that voted for a PSD deputy abandoned Caiado presidentially**
(1 − 2.60M/9.40M; median section ratio 0.33), and 89% of NOVO's did the same to
Zema — voting for their party down-ballot while defecting to a "lesser evil" at
the top, exactly the *lesser-evil voting* pathology the catalogue attributes to
plurality-family rules. Where they went is consistent with §3/§4: both map onto
the Tebet/D'Ávila profiles, whose transfer rows run 2:1 and 5:1 to Bolsonaro.

## 6. What this data cannot test

Condorcet winner/loser and cyclical majorities, best-is-worst, later-no-harm /
later-no-help, truncation, twin — all require ranked ballots, which Brazil does
not collect. Whether an eliminated candidate *would have beaten* a finalist
head-to-head (the true center-squeeze test for 2026) is unknowable from categorical
counts; §4 gives the transfer-model's estimate, not a ballot-based proof.
Monotonicity and no-show are addressed only as margins (§4), not as observed
behavior. Strategic voting is unmeasurable without preference polls, which this
project does not collect. Everything above is computed on the votes as cast.

## Reproducibility

`cd analysis-tool && uv run python ../brazil-oct-2026/scripts/run_paradox_analysis.py`
(≈4 min; 200 bootstrap resamples) → `analysis/paradox/`:
`cloning_clusters.csv`, `cloning_corr_spearman.csv`, `transfers_2022_matrix.csv`,
`transfers_2022_bootstrap_ci.csv`, `mapping_2026_to_2022.csv`,
`desertion_parties.csv`, `paradox_results.json`. Section sums match the official
TSE totals to the exact vote (`data/secoes_presidente_2026_checks.json`); the
2022 control covers 472,075 sections present in both rounds; the deputy dataset
lumps six micro-parties (including Samara's União 80, Hertz's PDT 16) into a
common `votes_p00` column, so §5 covers the seven candidates whose party column
survives.
