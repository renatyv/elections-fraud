# Bulgaria 2026 presidential runoff (1 November): statistical screening

Checked **2 November 2026**. National source stamp: **2 November, 09:15 EET**, **100%** of
section-commission protocols processed. This does not imply certification.

**The available screening does not establish ballot stuffing. The tail, integer-peak and
correlation diagnostics are small and, for the first time in this election, the Shpilkin
cutoff is calibrated on an external reference (round 1 on the same sections). One digit
flag for the winner survives correction and stays open; 14 protocol-balance discrepancies
are documented.** Round 1 is a reference election on the identical sections, not a
validated honest baseline — it carried its own unresolved flags.

## Official result

[CIK national table](https://results.cik.bg/pvr202610/tur2/rezultati/index.html), 2 candidates plus "nobody":

| Candidate pair | Votes | Displayed share |
|---|---:|---:|
| Yotova / Valchev (no. 25) | 1,093,852 | 57.566% |
| Gyurov / Kandev (no. 4) | 750,251 | 39.483% |
| Do not support anyone | 56,080 | 2.951% |
| All listed votes | 1,900,183 | 100.000% |

Listed votes equal **28.63%** of the 6,637,274-entry register used by the portal's turnout
reports (11:00 report 6.11%, 16:00 report 19.33%) — a lower bound, since invalid ballots are
not included. The official intraday reports are below the final count, not comparable to it.

Round-1 context: Yotova 34.759% vs Gyurov 31.952% (+2.807 points nationally, +3.56 among
domestic sections). The runoff margin is **+18.083 points nationally, +19.68 domestic**.
Domestic turnout in the chart sample rises from 21.43% to **26.71%** (+5.28 points of register).

## Source validation and exclusions

The numeric-protocol index links **12,717 sections** (two fewer than round 1's 12,719),
all successfully captured. Where aggregate form 0 exists it is used once; component forms
are not double-counted. **All captured candidate totals and the nobody total reconcile
exactly with the national table** (Gyurov 750,251, Yotova 1,093,852, nobody 56,080).

**14 sections** have an internal voter/signature balance discrepancy (12 domestic, 2
abroad), down from 22 in round 1. As in round 1 these are discrepancies in published
numerical fields requiring protocol review, not proof of fabricated ballots; the parser
preserves them.

| Sequential selection | Sections |
|---|---:|
| All indexed protocols | 12,717 |
| Exclude abroad (includes 2 balance discrepancies) | −613 |
| Exclude remaining domestic balance discrepancies | −12 |
| Exclude registers below 100 | −1,436 |
| Eligible domestic sections | **10,656** |

Eligible sections contain **6,555,339 registered electors** and **1,750,174 signatures**
(26.70% turnout on the opening-register-plus-additions denominator); **1,020,862 Yotova
votes**, i.e. **58.329% of this subset** against the national 57.566% listed-vote share.
As in round 1, "nobody" occupies the toolkit's `blank_votes` field as an explicit
non-candidate category; `null_votes` is the residual, not a verified invalid-ballot count.

## Method results

### 1. Shpilkin-style high-turnout tail, control-calibrated

Unlike round 1, the cutoff is **external**: the toolkit takes the 99.5th percentile of the
control election (round 1, same sections) — **50.482%**. Tail: **60,230 voters /
28,904 Yotova ballots, 2.831% of her subset votes**. Removing the whole tail would move her
subset share from **58.329% to 58.698%** (+0.368 points). This remains a model-defined
diagnostic, not an estimate of fabricated votes.

| Reference | Turnout cutoff | Yotova tail ballots | Share of her subset votes |
|---|---:|---:|---:|
| Round 1, 99.5th pct (used by the toolkit) | 50.482% | 28,904 | 2.831% |
| Own 99th pct | 52.562% | 22,530 | 2.207% |
| Own 99.5th pct | 58.405% | 14,683 | 1.438% |
| Own 99.9th pct | 100% | 0 | 0% |

The weighted turnout–share correlation is **−0.151** for Yotova (round 1: −0.140) and
**+0.155** for Gyurov. Sign and size match the round-1 pattern; no inflated-tail signature.

### 2. Comet scatter and Klimek-style fingerprints

The two-component Gaussian mixture now **separates** (round 1: it did not), with second
component weight **0.751** — a fitted cluster weight, not a fraud fraction. The components
differ mainly in turnout (means 20.15% vs 28.87%) with Yotova means 51.14% vs 62.21%,
i.e. the split may reflect province/city turnout geography, but this explanation has not
been tested against district membership. Interpretation stays exploratory.

### 3. Kobak-style integer peaks

Under the section-size-aware binomial Monte Carlo null: integer turnout **1.623% observed
vs 1.819% expected (z = −1.80)** — below the null. Integer Yotova share z = −0.43; multiples
of five: turnout z = −0.08, Yotova share z = +0.02. **No integer excess anywhere.**

### 4. Second digit and last digit

Both runoff candidates clear the toolkit thresholds. Holm correction covers **4
candidate/test combinations** (Yotova and Gyurov × second/last digit):

| Test | Candidate | n tallies | MC p (smooth null) | Holm-adjusted |
|---|---|---:|---:|---:|
| Second digit | Yotova | 10,445 | **0.00249** | **0.0100** |
| Last digit | Yotova | 5,089 | 0.04738 | 0.1421 |
| Last digit | Gyurov | 2,037 | 0.19451 | 0.3890 |
| Second digit | Gyurov | 10,006 | 0.44389 | 0.4439 |

**Yotova's second-digit flag survives Holm at 5%.** Her second-digit profile shows an
excess of 0–3 (second-digit 0: 1,452 observed vs ≈1,250 Benford-expected) and
a deficit of 5–9; the
fitted smooth-lognormal reference makes the residual pattern unlikely (p≈0.0025). This is
a model-relative flag: correlated protocol sizes, machine-voting count structure and
reference-fit issues can contribute. In round 1 the leader's own second digit was clean
(smooth-null p = 0.693) while minor candidates carried the flags; inspect geography,
voting mode and the fitted reference before attributing this to manipulation.

### 5. Round 1 → runoff on matched sections

The toolkit matches **10,581 sections** present and eligible in both rounds. Turnout
changes: mean **+5.37**, median +5.28 points; **215 sections gain more than +15 points**,
43 lose more than 15. The toolkit's jump flag (|Δ turnout| > 15 **and** |Δ share| > 15)
fires on 199 sections, but the share side is uninformative by construction in a runoff:
the national pair structure collapsed from 27 candidates to 2, and the median section's
Yotova share moved +24.6 points. The turnout-jump list (and the small sections with 100%
runoff turnout at its top) is a review list, not a finding.

### 6. Local outliers and machine learning

The robust within-municipality screen flags **364 sections** with |z| > 4; Isolation Forest
flags **107** at a configured 1% contamination. Both are inspection priorities; the ML rate
is set by a parameter.

### 7. Synthetic injection (self-test)

Adding synthetic Yotova ballots in the toolkit's injection scenario grows the tail signal
**×5.35** (14,683 → 78,570); a separate rounded-turnout injection moves the integer-peak z
from −1.91 to +0.66. The tests respond to planted patterns; this checks sensitivity, not
specificity to real fraud.

## District picture (descriptive)

Yotova leads in **28 of 31 domestic districts**; Gyurov keeps Sofia-23 (−22.4), Kardzhali
(−19.0), Sofia-24 (−15.2) and the abroad aggregate (−17.7 on 99,397 listed votes, 5.2% of
the national total). Kardzhali is the notable flip: +21.6 for Yotova in round 1, −19.0 in
the runoff (a 40.5-point swing at the lowest domestic turnout, 12.8% vs 8.1%). Sofia-25
and Plovdiv-city flip the other way, from −9.8/−7.2 to +3.6/+7.0. District turnout
correlates with the runoff margin at r = −0.29 (round 1: −0.63, −0.32 without the big-city
districts). Runoff margins redistribute first-round votes mechanically; district swings
are descriptive, not forensic evidence.

District charts include sections with final registers ≥100 and positive signatures,
aggregated separately in each round (not a matched sample). Published balance discrepancies
are retained in these descriptive charts; margins use signatures as the denominator,
not national listed votes. Turnout rose in all 31 domestic districts.

## Controls and remaining limits

Round 1 on the identical sections serves as the cutoff-calibration control; it is **not a
validated honest baseline** (round 1 itself carried 22 balance discrepancies and
minor-candidate digit flags). Machine-learning and outlier flags are review lists.
Physical ballots, coercion, vote buying and register quality were not audited. The
14 source balance discrepancies and the surviving Yotova second-digit flag merit follow-up;
the aggregate diagnostics do not establish a mechanism or a quantity of manipulation.

## Reproduction and outputs

Raw HTML is cached under `data/official_20261102_tur2/` (gitignored); section totals in
`sections.json`, reconciliation in `summary.json`. The adapter writes
`data/ef_tur2/results_freguesias.csv`, `exclusions.csv`, `audit.json` (round 1 stored
alongside as `results_all_previous.csv` for the matched-section comparison).

```bash
bulgaria-oct-2026/.venv/bin/python bulgaria-oct-2026/scripts/capture_tur2.py --sections
bulgaria-oct-2026/.venv/bin/python bulgaria-oct-2026/scripts/build_ef_csv.py \
  --source data/official_20261102_tur2 --out data/ef_tur2 \
  --control-label "round 1 of the same election, 25 Oct 2026 (same sections, matched by key)"
cp bulgaria-oct-2026/data/ef/results_freguesias.csv bulgaria-oct-2026/data/ef_tur2/results_all_previous.csv
MPLCONFIGDIR=/tmp/bulgaria-mpl analysis-tool/.venv/bin/ef-analyze \
  --data bulgaria-oct-2026/data/ef_tur2 --out bulgaria-oct-2026/analysis/ef_tur2 \
  --title 'Bulgaria 2026 R2 runoff — domestic sections, round 1 control' \
  --controls bulgaria-oct-2026/data/ef --prev-party 'votes:Yotova'
analysis-tool/.venv/bin/python bulgaria-oct-2026/scripts/summarize_forensics.py \
  --data data/ef_tur2 --out analysis/ef_tur2
MPLCONFIGDIR=/tmp/bulgaria-mpl analysis-tool/.venv/bin/python \
  bulgaria-oct-2026/scripts/build_site_figures_tur2.py
```

The capture intentionally retains its dated cache. To check a later publication, use a new
cache directory; do not overwrite the archived observation.
