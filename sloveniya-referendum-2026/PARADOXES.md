# Voting paradoxes in the Slovenian referendums of 11.10.2026

*Which items of the catalogue [`paradoxes.md`](../paradoxes.md) are testable on this
data — and what they show. A binary ZA/PROTI ballot cannot produce vote-splitting,
so most of the catalogue (Condorcet winner/loser, center squeeze, spoiler, cloning,
best-is-worst, lesser-evil, later-no-harm/help) is structurally out of scope: it needs
preferences over 3+ alternatives. Three items are testable — all three turn out
to be live on this election. Data: official DVK aggregates
(`data/derived/nacionalni_pregled.csv`) and precinct results
(`data/derived/volisca_all.csv`); outputs in `analysis/paradoxes/`.*

## 1. Multiple-district paradox — it occurred, on the real territories

Slovenian referendums are decided by the national vote total. Had they instead been
decided by winning a **majority of territories** (electoral-college style), the
outcomes would change: on `rtv_prispevek` the national PROTI win (by 546 votes)
turns into a ZA win at every territorial level, and on `preiskava` (PROTI by
23,147 votes) into a ZA win at the level of the 8 electoral units and of polling
stations — only the 88 districts keep PROTI (48:40):

| Referendum | National winner | 8 units | 88 districts | 3,083 stations |
|---|---|---|---|---|
| ZPPre-B (binding) | **PROTI 51.26%** | ZA 5 : 3 PROTI **← reversal** | ZA 40 : 48 PROTI | ZA 1,728 : 1,327 PROTI (+28 ties) **← reversal** |
| social assistance | **ZA 60.54%** | ZA 8 : 0 PROTI | ZA 71 : 17 PROTI | ZA 2,602 : 463 PROTI (+18 ties) |
| voting rights | **ZA 55.30%** | ZA 6 : 2 PROTI | ZA 64 : 24 PROTI | ZA 2,213 : 842 PROTI (+28 ties) |
| RTV fee | **PROTI 50.03%** | ZA 5 : 3 PROTI **← reversal** | ZA 46 : 42 PROTI **← reversal** | ZA 1,857 : 1,198 PROTI (+28 ties) **← reversal** |

This is the multiple-district paradox on real, non-designed territories, and the
territorial form of the *frustrated majority*: on both rejected questions the
nationally winning side is the minority among territories. Figure: `figures/territory.png`.

### 1a. Aggregation over time: the counting-night reversals

The same sensitivity plays out over time (media-reconstructed partial results,
[`data/wikipedia/counting_night_dynamics.md`](data/wikipedia/counting_night_dynamics.md)):
on all four questions **ZA led after the first fifth of ballots counted**; both final
PROTI wins are counting-order reversals — cities (ZA-leaning) are counted faster.

### 1b. Aggregation over ballot mode: who actually decided it

Decomposing the national totals (the 9% of ballots without a regular-precinct
breakdown flipped both rejections):

| Referendum | Election-day precincts | Early voting | Postal/abroad (residual) | National |
|---|---|---|---|---|
| ZPPre-B (binding) | ZA +10,255 | PROTI -30,212 | PROTI -3,190 | PROTI 23,147 |
| social assistance | ZA +208,991 | PROTI -13,018 | PROTI -1,268 | ZA 194,705 |
| voting rights | ZA +120,275 | PROTI -20,564 | PROTI -1,935 | ZA 97,776 |
| RTV fee | ZA +29,734 | PROTI -27,041 | PROTI -3,239 | PROTI 546 |

**On election-day ballots alone, all four questions went ZA.** Both rejections were
decided by early voters (>75,000 people, the second-largest early turnout in Slovenian
referendum history) plus postal/abroad votes. Figure: `figures/decomposition.png`.

## 2. Gerrymander bound — a quarter of the vote is enough in principle

With precinct-level districting and winner-take-all districts, can the national
loser win a majority of 88 (roughly equal) districts? Deterministic greedy packing
(loser's strongest precincts first, districts 0.85–1.15 of the target electorate,
no geography constraint — one construction, hence a lower bound on what a motivated
mapmaker could do):

| Referendum | National loser | Districts won by packing | Enough for 45? |
|---|---|---|---|
| ZPPre-B (binding) | ZA (50.53%) | 45 | **yes** |
| social assistance | PROTI (37.65%) | 17 | no |
| voting rights | PROTI (42.93%) | 32 | no |
| RTV fee | ZA (51.68%) | 45 | **yes** |

The packing succeeds exactly where the loser is near parity on election-day
precincts (50.5% and 51.7%):
Slovenia's precinct geography is not segregated enough to
stretch a 38–43% minority over 45 districts of ~equal size. The arithmetic floor
is unchanged, though: winning 45 of 88 equal winner-take-all districts requires
just above **25.6%** of the national vote.
Slovenia does not decide referendums this way — the numbers quantify how much the
aggregation rule, not the voters, would decide the outcome.

## 3. Art. 90 quorum and the no-show family — exact margins

The binding referendum (`preiskava`) is rejected only if **PROTI wins a majority of
valid votes AND PROTI ≥ 1/5 of all registered voters**. Margins on both conditions
(the other three were consultative; their rows are the same arithmetic applied
counterfactually):

| Referendum | PROTI votes | Quorum | Margin over quorum | Majority margin | Loser's flip votes | Extra registrations to void the quorum |
|---|---|---|---|---|---|---|
| ZPPre-B (binding)* | 472,444 | 339,473 | +132,971 | 23,147 | 23,148 (3.01% of abstainers) | +664,854 |
| social assistance | 364,377 | 339,473 | +24,904 | 194,705 | 194,706 (25.28% of abstainers) | — |
| voting rights | 412,708 | 339,473 | +73,235 | 97,776 | 97,777 (12.69% of abstainers) | — |
| RTV fee | 462,299 | 339,474 | +122,825 | 546 | 547 (0.07% of abstainers) | +614,127 |

\* binding; Art. 90 applies formally only here. Figure: `figures/quorum.png`.

Reading the table through the paradoxes.md families:

- **No-show / perverse response: absent, provably.** The rule is individually
  monotone — an extra ZA vote can never cause rejection, an extra PROTI vote can
  never prevent it — exactly matching the catalogue's "Plurality: −" for these rows.
- **The quorum imports non-voters into the outcome.** Rejection of ZPPre-B needed
  339,473 PROTI votes *because 1,697,366 people were registered*. Had the
  register been 2,362,220
  (39% larger), the same
  472,444 PROTI votes would no longer have cleared 1/5 — the law would have
  stood without a single vote changing. The flip side: 23,148 additional
  ZA voters (3.0% of the 770,243 abstainers)
  would have kept the law.
- **Fragility is real but bounded.** The RTV margin — 546 votes
  out of 924,052 valid — is smaller than its 2,913
  invalid ballots; 547 extra ZA votes flip it. Yet even under the
  Art. 90 rule applied counterfactually to all four questions, no outcome changes:
  on both PROTI-won questions PROTI also cleared the quorum
  (+132,971 and +122,825), and on the ZA-won ones the
  quorum does not stand in the way of approval.

## 4. What this data cannot test

Condorcet winner/loser and cyclical majorities, center squeeze, spoiler, cloning,
best-is-worst, lesser-evil, later-no-harm/help, truncation, twin — all require
ranked ballots or ≥3 options; a ZA/PROTI vote has two strategies and no
vote-splitting. Strategic voting (the catalogue's one "+" for every procedure)
is unmeasurable without preference polls, which the project does not collect.

## Reproducibility

`uv run python scripts/analyze_paradoxes.py` → `analysis/paradoxes/`
(tables: `territorial_winners.csv`, `decomposition.csv`, `gerrymander.csv`,
`quorum_margins.csv`; figures: `territory.png`, `decomposition.png`, `quorum.png`;
`metrics.json`). Precinct sums vs national totals differ by construction
(early-voting points and the postal/abroad residual) — the national rows of
`nacionalni_pregled.csv` are authoritative, as everywhere in this project.
