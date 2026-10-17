# Drafts: letters and posts (English)

*Numbers are from the 13.10.2026 snapshot (99.98% counted, `is_final=false`;
DVK review of abroad votes — 19.10.2026). Re-verify after the final review.
All drafts refer to: <https://renatyv.org/sloveniya-referendum-2026/>*

*The letters below are the English versions. The Slovenian originals of the
same letters are preserved in [`DRAFTS_sl.md`](DRAFTS_sl.md) — for Slovenian
media desks and official bodies a Slovenian letter normally lands better;
English is perfectly fine for Pod črto/Oštro, the forensics community and
international institutions (all of them work in English).*

---

## 1. Press pitch — editors (RTV MMC, STA, Delo, Dnevnik, Večer, 24ur, Siol, Finance; EN)

**Subject:** 
62% of units and 60% of stations said YES to the 'RTV Slovenia fee'

**Content**
Dear editors,

I have independently checked the results of all four referendums of 11 October
at the level of all 2,984 polling stations. Two findings your readers may find
interesting:

1. 62% of units and 60% of stations said YES to the 'RTV Slovenia fee'
2. 62% of units and 56% of stations said YES to the 'Parliamentary Investigations Act'
3. No traces of manipulation.

Link to full analysis:
https://elections-fraud.com/sloveniya-referendum-2026/index.html

Best regards,
Renat Iuldashev, Former professor of Applied Math., currently software engineer.

---

## 2. Letter to the editor — Delo / Dnevnik / Večer (~1,900 characters; EN)

**546 votes: what the referendums tell us about the rules**

I checked the referendums of 11 October station by station — 2,984 polling
stations, official data of the State Electoral Commission. The finding that
pleasantly surprised me: **no statistical traces of manipulation.** The tests
election forensic teams worldwide use to detect inflated results — from the
Shpilkin method to machine learning — all came out clean. When I injected
simulated fraud into the data, every alarm fired; nothing is a blind spot.
The Slovenian count looks like a textbook honest count.

Yet the same votes reveal something worth a public debate: how much the rules
of aggregation matter.

- The RTV Slovenia fee survived: abolition was rejected by **546 votes** — fewer
  than the number of invalid ballots (2,913). Voters who came to the polls on
  11 October were in favour of abolition (a margin of 29,734 votes); early
  voters (more than 75,000 — the second-largest early turnout in Slovenian
  referendum history) and postal voters decided otherwise.
- Slovenia sums its referendums nationally. If the same votes were counted by
  territory — as most of the world does — abolition would win in 5 of the 8
  electoral units, in 46 of the 88 districts and in 1,857 of the 3,083 polling
  stations. Under different rules, the outcome on the parliamentary-investigations
  act would flip as well.
- That law fell under Article 90 of the Constitution: it is rejected only if NO
  wins a majority **and** at least one fifth of **all registered voters** votes
  NO. The bar of 339,473 votes exists only because 1,697,366 people are on the
  register — with 39% more registrations and the same votes, the law would have
  survived. The quorum thus imports people who did not vote into the outcome.

No traces of manipulation does not mean the system is immune to reversals:
546 votes, 3% of abstainers or 39% more registrations — each would have written
a different ending. I trust the count; I question rules we, the public, never
explicitly chose. Report, code and data: renatyv.org/sloveniya-referendum-2026

[full name, place]

---

## 3. X/Twitter — EN thread

**1/** Four referendums, one day, 2,984 precincts — every Slovenian voter got
all four ballots. That's a statistician's dream: four independent counts you can
cross-check. I ran the full election-forensics toolkit on the official data.
The numbers are clean. But the same ballots also show how much the *rule*
decides. 🧵

**2/** Verdict first: 8 families of tests (Shpilkin anomalous votes, comet tail,
Klimek fingerprints, Kobak integer peaks, Benford/last-digit, outliers,
duplicate protocols, isolation forest) — **no statistical traces of manipulation.**
The entire anomalous zone holds ≤1% of YES votes; deleting it shifts any outcome
by ≤0.15 points.

**3/** Is "clean" real, not a blind spot? I injected synthetic ballot-stuffing
into the data — every alarm fires (anomalous-zone signal ×12). My totals match
the Wikipedia table to the exact vote; arithmetic across all 12,332 precinct-rows:
zero discrepancies. Code and data are open.

**4/** Now the fun part. The RTV Slovenia fee survived by **546 votes** — a margin
smaller than the 2,913 invalid ballots. Count the same votes by Slovenia's 8
electoral units: fee abolition wins 5:3. By the 88 districts: 46:42. Station by
station: 1,857:1,198. Same ballots, different counting rule, different winner.

**5/** On election-day ballots alone, **YES won all four referendums** — including
the investigations law (+10,255). Both final rejections were decided by early
voters (75,000+, 2nd-largest early turnout in Slovenian referendum history) and
postal votes: ~9% of ballots cast before election day. That's why both races
flipped overnight — YES-leaning cities count first.

**6/** And the quorum. Article 90 rejects a law only if NO wins the majority AND
NO ≥ 1/5 of *all registered voters*. NO scored 472,444 against a bar of 339,473 —
a bar that exists only because 1,697,366 people were on the roll. With 664,854
more registrations and not one vote changed, the law would have survived.
The quorum imports non-voters into the outcome.

**7/** Bottom line: the count looks like a textbook honest vote. But 546 votes,
3% of abstainers, or 39% more names on the register — any of these would have
written a different history. Data decides; so do rules. Full analysis, open code,
5 languages: https://renatyv.org/sloveniya-referendum-2026

## 4. X/Twitter — single posts

*(standard X limit is 280 chars; both texts need Premium long-posts, or use them
as the opening tweet of the thread above)*

**EN:**
Ran the full election-forensics toolkit on Slovenia's 4 referendums (2,984
precincts, 4 ballots each): **no statistical traces of manipulation** — and the
toolkit demonstrably fires on synthetic fraud. The twist: same ballots, different
rule → different winner. RTV fee survived by 546 votes (< 2,913 invalid ballots);
counted by regions instead of nationally, it goes 5:3 the other way. Election-day
precincts said YES to all four; early + postal votes decided both rejections.
Open data & code: renatyv.org/sloveniya-referendum-2026

**SL (for the Slovenian audience):**
Referendume 11. 10. sem kot statistik preveril do zadnjega glasu: 2.984 volišč,
8 družin testov — **brez statističnih sledi manipulacije** (simulirane goljufije
sprožijo vse alarme, torej nič ni slepa pika). A isti glasovi kažejo, koliko
pomenijo pravila štetja:
→ pristojbina RTV je obstala z razliko **546 glasov** — manj kot neveljavnih
glasovnic (2.913); po volilnih enotah bi odprava zmagala 5 : 3;
→ na voliščih volilnega dne je ZA zmagalo na **vseh štirih** vprašanjih —
odločilo je predčasno in poštno glasovanje (~9 % glasovnic).
Podatki, koda, poročilo (SL/EN/HR/IT/HU): renatyv.org/sloveniya-referendum-2026

## 5. Reddit r/slovenia

**Title:** Preveril sem vseh 2.984 volišč s 4 referendumov: statistično čisto — ampak pravila odločajo

Celotna analiza z grafikoni, kodo in podatki: https://renatyv.org/sloveniya-referendum-2026
(V komentarjih z veseljem odgovorim na vprašanja o metodah.)

Kratek povzetek: osem družin volilno-forenzičnih testov (Shpilkin, Klimek, Kobak,
Benford/digitalni testi, dvojniki protokolov, izolacijski gozd …) ne najde sledi
manipulacije; vbrizgane sintetične goljufije sprožijo vse alarme; vsote so
preverjene do zadnjega glasu. Zanimivejše je drugo: isti glasovi pod različnimi
pravili dajejo različne zmagovalce — pristojbina RTV je obstala z razliko 546
glasov (manj kot neveljavnih glasovnic), po volilnih enotah bi odprava zmagala
5 : 3, na voliščih volilnega dne pa je ZA zmagalo na vseh štirih vprašanjih
(odločilo je predčasno in poštno glasovanje). Kvorum 90. člena pa je dobesedno
odvisen od velikosti volilnega registra.

## 6. Email to DVK (Državna volilna komisija; EN)

**Subject:** Thank you for open data + observations from an independent check of the 11 Oct referendums

Dear members of the Commission,

I have independently verified the results of all four referendums at precinct
level (2,984 precincts × 4 ballots; analysis: renatyv.org/sloveniya-referendum-2026).
First, praise: the machine-readable data (JSON/CSV, the country–unit–district–
precinct hierarchy, `is_final` flags etc.) enables external verification of a
kind only a handful of election bodies in Europe provide.

I found no signs of manipulation. Three technical observations from the data:
1. At precinct 6005_044, the number of counted ballots exceeds the number of
   issued ballots by 1 in two referendums — most likely a desynchronization of
   the `udelezba`/`rezultati` files at the moment of collection.
2. At precinct 5007_005, `upr` = 999 in one referendum and 1001 in another
   (a minor register inconsistency).
3. Early voting (99 points, ~75,000 ballots) and OMNIA precincts are published
   aggregated, without a per-point breakdown — publishing them individually
   would extend external verification from 91% to 100% of ballots.

Analysis, code and data are open; I am happy to answer any questions.

Best regards, [name]

## 7. Email to academia / forensics community (FDV, UNG, Statistical Society; Kobak/Klimek/Alvarez; EIP, EPSA)

**Subject:** Four simultaneous referendums, one electorate — forensics & paradoxes case study (Slovenia, open data)

Dear colleagues,

I'd like to flag a dataset and analysis you may find useful. On 11 Oct 2026
Slovenia held **four referendums on one day, at the same 2,984 precincts, with
every voter receiving all four ballots**. That mutual control (identical turnout
distributions; three referendums serve as the honest control for the fourth) is
rare — I'd argue it's close to an ideal setting for election-forensics methods.

Analysis (open code + data): https://renatyv.org/sloveniya-referendum-2026

Headline results:
- 8 test families (Shpilkin, comet tail, Klimek fingerprints, Kobak integer peaks,
  Benford/Beber–Scacco digits, neighbor outliers, Isolation Forest, duplicate
  protocols): clean; anomalous-zone removal shifts outcomes ≤0.15 pp.
  Power quantified by injection self-tests (Shpilkin ×12; the integer-peaks test
  shown to be low-powered at ~460 voters/precinct).
- Three borderline second-digit p-values (min 0.005 vs Monte-Carlo null) do not
  survive Bonferroni over 16 tests and have the *opposite* of the fabricated-number
  profile; critique welcome.
- Paradox side: both rejections are counting-order reversals (election-day
  precincts went YES on all four; early/postal decided); territorial-majority
  counting flips both; the Art. 90 quorum makes rejection contingent on register
  size (+664,854 registrations ⇒ same votes keep the law).

I'd genuinely appreciate methodological criticism — particularly on the borderline
digit tests and on what four-simultaneous-ballots adds to Shpilkin-style controls.
Happy to share the per-precinct dataset (CSV) or walk through the pipeline.

Best regards, [name, one-line intro]

## 8. Letter to institutions / politicians (DVK, DZ Commission on Mandates and Privileges; cc party offices; EN)

**Subject:** Results of an independent statistical check of the 11 Oct referendums — and two questions about the rules

Dear Madam/Sir,

I have independently checked the results of all four referendums of 11 October
(2,984 precincts, official DVK data; report, code and data:
renatyv.org/sloveniya-referendum-2026). Two main findings:

**1. No traces of manipulation.** Eight families of election-forensics tests are
clean, and the toolkit demonstrably responds to injected synthetic fraud
(signal ×12). Trust in the count is warranted by these data.

**2. Beyond the votes, the rules decided the outcomes.** (a) On election-day
ballots, YES won all four questions — both rejections were decided by early and
postal voting (~9% of ballots). (b) The RTV fee survived by 546 votes — fewer
than the number of invalid ballots; under territorial counting, abolition would
have won (5:3 by units, 46:42 by districts). (c) The Article 90 quorum (one fifth
of all registered voters) depends on the size of the register: with 664,854 more
registrations, the same votes would have kept the law.

Two questions I am accordingly directing to you:
- Could the DVK publish early-voting results per individual point (currently
  aggregated into 99 groups without a breakdown)? That would extend external
  verification from 91% to 100% of ballots.
- Is the National Assembly's Commission on Mandates and Privileges considering
  an assessment of how sensitive the Article 90 quorum is to the size of the
  voter register?

I would gladly present the analysis in person or by video call; data and code
are open.

Best regards, [name, contact]

---

### Sending checklist

- [ ] 19.10: `uv run sloref fetch --volisca` → rebuild derived CSVs →
      `../analysis-tool/run_forensics_slovenia.sh` → `scripts/analyze_paradoxes.py`
      → `scripts/build_site_figures.py` → redeploy `site/`
- [ ] Update all numbers in drafts if any shifted; add «final results» note
- [ ] Verify X handles (many may be dormant); prefer email desks first
- [ ] Personalize pitch per outlet (RTV: RTV-fee angle; Finance: quorum/economics;
      Pod črto/Oštro: methodology + open data)
- [ ] EN thread: tag method authors; SL post: tag media; do not tag politicians
      in the same post as media (keeps it non-partisan)
- [ ] For Slovenian desks (RTV, STA, Delo, Dnevnik, Večer, 24ur, Siol, Finance)
      consider sending the Slovenian originals from `DRAFTS_sl.md`
