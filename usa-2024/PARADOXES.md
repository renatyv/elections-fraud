# U.S. congressional voting paradoxes, 2024: official-source update

**Rechecked 18 October:** the expanded download analysis recalculates the same ten nationwide bounds and verifies their strict-win thresholds. New precinct files supply no same-contest lower rankings. [Expanded analysis](EXPANDED_REPORT.md) includes every root criterion and source-reconciliation limits; [recomputed bounds](analysis/expanded/paradox_bounds.csv) include required transfer fractions.

17 October 2026. **Ten arithmetic spoiler bounds; no demonstrated preference
paradox.** This replaces the previous seven-race MEDSL-only screen.
Source: [House Clerk 2024 official-source statistics](https://clerk.house.gov/member_info/electionInfo/2024/statistics2024.pdf).
All 435 House and 33 regular Senate contests are inventoried; 448 plurality
contests with two or more records are screenable. Alaska/Maine ranked choice
and Louisiana majority-rule races are excluded; unopposed contests without
printed vote counts retain missing values. Candidate fusion lines are combined.
Blank, void, over/under-votes and Nevada “None of These Candidates” are excluded.
Pooled write-ins, “Scattering”, “All Others” and “Miscellaneous” remain pooled
candidate categories, not fictitious individual candidates.

## Exact counterfactual bounds

| State | Office | District | Leader | Margin | Other votes | Runner-up votes needed if rest abstain | Runner-up votes needed if rest back leader |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AZ | US HOUSE | 006 | Juan Ciscomani | 10822 | 10850 | 10823 | 10837 |
| CO | US HOUSE | 008 | Gabe Evans | 2449 | 9425 | 2450 | 5938 |
| IA | US HOUSE | 001 | Mariannette Miller-Meeks | 799 | 967 | 800 | 884 |
| MI | US SENATE | STATEWIDE | Elissa Slotkin | 19006 | 170821 | 19007 | 94914 |
| NC | US HOUSE | 001 | Donald G. Davis | 6307 | 9949 | 6308 | 8129 |
| NV | US SENATE | STATEWIDE | Jacky Rosen | 24059 | 42197 | 24060 | 33129 |
| OH | US HOUSE | 009 | Marcy Kaptur | 2382 | 15381 | 2383 | 8882 |
| OR | US HOUSE | 005 | Janelle S. Bynum | 10945 | 29508 | 10946 | 20227 |
| PA | US SENATE | STATEWIDE | Dave McCormick | 15115 | 179662 | 15116 | 97389 |
| WI | US SENATE | STATEWIDE | Tammy Baldwin | 28781 | 74014 | 28782 | 51398 |

For top-two margin M and other-candidate pool O, the bound is O > M. If x
other voters move to the runner-up and the rest abstain, x ≥ M+1 reverses the
result. If all remaining other voters back the leader, x ≥ floor((O+M)/2)+1.
These are integer strict-win thresholds, not transfer estimates. Existing top-two
votes are held fixed; no turnout changes or sincere preferences are observed.
For Iowa House 1 the 967 pooled write-ins exceed the margin of 799, but no
assumption that they are one candidate or would vote as a bloc is justified.

The earlier Arizona Senate bound disappears (official M=80,574, O=76,818).
Iowa House 1, Michigan Senate, Nevada Senate and Oregon House 5 enter the list.
Pennsylvania's margin becomes 15,115 rather than 16,910. Luna 6, reasoning low,
independently calculated the four fields of all ten rows plus Arizona Senate
from 11 rendered PDF pages; the parser and model agree. This validates those
transcriptions, not voters' hypothetical behavior. Retain source PDF hash and
page locators in the downloadable tables because the compilation is a snapshot.

## Every root paradox family: observed status

| Root criterion | What the actual returns establish |
|---|---|
| Frustrated majority / Condorcet winner | Unknown: candidate totals do not contain same-contest pairwise preferences |
| Condorcet loser / absolute loser | Unknown: an elected plurality leader need not be pairwise winner or loser |
| Condorcet cyclical majorities | Unknown without a pairwise matrix |
| Center squeeze | Unknown: requires lower preferences and, for elimination claims, the relevant rounds |
| Spoiler / independence of irrelevant alternatives / SCC | Ten arithmetic bounds only; withdrawals and preference transfers are unobserved |
| Cloning | Unknown: party labels do not establish preference clones |
| Best-is-worst | Unknown: reverse rankings are absent |
| Lesser-evil / strategic voting | Unknown: votes do not reveal sincere favorites or voting incentives |
| Absolute majority | No new empirical violation: ten leaders lack a majority of included candidate votes; this is not proof a different candidate had a majority of first preferences |
| Pareto dominance | Unknown from totals; ordinary plurality with complete strict rankings cannot elect a universally dominated candidate |
| Later-no-harm / later-no-help | Ordinary plurality ignores later rankings, satisfying both; no empirical ranking test is possible |
| Perverse response / monotonicity | Ordinary plurality is monotonic for fixed candidates and tie-breaking; no observed ranked-rule violation established |
| No-show / participation / twin | Ordinary plurality satisfies participation for fixed candidates and tie-breaking; no Alaska/Maine ranked-ballot counterfactual computed |
| Multiple-district paradox / map effects | No legal alternative-map test: need geometry, population, district rules and map constraints; seat/vote imbalance alone does not establish the specific root pathology |
| Reinforcement / consistency | Ordinary plurality is consistent with a fixed candidate set and coherent tie-breaking; preference aggregation not inferred from cross-office totals |
| Truncation | Ordinary plurality never reads lower ranks, so truncating them cannot change the tally |
| Path independence | No empirical candidate-removal experiment; no lower preferences assumed |

Rule properties are conditional mathematical statements about the ordinary
plurality rule, not empirical declarations that U.S. elections have no paradoxes.
Alaska/Maine require their own ranked-ballot rules and data; Louisiana requires
its own majority threshold. Cross-office split tickets cannot replace rankings
among candidates in the same contest. Final results have no chronology or
candidate similarity metric.

## Evidence limits and reproducibility

[Candidate totals with PDF pages](analysis/clerk_candidate_totals.csv),
[all official-source race screens](analysis/clerk_race_screens.csv),
[MEDSL comparison](analysis/clerk_medsl_race_reconciliation.csv), and
[precinct/statistical report](PRECINCT_REPORT.md). Code:
`scripts/clerk_results.py`, `scripts/verify_clerk.py`.

The Clerk source aggregates official returns, not an independent ballot-level
recount. Maine House 2 totals reflect a ranked count while Alaska's reported
candidate totals do not reconstruct all ranked transfers; both are excluded
from plurality claims. Renewed Alaska/Maine downloads returned verification/
access-denied pages; no CVR ballots or full preference rankings were acquired.
No Condorcet, cloning, no-show or sincere lesser-evil claim is inferred from
unavailable evidence. No deployment was performed.
