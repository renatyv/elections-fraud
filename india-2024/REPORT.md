# India, Lok Sabha 2024: statistical fraud analysis and the Uttar Pradesh Form 20 dataset

Report on running the election-forensics methods from the review
[`fraud_detection_methods.md`](../fraud_detection_methods.md) with the
[`analysis-tool/`](../analysis-tool/) pipeline over everything the project
collected for the 2024 Indian general election. Analysis date: 15.10.2026.

**Conclusion up front: at every level the collected data can support, the
2024 Lok Sabha election shows no systematic statistical traces of the kind
these methods treat as fingerprints of fraud.** The Shpilkin tail, comet
cloud, integer peaks, turnout×leader correlations, last-digit tests and the
swing vs 2014 are all where honest elections put them — nationally (542
constituencies), in Uttar Pradesh at the assembly-segment level (81 segments),
and in the digit statistics of ~105k UP polling stations. The self-test
confirms the methods are sensitive on this data. The structural limitation is
granularity: official 2024 results are published per constituency, and the
booth-level Form 20 recovery (this project's dataset) carries **no per-station
electors**, so the flagship turnout-based tests cannot be run at booth level
for 2024; the same machinery on GE-2014 UP — the one year with official
per-booth electors — shows what honest UP booth data looks like, and it looks
like 2024's digit statistics.

This is a statement about *statistical* traces at these granularities, not a
certificate about the election; see sections 12–13 for what this analysis
cannot see.

## Summary table of methods

| № | Method | Level(s) | Result | Verdict | § |
|---|--------|----------|--------|---------|---|
| 2 | Shpilkin (turnout tail) | PC-2024, UP AC-2024 | boundary from 2014 control; tail votes **0** nationally and in UP; recount ±0.2 pp | **clean** | 2 |
| 1 | Klimek fingerprints / comet | PC-2024, UP AC-2024 | no second cluster, no separation; comet cloud compact, sloped down | **clean** | 3 |
| 3 | Integer peaks | PC-2024, UP AC-2024, UP booths | z(turnout) +0.3 / −0.8; booth-level 2024 BJP-share z=−3.1 (deficit, not excess); 2014 booths z=−1.1 | **clean** | 4 |
| 4 | Benford 2nd digit | PC-2024, UP AC, UP booths | p_mc 0.29/0.33 at PC/AC; booths p_mc=0.002 *identically in the honest 2014 control* | **structural artifact, not fraud** | 5 |
| 5 | Last digit (Beber–Scacco) | PC-2024, UP AC, UP booths | BJP p_mc 0.63 / 0.39 / 0.57; max deviation ≤0.4 pp | **clean** (SP mild, §6) | 6 |
| 3b | 2D correlations | PC-2024, UP AC | BJP −0.12 / −0.29 (negative!); regional parties +0.3–0.4 in their strongholds | **heterogeneity, not fraud** | 7 |
| 8 | Neighbours / ML outliers | PC-2024, UP AC | 19 PCs (3.5%) at \|z\|>4, 6 PCs ML — small stations/PCs, no pattern | **audit candidates** | 8 |
| 9 | Swing vs previous election | PC-2024 vs PC-2014 (507 linked) | 0 units flagged (turnout+jump), 2 turnout-only | **clean** | 9 |
| — | Self-test (synthetic injections) | all levels | stuffing detected (×18M signal growth nationally), integer peaks z→11.8 | **methods sensitive** | 10 |
| — | 2014 booth-level control (UP) | 137,969 stations | Shpilkin tail 0.75%, turnout peaks z=−1.1, corr +0.06 — the honest baseline | **baseline** | 11 |
| 6, 9, 10 | Ballot series / intraday dynamics / anchors | — | not applicable (no data collected) | — | 12 |

---

## 1. Data and self-consistency

Four analysis datasets were built from the collected sources
(`scripts/build_mai_datasets.py`):

| dataset | units | source | registered | ballots |
|---|---|---|---|---|
| `mai_pc_2024` | 542 PCs | official ECI in-rolls constituencywise export | 977,965,560 | 646,420,869 |
| `mai_pc_2014` | 543 PCs | ECI 2014 candidate-wise + PC turnout | 834 M | 554 M |
| `mai_up_ac_2024` | 297 ACs (81 with electors) | Form 20 recovery, cleaned | 32,426,250 (subset) | 17,742,025 |
| `mai_up_booth_2014` | 137,969 booths | ECI 2014 booth results + booth electors | 127,813,583 | 78,557,002 |

Sanity anchors: national turnout 66.10% (ECI's published final figure 65.79%
uses a narrower electors snapshot); 2014 turnout 66.40% (official 66.4%);
rejected ballots 2024 = 7.43 M (1.15% of ballots). Surat (won unopposed, no
poll) is absent from the ECI export — 542, not 543 PCs.

**Form 20 integrity.** The UP booth table (109,952 stations, 1.16 M
station-candidate rows) was parsed under per-row arithmetic checksums
(Σ candidate votes = valid; valid + NOTA + rejected = total). Aggregated to
ACs and compared with the official ECI constituency results: every PC's delta
is ≤ 0 (nothing exceeds the official count); of the 50 PCs with all their
ACs recovered, 11 match within ±0.5%; larger shortfalls are partial source
files (fewer stations than the AC has, worst: Gautam Buddha Nagar −51%).
See `data/form20/parsed/validation_form20.txt`.

**Party labels for Form 20 candidates.** Form 20 lists candidates without
parties; official results are alphabetical, form order is not. Candidate
columns were labeled by rank-pairing each PC's Form-20 column sums against
the official PC candidate totals (both sorted descending; micro-candidates
beyond the shorter list fall to "Others"). Validation
(`party_matching_diagnostics.csv`): for PCs with ≥90% station coverage
(median coverage 93.8%), labeled BJP/SP/INC/BSP totals track the
coverage-scaled official totals within <5%; deviations up to ~13% occur only
in the four low-coverage PCs (Amroha 19%, Farrukhabad 20%, Kannauj 11%,
Mainpuri 37%) — party columns for those PCs are approximate. Since all
stations of a PC share one ballot, the rank map applies uniformly to the
PC's ACs and booths.

**2014 booth control.** The two official ECI 2014 exports (votes, electors)
disagree on 445 booth keys of 138k (0.3%, ratios up to 22× — clearly
mismatched stations, not stuffing); those rows are dropped. The 2014
turnout numerator is valid votes only (rejected votes are not in the export),
understating turnout by ~1 pp uniformly.

## 2. Shpilkin method (turnout distribution, honest core)

The honest-core boundary is taken from the control election's turnout
distribution (99.5th percentile of elector-weighted turnout), not from the
audited data itself.

- **National (542 PCs):** boundary 87.6% (2014 control). No constituency
  votes to the right of it: **anomalous votes for the leader = 0**. BJP
  result recomputed without the anomalous component: 36.73% vs observed
  36.50% — i.e. the "correction" moves the *wrong way* to be fraud
  (there is no tail to remove).
- **UP, 81 assembly segments:** boundary 82.8% (UP-2014 AC control), tail
  votes **0**, honest share = observed share (39.93%).

The turnout distribution itself is a clean single mode with no right-side
structure (`analysis_pc/figures/shpilkin_core.png`,
`controls_turnout.png`).

## 3. Electoral fingerprints, comet tail (Klimek et al. 2012)

- **National:** the turnout × BJP-share cloud is a compact horizontal band;
  high-turnout PCs are *not* higher-BJP (comet points up-left if anything).
  The 2-component Gaussian mixture gives a degenerate second component
  (weight 0.18 pinned near 0% share) — no separated fraud cluster.
- **UP ACs:** no separation (`separated=false`); with 81 units the mixture
  is unstable, and the "anomalous" component it finds (mean 54.8% turnout /
  47.6% BJP) sits *inside* the main cloud — that is heterogeneity of
  segments, not a cluster at 90–100% turnout as the method's fraud
  signature requires.

## 4. Integer peaks (Kobak, Shpilkin, Pshenichnikov 2016)

- National PCs: 1.11% of constituencies have integer turnout vs 0.98%
  expected, z = +0.3. At ~1.8 M electors per unit an integer turnout is
  a coincidence of rounding, and the test is nearly vacuous — reported for
  completeness.
- UP ACs: 0 of 81 integer turnouts (z = −0.8).
- **UP booths, 2024** (turnout not computable; test applied to the leader's
  share of station ballots): 7.85% of stations at integer BJP share vs 7.95%
  binomial null, **z = −3.1 — a deficit**, the opposite of the
  human-written-protocol signature.
- **UP booths, 2014 (control):** integer turnout 2.02% vs 2.05% null
  (z = −1.1) — the honest baseline looks the same.

## 5. Benford's law, second digit (Mebane 2006; Deckert et al. 2011)

At constituency and AC levels the tests are comfortable (BJP p_mc 0.29 /
0.33). At booth level all four major parties reject the single-lognormal
Monte-Carlo null (p_mc ≈ 0.002, max deviation ≤1.3 pp) — with 70–96
thousand numbers per party, even 1 pp deviations are "significant". The
decisive observation: **the honest 2014 booth control rejects the same null
with the same strength** (BJP p_mc = 0.002). A fabrication signal would have
to be absent in 2014 and present in 2024; instead the deviation is a stable
property of UP booth-count structure (a mixture of urban/rural booth-size
regimes, which a single fitted lognormal does not describe). Read as in the
Brazil report: not applicable as a fraud indicator here.

## 6. Last digit (Beber–Scacco 2012)

| dataset | party | n | p (χ²) | p_mc | max dev |
|---|---|---|---|---|---|
| PC-2024 | BJP | 542 | 0.24 | 0.63 | 0.7 pp |
| UP AC-2024 | BJP | 81 | 0.30 | 0.39 | 1.9 pp |
| UP booths 2024 | BJP | 81,652 | 0.46 | 0.57 | 0.2 pp |
| UP booths 2024 | SP | 66,542 | 0.007 | 0.027 | 0.4 pp |
| UP booths 2014 | BJP | 107,722 | 0.04 | 0.09 | 0.3 pp |

The SP booth-level deviation is the single mildest flag in this report:
excess of trailing 0s and 1s (+0.37 / +0.22 pp, deficit of 8s −0.25 pp).
Fabricated-count signatures in the literature are an order of magnitude
larger (several pp on 0/5); this is within what booth-size rounding
structure produces, and the same test on 2014 BJP sits at p_mc = 0.09.
Verdict: consistent with noise; worth re-checking when the missing ACs are
recovered, not a fraud finding.

## 7. 2D correlations (Kobak et al. 2012)

Weighted Pearson r between turnout and party result:

- National: **BJP −0.12**, INC +0.08, SP −0.34 (its strongholds are
  lower-turnout UP segments), AITC +0.38, YSRCP +0.33.
- UP ACs: BJP −0.29, INC +0.25.
- UP booths 2014 (control): BJP +0.06.

The "party of power" analogue has *negative* turnout correlation — the
comet-tail signature is a strongly positive one. The positive correlations
of regional parties in their own strongholds (Turnout is higher where the
dominant regional party mobilises) are the classic benign heterogeneity
pattern the method's critics point to (as in the UK), and they mirror
each other between government and opposition coalitions rather than
pointing one way.

## 8. Outliers vs neighbours and ML (Myagkov–Ordeshook–Shakin 2009; Zhang et al. 2019)

19 of 542 PCs (3.5%) exceed |z|>4 against their own state's median
(handful in every large state; the usual suspects are small PCs and
northeastern states with idiosyncratic electorates). Isolation Forest flags
6 PCs (≈1%, its design share). In UP ACs: 4 and 1. These are audit
candidates by construction, not evidence; no geographic or party pattern
clusters them.

## 9. Swing vs the previous election

507 PCs matched by name between 2014 and 2024 (renames and the Telangana
split account for the rest). **Zero** constituencies combine a turnout jump
>15 pp with a leader-share jump >15 pp; 2 exceed the turnout jump alone
(both remote/small PCs). The Δturnout/Δshare cloud is structureless
(`analysis_pc/figures/swing_previous.png`).

## 10. Self-test of the methods (synthetic injections)

Additive stuffing re-injected into the clean data is detected: nationally
the tail signal grows from 0 to 17.6 M votes and integer-turnout peaks jump
z 0.4 → 11.8; in UP ACs 0 → 0.87 M; at the 2014 booth level the injection
multiplies the tail ×7 and peaks z −1.0 → 18.1. On this data the machinery
would see millions of stuffed ballots; it sees none.

## 11. The 2014 booth-level control (what honest UP booths look like)

GE-2014 is the only cycle for which ECI published both per-booth electors
and per-booth candidate votes; it doubles as the validation that the
booth-level machinery works on UP-scale data:

- Shpilkin: own boundary 92.1%, tail = 0.75% of BJP votes (honest tails are
  never exactly zero — this calibrates what "0 tail at coarser levels"
  means);
- integer turnout peaks 2.02% vs 2.05% (z = −1.1);
- turnout×BJP r = +0.06;
- leader-share integer peaks: z_mult5 = −0.16 (the ×5 variant, robust to
  the single-integer deficit artifact).

Every 2024 statistic above sits inside this baseline.

## 12. Methods not applicable to this data

- **Ballot-serial forensics (Podlazov–Makarov):** EVMs, no paper serials.
- **Intraday/counting dynamics:** ECI published only cumulative turnout
  snapshots per phase; nothing booth-timed was captured.
- **Non-statistical anchors** (parallel count, webcam reconciliation):
  out of scope for this repository.

## 13. Limitations — what this analysis cannot see

1. **Granularity.** The national tests run on 542 units of ~1.8 M electors.
   Fraud concentrated in a few hundred booths inside one constituency is
   statistically invisible at that level, and the integer-peak test is
   nearly vacuous there.
2. **The 81-AC UP subset is not random.** Form 20 electors survive only
   where the PDF header field was filled (Encore digital forms leave it
   blank). Selection correlates with district administration type.
3. **Booth-level turnout for 2024 does not exist in Form 20** (per-station
   electors are structurally absent — confirmed against the raw Encore
   text). The booth-level 2024 tests are therefore share/digit-based only.
4. Party labels in the four low-coverage PCs are approximate (§1).
5. The 2014 controls use valid votes as the turnout numerator (−1 pp
   uniform shift) and drop 445 mismatched booth keys.
6. EVM/VVPAT specifics (machine allocation, candidate symbol positions)
   are outside all these models.

## 14. What scanning the remaining Form 20s would and would not unlock

Completing the collection (106 of 403 ACs missing, 7 guard-flagged
Farrukhabad files, 5 unidentifiable Firozabad files; ~20 districts with no
Wayback capture) is worth doing for coverage, but it is important to be
clear about the shape of the payoff:

**Would unlock**
- Booth-level digit tests, share-peaks and neighbour-outlier detection at
  full state coverage (all 403 ACs instead of 297);
- exact per-AC/per-PC reconciliation everywhere (today 11 PCs validate
  within ±0.5%);
- per-candidate booth geographies (candidate-level Benford, coalition
  transfer analysis between 2014 and 2024 on matched segments);
- a second state: the Wayback survey found Andhra Pradesh (406 Form 20
  URLs), Odisha and Telangana with 2024-era captures — a two-state dataset
  changes the character of any publication.

**Would not unlock, by construction**
- booth-level *turnout* tests (Shpilkin tail, comet, integer turnout peaks,
  turnout-share correlations at station grain): Form 20 has no per-station
  electors. The missing input is **Form 17C / polling-station elector
  data** (ECI's turnout app exports, RTI releases, or CEO-site supplementary
  statistics). Any one of those joined to this dataset converts every
  turnout-based method to 110k-station resolution overnight. That join —
  not more Form 20s — is the highest-leverage next acquisition.

## 15. The dataset for publication and its uniqueness

The release package is `release/` (data card: [`release/DATACARD.md`](release/DATACARD.md)):
the booth long-table (1.16 M rows, gzipped), the party-labelled assembly-segment
table, the national constituency table, the source-PDF manifest, and full
provenance/validation notes.

**Is the scraped data unique? Yes** (verified 15.10.2026 against ECI
infrastructure, Kaggle, GitHub, Hugging Face, Zenodo, Dataverse and the
academic literature):

- The ECI's central 2024 publications stop at candidate-per-constituency; the
  results portal itself stated the "final data for each AC/PC will be shared
  in Form-20" — the ECI designates exactly the district documents this
  recovery is built from, and litigated through 2024–26 *against* publishing
  booth-level Form 17C data (ADR v. ECI, Supreme Court of India).
- The only prior polling-station dataset of this kind — Jensenius, Chhibber,
  Alam, Gupta, Somanathan, *Scientific Data* 2025
  ([DVN/KKOWNJ](https://doi.org/10.7910/DVN/KKOWNJ)) — covers 2009/2014
  (11 states incl. UP) and 2019 (UP only); it has **no 2024 data**. This
  dataset is the 2024-UP continuation of that series, not a duplicate.
- No booth-level 2024 dataset (any state) exists on Kaggle, GitHub, Hugging
  Face, Zenodo or Dataverse; the finest open 2024 granularity elsewhere is
  assembly-segment level (OpenCity). No booth-level analysis of UP-2024 has
  been published anywhere.

A practical corollary of the Jensenius overlap: **UP-2019 booth-level votes
are already openly available** (DVN/KKOWNJ) — a ready-made second control
election for the digit/share-based tests, worth adding before any republication.

## 16. Reproduction

```bash
cd india-2024
uv run python scripts/build_mai_datasets.py        # builds data/mai_*
cd ../analysis-tool
uv run ef-analyze --data ../india-2024/data/mai_pc_2024 \
  --out ../india-2024/analysis_pc --title "India Lok Sabha 2024 (constituencies)" \
  --controls ../india-2024/data/mai_pc_2014
uv run ef-analyze --data ../india-2024/data/mai_up_ac_2024 \
  --out ../india-2024/analysis_up_ac --title "Uttar Pradesh 2024 (Form 20 assembly segments)" \
  --controls ../india-2024/data/mai_up_ac_2014
uv run ef-analyze --data ../india-2024/data/mai_up_booth_2014 \
  --out ../india-2024/analysis_up_booth_2014 --title "Uttar Pradesh 2014 (booths, control)"
uv run python ../india-2024/scripts/booth_digit_tests.py   # 2024 booth digits + share peaks
```

Outputs: `analysis_pc/`, `analysis_up_ac/`, `analysis_up_booth_2014/`
(figures, tables, `metrics.json` each), `analysis_booth/` (booth digits).
