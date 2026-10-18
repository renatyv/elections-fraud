# U.S. congressional 2024: expanded analysis, 18 October 2026

47,236 eligible 2024 reporting units, 110 current contest samples and 65 historical samples. 694 digit tests: 10 theoretical-null flags, 8 refined fitted-lognormal flags, 8 in common (1 current, 7 historical), after separate Benjamini–Hochberg adjustments. These are model-dependent screens, not a finding of fraud.

The earlier 17 October results remain a separate reproducible snapshot. Do not combine their test counts with this family: this rerun already includes their nonoverlapping units.

## Shpilkin / turnout tails

The own-sample registration-weighted 99.5th-percentile tails contain 0–1.489% of leading-bloc votes in current samples. No honest-core model is established, so there is no defensible stuffed-vote total or corrected outcome. Historical samples are comparisons, not matched-precinct controls.

## Turnout × result correlations

Weighted and county-demeaned correlations are exported for every tested contest. Geographic gradients and the sign changing between states make a national fraud interpretation unjustified. Support uses candidate votes / all ballots, including contest nonvoting.

## Klimek fingerprints

Two Gaussian components are fitted within each eligible contest. This is a descriptive surrogate for population heterogeneity, not the paper’s mechanistic fraud model; component weights are not fraud rates.

## Kobak integer peaks

525 metric screens, each with 1,000 binomial simulations; integer and multiple-of-five excesses form a jointly adjusted family of 1050 approximate one-sided normal-tail tests. 0 metric screens flag in that approximation. Sparse discrete tails and endogenous binomial probabilities require calibration; the table is a follow-up queue.

## Benford second digits and last digits

694 tests; counts must be ≥10 / ≥100, with ≥100 eligible counts per test. 10 theoretical and 8 lognormal-null flags after separate BH adjustments; 8 overlap. The initial fitted-lognormal null uses 400 simulations. All theoretical BH flags and all minimum-p Monte Carlo hits (12 tests) are rechecked with 20,000 simulations (minimum p=1/20,001); unselected tests receive p=1 before a fresh full-family BH adjustment. This avoids interpreting a coarse simulation floor as absence of a signal. Neither null models all election heterogeneity.

## Similar precincts and machine learning

2,753 county median/MAD flags; 1,451 Isolation Forest flags over current and historical unit–contest observations. County peers are not physical neighbors or socioeconomic matches. Isolation Forest uses 1% imposed contamination and no labeled fraud training set.

## Repeated vectors

1,673 repeated-vector rows (registration, ballots, DEM, REP, other). Repetition is not itself improbable without a conditional null; small precincts can match by chance. Splits and overlapping Washington sources are not counted as independent precincts.

## Ballot serials / batches and voting dynamics

Not identifiable: the downloads contain final aggregates, not ballot identifiers, batch custody records, time-stamped voting records or independent snapshots. XML file-generation timestamps are not voting or counting dynamics.

## Documentary / physical anchor

The existing Minnesota official hand review remains the physical anchor: all 657 precinct–contest tables across 219 precinct identities were acceptable under the official thresholds. It does not validate every state, the newly added precincts, or every ballot.

## Synthetic precinct sensitivity

Minnesota Senate: a fixed original cutoff of 92.56% gives 9,401 Republican tail votes before injection and 156,258 after 45,950 synthetic Republican votes are added. Rounded-turnout injection into 194 units changes z from -1.49 to 0.31. The rounded scenario does not flag, so detection power is limited. The tail also counts pre-existing votes moved above the cutoff; it does not recover the injection size. These scenarios do not calibrate a fraud rate.

## Flagged digit tests

```csv
sample,district,party,test,n_numbers,p_value,q_bh,p_null_mc,q_mc_bh,p_mc_refined,q_mc_refined_bh
CA2020 HOUSE,027,DEM,benford2,227,0.000338,0.0261,0.00499,0.288,0.0005,0.0434
CA2020 HOUSE,028,DEM,benford2,215,2.19e-10,2.53e-08,0.00249,0.192,5e-05,0.00496
CA2020 HOUSE,030,DEM,benford2,213,6.44e-18,4.47e-15,0.00249,0.192,5e-05,0.00496
CA2020 HOUSE,032,DEM,benford2,235,7.01e-12,9.73e-10,0.00249,0.192,5e-05,0.00496
CA2020 HOUSE,033,DEM,benford2,212,1.71e-08,1.69e-06,0.00249,0.192,5e-05,0.00496
CA2020 HOUSE,043,DEM,benford2,224,0.000677,0.047,0.00748,0.325,0.00075,0.0578
CA2020 PRESIDENT,STATEWIDE,DEM,benford2,15524,1.01e-14,3.49e-12,0.00249,0.192,5e-05,0.00496
OH2024 SENATE,STATEWIDE,REP,benford2,8798,9.44e-14,2.18e-11,0.00249,0.192,5e-05,0.00496
WA2020 PRESIDENT,STATEWIDE,DEM,benford2,7117,5.96e-12,9.73e-10,0.00249,0.192,5e-05,0.00496
WA2024 SENATE,STATEWIDE,DEM,benford2,7657,6.52e-06,0.000565,0.00499,0.288,0.0013,0.0902
```

## Largest integer screens (approximate adjusted q)

```csv
sample,district,metric,n_units,observed_integer,z_score,q_joint_normal_approx
MN2016 HOUSE,006,turnout,277,12,3.36244,0.25036
CA2024 HOUSE,29,share:votes:REP,135,6,2.69765,0.91653
MN2016 HOUSE,007,share:votes:REP,1316,102,2.46101,0.95306
CA2024 HOUSE,32,share:votes:DEM,173,8,2.41574,0.95306
CA2024 HOUSE,44,share:votes:DEM,167,7,2.38953,0.95306
VA2024 HOUSE,010,share:votes:REP,196,5,2.07313,1.0
CA2024 HOUSE,17,share:votes:DEM,217,8,1.99799,1.0
VA2024 HOUSE,008,turnout,170,4,1.99272,1.0
CA2024 HOUSE,48,share:votes:DEM,429,21,1.83787,1.0
CA2020 HOUSE,043,turnout,229,10,1.82714,1.0
```


## Coverage and source limitations

Source limits retained: Washington statewide data replaces King County, with registration differences of 13 versus the recorded statewide table and 4,521 versus the active-voter reconciliation workbook; every county ballot total and all 33 congressional candidate columns reconcile. Iowa, West Virginia and Ohio are pinned mirror copies, not freshly retrieved official files. Ohio write-ins are missing (640 Senate, 4 House district 2 and 29 House district 11 votes versus the Clerk); named-candidate digits remain observable. West Virginia’s other-candidate pool is short by 15 Senate and 174 House district 1 votes. None is filled with inferred precinct counts.
Geography and exclusions: split House precinct rows are excluded when full-precinct turnout cannot be assigned to a fragment. California suppression, above-registration counts, zero denominators and missing joins remain excluded. Virginia and South Carolina use name joins with numeric padding removed, collision checks and outer-join audits; unmatched rows stay unknown. South Carolina precinct ballots and registration sum exactly to its county/state Election History totals; VREMS voter-history denominators are not substituted. Vermont’s 247 town rows contain partial district results in multi-district towns and incomplete statewide candidate totals, so all are excluded from the combined diagnostics. Maryland administrative participation is still incompatible. Wyoming and North Dakota lack registration; Pennsylvania lacks ballots; North Carolina supplies registration only. Provisional OCR rows and Kentucky’s new four PDFs remain outside the sample: transcript arithmetic alone does not validate the needed joins, and Kentucky’s published turnout has an unofficial/roll-timing caveat.

sample,rows,eligible,unknown,zero_denominator,over_registration,contest_over_ballots,source_exclusion
CA2020 HOUSE,21346,17241,0,3928,357,0,0
CA2020 PRESIDENT,21346,17241,0,3928,357,0,0
CA2024 HOUSE,25245,17870,1974,5431,409,0,78
CA2024 SENATE,25245,17867,1974,5431,409,3,78
IA2024 HOUSE,1653,1378,2,271,273,0,0
ID2024 HOUSE,986,974,1,11,10,1,0
MD2024 SENATE,2227,0,514,4,16,335,2227
MN2016 HOUSE,4120,4083,0,31,6,0,0
MN2020 HOUSE,4110,4075,0,33,2,0,0
MN2020 SENATE,4110,4075,0,33,2,0,0
MN2024 HOUSE,4103,4075,0,28,0,0,0
MN2024 SENATE,4103,4075,0,28,0,0,0
MS-Union2024 HOUSE,20,20,0,0,0,0,0
MS-Union2024 SENATE,20,20,0,0,0,0,0
OH2024 HOUSE,8915,8841,0,0,0,0,74
OH2024 SENATE,8878,8878,0,0,0,0,0
SC2024 HOUSE,2674,2075,366,206,154,0,90
VA2024 HOUSE,2695,2523,156,2,0,2,38
VA2024 SENATE,2675,2531,144,2,0,2,0
VT2024 HOUSE,247,0,0,0,0,0,247
WA2020 PRESIDENT,7436,7278,85,68,6,1,0
WA2024 HOUSE,7824,7821,0,2,3,0,0
WA2024 SENATE,8136,7822,202,111,3,0,0
WV2024 HOUSE,1651,1613,2,35,35,0,0
WV2024 SENATE,1651,1613,2,35,35,0,0


## Voting paradoxes

Ten Clerk bounds were recalculated from the full contest inventory; the new inputs do not provide preference rankings.

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

state_po,office,district,margin,other_votes,minimum_transfer_if_rest_abstain,minimum_transfer_if_rest_back_leader
AZ,US HOUSE,006,10822,10850,10823,10837
CO,US HOUSE,008,2449,9425,2450,5938
IA,US HOUSE,001,799,967,800,884
MI,US SENATE,STATEWIDE,19006,170821,19007,94914
NC,US HOUSE,001,6307,9949,6308,8129
NV,US SENATE,STATEWIDE,24059,42197,24060,33129
OH,US HOUSE,009,2382,15381,2383,8882
OR,US HOUSE,005,10945,29508,10946,20227
PA,US SENATE,STATEWIDE,15115,179662,15116,97389
WI,US SENATE,STATEWIDE,28781,74014,28782,51398

## Reproduction

```sh
python3 usa-2024/scripts/check_turnout_continuation.py
MPLCONFIGDIR=/tmp/usa-matplotlib OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 analysis-tool/.venv/bin/python usa-2024/scripts/expanded_analysis.py
MPLCONFIGDIR=/tmp/usa-matplotlib OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 analysis-tool/.venv/bin/python usa-2024/scripts/refine_digit_nulls.py
MPLCONFIGDIR=/tmp/usa-matplotlib OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 analysis-tool/.venv/bin/python usa-2024/scripts/build_expanded_report.py
```

Prerequisite: existing extraction/reconciliation outputs described in RECONCILIATION.md. No raw source is modified. Fixed random seeds: toolkit defaults; self-test seed 7. Digit Monte Carlo: 400 initial replicates, then 20,000 for theoretical BH flags or minimum-p hits, unselected p=1 for the refined full-family adjustment; integer peaks: 1,000 replicates. Every tested sample has ≥100 eligible rows and both major blocs.

Outputs in analysis/expanded/ include all eligible/excluded joins, coverage, digit nulls and BH adjustments, mixtures/tails/correlations, integer screens, outliers, repeated vectors, source totals, synthetic tests and exact paradox bounds.

Sources: [Clerk](https://clerk.house.gov/member_info/electionInfo/2024/statistics2024.pdf), [integer percentages paper](https://arxiv.org/abs/1410.6059), and the linked local download manifests in TURNOUT_EXPANSION.md.
