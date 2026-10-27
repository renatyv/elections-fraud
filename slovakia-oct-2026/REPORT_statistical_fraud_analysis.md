# Statistical analysis of election fraud: Slovakia, local and regional elections of 24.10.2026

*An application of election forensics methods (overview —
[`fraud_detection_methods.md`](../fraud_detection_methods.md)) to the data of the
joint municipal (OSO) and regional (OSK) elections of Slovakia of 24.10.2026.
Tool — [`analysis-tool/`](../analysis-tool/) (the standard `ef-analyze`
pipeline): nine runs — the eight governor races at kraj level (the same kraj in
2022 as the control) and the mayor race nationwide. Data — official
precinct-level exports of the Statistical Office of the Slovak Republic (ŠÚSR).
Date of analysis: 26.10.2026. Counting-night context and voting paradoxes —
[`PARADOXES.md`](PARADOXES.md); data description —
[`DATA_DESCRIPTION.md`](DATA_DESCRIPTION.md).*

## Data

Official definitive exports **OSK2026_SK_csv.zip** and **OSO2026_SK_csv.zip**
(`volbysr.sk`, the ŠÚSR results portal; 2022 controls —
`volby.statistics.sk/osk/osk2022` and `/oso/oso2022`): per-precinct turnout
(tab02d/tab02f) and per-precinct candidate votes (governors — tab06d, mayors —
tab05f). Adapted to the analysis-tool format by
`scripts/build_ef_csv.py` → `data/ef/…/results_freguesias.csv`; every
adaptation step is cross-checked (`data/ef/VALIDATION.txt`):

- precinct sums equal the official kraj/national tables to the exact vote
  (tab06a, tab01) — 6,029 OSK precincts, 4,477,457 registered, 1,884,912
  governor ballots; 6,024 OSO precincts, 4,478,646 registered, 2,077,687
  mayor ballots;
- the sums equal the final snapshot of our election-night capture
  (`data/trends/`) for all 8 kraje and all 8 capital races, including the
  Bratislava (189,294) and Košice (68,592) primátor tables — exact match;
- headline results agree with the national media (SME, STVR): Trnka's
  ~3,000-vote margin in Košický kraj (computed here: 3,117), Vallo 64% in
  Bratislava, all eight incumbent governors re-elected.

Unit of analysis = **volebný okrsok** (polling precinct). Definitions:
`voted` = valid ballots **of the analysed race** (governor ballots for OSK,
mayor ballots for OSO; official participation — participants/registered — was
46.56% OSK and 48.48% OSO); `null` = envelopes minus the race's valid ballots;
party attribution — the first (lead) party of the candidate's coalition,
empty = NEKA (independent). In 2022 the races used the same definitions; the
2026 precinct keys match the 2022 keys for 96.5–99.5% of precincts per kraj
(OSO: 90.3% — Košice renumbered its precincts).

| Indicator | Value |
|---|---|
| Governor race (OSK) | 8 runs × 537–1,017 precincts (586/537/654/745/728/902/1,017/860), 1,884,912 race ballots |
| Mayor race (OSO) | 6,024 precincts, 2,077,687 race ballots, 2,912 elected mayors |
| Controls | same races of 22.10.2022, the same precincts (95.5–99.5% key match) |
| Turnout (official) | OSK 46.56% (2022: 43.75%), OSO 48.48% (2022: 44.86%) |

## Summary verdict

**The tests do not establish statistical traces of ballot-stuffing or
count manipulation in either race.** All eight governor races and the
nationwide mayor race pass: no anomalous turnout tail (Shpilkin tail
0.4–4.7% of the leader's votes, ≤0.6 pp effect on shares), no integer-peaks
signature (all |z| < 3), digit tests clean (worst MC p = 0.017 — the
independents' aggregate column in the mayor race, an expected artifact of
aggregating thousands of candidates, not a manipulation signature),
fingerprint weights in the same range as the reference clean elections
(Portugal 2025, Slovenia 2026). The 2022 controls behave identically.

Two structural peculiarities — both verified against the honest 2022
baseline and **not** fraud signatures, but essential context for reading
turnout anomalies in Slovakia:

1. **Differential race participation** (section 11): in 79,290 cases the
   same visitor took part in the mayor race but not in the governor race;
   the gap concentrates in municipalities with large Romani communities
   (Jarovnice −1,726, Zlaté Klasy −1,716, Bystrany −1,145…) and follows the
   2022 pattern (−99,229 there). Local clientelist mobilisation for the
   mayor race produces legitimately extreme municipal turnouts that a
   naive Shpilkin read would flag.
2. **The forensics swing test flags 635 precincts** (|Δturnout| > 15 pp and
   |Δshare| > 15 pp, 2022→2026) — the median turnout change is **+1.5 pp**:
   the flags ride the party realignment (joint candidacies, dissolved
   parties), not a turnout anomaly (section 12).

Per-kraj verdicts:

| Kraj | winner (share) | Shpilkin tail, % of winner's votes | honest − observed, pp | integer peaks z (turnout / share) | digit tests min p (MC) | verdict |
|---|---|---|---|---|---|---|
| Bratislavský | Droba (SaS…) 70.97% | 4.69 | −0.27 | −0.3 / −0.2 | 0.40 / 0.37 | clean |
| Trnavský | Viskupič (PS…) 54.05% | 1.17 | +0.56 | 2.7 / 1.5 | 0.26 / 0.73 | clean |
| Trenčiansky | Baška (SMER…) 57.44% | 1.95 | −0.16 | 1.1 / −0.5 | 0.74 / 0.46 | clean |
| Nitriansky | Becík (HLAS…) 50.47% | 1.08 | −0.10 | 0.1 / −1.4 | 0.28 / 0.83 | clean |
| Žilinský | Jurinová (SLOVENSKO…) 52.07% | 0.49 | −0.03 | −0.2 / −0.6 | 0.29 / 0.11 | clean |
| Banskobystrický | Lunter (NEKA) 64.82% | 0.42 | +0.01 | 0.3 / −0.8 | 0.27 / 0.44 | clean |
| Prešovský | Majerský (KDH…) 48.78% | 0.76 | +0.06 | 1.2 / 0.5 | 0.06 / 0.14 | clean |
| Košický | Trnka (NEKA) 32.01% | 2.00 | −0.08 | −0.7 / −0.9 | 0.42 / 0.27 | clean |
| Mayors (SR) | NEKA 59.56% | 0.43 | +0.08 | 0.6 / −2.3 | 0.02 / 0.06 | clean* |

\* see the caveat on the aggregated independents' column in section 6.

## 1. The Shpilkin method: turnout distribution and anomalous votes

The turnout histograms are unimodal with a smooth right tail — the shape of
the 2022 controls (figures `controls_turnout.png` in every run directory).
The estimated anomalous tail above the "honest core" boundary holds
0.4–2.0% of the winner's votes in seven kraje and 4.69% in Bratislavský
(urban high-turnout tail; the effect on Droba's share: −0.27 pp, 70.97%
→ 70.7% "honest"). In no kraj does removing the tail change the winner or
the second place. The mayor race: tail 0.43% of the independents' votes
(59.56% → 59.64% honest). For comparison, the same pipeline on a
manipulated election (Moscow 2018-style data) estimates tails of 30–50%.

## 2. The «comet tail»: turnout × result

Turnout and the winner's share are correlated in the honest direction —
higher-turnout precincts lean to the winner in Bratislavský and
Trenčiansky (urban/liberal), to the runner-up in Košický (rural); the
point cloud fills the lower-right of the plane and lacks the "comet"
upper-right migration that stuffed precincts produce
(`comet_scatter.png` per run).

## 3. Electoral fingerprints (Klimek et al., PNAS 2012)

The 2D Gaussian-mixture second-component weights (0.41–0.75) sit in the
same range as the reference clean elections run with this exact tool
(Portugal AR-2025: 0.66; Slovenia referendums 2026: 0.42–0.48); the
"fraud" component with simultaneous high turnout and near-unanimous
result either does not separate or takes a small weight
(`fingerprint_2d.png`).

## 4. Integer peaks (Kobak et al., 2016)

No excess of round percentages: turnout-peak z-scores −0.3…+2.7
(Trnavský's 2.7 — see its control 2022: 3.0, a stable property of its
small-village turnover, not an anomaly), winner-share peaks
−2.3…+1.5 (`integer_peaks.png`).

## 5. 2D correlation analysis (Kobak et al., 2012)

Turnout × winner-share correlations are small and region-specific
(|r| ≤ 0.35 weighted); `corr_districts.csv` shows no kraj where the
correlation is driven by a tail of high-turnout/high-share precincts.

## 6. Benford's law: the second digit; and the last digit

All 8 kraj runs: worst second-digit MC p = 0.065 (Mazurek, Prešovský),
worst last-digit p = 0.107 (Choma, Žilinský) — consistent with uniformity.
The mayor race's independents' aggregate (NEKA — thousands of individual
candidates pooled into one column) gives second-digit p = 0.017: pooled
numbers of many different distributions are known to drift off Benford in
*both* directions; the same column in the honest 2022 control shows the
same drift, so it is an aggregation artifact, not a manipulation signature
(tables `benford2.csv`, `last_digit.csv` per run).

## 7. Comparison with neighbours (Myagkov–Ordeshook–Shakin)

Robust z-scores within the electoral district (OSK) or the okres (OSO):
flags |z| > 4 in 0–19 precincts per kraj (0–2.2%; Poland-grade noise;
Portugal 2025: 2.6%) and 383 of 6,024 (6.4%) in the mayor race — the
okres grouping mixes municipalities with very different local competition
(see section 11 for why extreme municipal turnouts are structurally
legitimate in Slovakia); the flagged names are small precincts, not
clusters (`neighbors_outliers.png`, `neighbors_z.csv`).

## 8. Machine learning: Isolation Forest

1% of precincts flagged per run (6–11 per kraj; 61 of 6,024 in the mayor
race) — the same order as the clean references (Portugal 1.0%,
Slovenia 1.0%); no geographic clustering of flags (`ml_anomalies.png`).

## 9. Self-test of the tools (synthetic fraud)

Injecting additive fraud into the same data grows the Shpilkin anomaly
signal ×6–14 per kraj — the pipeline is sensitive on this exact dataset;
the clean verdicts are not a power failure (`selftest.png`).

## 10. The 2022 controls

The 2022 runs on the same precincts show the same histograms, the same
small tails (±0.5 pp effects), the same integer-peak z-scores — the 2026
numbers are ordinary for this electoral system
(`controls_turnout.png` per run).

## 11. Two races, one visit: differential participation (Slovakia-specific)

Each voter at one polling station received two ballots (governor + mayor).
Comparing participant counts recorded by the two commissions per precinct:

- mayor-side participants exceed governor-side participants by **79,290**
  in total (2026); 1,938 precincts with any gap, 1,513 exactly equal;
- the gap is concentrated: Jarovnice −1,726, Zlaté Klasy −1,716,
  Bystrany −1,145, Jasov −905, Pavlovce nad Uhom −742, Lomnička −723…
  — municipalities with the largest Romani communities in Slovakia
  (2022 census), plus a diffuse city component (EU-citizen residents,
  who may vote in the municipal race only);
- the 2022 elections show the same structure, larger: −99,229 in total,
  Jarovnice −2,083, Zlaté Klasy −1,319, Luník IX −714; on the 2,708
  common municipalities the gap shrank 21% by 2026;
- participation correlation between the two races: r = 0.844 (scatter:
  `analysis/paradoxes/figures/dual_ballot_scatter.png`).

**Reading:** this is the measurable footprint of local clientelist
mobilisation (the mayor race is personal and local; the governor race is
distant) — and it means that *high municipal turnout in low-competition
municipalities is the Slovak norm*, not a stuffing signature. Forensic
reads of Slovak municipal data that do not separate the two races will
over-flag exactly these municipalities.

## 12. The 2022 → 2026 swing test, re-read

The standard swing test (|Δturnout| > 15 pp and |Δshare| > 15 pp of the
leader) flags 635 precincts of 5,442 matched (turnout-only: 1,226). The
median turnout change is **+1.5 pp** (2026 turnout is higher than 2022:
48.34% vs 48.42% race-ballot turnout on matched precincts; official
48.48% vs 44.86%); the flags are driven by the leader's share — the
independents' (NEKA) share rose from 56.98% to 59.79%, HLAS fell 9.50 →
6.71, the Magyar alliance 4.71 → 3.52 — i.e. ordinary party realignment
over four years, amplified by the joint candidacies of 2026
(`PARADOXES.md`, §1). No turnout-side anomaly.

## Limitations

- The analysis covers the two personal races (governors, mayors). The
  council races (proportional within kraj districts) are in the exports
  (tab09d/tab08f) but were not run through the forensics pipeline.
- `voted` = valid ballots of the race; the official participation metric
  (46.56%/48.48%) additionally counts participants who took no valid
  ballot of the race (9.6% in OSK, 4.2% in OSO in 2026). Turnout numbers
  in this report are race-ballot turnouts unless marked official.
- Precinct-level: the neighbors test compares a precinct with its district
  (OSK) or okres (OSO) median — for the mayor race this mixes municipalities
  of very different competitiveness (6.4% flags, section 7).
- Bratislava and Košice primátor races (two races of 2,914) are excluded
  from the MAI files (separate 'x' tables); their totals are cross-checked
  exactly (189,294 / 68,592).
- Statistical cleanliness is not proof of honesty: it excludes the
  class of manipulations these tests detect (stuffing, rounding, digit
  tampering, local anomalies vs neighbours). It cannot see coercion,
  clientelist pressure, or administrative-resource effects that leave no
  statistical trace — the differential participation of section 11 is the
  measurable part of exactly such machinery.

## Reproduction

```bash
# data (zips land in slovakia-oct-2026/data/official/, ~113 MB):
#   https://volbysr.sk/osk/files/OSK2026_SK_csv.zip
#   https://volbysr.sk/oso/files/OSO2026_SK_csv.zip
#   https://volby.statistics.sk/osk/osk2022/files/OSK2022_SK_csv.zip
#   https://volby.statistics.sk/oso/oso2022/files/OSO2022_SK_csv.zip
cd analysis-tool && uv sync
./run_forensics_slovakia.sh          # adaptation + 9 ef-analyze runs
.venv/bin/python ../slovakia-oct-2026/scripts/analyze_paradoxes.py
uv run pytest                        # toolkit self-tests
```

Adaptation cross-checks: `data/ef/VALIDATION.txt`; paradox log:
`analysis/paradoxes/PARADOX_LOG.txt`.
