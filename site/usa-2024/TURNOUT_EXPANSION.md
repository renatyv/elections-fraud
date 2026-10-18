# Additional precinct turnout sources — 18 October 2026

**Analysis follow-up, 18 October:** [EXPANDED_REPORT.md](EXPANDED_REPORT.md) now incorporates compatible structured sources and reports exclusions for the remaining downloads. Statements below that no pipeline was rerun describe the original collection pass, before this follow-up.

**Extraction follow-up:** [RECONCILIATION.md](RECONCILIATION.md) now records
spreadsheet exports, historical normalization, Washington county/candidate
reconciliation and PDF extraction. Remaining-work statements below describe
the original download pass; the primary forensic results remain unchanged.

Precinct turnout means ballots cast / registered voters on the **same reporting
geography**, with candidate votes on that geography. It is not votes for the
winning candidate / registration, or votes for all congressional candidates /
registration: voters can skip that contest. Registration timing, election-day
registration, inactive voters, central absentee pools and split precincts matter.

This collection expands the inputs available for Shpilkin-style comparisons.
It does not rerun the forensic pipeline or change published results. The earlier
25,682-unit headline still describes the earlier completed analysis.

Downloaded **7 data/supporting files (65.2 MB)**, plus source pages.

Raw files: `data/raw/precinct_sources/expansion_20261018/` (Git-ignored).
[Download manifest](data/source_search/turnout_expansion_20261018.json) records
URLs, resolved URLs, dates, byte counts, SHA-256 and failures.
[Schema/arithmetic checks](data/source_search/turnout_expansion_checks_20261018.json)
record the following results. ZIP/XLSX archive CRC checks passed on downloads.

| Source | Newly obtained data | Actual checks / remaining work |
|---|---|---|
| [Washington 2024](https://www.sos.wa.gov/vi/node/12933) | Statewide GIS-ready ZIP: precinct turnout plus federal, legislative and other results; reconciliation and district/precinct-association XLSX | 7,934 unique turnout keys, 8,136 unique federal-result keys. Same-key Senate join has 7,822 arithmetically eligible rows. These are not all new precincts: King County overlaps the existing sample. Association workbook is a many-to-many table, not 237,710 distinct precincts. |
| [Washington 2020](https://www.sos.wa.gov/elections/data-research/election-data-and-maps/election-results-and-voters-pamphlets/2020-general-election-data) | GIS-ready ZIP with results XLSX, turnout XLSX and publisher README PDF | Turnout: 7,351 unique keys, 4,892,871 registered, 4,116,894 ballots; six rows exceed registration. Result workbook not normalized. Source page labels the link XLSX but the downloaded file is a ZIP. |
| [California 2020](https://statewidedatabase.org/d10/g20.html) | Statewide SR-precinct Statement of Vote ZIP and publisher errata | 21,346 unique SRPREC_KEY rows; TOTREG, TOTVOTE and congressional candidate fields present. No U.S. Senate election in 2020. Publisher errata document consolidation and registration issues; exclusion policy and total reconciliation remain necessary. Research compilation, not a fresh state certification. |
| [Minnesota 2016](https://www.sos.mn.gov/elections-voting/election-results/2016/2016-general-election-results/2016-precinct-results-spreadsheet/) | Official precinct XLSX | 4,120 real VTDID rows, 3,623,913 registration including EDR, 2,968,281 ballots; six rows exceed registration. Worksheet is Results, not Precinct-Results as in the existing newer files. House/presidential counts available; no Senate race. |

## Continued downloads — seven additional states

A second download pass obtained **162 data files, 31,872,867 bytes (31.9 MB)**
from Iowa, West Virginia, Ohio, Virginia, Kentucky, South Carolina and Vermont.
These are source acquisitions, not additions to the validated forensic sample.
Raw files are under `data/raw/precinct_sources/continuation_20261018/`.

[County manifest](data/source_search/turnout_continuation_20261018.json),
[additional-state manifest](data/source_search/turnout_continuation_additional_20261018.json)
and [checks](data/source_search/turnout_continuation_checks_20261018.json)
preserve exact URLs, retrieval times, errors, byte counts and SHA-256 hashes.
All 162 recorded data-file hashes and sizes were rechecked. All 154 county ZIPs
and the Ohio XLSX passed archive CRC checks; county XML election dates are
November 5, 2024. The four Kentucky files have PDF signatures but were not
transcribed in this pass.

**Provenance:** Virginia, South Carolina and Vermont downloaded directly from
their official hosts. Official requests for Iowa, West Virginia, Ohio and
Kentucky failed; their 159 files were recovered from the public
[CivicResultMaps repository](https://github.com/Camreyn/civicresultmaps/tree/5195a57d913c839106ce1d2de32e3510d9ef3d3a/data),
pinned at commit `5195a57d913c839106ce1d2de32e3510d9ef3d3a`.
These are mirrored copies of publisher artifacts, not fresh official downloads;
the mirror's claimed official URLs are retained and have not been independently
hash-matched against accessible official copies. The county source-URL sidecars
were also preserved, separately from the 162-file count.

| State | Obtained and checked | Limits before analysis |
|---|---|---|
| Iowa | All 99 county detail XML ZIPs: 1,651 turnout rows, 1,672,068 ballots, 1,893,715 registered voters | Mirrored artifacts; candidate/turnout joins still required |
| West Virginia | All 55 county detail XML ZIPs: 1,649 turnout rows, 770,587 ballots, 1,187,991 registered voters | Mirrored artifacts; candidate/turnout joins still required |
| Ohio | Statewide official-canvass XLSX; presidential sheet has 8,878 distinct county/precinct-code keys; 5,851,387 ballots and 8,159,946 registered voters, matching its printed total | Mirrored artifact; precinct write-in counts unavailable according to workbook; House sheet not normalized |
| Virginia | Official turnout CSV: 2,669 distinct locality/precinct keys; nonblank totals are 4,537,976 ballots and 6,434,637 registered voters | 133 registration fields and 131 turnout fields are blank; row count is not usable-pair count; congressional result joins pending |
| Kentucky | State Board county/precinct turnout and county/precinct registration PDFs | Mirrored artifacts; publisher's unofficial turnout/roll-reopening caveat retained; extraction and reconciliation pending |
| South Carolina | Official Election History export: 2,446 precinct, 46 county and one state row; state total 2,566,404 ballots and 3,451,344 registered voters | Precinct reconciliation pending; totals differ from VREMS voter-history package; do not mix denominators |
| Vermont | Official turnout JSON: 247 town rows, 372,885 voters cast, 517,051 registered voters, with nested contest results | Town geography; denominator timing differs from canvass/EAC sources; nested contest rows not normalized |

Recheck local integrity and these structural counts from the repository root:

```sh
python3 usa-2024/scripts/check_turnout_continuation.py
```

This remains an incomplete nationwide precinct-turnout collection. None of the
new sources has been promoted into the forensic sample or site figures.

## Washington 2024 join audit

[Every federal-result/turnout key](analysis/wa2024_senate_source_join_audit.csv.gz)
is retained in an outer join. There are 202 federal-result keys without turnout;
none of the turnout keys lacks a federal result. Among matched keys, 111 have
zero registration or zero ballots, three report ballots above registration,
and none reports Senate candidate sums above ballots. Exclusion categories
can overlap. Arithmetic eligibility is not source certification.

Turnout ballots sum to **3,961,569**, matching the
[published statewide total](https://www.sos.wa.gov/elections/data-research/election-data-and-maps/reports-data-and-statistics/general-election-turnout).
Registration sums to **5,017,633**, versus **5,017,620** in that table: a difference
of 13 remains unresolved. Do not force these totals to match or silently discard
unmatched records. County reconciliation and the ZIP's other contest tables
still need review before adding this source to the primary statistical sample.

## Earlier download failures and remaining gaps

The entries below record the earlier pass. The continuation above recovered
mirrored Iowa, West Virginia, Ohio and Kentucky artifacts and an official
Virginia turnout CSV; those earlier failures no longer mean no local file exists.

- Ohio's official index and attempted statewide precinct workbook URL returned
  HTTP 403. The workbook filename remains an unverified direct-link lead.
- New Mexico's official 2024 precinct-turnout page returned HTTP 403.
- Virginia's previously advertised direct turnout CSV returned HTTP 404.
  The current report page downloaded as an application shell; no replacement
  turnout file was obtained.
- Iowa's official election-results host and the Clarity report frontend returned
  HTTP 403. West Virginia's official page points to its Clarity frontend, which
  also returned HTTP 403. No new state datasets are claimed from those requests.
- A separate King County 2020 final CSV download timed out at 100 seconds; the
  partial file was removed. The downloaded statewide Washington 2020 archive
  remains the broader historical source.
- Idaho's 2020 page is available but the inspected links did not yield a comparable
  precinct turnout workbook in this pass.
- The already downloaded Mississippi/Utah/Wyoming and other PDFs remain an
  extraction/reconciliation backlog. This is a separate gap from downloading.

Historical samples do not automatically provide a clean baseline. Precinct
boundaries, congressional districts, registration definitions and turnout
conditions changed. The new files enable additional within-state sensitivity
comparisons; they do not establish a nationwide matched precinct panel.

No Shpilkin excess-vote model was fitted and no site figures were regenerated.
