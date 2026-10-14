# Statistical analysis of election fraud: Slovenia, four referendums of 11.10.2026

*An application of election forensics methods (overview — [`fraud_detection_methods.md`](../fraud_detection_methods.md)) to the data of the four nationwide referendums of Slovenia of 11.10.2026. Tool — [`analysis-tool/`](../analysis-tool/) (the standard `ef-analyze` pipeline), data — per-precinct results of DVK. Date of analysis: 13.10.2026. Context and data collection — [`report.md`](report.md), results and the Wikipedia cross-check — there, section 8.*

## Data

Official per-precinct results of the State Electoral Commission (DVK,
`volitve.dvk-rs.si`): per referendum — 3,083 «precincts» (files
`volisca_XX_YY.json`). Of them **2,984 regular precincts** (numbers < 900) plus
**99 aggregated early-voting points** (Predčasno glasovanje, numbers ≥ 900,
no electorate of their own — `upr` = 0). The data is combined into
[`data/derived/volisca_all.csv`](data/derived/volisca_all.csv)
(`scripts/build_volisca_csv.py`) and adapted to the analysis-tool format
(`scripts/build_ef_csv.py` → `data/ef/<referendum>/results_freguesias.csv`,
cross-check log — `data/ef/VALIDATION.txt`).

What makes the dataset unique: **four referendums on one day, at the same
precincts, with one electorate** — every voter received all four ballots. This
provides a mutual control that ordinary elections do not have: the turnout and
electorate of a precinct must agree across referendums (section 11), and the
geography of the results must be common (r = 0.94–0.96).

| Indicator | Value |
|---|---|
| Precincts in the analysis | 2,984 × 4 referendums (+99 early-voting points separately) |
| Electorate / ballots at the precincts | 1,581,696 (93.2%) / 843,250–843,285 (91.0%) |
| Turnout | 53.31% at the precincts; 54.62% nationwide |
| Result of preiskava (ZPPre-B act) | ZA 48.74% / **PROTI 51.26%** — act rejected, the 1/5 quorum met |
| Result of socialna_pomoc | **ZA 60.54%** / PROTI 39.46% — approved |
| Result of volilna_pravica | **ZA 55.30%** / PROTI 44.70% — approved |
| Result of rtv_prispevek | ZA 49.97% / **PROTI 50.03%** — rejected, a margin of 546 votes |
| Invalid (precincts) | 0.32–0.58% of ballots |

Outside the per-precinct coverage: early-voting points (75,300 ballots, 8.1% — ZA overall
29.9–41.3%, so at the precincts ZA is systematically 1.5–2 pp above the national
result), OMNIA precincts, postal and embassy voting (~8,400 ballots, 0.9%).
The DVK stamp — 12.10.2026, 99.98% counted, `is_final=false` (review of votes
cast abroad — 19.10.2026). At the precincts the shares are computed from all ballots
(«glas»), the official results — from valid ones; the difference is the invalid ballots.

## Summary verdict

| Method | Result | Verdict |
|---|---|---|
| Shpilkin (anomalous votes) | a tail of 4,135–4,651 ZA votes (0.89–1.00%) and 1,297–1,812 PROTI (0.41–0.45%); result shift ≤ 0.15 pp | ✅ clean |
| Comet tail (turnout × result) | ZA +0.27…+0.38, PROTI mirrored; a smooth gradient across the whole turnout range, above 80% — 10 tiny precincts (0.1% of ballots) | ✅ no tail |
| Fingerprints (Klimek) | two components — a city/rural gradient (+4–5 pp turnout), both at 51–56% turnout; no 80–100% cluster | ✅ clean* |
| Integer peaks | turnout z = −0.0…+0.4; ZA share z ≤ +1.1, PROTI z ≤ +1.3 | ✅ clean |
| 2D correlations | +0.27…+0.38 for ZA in all four, homogeneous across the 8 units | ⚠️ structure |
| Benford, second digit | 16 tests: 13 clean; socialna/ZA p = 0.005, volilna/PROTI 0.057, rtv/ZA 0.122 | ⚠️ borderline* |
| Last digit (precincts) | all p ≥ 0.05 (minimums 0.052 and 0.065), no 0/5 profile | ✅ clean |
| Last digit (early-voting points) | p = 0.37 / 0.19 | ✅ clean |
| Outliers vs neighbors | 22–40 of 2,984 (0.7–1.3%), tiny precincts, mixed directions | ✅ no pattern |
| ML (Isolation Forest) | 30 anomalies (1% by construction) — precincts of 16–342 voters | ✅ no pattern |
| Cross-referendum checks | turnout r ≈ 1.000; discrepancy ≤ 2 ballots for 99.6%; shares r ≈ 0.94–0.96 | ✅ clean |
| Duplicate protocols | within a referendum 38–60 duplicates against a null of 37–53; across ballots Δ=0 is half as frequent as Δ=1 | ✅ coincidences |
| Row arithmetic | 0 discrepancies in all 12,332 rows | ✅ clean |
| Self-test | a «ballot stuffing» is visible: a ×12–13 signal; integer rigging at precincts of ~460 voters — the test is low-powered (z → 0.8–1.6) | ⚠️ power |

\* the three borderline values of the digit tests and the «separation» of the fingerprints
are analysed in sections 3 and 6: the deviation profile is the opposite of the
«hand-made» one (an excess of round 0/5), the Bonferroni threshold over 16 tests — 0.003; the
fingerprint separation — a gradient inside one cloud, common to all four referendums.

**Conclusion: no systematic statistical traces of fraud were found.**
The turnout distribution fades out around 70% (above 80% — only 10 tiny
precincts of 16–371 voters each, 808 ballots in total — 0.1%), the results
shift by no more than 0.15 pp when the anomalous zone is cut off, the digit
tests are clean, integrity agrees to the ballot, and four simultaneous counts
of the same precincts give a mutually consistent turnout picture and result
geography. The «turnout ↑ → ZA ↑» slope (+0.3) — a property of the territorial
structure (city/rural), the same for all four referendums.

---

## 1. The Shpilkin method: turnout distribution and anomalous votes

Precinct turnout: mode 55.2%, σ = 7.0 pp, range 21.3–100% (the maximum — a precinct
of 19 voters: 19 of 19). The honest-decline boundary — **70.06%** — the upper
percentile q99.5 of the other three referendums (the controls of the standard pipeline
`--controls`; all four have the same turnout distribution to within
1–2 ballots per precinct). Beyond the boundary: 5,970 voters (0.71%
of ballots) at 67 precincts — small rural ones (median size 98 voters,
range 16–468). The anomalous mass of votes:

| Referendum | ZA tail | % of ZA votes | PROTI tail | % of PROTI votes | ZA result: observed → «honest» |
|---|---|---|---|---|---|
| preiskava | 4,223 | 1.00% | 1,709 | 0.41% | 50.32% → 50.17% |
| socialna_pomoc | 4,651 | 0.89% | 1,297 | 0.41% | 62.20% → 62.09% |
| volilna_pravica | 4,438 | 0.92% | 1,508 | 0.42% | 56.93% → 56.81% |
| rtv_prispevek | 4,135 | 0.95% | 1,812 | 0.45% | 51.60% → 51.48% |

In the tail the ZA share is indeed elevated (preiskava: 70.7% against 50.6% on
average) — but this is not a separate «stuffed» cluster, it is the right edge of the same
city/rural gradient that is visible across the whole turnout range and for all four
referendums. The ZA share by turnout bins (preiskava / socialna_pomoc):

| Turnout, % | 30–40 | 40–45 | 45–50 | 50–55 | 55–60 | 60–65 | 65–70 | >70 |
|---|---|---|---|---|---|---|---|---|
| Precincts | 117 | 213 | 481 | 720 | 763 | 456 | 166 | 66 |
| ZA, % | 41.3 / 53.7 | 43.5 / 56.2 | 45.8 / 58.7 | 49.3 / 61.4 | 52.3 / 64.1 | 55.7 / 66.4 | 62.0 / 71.8 | 71.2 / 78.3 |
| Median size | 517 | 522 | 553 | 518 | 487 | 354 | 212 | 99 |

The growth is monotone, without a jump at the boundary: a precinct with 60% turnout is on
average ~4 pp more «ZA» than a precinct with 50%, and with each turnout step the precincts get smaller —
this is the rural periphery. The Shpilkin method estimates exactly the contribution of the right edge beyond
a smooth model: recounting the result without the anomalous zone shifts it only by
0.11–0.15 pp. The essential difference from falsified samples: above 80%
turnout — only 10 precincts of 16–371 voters (808 ballots, 0.1%), above
85% — two (19 and 21 voters); stuffing, in contrast, leaves a mass precisely at 80–100%
of large precincts.

![Shpilkin, preiskava](analysis/preiskava/figures/shpilkin_core.png)

## 2. The «comet tail»: turnout × result

The cloud (turnout × ZA share) is tilted up-right: weighted correlation +0.36
(preiskava), +0.35 (socialna), +0.38 (volilna), +0.27 (rtv); PROTI is mirrored
minus. But this is the tilt of **the whole cloud**, smooth across the whole turnout range
(bins in section 1): a precinct with 60% turnout is consistently more «ZA» than a precinct with 50%
by ~4 pp, with no break at the right edge. In falsified samples the «comet
tail» is different: the main mass at 50–60% turnout and a separate elongated cloud
going to results of 80–95% at 80–100% turnout of large precincts, with a mirrored
drop of the opponent precisely in that tail. Here above 80% — 10 precincts of 16–371
voters (808 ballots), and their ZA elevation is a continuation of the same
demographic gradient, identical for all four referendums.

![Comet, preiskava](analysis/preiskava/figures/comet_scatter.png)

## 3. Electoral fingerprints (Klimek et al., PNAS 2012)

A mixture of two 2D Gaussians splits the precincts into components (turnout 51.0–51.6%; ZA
41.4–53.5%) and (55.4–55.6%; 61.2–70.2%) with weights 0.42–0.49. Formally the
«right-up» criterion fires (the second component is higher on both axes), but it is a
**gradient inside one continuous cloud**, not a separate cluster: the difference
of the turnout means — 4–5 pp at a mode of 55%, both components lie in the middle of the range.
The classical «falsified» cluster — a compact island at 80–100% turnout with
a result of 60–95% (Russia 2011/2012, Uganda) — is absent from the density:
above 85% turnout only two precincts of 19 and 21 voters are marked. The same
bimodal structure in all four referendums
with a share correlation of 0.94–0.96 (section 11) — this is the polarization of the electorate
(rural municipalities for ZA, urban for PROTI), a known limitation of the method
(section 4 of the overview).

![Fingerprints, preiskava](analysis/preiskava/figures/fingerprint_2d.png)

## 4. Integer peaks (Kobak et al., 2016)

| Metric | preiskava | socialna_pomoc | volilna_pravica | rtv_prispevek |
|---|---|---|---|---|
| Integer turnout, observed / null | 2.25 / 2.24% | 2.35 / 2.26% | 2.25 / 2.26% | 2.31 / 2.26% |
| z (turnout) | +0.0 | +0.4 | −0.0 | +0.2 |
| z (multiples of 5) | −0.1 | +0.2 | −0.2 | +0.2 |
| z (ZA share) | +1.1 | +0.4 | +0.2 | +0.2 |
| z (PROTI share) | +1.0 | +1.2 | +1.2 | +1.3 |

All z within ±1.3 — no «drawing» of protocols to round values, neither in
turnout nor in the option shares. On the power of the test at precincts of this size —
section 10 (the self-test).

![Integer peaks, preiskava](analysis/preiskava/figures/integer_peaks.png)

## 5. 2D correlation analysis (Kobak et al., 2012)

National turnout × share correlations (weighted Pearson / Spearman):

| | ZA | PROTI |
|---|---|---|
| preiskava | +0.36 / +0.31 | −0.36 / −0.32 |
| socialna_pomoc | +0.35 / +0.30 | −0.35 / −0.30 |
| volilna_pravica | +0.38 / +0.33 | −0.38 / −0.33 |
| rtv_prispevek | +0.27 / +0.26 | −0.27 / −0.26 |

The ZA/PROTI mirroring is mechanical (two shares of one set of ballots).
What is essentially different: **the positive association is the same for all four questions** —
including the national «PROTI» winners (preiskava, rtv_prispevek), whose
association with turnout is negative. If the count of one ballot were being adjusted, its
correlation would stand out from the other three; instead all four lie in the
+0.27…+0.38 band with the same ordering across units (KRANJ +0.60…+0.69,
PTUJ +0.16…+0.19). Such a non-specific correlation is known from honest
elections (the UK; the «Limitations» section of the overview) and reflects
the city/rural turnout distribution, not a transfer of votes.

![Correlations, preiskava](analysis/preiskava/figures/correlations.png)

## 6. Benford's law: the second digit

The second digits of the ZA and PROTI tallies (~2,900 numbers per option) against Benford's law
and a smooth lognormal Monte-Carlo null — 16 tests:

| Referendum | ZA p (theory / MC) | PROTI p (theory / MC) |
|---|---|---|
| preiskava | 0.67 / 0.80 | 0.83 / 0.84 |
| socialna_pomoc | **0.001 / 0.005** | 0.96 / 0.97 |
| volilna_pravica | 0.81 / 0.88 | 0.04 / 0.057 |
| rtv_prispevek | 0.05 / 0.12 | 0.44 / 0.47 |

Thirteen tests are clean. The only value below 0.05 against the MC null —
socialna_pomoc/ZA (p = 0.005). The deviation profile: an excess of digit 4 (12.1%
against 10.0% expected, the top of the null band 11.1%) and a deficit of 0 (10.3% against
12.0%, the bottom of the band 11.1%); digit 5 — normal. This is the **opposite** of the
made-up-numbers profile (an excess of round 0/5 — Beber–Scacco). After the correction for
multiple testing (Bonferroni over 16 digit tests, threshold 0.003)
the deviation is not significant; moreover, a mixture of 3,000 precincts of different scale
(from 16 to 2,908 voters) deviates from a lognormal
null by itself — an analogue of the CH p = 0.006 case in the Portuguese per-section analysis.

![Benford, socialna_pomoc](analysis/socialna_pomoc/figures/digit_benford2.png)

## 7. The last digit (Beber–Scacco)

The last digits of tallies ≥ 100 across precincts (1,263–2,033 numbers per option) — all
16 tests at p ≥ 0.05: the minimums — rtv/PROTI p = 0.052 (deviations of ±1.7
pp on digits 3 and 9, 0/5 normal) and preiskava/ZA p = 0.065 (an excess of 2, a deficit of
4 — also without a round profile); the rest p ≥ 0.14. At the **early-voting points**
(99 points × 4 referendums, a pool of 372–387 numbers ≥ 100) — p = 0.37 (ZA) and 0.19
(PROTI). Early voting (separate commissions, separate protocols) carries no
digit traces.

![Last digit, rtv](analysis/rtv_prispevek/figures/digit_last.png)
![Last digit, early-voting points](analysis/cross/figures/digit_last.png)

## 8. Comparison with neighbors (Myagkov–Ordeshook–Shakin)

A robust z-score of each precinct against the median of its district (okraj, 88 groups
of ~34 precincts): 40 outliers (preiskava), 29 (rtv), 25 (socialna), 22 (volilna)
at the |z|>4 threshold — 0.7–1.3%, a normal tail. The turnout directions are
symmetric (+7/−9 in all four); for the ZA share there are more high ones (+22/−2 in
preiskava) — a consequence of the right-skewed distribution of the ZA share (rural
precincts with ZA 70–90%), not of a one-sided addition: for the national
«PROTI» winners the picture is mirrored. The largest deviations are small precincts:
KOPER 2 (66 voters, ZA z = +7.8), RUŠE (173, ZA share z ±5–7 in three
referendums), NOVO MESTO 2 (342, turnout z = −8.9 — the same in all four
ballots, i.e. a property of the place, not of the count). No clusters at high turnout.

![Neighbors, preiskava](analysis/preiskava/figures/neighbors_outliers.png)

## 9. Machine learning: Isolation Forest (Zhang et al., 2019)

30 anomalous precincts per referendum (1% by construction; features: turnout, the share
of the leader, invalid, size). These are the same extremes in all four
runs: Stavba Makuc (16 voters, turnout 81%), Janeževo Brdo (19, turnout 100% —
19 of 19), Stavba Rejc (26, invalid 10%), Mlekarna Potoki (44,
invalid 11.5%), Vrtec Žabjak (342, turnout 21%). The anomaly is the size and
extreme values of tiny precincts, candidates for manual review, but not a signal
of fraud: no clusters at high turnout/result.

![ML, preiskava](analysis/preiskava/figures/ml_anomalies.png)

## 10. Self-test of the tools (synthetic fraud)

- **«Ballot stuffing»**: +10% of precincts, turnout +5–35 pp, 60–95% of the added ballots for
  the leader → the estimated anomalous zone grows from 4.1–4.7 thousand to 52–59 thousand votes
  (**×12–13**): on this dataset the Shpilkin method sees an injection of that scale
  with a large margin.
- **«Round protocols»**: fitting turnout to an integer percent in 146 precincts (5%) →
  the z of the integer peaks grows only from −0.2…+0.3 to **+0.8…+1.6**. The reason —
  the size of the unit: at a median precinct of 464 voters an «integer percent» of turnout
  is hit exactly in only ~1% of fits (464 × 0.6 = 278.4 votes), whereas on the
  parishes of Portugal (a median of ~3,000 voters) the same test gave z = 5.1.
  That is, the zero z of section 4 mean the absence of *crude* round-number rigging, but
  against rigging a small share of per-precinct protocols the integer test at precincts of
  this size is low-powered.

![Self-test, preiskava](analysis/preiskava/figures/selftest.png)

## 11. The mutual control of the four referendums

Simultaneity and the common ballot of a voter provide checks unavailable at ordinary
elections (`scripts/analyze_extra.py`, output `analysis/cross/`):

- **One event's turnout, four records.** Weighted turnout correlations between
  referendums 0.9988–1.0000. Absolute discrepancies: at 2,774 precincts (93%)
  the number of issued ballots is identical across all four, at 198 (6.6%) — 1–2
  (the voter did not take part of the ballots), at 6 — 3–5, at 6 — more than 5. The maximum —
  7005_003 (volilna_pravica: 760 against 670 in the others, the station was only 87%
  counted at the moment of the snapshot); 6007_005 (preiskava: 74 against 44, 59%
  counted) — both rows were still being counted. No mass discrepancies.
- **Electorate**: at a single precinct 5007_005 `upr` = 999 against 1001
  (rtv_prispevek) — a 2-record discrepancy of the DVK files.
- **A common geography of results**: correlations of the ZA share between referendums
  0.935–0.962. A «faked» referendum would fall out of the common picture —
  none does.
- **The overlap of the turnout distributions** of the four referendums matches in shape
  (the `controls_turnout.png` figure) — a common control of the standard pipeline.

![ZA shares across referendums](analysis/cross/figures/cross_shares.png)

## 12. Data integrity

- **Arithmetic**: in all 12,332 rows (4 × 3,083) ZA + PROTI =
  valid and valid + invalid = ballots —
  **0 discrepancies to the single ballot** (log — `data/ef/VALIDATION.txt`).
- **Duplicate protocols**: within each referendum 38–60 repeats of the vector
  (ZA, PROTI, invalid) at valid ≥ 50 — a parametric
  bootstrap null gives 37–53 ± 5–7: natural collisions of similar precincts
  (37 of the 38 preiskava pairs — precincts from different districts); no sign of copy-paste.
  Across the ballots of one precinct 230 pairs of matching vectors, but the copy
  control removes them: in the distribution of |ΔZA| between referendums the value 0 occurs
  **twice as rarely** as the value 1 (412 against 798) — a decline to zero, not a peak;
  vectors matching in all four ballots — 2.
- **File boundaries**: at 2 rows «counted» exceeds issued by 1 ballot
  (6005_044, two referendums — a desynchronization of the DVK turnout/results files);
  at 188 precincts in at least one ballot the counted share is < 1 (99.98% nationwide;
  the minimum 59% — 6007_005).
- **Invalid**: a median of 0.00–0.43% across referendums (the legislative
  ballot is more complex), a maximum of 10–11.5% at precincts of 10–26 ballots —
  no extreme values.

![Turnout discrepancies between referendums](analysis/cross/figures/turnout_diff_hist.png)

---

## Limitations

- **A coverage of 93.2% of the electorate / 91% of the ballots.** Early-voting points (8.1%),
  OMNIA, postal and embassy voting (~0.9%) have no per-precinct breakdown and
  were checked only by the digit tests (section 7) and the sum cross-check.
- **`is_final=false`** (99.98% counted, the review of the abroad votes 19.10.2026):
  the final results may shift by tens of votes — such a scale does not affect
  the conclusions.
- **The power of the digit tests at precincts of ~460 voters**: the integer test
  would not see rigging of a small share of protocols (the self-test, section 10); the
  last/second digit tests have ~2,000–3,000 numbers per option — sensitive
  only to mass distortions.
- **The turnout × ZA correlation is non-specific**: a soft manipulation spread across
  all precincts (administrative mobilization) is not statistically separable from the
  city/rural structure — this is a limitation of the method, not a feature of the data.
- **Statistics show anomalousness, but not the mechanism**: protocols, exit polls
  and parallel counts are not in the dataset. An additional anchor here — the mutual
  agreement of the four independent ballots (section 11) and the similarity to the honest
  profile of past Slovenian votes (see section 8 of the
  [`report.md`](report.md)).

## Reproduction

```bash
# data (if not collected yet)
cd sloveniya-referendum-2026
uv run sloref fetch --volisca                          # snapshot of the DVK files
PYTHONPATH=src uv run python scripts/build_volisca_csv.py   # combined precinct CSV

# the full forensics cycle in one command
cd ../analysis-tool
./run_forensics_slovenia.sh
```

The step-by-step equivalent:

```bash
cd analysis-tool && uv sync
uv run python ../sloveniya-referendum-2026/scripts/build_ef_csv.py   # adaptation + validation
uv run ef-analyze \
  --data ../sloveniya-referendum-2026/data/ef/preiskava \
  --out ../sloveniya-referendum-2026/analysis/preiskava \
  --title "Slovenia, ZPPre-B referendum 11.10.2026 (precincts)" \
  --controls ../sloveniya-referendum-2026/data/ef/socialna_pomoc,../sloveniya-referendum-2026/data/ef/volilna_pravica,../sloveniya-referendum-2026/data/ef/rtv_prispevek
# ×4 referendums (socialna_pomoc, volilna_pravica, rtv_prispevek similarly)
uv run python ../sloveniya-referendum-2026/scripts/analyze_extra.py  # cross-checks and the second option
```

Output: `analysis/<referendum>/{figures,tables,metrics.json}` (the standard pipeline)
and `analysis/cross/` (cross-checks); the adapted data —
`data/ef/<referendum>/results_freguesias.csv` with the log
`data/ef/VALIDATION.txt`. analysis-tool tests: `uv run pytest` (in `analysis-tool/`).
