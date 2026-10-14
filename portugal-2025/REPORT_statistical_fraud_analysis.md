# Portugal, parliamentary elections AR 2025 (18.05.2025): statistical fraud analysis

*Application of the election-forensics methods (review: [`fraud_detection_methods.md`](../fraud_detection_methods.md)) to the data of the 18 May 2025 election to the Assembly of the Republic. Tool: [`analysis-tool/`](../analysis-tool/) (uv, pandas/scipy/scikit-learn). Analysis date: 10.10.2026; updated 12.10.2026 — the section level added (section 13, [`analysis_seccoes/`](analysis_seccoes/)).*

## Data

Official export of the MAI portal (eleicoes.mai.gov.pt) at the parish (freguesia) level — the lowest level the portal itself serves; MAI does not publish per-section (secções) data. Section-level maps are nevertheless published by individual municipalities: six were found for AR-2025, parsed, cross-checked against MAI down to the last vote, and run through the statistical tests (section 13, output — [`analysis_seccoes/`](analysis_seccoes/)). The AD coalition's columns are merged (in the mainland `PPD/PSD.CDS-PP`, in the Azores `PPD/PSD.CDS-PP.PPM`). Control elections — AR 2022 and AR 2024 (same territories).

| Indicator | Value |
|---|---|
| Territories (parishes) | 3,092 (mainland + Madeira + the Azores; abroad excluded) |
| Registered / voted | 9,265,493 / 5,965,446 (turnout 64.4%) |
| AD (leader) / PS / CH | 32.7% / 23.4% / 22.6% |
| Blank / invalid | 1.44% / 0.99% |

## Summary verdict

| Method | Result | Verdict |
|---|---|---|
| Shpilkin (anomalous votes) | 2,980 AD votes = 0.15% of AD votes; final 32.71% vs 32.72% | ✅ clean |
| Fingerprints (Klimek et al.) | no "up-right" cluster | ✅ clean |
| Integer turnout peaks | 1.46% against a 1.44% null (z = 0.1) | ✅ clean |
| 2D turnout×result correlations | leader −0.09 (weighted Pearson) | ✅ clean |
| Benford, second digit | all p ∈ [0.10; 0.79] | ✅ clean |
| Last digit | all p ≥ 0.20 except AD p = 0.02 | ⚠️ borderline* |
| Outliers vs neighbors | 81/3,092 (2.6%), small parishes | ✅ no pattern |
| Jumps vs the 2024 election | 0 parishes with a double jump >15 pp | ✅ clean |
| ML (Isolation Forest) | 31 anomalies (1% by construction), no clustering | ✅ no pattern |
| Sections × MAI (6 concelhos, 91 sections) | all figures agree down to the last vote | ✅ clean |
| Sections: statistical tests (91 sections) | turnout ≤ 76.9%, none above the national boundary; turnout peaks z = 0.7, shares of all top-6 z ≤ +0.2; 0 duplicate protocols; neighbor/ML outliers — tiny sections without a pattern; digits: CH p = 0.006 with no 0/5 profile | ✅ clean* |

\* two borderline deviations of the digit tests: AD at parishes (p = 0.02 out of 12 tests; the Bonferroni threshold of 0.004 removes it) and CH at sections (p = 0.006, smooth MC null 0.017, Bonferroni over three parties ≈ 0.05). Neither has an excess of round 0/5, i.e. no "hand-made numbers" profile; details in sections 7 and 13.2.

**Conclusion: no systematic statistical traces of fraud were found.** All anomalies are explained by territorial heterogeneity (north/south, the islands, small parishes) and are not supported by more than one method.

---

## 1. Shpilkin method: turnout distribution and anomalous votes

Turnout (weighted by electorate): mode 69.3%, σ = 6.7 pp, decline to zero at ~78–83%. The anomalous-turnout boundary is 78.6% — the upper percentile q99.5 of the control elections (2022: 73.2%; 2024: 78.6%). Beyond the boundary: 7,779 votes cast (0.13%), of which 2,980 for AD. Recounting the result without the anomalous zone gives AD 32.71% against the observed 32.72% — it changes nothing.

The key difference from falsified elections: **the tail at 80–100% turnout is physically absent** (the distribution is empty past 78%), whereas stuffing shifts mass precisely there.

![Shpilkin method](analysis/figures/shpilkin_core.png)

## 2. "Comet tail": turnout × result

For AD, PS and CH the cloud is vertically compact at any turnout — the result does not grow with turnout. Under falsification the cloud stretches up-right (rising turnout → rising result of the "party of power" while the opponents fall) — there is none of that here.

![Comet tail](analysis/figures/comet_scatter.png)

## 3. Electoral fingerprints (Klimek et al., PNAS 2012)

2D density (turnout × AD share), weighted by voters. A mixture of two Gaussians splits the data into clusters (60.0%; 39.7%) and (66.7%; 29.2%) — northern rural parishes vs the south and the cities, i.e. heterogeneity of the electorate. The "fraudulent" up-right cluster (as in Russia-2011/2012 or Uganda) is **absent**: nowhere is there a compact clump at both high turnout and a high result.

![Fingerprint](analysis/figures/fingerprint_2d.png)

## 4. Integer peaks (Kobak et al., 2016)

The share of parishes with exactly integer turnout: **1.46% against 1.44%** expected under a binomial Monte Carlo null (z = 0.07); no peaks at multiples of 5 (z = −0.3). For the leader's share: 6.73% against 6.80% (z = −0.3). "Painting" protocols toward round numbers produces z in the tens and hundreds (see the self-test below) — here the deviation is nil.

![Integer peaks](analysis/figures/integer_peaks.png)

## 5. 2D correlation analysis (Kobak et al., 2012)

National turnout×result correlations (weighted Pearson / Spearman):

| AD | PS | CH | IL | L | PCP-PEV |
|---|---|---|---|---|---|
| −0.09 / −0.23 | +0.03 / −0.03 | −0.22 / +0.11 | +0.58 / +0.52 | +0.38 / +0.43 | +0.07 / +0.24 |

The leader has no association — no "vote transfer" with rising turnout is observed. The positive correlations of IL and L are a mobilization pattern of their urban base; a similar non-specificity of correlations is known from the honest UK elections (the "Limitations" section of the review). Across districts the picture is heterogeneous (AD from −0.49 in Madeira to +0.58 in Lisbon) — there is no targeted uniform shift.

![Correlations](analysis/figures/correlations.png)

## 6. Benford's law: second digit

Second digits of the top-6 parties' votes against Benford's law, with a smooth (lognormal) Monte Carlo null: all empirical p ∈ [0.10; 0.79]. No deviations (with the review's caveat: the test is weak and on its own carries little information).

![Benford](analysis/figures/digit_benford2.png)

## 7. Last digit (Beber–Scacco)

Test on counters ≥ 100 (for smaller numbers uniformity fails for natural reasons): PS p = 0.94; CH 0.67; IL 0.70; L 0.24; PCP-PEV 0.60; **AD p = 0.02** — the only borderline value out of 12 tests: a deficit of digit 4 (8.2% against 10%). There is no excess of "round" 0/5, which is typical of invented numbers; after the multiple-testing correction the deviation is insignificant.

![Last digit](analysis/figures/digit_last.png)

## 8. Comparison with neighbors (Myagkov–Ordeshook–Shakin)

Robust z-score of each parish against the median of its municipality (concelho): 81 outliers (2.6%) at the |z|>4 threshold — a normal tail for 3,092 heterogeneous territories. The largest outliers are small parishes (Anobra, 1,101 voters, an anomalously **low** AD share, z = −22.6; Furadouro, 173 voters) — the direction is opposite to falsification in the leader's favor. No clustering of the outliers by turnout.

![Neighbor outliers](analysis/figures/neighbors_outliers.png)

## 9. Jumps relative to the 2024 election

Comparing the same 3,092 parishes with AR-2024: not a single parish with a simultaneous jump in turnout and in the AD share >15 pp (the method requires a joint jump of "turnout↑ + result↑"). The discrepancies are explained by the regrouping of the coalitions, not by the counting of votes.

![Jumps to 2024](analysis/figures/swing_previous.png)

## 10. Machine learning: Isolation Forest (Zhang et al., 2019)

31 anomalous parishes (top-1% by construction) — small parishes of the Azores and of the mountainous interior of the mainland with a high share of blank ballots (up to 9–10%). These are candidates for manual checking, not a fraud signal: the anomalies do not cluster at high turnout/result and form no geographic clusters.

![ML anomalies](analysis/figures/ml_anomalies.png)

## 11. Self-test of the tools (synthetic falsifications)

Validation of the methods' sensitivity on the same data:

- **"Stuffing"**: +10% of parishes, turnout +5–35 pp, 60–95% of the added ballots for AD (131,629 votes) → the anomalous-zone estimate grew from 14,589 to 255,496 (×18). The estimate exceeds the number of injected ballots because it also counts honest votes that "moved" into the tail together with the boosted turnout — this is a convention of the Shpilkin method (all leader votes at anomalous turnout are counted as anomalous).
- **"Round protocols"**: fitting turnout to a whole percent in 5% of parishes → the integer-peaks z goes 0.2 → 5.1.

That is, the null result of the main analysis is not blindness of the tools: injected falsifications they do see.

![Self-test](analysis/figures/selftest.png)

## 12. Control: previous elections

The turnout distributions of AR-2022 / AR-2024 / AR-2025 over the same parishes are comparable in shape and in the upper bound of support (~78–80%). There is no drift of the shape toward a high-turnout tail from election to election.

![Control elections](analysis/figures/controls_turnout.png)

## 13. Sections: cross-check against MAI and statistical tests (91 sections)

Six municipalities publish AR-2025 results by section (secções de voto) — see [`data/seccoes/PUBLISHER_CATALOG.md`](data/seccoes/PUBLISHER_CATALOG.md) for details. All maps were parsed into a single dataset, [`data/seccoes/ar2025_seccoes.csv`](data/seccoes/ar2025_seccoes.csv) (`scripts/parse_seccoes_ar2025.py`): Benavente 27 sections, Alcácer do Sal 21, Vendas Novas 16, Ferreira do Alentejo 14, Borba 8, Sousel 5 (a scan — OCR transcription) — in total **91 sections, 60,711 voters (0.66% of the electorate), 38,738 votes cast (turnout 63.8%)**; plus Gouveia (16 rows), where the sections coincide with the parishes — an independent transcription by the câmara.

### 13.1. Cross-check against MAI

Checked across all 22 parishes of the six concelhos: the electorate, turnout, blanks, invalids and the votes of **every** list agree down to the last vote (log — `ar2025_seccoes_validation.txt`). The only discrepancy is in the municipal PDF itself: the summary row of Ferreira do Alentejo ("resultados corrigidos") understates the blanks by 3 (31 against 34; the breakdown by mes and MAI give 34).

### 13.2. Statistical tests at the section level

A run of `analysis-tool` over the 91 sections — `scripts/analyze_seccoes.py`, output [`analysis_seccoes/`](analysis_seccoes/) (figures/, tables/, metrics.json): Shpilkin, comet tail, fingerprints, integer percentages (turnout + the shares of all top-6 parties), digit tests, neighbors (by concelho and within the freguesia), correlations, ML, duplicate protocols, row arithmetic; the self-test is in 13.3. In this territory the leader by votes is **CH** (30.8%; then PS 24.4%, AD 23.2%, PCP-PEV 8.3%): all six concelhos are in the south, where the split differs from the national one. Results:

- **Turnout (Shpilkin)**: mode 64.8%, σ = 4.1 pp, range 51.8–76.9%. Above the national anomaly boundary (78.6%, section 1) — **zero sections**; above its own q99.5 (75.3%) — 93 voters and 44 CH votes (0.37% of the CH votes); the recount gives 30.80% against the observed 30.84%. There is no high-turnout tail at the section level either. The spread of the sections (51.8–76.9) is wider than the parishes' (the same 22 parishes: 56.5–73.7) — the variance grows as the unit of analysis shrinks, but it expands downward, not upward.
- **Fingerprints (Klimek)**: the mixture of two components splits by the **result**, not by turnout — (63.4%; 26.3%) vs (64.5%; 37.8%), a turnout difference of 1.1 pp: these are the CH-weak and CH-strong parishes. There is no "up-right" cluster.
- **Integer percentages (Kobak)**: exactly integer turnout in 2.20% of the sections against 1.42% under the binomial null (z = 0.7); for the leader's share 1.10% against 2.36% (z = −0.8). The shares of **all** top-6 parties were additionally tested: z from −2.5 (IL) to +0.2 (AD) — there is no excess of integer percentages for any of them (IL and L show a deficit, the direction opposite to painting).
- **Digit tests**: the second digit (Benford) — 6 parties, all p ∈ [0.19; 0.98]. The last digit is applicable only to CH/PS/AD (≥30 counters of ≥100 are required; the PCP-PEV/IL/L sections are smaller): PS p = 0.85, AD p = 0.19, **CH p = 0.006** (against a smooth MC null of 0.017) — an excess of the digits 6 (23.2%) and 7 (17.9%) with a deficit of 0, 1 and 9. This is the opposite of the invented-numbers profile (which has an excess of round 0/5); after the Bonferroni correction over the three parties p ≈ 0.05, and at n = 56 numbers a mixture of differently scaled municipalities itself deviates from the lognormal null. A borderline deviation without a fraudulent profile — an analogue of the AD p = 0.02 case in the main analysis (section 7).
- **Neighbors (Myagkov–Ordeshook–Shakin)**: a section against the median of its concelho's sections — 4 outliers out of 91 (4.4%) at the |z|>4 threshold: Alcácer do Sal S15 (53 voters, a CH share of 5.6%, z = −4.7 — **against** the leader), Santo Estêvão S2 (turnout 75.3%, z = +4.4), São Martinho S1 (72.1%, z = +4.8), Vendas Novas S15 (83 voters, turnout 51.8%, z = −4.6). The directions are mixed, the extremes are tiny sections; there is no clustering at high turnout.
- **Turnout×result correlations** (weighted Pearson): CH +0.10; PS −0.24; AD +0.35; PCP-PEV −0.17; IL +0.29. The leader has almost no association; the AD correlation is heterogeneity of the southern sample (in the main analysis AD ranges from −0.49 to +0.58 across the districts).
- **ML (Isolation Forest, contamination 5%)**: 5 candidates for manual checking — all tiny sections (53–121 voters): Alcácer do Sal S15 (53; invalid 5.6%), Vendas Novas S15 (83; the lowest turnout, 51.8%), Ferreira do Alentejo S5 (121; the highest turnout, 76.9%), Alcácer do Sal S5 (103; turnout 53.4%), Ferreira do Alentejo S7 (118; a CH share of 47.8%). These are the same extremes that the neighbors test catches — ML reveals no new type of anomaly, and there is no clustering at high turnout/result.
- **Neighbors within the freguesia** (groups of ≥4 sections: 5 freguesias, 62 sections — within a parish the sections are maximally comparable): 3 outliers |z|>4 — Benavente S9 (turnout below the parish median, z = −6.6 — the direction is against "stuffing"), Alcácer do Sal S15 (the CH share, z = −6.8 — against the leader), Ferreira do Alentejo S5 (turnout, z = +5.1; the same maximal 76.9% < the national boundary). With 9–15 sections in a group the robust z has heavy tails — 3 flags over 62 sections are consistent with noise, and the directions are mixed.
- **Duplicate protocols**: among the 91 sections there are **zero** fully identical vectors (the votes of all lists + blanks + invalids); the copy-paste sign of "painted" protocols is absent.
- **Blanks/invalids**: medians 1.19% / 0.81% (nationally by parishes 1.44% / 0.99%); maxima 3.22% (Orada S1) and 5.56% (Alcácer do Sal S15 — 2 ballots out of 36). There are no extreme values.
- **Row arithmetic**: in all 91 sections Σvotes + blanks + invalids = votantes and votantes + abst = eleitores — 0 discrepancies down to the last ballot (together with the cross-check of the sums against MAI from 13.1 this is the full trio of integrity checks).
- **Jumps to past elections** are impossible at the sections: section-level data for past years does not exist.

![Turnout by section](analysis_seccoes/figures/shpilkin_core.png)

![Last digit, sections](analysis_seccoes/figures/digit_last.png)

![Outliers vs neighbors, sections](analysis_seccoes/figures/neighbors_outliers.png)

### 13.3. Test power at n = 91 (self-test)

Synthetic injections into the same 91 sections (analogous to section 11): "stuffing" of +831 ballots for CH in 9 sections raises the anomalous-zone estimate from 44 to 1,924 votes (×44) — the Shpilkin method sees the addition at this scale too. "Painting" of protocols (fitting turnout to a whole percent in 8 sections, ~9%) the integer test does **not** catch (z 1.2 → 1.1): at n = 91 it is blind to fitting a small share of the protocols.

![Self-test on sections](analysis_seccoes/figures/selftest.png)

Bottom line: on all the available section-level data the MAI aggregates agree with the section protocols down to the last vote, and all the applicable statistical tests find no traces of fraud; the only borderline deviation (the CH last digit) has no fraudulent profile. This is a check of 0.66% of the electorate: the section run confirms that these territories are clean, but the micro level (digits, round numbers) can only be partially tested on 91 sections — which is exactly what the self-test shows.

---

## Limitations

- The main level of analysis is the parishes: MAI does not serve sections. The section maps of the six concelhos (0.66% of the electorate) agree with MAI down to the last vote, and all the applicable tests on them are clean (section 13), but there is no nationwide section coverage. The self-test on the 91 sections shows the price of the scale: the integer test does not see the painting of ~9% of the protocols, and the last digit has power for only three parties — point falsifications outside these six concelhos are beyond the resolution of statistics of this volume.
- The Shpilkin method estimates the scale under the model's assumptions (the shape of the honest core, no "negative" falsifications); here the anomaly boundary is set by the control elections, not only by the shape of the distribution.
- Benford and the last digit are weak tests; the borderline AD deviation (p = 0.02) forms no pattern and is not confirmed by the other methods.
- Statistics show anomaly, not mechanism: this analysis is no substitute for documentary evidence (protocol discrepancies, exit polls).
- The overseas electorate (~1.6 million registered) is excluded: it is absent from the MAI freguesias export.

## Reproduction

```bash
cd analysis-tool && uv sync
uv run ef-analyze \
  --data ../portugal-2025/data/legislativas2025_mai \
  --out ../portugal-2025/analysis \
  --title "Portugal AR 2025 (freguesias)" \
  --merge "votes:PPD/PSD.CDS-PP<-votes:PPD/PSD.CDS-PP.PPM" \
  --controls ../portugal-2025/data/legislativas2022_mai,../portugal-2025/data/legislativas2024_mai
```

Section level (91 sections, section 13):

```bash
uv run python ../portugal-2025/scripts/analyze_seccoes.py
```

Output: `analysis/figures/*.png`, `analysis/tables/*.csv`, `analysis/metrics.json`; for the sections — `analysis_seccoes/` in the same format. Tests: `uv run pytest`.
