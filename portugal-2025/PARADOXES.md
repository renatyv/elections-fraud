# Voting paradoxes in the Portuguese elections of 2025–2026

*Which items of the catalogue [`paradoxes.md`](../paradoxes.md) are testable on
official Portuguese results — and what they show. Portugal has no ranked ballots,
so the ranked-only part of the catalogue (Condorcet cycles, best-is-worst,
later-no-harm/help, truncation, twin) is out of scope; but unlike a two-option
referendum, Portuguese ballots name 10+ lists — so the splitting family
(referendum/multiple-district, spoiler, cloning, frustrated majority) and the
runoff family (center squeeze, lesser-evil, no-show) are all live. Four real
elections are used: legislativas 18.05.2025 (the paradoxes of PR-D'Hondt and a
winner-take-all simulation on the same votes), autárquicas 12.10.2025 (real FPP
races for 308 câmaras), presidenciais 18.01.2026 + 08.02.2026 (two-round runoff).
Data: MAI exports (`data/legislativas2025_mai`, `data/autarquicas2025_mai`,
`data/presidenciais2026_{1S,2S}_mai`), CNE official seat map
(`data/cne/2025_ar_mapa_resultados.xlsx`); outputs in `analysis/paradoxes/`.*

## 1. Referendum paradox — PS beats CH on votes, loses to CH on seats

The actual system (22 D'Hondt círculos, no national tier) produced a genuine
inversion: the Socialist Party finished **ahead of Chega on national votes —
+4,313 votes, 23.81% vs 23.74% — yet 2 seats behind (58 vs 60)**. The CNE
official map gives the same inversion with an even narrower margin (PS
1,442,546 vs CH 1,438,554 = +3,992; MAI export: +4,313). Both parties also sit
below the 12 regional lists that dominate seat allocation, so tiny vote edges
in mid-magnitude círculos do not convert into seats.

| Counting rule | PS | CH | AD | winner |
|---|---|---|---|---|
| national votes (share) | 1,442,194 (23.81%) | 1,437,881 (23.74%) | 2,008,488 (33.15%) | **PS over CH by 4,313** |
| 22 D'Hondt círculos (actual) | 58 | 60 | 91 | **CH over PS by 2** |
| single 230-seat national D'Hondt district | 56 | 56 | 78 | tie |

A single national district would erase the inversion (56 : 56) — the same votes,
one change in the aggregation rule, three different PS–CH relationships. The
engine reproduces the official CNE allocation in all 22 círculos exactly before
any counterfactual is run.

## 2. Multiple-district paradox — winner-take-all would hand AD three quarters of the seats

Simulating single-member plurality on the *same* legislativas votes: AD wins
**2,343 of 3,092 freguesias (75.8%)** and **224 of 325 concelhos (68.9%)** —
on 33.2% of the vote. Under the actual D'Hondt it holds 91 of 230 seats (39.6%).

| Party | Vote share | D'Hondt seats | FPTP concelhos | FPTP freguesias |
|---|---|---|---|---|
| AD | 33.2% | 91 (39.6%) | **224 (68.9%)** | **2,343 (75.8%)** |
| CH | 23.7% | 60 (26.1%) | 67 (20.6%) | 309 (10.0%) |
| PS | 23.8% | 58 (25.2%) | 34 (10.5%) | 429 (13.9%) |

Note the PS–CH order flipping *again* between the two district sizes: PS beats
CH among freguesias (429 : 309 — urban parishes) but loses badly among
concelhos (34 : 67 — CH's wins are broad and rural, PS's are dense and urban).
Three aggregation rules — votes, freguesias, concelhos — give three different
PS↔CH answers, the multiple-district sensitivity in one dataset.

## 3. Spoiler and cloning counterfactuals — alliances, not voters, move 60+ seats

Exact counterfactuals: merge or split lists per círculo, re-run D'Hondt,
compare to the official 230 (engine validated against CNE first):

| Scenario | AD / united right | PS / united left | CH | IL | note |
|---|---|---|---|---|---|
| **actual** | 91 | 58 | 60 | 9 | CH 2 seats over PS |
| AD+CH united right | **154** | 57 | — | 9 | constitutional majority (154 > 115) on the same votes |
| Left united (PS+BE+PCP-PEV+PAN+L) | 81 | **84** | 55 | 9 | united left becomes the largest force on 34.1% of votes |
| IL does not run | 95 | 60 | 62 | — | IL's 9 seats: AD +4, CH +2, PS +2 |
| AD splits (PSD/CDS as in 2022) | 87 (86+1) | 61 | 61 | 9 | splitting costs AD 4 seats; PS and CH each gain |

Reading through the catalogue: the united-right result is the **spoiler effect**
in its purest form — CH's separate run costs the right a constitutional
majority, while AD+CH together on the same ballots take 154 of 230. The
left-united result is the same mechanism from the other side: 34% of votes
become the largest bloc (84 vs AD's 81). The AD split is the **cloning
paradox**: a perfectly natural split (the pre-2024 coalition status quo) would
have cost the AD list 4 seats to vote-splitting, handing PS +3 and CH +1 — no
voter changing their mind.

## 4. Frustrated majority — the autárquicas câmaras, real FPP races

Portugal's municipal presidents are elected by straight plurality — the exact
rule the catalogue flags for vote-splitting. In the 308 câmaras of 12.10.2025:

- **142 winners (46.1%) took office without a majority** of the valid vote;
- in **49 câmaras the winning list trails the opposing ideological bloc
  combined** — the *frustrated majority* form (the left/centre-left majority of
  voters is represented by a right-wing president, or vice versa);
- by winner's family: 27 socialist, 17 right, 4 communist, 1 left-wing winners
  sit against a local majority;
- the flagship case is **Lisboa**: the AD+IL list won the câmara with 110,586
  votes (42.8%) while the left lists together polled 116,837 — a 6,251-vote
  majority for the losing bloc. Sintra (winner 34.6% vs left bloc 61,681),
  Vila Nova de Gaia, Porto and Braga follow the same pattern.

Full table: `analysis/paradoxes/tables/autarquicas_frustrated.csv`.

## 5. Presidential runoff 2026 — center squeeze, lesser-evil evidence, no-show margins

First round (18.01.2026, mainland, 5,570,922 valid): Seguro 31.2%, Ventura
23.3%, Cotrim 16.0%, Gouveia 12.4%, Mendes 11.3%, others 5.8%. Only the top two
advanced — eliminating **Cotrim + Gouveia + Mendes, 2,215,086 votes = 39.8% of
valid ballots**, while the finalists carried 54.5%. That is the *center
squeeze*: the middle of the electorate was removed from the choice precisely
because its support was spread over three names. Whether any eliminated
candidate would have beaten either finalist head-to-head is not measurable on
categorical ballots; what is measurable is what their voters did next.

**Lesser-evil voting, measured.** An ecological transfer matrix
(freguesia-level weighted least squares, R² = 0.997; assumption of homogeneous
transfer rates) estimates 1S→2S behavior:

| 1S vote | → Seguro | → Ventura | → blank | → null | → abstain |
|---|---|---|---|---|---|
| Cotrim | 40.4% | 22.9% | 13.4% | 8.1% | 15.1% |
| Gouveia | 77.4% | 9.9% | 1.2% | 0.0% | 11.4% |
| Mendes | 76.6% | 15.4% | 6.9% | 1.1% | 0.0% |
| Seguro | 99.7% | — | — | 0.3% | — |
| Ventura | — | 99.0% | — | 1.0% | — |

Between the rounds, **blank ballots nearly tripled (+113,538, from 60,899 to
174,437) and null ballots grew by +33,316**, while turnout itself fell by
262,687 — the classic two-round lesser-evil pressure signature: voters whose
candidate was eliminated either defected to a "lesser evil", spoiled, or went
home. The moderate-right center (Cotrim) split — only 40% transferring to
Seguro against 23% to Ventura and 21% to blank/null — is exactly the
vote-splitting that decides runoffs.

**No-show / perverse response: absent, with explicit margins.** Both runoff
slots were safe by wide margins: Seguro led Ventura by 441,208 in the first
round; Ventura led the third-placed Cotrim by **405,745** — Ventura would have
missed the runoff only if >405,745 of his first-round voters had stayed home
(that many stayed-home voters *causing* their side to lose is the no-show
scenario; the observed gap makes it unreachable). The rule's known
non-monotonicity (a candidate harmed by *receiving more* first-round votes —
pushing a stronger rival into the final) had no room to fire: displacing
Seguro from the top two would have required a >405,745-vote swing.

## 6. What this data cannot test

Condorcet winner/loser and cyclical majorities, best-is-worst, later-no-harm /
later-no-help, truncation, twin — all require ranked ballots, which no
Portuguese election offers. The absolute-majority and reinforcement rows of the
catalogue are rule-design questions, not measurable on a single ballot set.
Strategic voting is unmeasurable without preference polls. Everything above is
computed on the votes as cast; no survey data is used.

## Reproducibility

`uv run scripts/analyze_paradoxes.py` → `analysis/paradoxes/`
(`metrics.json`; tables: `ar2025_counterfactual_seats.csv`,
`autarquicas_frustrated.csv`, `fptp_raw.json`). The D'Hondt engine is checked
against the official CNE map (all 22 círculos, 230 seats) before any
counterfactual runs; national vote totals come from the MAI círculo export and
differ from the CNE map by ≲700 votes per party (≈0.05%) — margin statements
above quote both where they differ. Presidential figures cover the mainland
freguesia export (3,259 units, 9,262,653 registered; emigrant circles excluded,
as everywhere in this project; the two rounds are joined on the ID-stripped
territory path, since MAI re-keys territories between elections).
