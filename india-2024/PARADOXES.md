# India, Lok Sabha 2024: what the voting-system paradoxes look like in the official counts

Companion analysis to [REPORT.md](REPORT.md) (statistical fraud check): the same
data, a different question. Instead of *was the count honest*, this asks *what
the first-past-the-post rule itself did to the votes* — the pathological
behaviours catalogued in [`paradoxes.md`](../paradoxes.md). Analysis date:
16.10.2026.

**Conclusion up front: in 2024, 182 of 542 contested seats (33.6%) were
decided by vote splitting — a third candidate's votes exceeded the winner's
entire margin — and 263 winners (48.5%) were elected with less than half the
vote.** Fragmentation decided one seat in three: it was higher than 2019
(23.6%) but lower than 2014 (44.0%). The BSP was the single biggest spoiler
nationally (54 seats), cutting both ways — the runner-up was hurt in 112
INDIA-won and 61 NDA-won seats. Under a full INDIA-bloc consolidation
counterfactual the bloc gains 10 seats (NDA 292 → 285 — still a governing
majority); NDA consolidation gains 2. In Uttar Pradesh, the recovered Form 20
booth data shows that in most BSP-spoiler seats the BSP's support overlaps
the opposition's turf far more than the BJP's (permutation p < 0.05 in 27 of
46 cases) — the vote-transfer required by the counterfactual is
geographically plausible there, though it remains an assumption, not a
measurement. Everything preference-based in `paradoxes.md` (Condorcet loser,
center squeeze, best-is-worst, lesser-evil) is untestable from any plurality
count: India's ballots record one mark each, and no ranked or approval data
exists for this election.

## 1. What official plurality counts can and cannot test

The paradoxes in `paradoxes.md` are properties of *preferences*. The official
results — like every Indian FPTP publication — record only first-preference
totals per candidate. Three families survive that limitation:

| check | what it needs | status |
|---|---|---|
| Frustrated-majority bound | winner's vote share | **exact**: >50% ⇒ winner is Condorcet winner, paradox impossible |
| Spoiler / vote-splitting | per-candidate totals | **exact arithmetic**: third votes vs margin |
| Alliance consolidation | party→bloc map + totals | **counterfactual**, assumption stated |
| Booth-level transfer plausibility | Form 20 booth counts | **ecological**: says where spoiler votes sit, not where they would go |

Not checkable at all: Condorcet loser, center squeeze, best-is-worst
(anti-plurality), lesser-evil voting (all require lower preferences);
later-no-harm/help (vacuous — plurality ignores later preferences);
no-show, perverse response, monotonicity (properties of multi-round or
counterfactual procedures; a single-round FPTP count contains nothing to
test, and FPP is provably immune to no-show/perverse response);
multiple-district paradox (impossible under FPP by theory — the
booth-level data would allow *gerrymander sensitivity* simulations, which
are adjacent but out of scope here).

Datasets: the official ECI in-rolls export (542 contested PCs, 2024) with
2014 and 2019 ECI exports as controls, and the project's Form 20 booth
recovery for Uttar Pradesh (68 of 80 PCs, ~110k stations). NOTA is excluded
from all candidate arithmetic (it is a rejection, not a candidacy). Winner
shares use valid votes for candidates, excluding NOTA. Reproduction:
`uv run python scripts/paradox_analysis.py` → `analysis_paradoxes/`.

## 2. The majority bound: where the frustrated-majority paradox is impossible

A candidate with more than half of all candidate votes pairwise-beats every
rival *by construction* — every voter who ranked them first prefers them to
everyone else, and they are a majority. So the frustrated-majority paradox
can only occur in sub-50% seats.

| year | seats | median winner share | winners >50% (paradox impossible) | winners <50% (possible, unverifiable) |
|---|---|---|---|---|
| 2014 | 543 | 47.2% | 206 (37.9%) | 337 (62.1%) |
| 2019 | 542 | 52.8% | 354 (65.3%) | 188 (34.7%) |
| 2024 | 542 | 50.1% | 279 (51.5%) | 263 (48.5%) |

The BJP's own seats tell the fragmentation story directly: 143 of its 282
seats in 2014 (50.7%) were won below half the vote (median share 50.0%);
in 2019, 73 of 303 (24.1%, median 55.7%); in 2024, 74 of 239 contested seats
(31.0%, median 53.2%).

## 3. The spoiler effect: one seat in three

A seat is *spoiler-decided* when at least one non-top-two candidate polled
more votes than the winner's margin — i.e. the runner-up would have won
receiving only that candidate's votes.

| year | spoiler-decided seats | share | mean spoilers per such seat |
|---|---|---|---|
| 2014 | 239 | 44.0% | 1.78 |
| 2019 | 128 | 23.6% | 1.79 |
| 2024 | 182 | 33.6% | 1.54 |

2024 sat between the two controls: less fragmented than the 2014 wave, much
more than the two-cornered 2019. Top spoiler parties 2024: **BSP 54 seats**,
BJP 27, INC 26, CPI(M) 14, BRS 11, independents 11. The spoiling cut both
blocs: the winner belonged to INDIA in 112 of these seats, to the NDA in 61.

Largest 2024 cases (votes by which the spoiler covered the whole margin):

| constituency | winner (share) | runner-up | margin | top spoiler | spoiler votes |
|---|---|---|---|---|---|
| Attingal (KL) | INC 33.6% | CPI(M) | **684** | BJP | 311,779 |
| Medak (TG) | BJP 34.1% | INC | 39,139 | BRS | 396,790 |
| Maldaha Uttar (WB) | BJP 37.4% | AITC | 77,708 | INC | 384,764 |
| Baharampur (WB) | AITC 38.1% | INC | 85,022 | BJP | 371,885 |
| Patiala (PB) | INC 26.7% | AAP | 14,831 | BJP | 288,998 |

Attingal is the extreme: a 684-vote margin with a third candidate holding
311,779 votes — the winner's margin is 0.2% of the spoiler's vote. The same
seat family recurs across cycles: 2019's record was Maldaha Dakshin
(INC won by 8,222 with the AITC at 351,353); 2014's was Chikkballapur (INC
by 9,520 with the JD(S) at 346,339).

## 4. Alliance consolidation: the bloc counterfactual

Mapping parties to their 2024 blocs (`data/alliances_2024.csv`; 85.7% of
candidate votes mapped, the rest — regional and independent — treated as
unaffiliated), the seat totals are NDA 292, INDIA 233, other 17.

One-sided counterfactual — *one bloc pools every vote it received in the
seat into a single candidate; the rival bloc stays exactly as split as it
actually was; third parties keep their votes*:

- **INDIA consolidates everywhere: +10 seats** (7 from the BJP, 2 from
  independents, 1 from the SAD — the latter two outside the NDA, so the bloc
  itself only drops to 285). NDA 292 → 285 — still above the 272 needed
  to govern. Fragmentation cost the INDIA bloc roughly a tenth of the seats
  it contested together-but-separately, but full unity would not have
  changed the government.
- **NDA consolidates everywhere: +2 seats** (Cuddalore and Virudhunagar in
  Tamil Nadu, both from the INC — seats where the split NDA vote and the
  Naam Tamilar Katchi's surge fractionated the field).

The asymmetry is structural: the NDA entered 2024 mostly seat-adjusted
(one candidate per ally per seat), while the INDIA bloc failed to adjust in
several states (IND+AAP in Punjab, SP+INC leftovers, West Bengal's
four-cornered contests). Note these are *upper bounds with a behavioural
assumption* — pooling assumes bloc voters would transfer, which section 5
shows is plausible in some states and questionable in others.

## 5. Uttar Pradesh: booth-level transfer plausibility (Form 20)

The Form 20 recovery (per-station candidate counts, 68 of 80 PCs) turns the
spoiler arithmetic into geography. For every spoiler case in a covered
constituency: correlate the spoiler's booth-level vote share with the
runner-up's and with the winner's across ~1,300–1,700 stations each, and
permutation-test the difference (2,000 shuffles). Shares are compositional
(they compete for the same 100%), so *both* correlations are negative by
construction — the informative quantity is the **asymmetry**: a spoiler
sitting on the runner-up's turf (r_spoiler,runner ≫ r_spoiler,winner) draws
from a voter pool the runner-up could plausibly absorb.

- 46 spoiler cases in the covered constituencies; the BSP is the spoiler in
  nearly all of them.
- **27 of 46 show a significant asymmetry (p < 0.05)**; in the strong
  majority the BSP's support overlaps the opposition's (SP/INC) booths far
  more than the BJP's — e.g. Sambhal (r −0.13 vs −0.45, diff +0.32,
  p = 0.0005), Sultanpur (+0.22, p = 0.0005), Dhaurahra (+0.24,
  p = 0.0005).
- Reversed cases exist: in Bhadohi the BSP's votes sit relatively on the
  *BJP's* turf (diff −0.20, p = 0.0005), in Ghazipur slightly so (−0.07) —
  there, BSP votes are not an obvious SP reservoir.

UP totals for context: of the 80 seats, 56 winners were below 50%; the BJP
won 33, and in **18 of those the combined opposition vote exceeded the
BJP's** — the frustrated-majority pattern in its pure form, subject to the
same untestable transfer assumption.

## 6. Limitations

1. **No preferences exist.** Every "would have transferred" statement is an
   assumption; the booth correlations describe where votes *are*, not where
   they *would go*. Individual-level transfer can differ from ecological
   overlap (robustness: permutation-tested asymmetries only, shares with
   compositional bias noted).
2. **The bloc map is best-effort** (85.7% vote coverage). Small and
   state-party memberships changed during the cycle; 15–20 seat-level
   judgements would move individual seats but not the pattern.
3. **Booth coverage** is 68 of 80 UP PCs; four low-coverage constituencies
   are approximate (see the DATACARD). Candidate columns are labelled by
   matching to official totals — independent columns carry no party signal
   and are excluded from the correlation analysis.
4. 2019's ECI export has no electors field, which this analysis does not
   need; 2014/2019 spoiler comparisons use identical arithmetic on the
   candidate totals.
5. Surat (won unopposed) is absent from the 2024 export — 542, not 543.

## 7. Outputs

| file | content |
|---|---|
| `analysis_paradoxes/pc_paradoxes_{2014,2019,2024}.csv` | per-constituency: winner/runner-up, margin, majority flag, spoiler counts and largest spoiler |
| `analysis_paradoxes/alliance_2024.csv` | per-constituency bloc totals and consolidation flips |
| `analysis_paradoxes/up_booth_transfer_2024.csv` | per-UP-spoiler-case booth correlations and permutation p-values |
| `analysis_paradoxes/up_party_correlations_2024.csv` | booth-share correlations between major UP parties per constituency |
| `analysis_paradoxes/summary_by_year.csv`, `summary.json` | headline numbers |

Public summary: [site/india-2024](../site/india-2024/) (English / हिन्दी),
figures from `scripts/build_paradox_figures.py`.
