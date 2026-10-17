# Outreach: Slovenian referendums 11.10.2026 — targets and drafts

Public page: `https://renatyv.org/sloveniya-referendum-2026/` (5 languages: SL/EN/HR/IT/HU).
Reports: [`../statistical_fraud_analysis.md`](../statistical_fraud_analysis.md),
[`../PARADOXES.md`](../PARADOXES.md), [`../report.md`](../report.md).
Drafts: [`DRAFTS.md`](DRAFTS.md).

## Two stories, deliberately kept separate

1. **«Чисто» / Clean** — independent forensics on the official DVK precinct data found
   no statistical traces of manipulation (8 test families, 2,984 precincts × 4 ballots,
   toolkit self-tested: synthetic stuffing fires ×12). This is the *trust* story —
   it protects against «украли выборы» narratives on all sides.
2. **«Правила решают» / Rules matter** — the paradoxes: territorial flips (RTV fee lost
   nationally by 546 votes but wins 5:3 among the 8 units, 46:42 among districts,
   1,857:1,198 among precincts); election-day ballots alone went YES on **all four**
   questions — early (75,000+) and postal votes decided both rejections; the 546-vote
   margin is smaller than the 2,913 invalid ballots; the Art. 90 quorum imports
   non-voters (+664,854 registrations and the same votes would keep the law).
   This is the *news* story. Frame it strictly as «how aggregation rules shape outcomes»,
   never as «the real winner is X» — Slovenia's rule is the national total, and the
   result is legitimate; anything else hands the story to conspiracists.

## Timing

- Data snapshot: 12.10.2026, 99.98% counted, `is_final=false`. DVK reviews the
  abroad/postal votes on **19.10.2026**. Recommended send window: **19–20 October**,
  after `uv run sloref fetch --volisca` + re-run of `../analysis-tool/run_forensics_slovenia.sh`
  and `scripts/build_site_figures.py`, so every number in the drafts is final.
  (The drafts below carry the snapshot numbers; they are unlikely to shift by more
  than tens of votes, but re-verify before sending.)

## Targets

### Slovenian media (email desks first, then social)

| Outlet | Why them | Channel |
|---|---|---|
| **RTV Slovenija / MMC** | The RTV-fee question is literally about them; strongest data desk | novicedesk / mmc@rtvslo.si (verify current address) |
| **STA** (press agency) | One wire piece propagates everywhere | urednistvo@sta.si |
| **Delo**, **Dnevnik**, **Večer** | Quality dailies, «pismo bralca» + op-ed culture | letters/op-ed desks |
| **24ur.com**, **Siol.net** | Biggest portals; love a flip-the-rule visualization | news desks |
| **Finance** | Work-requirement & quorum/economics angle | news desk |
| **Pod črto**, **Oštro**, **Necenzurirano** | Data/investigative outlets — best fit for methodology; likely to reproduce the analysis themselves | editorial emails |
| **Mladina**, **Reporter**, **Demokracija**, **Nova24TV** | Opinion magazines of both blocs; the clean-verdict finding serves everyone | editorial emails |

Caveat: Demokracija/Nova24TV may spin the territorial-flip card into «stolen vote» —
the clean verdict + explicit «Slovenia counts by national total» framing is the antidote;
send to them anyway (the message is inoculation, not partisanship).

### X/Twitter (handles from training data — **verify before posting**, many Slovenian
outlets are more active on Facebook/Instagram/Bluesky)

- Media: `@RTVSlo`, `@deloslovenija`, `@dnevnik`, `@24ur`, `@SiolNET`, `@STAagency`,
  `@Necenzurirano`, `@PodCrto`, `@OstroSlo`, `@Mladina`, `@vecer_com`
- Politics/institutions: `@jjansasds` (J. Janša, SDS), PM R. Golob (check current handle),
  `@vladaRS` (government), DVK (mostly web-only, email instead)
- Method authors / forensics community (EN thread): `@dimakobak` (Kobak — integer peaks),
  `@pklimek` (Klimek — fingerprints), `@RMichAlvarez` (Caltech, election forensics),
  `@berndbeber` (Beber — last digits); they often engage with applied studies
- Also: r/slovenia (one post, neutral title), Wikipedia article
  «2026 Slovenian referendum» (add analyses only via reputable citations, not self-PR)

### Institutions

- **DVK** (Državna volilna komisija, `dvk-rs.si`) — data-format feedback + the ask to
  publish early-voting points with precinct-level breakdown (they are aggregated in
  99 points, outside the precinct pipeline)
- **Mandatno-imunitetna komisija DZ** — the Art. 90 quorum registration-sensitivity is
  directly in their remit
- **OSCE/ODIHR** Elections Department (elections@odihr.pl) — reference material for
  referendum observation methodology; **Venice Commission** secretariat — the quorum /
  aggregation findings map onto their Code of Good Practice on Referendums (2007)

### Academia

- **FDV Ljubljana** (Centre for Political Science Research) — e.g. Alem Maksuti
  (has published on detecting electoral manipulation in Slovenia; verify affiliation),
  Simona Kustec (electoral studies; verify)
- **Univerza na Novi Gorici** (school of governance; T. Deželan — participation studies; verify)
- **Statistično društvo Slovenije** — newsletter/seminar offer
- International: Electoral Integrity Project; EPSA political methodology; ACE-ENN

### Politicians (who cares and why)

| Actor | Interest |
|---|---|
| RTV-fee abolition initiative + SDS/Nova24TV ecosystem | Lost by **546 votes**; the voting-channel decomposition (early/postal went NO on all four) and 547-votes-flip card are their material |
| Coalition (Svoboda/SD/Levica) around ZPPre-B | The law they passed was rejected; early+postal decided it; quorum arithmetic argues for a look at the rule itself |
| Levica | Local voting-rights question curtails third-country nationals' local vote — decomposition + territorial map show where |
| DVK + DZ Mandates Commission | Early-voting data granularity; quorum's dependence on the voter register size |
| RTV Slovenija management | Public, independent proof the fee-survival was not manipulated — counterweight to «abolish the fee» pressure |

## Files

- [`CONTACTS.md`](CONTACTS.md) — verified send-to list: emails of Slovenian media,
  institutions and academia, each with the source URL it was taken from.
- [`DRAFTS.md`](DRAFTS.md) — drafts in English: press pitch, letter to the editor,
  X thread (EN) + single posts (EN/SL), Reddit post (SL), DVK email, academia email,
  politician/institution letter — all letters in English.
- [`DRAFTS_sl.md`](DRAFTS_sl.md) — Slovenian originals of the same letters
  (for Slovenian media desks and official bodies a Slovenian letter lands better).
