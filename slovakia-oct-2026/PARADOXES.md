# Voting paradoxes in the Slovak local and regional elections of 24.10.2026

*Which items of the catalogue [`paradoxes.md`](../paradoxes.md) are testable on
this data — and what they show. Slovakia elects governors and mayors by
single-round first-past-the-post (plurality), so the catalogue's
FPTP-susceptible items are all in scope; three of them turn out to be live.
Data: official ŠÚSR/volbysr.sk exports (`data/official/`), the MAI adaptation
(`data/ef/`, `scripts/build_ef_csv.py`), the election-night capture
(`data/trends/`). Numbers: `scripts/analyze_paradoxes.py`, log —
`analysis/paradoxes/PARADOX_LOG.txt`, tables and figures —
`analysis/paradoxes/{tables,figures}/`. Forensics (do the numbers add up?) —
[`REPORT_statistical_fraud_analysis.md`](REPORT_statistical_fraud_analysis.md).*

## 1. Cloning, inverted: the joint candidacies consolidated both blocs

The catalogue's cloning paradox punishes FPTP for vote-splitting between
copies. Slovakia 2026 is the mirror image — the parties **de-cloned**
themselves: in seven of eight kraje the two big camps each ran ONE joint
candidate where in 2022 the same parties competed separately (SMER–SD, HLAS
and SNS jointly; on the opposition side PS, SaS, KDH, Demokrati, SLOVENSKO…
jointly, with the lead varying by kraj).

Governor races, joint candidate 2026 vs the combined vote of the same bloc's
2022 candidates (`analysis/paradoxes/tables/bloc_consolidation.csv`):

| Kraj | Bloc | 2022 combined (candidates) | 2026 joint | Δ |
|---|---|---|---|---|
| Bratislavský | opposition (Droba) | 172,848 (3) | **188,732** | +15,884 (+9.2%) |
| Bratislavský | government (Gajarský) | 32,662 (2) | 30,695 | −1,967 (−6.0%) |
| Trnavský | opposition (Viskupič) | 69,743 (1) | **103,083** | +33,340 (+47.8%) |
| Trnavský | government (Hambálek) | 25,941 (2) | 22,263 | −3,678 (−14.2%) |
| Trenčiansky | government (Baška) | 137,506 (2) | **119,827** | −17,679 (−12.9%) |
| Trenčiansky | opposition (Svítková) | 32,547 (1) | 81,400 | +48,853 (+150.1%) |
| Nitriansky | government (Becík) | 63,733 (2) | **115,058** | +51,325 (+80.5%) |
| Nitriansky | opposition (Varga) | 33,467 (1) | 65,807 | +32,340 (+96.6%) |
| Žilinský | opposition (Jurinová) | 80,049 (1) | **134,617** | +54,568 (+68.2%) |
| Žilinský | government (Choma) | 80,272 (3) | 66,725 | −13,547 (−16.9%) |
| Prešovský | opposition (Majerský) | 111,343 (1) | **138,819** | +27,476 (+24.7%) |
| Košický | opposition (Porvažník) | 122,289 (2) | 73,304 | −48,985 (−40.1%) |
| Košický | government (Šimko) | 52,182 (3) | 57,682 | +5,500 (+10.5%) |

Interpretation (with the usual four-year caveat — these are different
elections, not a controlled experiment): where the joint nomination united a
bloc that had been competing with itself, it captured more than the sum of
its 2022 parts (Viskupič +48%, Becík +81%, Jurinová +68%, Svítková +150%);
where the bloc was already consolidated in 2022, the joint candidate tracked
the combined total (Baška −13%, Gajarský −6%). In Košický the opposition's
two 2022 candidates totalled 122,289, but 2026's single candidate Porvažník
managed only 73,304 — while the winner Trnka (independent, ex-bloc) lost
votes relative to nobody: he simply kept a plurality. The 2022 splitting
that let a 32% candidate win in 2026 was built four years earlier.

## 2. Frustrated majority: two of eight governors, 13.6% of mayors

Single-round plurality elects winners the majority voted against:

- **Košický kraj: Rastislav Trnka won with 32.00%** — 68.00% voted for
  someone else; margin over Porvažník: 3,117 votes (76,421 vs 73,304).
  A two-round runoff (as in most of the world for such offices) would have
  pit Trnka against Porvažník with the other 37% of first preferences
  in play — the outcome would be unknowable from plurality ballots, which
  is precisely the information FPTP refuses to collect.
- **Prešovský kraj: Milan Majerský won with 48.77%** — 51.23% against.
- Mayors: 395 of 2,912 (13.6%) elected with <50%, 134 (4.6%) with <40%,
  minimum 20.7%; **779,695 votes — 37.5% of all mayor-race votes — elected
  nobody**. Structure barely moved against 2022 (432/2,913 below 50%;
  histogram: `analysis/paradoxes/figures/winners_share_hist.png`).

The centre-squeeze and spoiler items of the catalogue need preference data
that FPTP ballots do not carry — not testable, but their *prevalence* is
visible: in a third of municipalities the elected mayor is the first choice
of under half of the voters who took part in his own race.

## 3. Counting-night dynamics: no reversal after 38% counted

The intraday capture (36 snapshots, 24.10 22:02 → 26.10 09:51 SELČ) covers
all 8 governor races and the 8 capital mayor races. The capture starts at
38.3% counted (OSK), and in **not one of the 16 races did the leader change
after that point** (`analysis/paradoxes/tables/intraday_leaders.csv`;
timeline of the tightest race:
`analysis/paradoxes/figures/intraday_kosicky.png`). In Košický the count
never threatened Trnka's lead despite the 3,117-vote final margin — the
early-counted cities (Košice, Porvažník-leaning) and the late-counted
villages were close enough in the first two fifths. An honest uniform
count, no Chicago-style late surges.

## 4. Two ballots, one visit: the differential-participation signature

The Slovak joint election is a natural experiment: every voter receives a
governor ballot and a mayor ballot at the same table, minute. The two
commissions record participants separately, and they disagree — by
**79,290** in 2026 (mayor-side higher; 2022: −99,229, shrinking 21% on
common municipalities). The gap concentrates in municipalities with
Slovakia's largest Romani communities (Jarovnice −1,726, Zlaté Klasy
−1,716, Bystrany −1,145, Luník IX −575…) plus a diffuse city component
(EU-citizen residents may vote municipally only). Scatter:
`analysis/paradoxes/figures/dual_ballot_scatter.png`.

This is the measurable trace of clientelist mobilisation — local machines
delivering "their" voters for the personal, local race and nobody for the
regional one. Two consequences:

1. **For forensics:** extreme municipal turnout in low-competition
   municipalities is the Slovak structural norm. A Shpilkin-type read of
   the mayor race that treats the high-turnout tail as anomalous will
   flag precisely these municipalities (the forensics report handles this
   by per-kraj runs and the 2022 controls — the tails stay within the 2022
   pattern).
2. **For the paradox catalogue:** the "no-show paradox" family assumes
   sincere abstention; here abstention is manufactured selectively — the
   same electorate is 20 points larger in the race where a local patron
   has an interest. FPTP's vulnerability is not only how votes are counted
   but who is motivated to show up for which race on the same ballot paper.

## 5. Out of scope, and why

- **Condorcet, centre-squeeze, best-is-worst, later-no-harm/help** —
  require ranked or rated preferences; plurality ballots carry none.
- **Multiple-district / gerrymander bound** — the governor races are
  at-large in fixed kraje (no districting to manipulate); the mayors are
  one seat per municipality. Nothing to gerrymander in the personal races.
  (The council races are proportional — out of this report's scope.)
- **Lesser-evil desertion** — measurable only with panel data on individual
  voters; the aggregate 2022→2026 swings (HLAS −2.8 pp, independents +2.0
  pp, table `party_swing_2022_2026.csv`) are consistent with, but do not
  identify, lesser-evil behaviour within the 2026 joint candidacies.

## Figures

| File | Content |
|---|---|
| `figures/winners_share_hist.png` | winning-mayor share distributions, 2022 vs 2026 |
| `figures/intraday_kosicky.png` | Košický governor race, candidate shares vs count progress |
| `figures/dual_ballot_scatter.png` | OSK vs OSO participation, same precincts, 2026 |
| `figures/turnout_2022_2026.png` | mayor-race turnout per precinct, 2022 vs 2026 |
