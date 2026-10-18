# Download extraction and reconciliation — 18 October 2026

**Analysis follow-up, 18 October:** [EXPANDED_REPORT.md](EXPANDED_REPORT.md) now runs forensic diagnostics on compatible normalized sources. This extraction audit remains a separate record; statements below about unchanged published coverage refer to the earlier extraction pass.

**Later download continuation:** [TURNOUT_EXPANSION.md](TURNOUT_EXPANSION.md)
adds 162 data files across seven states. They have a separate integrity check and
are outside the extraction inventory and reconciliation counts below.

This audit covers the files already downloaded in `usa-2024/`. Raw files are
preserved. Extraction outputs and source-join audits are separate from the
published 25,682-unit forensic sample: arithmetic agreement alone does not
establish compatible precinct boundaries, registration definitions, or final
certification.

## Download integrity and extraction

- **278 local raw files, 614,158,531 bytes** inventoried, including existing
  derived CSVs beside the downloads. [Inventory](analysis/download_inventory.csv).
- **271 manifest records** checked against the actual files: every recorded
  SHA-256 and available byte count agrees. Two older EAC manifest records have
  hashes but no recorded byte count. [Integrity audit](analysis/download_integrity.csv).
- **71 ZIP/XLSX CRC checks** passed and are recorded in
  [archive checks](analysis/download_archive_checks.csv).
- **103 tables, 1,808,708 exported rows**, including headers, blank rows and
  printed totals. These are not counts of distinct precincts.
  [Source/member/worksheet/output index](analysis/extracted_tables.json).
- Every downloaded precinct-source ZIP has been unpacked; every downloaded
  XLSX, including the Wyoming ZIP's workbooks and both Washington 2020 result
  representations, has a CSV export. Supporting codebooks, errata and notes
  are retained. Exported workbook values use the publisher's cached formula
  values; original workbooks remain available for formula inspection.

Exports are in `data/extracted/` (Git-ignored). Spreadsheet CSVs retain source row
order, original headings, blank rows and aggregate rows. Extraction does not
silently equate those rows with usable precincts. No new datasets were downloaded.

## Structured-source reconciliation

[All total comparisons](analysis/download_reconciliation.csv),
[supplemental coverage](analysis/supplemental_precinct_coverage.csv), and
[every supplemental join/exclusion](analysis/supplemental_precinct_join_audit.csv.gz)
are retained, including unmatched and arithmetically invalid rows.

| Source | Extracted and reconciled | Remaining limitation |
|---|---|---|
| Washington 2024 | 8,136 federal-result keys; 7,934 turnout keys; all **33 congressional candidate columns match the House Clerk individually**. House candidate votes 3,768,180; Senate 3,812,391. All 39 counties' ballot counts match the reconciliation workbook, statewide 3,961,569. | 202 result keys lack turnout; 7,822 keys pass basic arithmetic. Registration totals differ among source publications. |
| Wyoming 2024 | **432 precinct keys**, all matched to printed ballots. Every Senate and House candidate sum plus under/overvotes equals ballots. Statewide ballots 271,123; Senate candidate votes 264,162 and House 261,548 match the Clerk. | No precinct registration denominator was obtained. Excel converted some precinct codes into 2022 dates; their month/day codes were recovered, originals retained, and all joins and ballot identities checked. |
| North Dakota 2024 | **385 precincts**, ballots sum exactly to the HTML's statewide **371,975**. Both congressional result joins and Clerk comparisons are retained. | Census eligible population is not voter registration and is not assigned to precincts. |
| Maryland official 2024 | Both direct official result tables extracted and joined to registration/participation: House **2,935,328**, Senate **3,021,378** candidate votes, exactly matching the Clerk. | Administrative participation contains rejected ballots and registry changes; all rows retain a source-comparability exclusion. It is not a certified accepted-ballot denominator. |
| Minnesota official 2024 (existing extraction) | House **3,146,762**, Senate **3,189,323**, exactly matching the Clerk. | Existing source and precinct exclusions remain in the primary audit. |
| Idaho official 2024 (existing extraction) | House **873,704**, exactly matching the Clerk. | Exact statewide agreement does not resolve every unmatched registration row. |
| Delaware 2024 CSV | House **497,436**, Senate **500,606**, both match the Clerk; voting-mode sums match printed totals. | This CSV is a statewide/district summary, not precinct candidate results. The separate participation PDF is audited below. |
| Pennsylvania 2024 | Precinct congressional returns and registration joined, retaining missing keys. Precinct registration **9,175,133** versus county workbook **9,175,132**. | Returns are **2,185 House votes** and **2,362 Senate votes** below the Clerk. County code 56 / precinct 135 has results but no registration. The zero-registration `0\|99999` record is retained separately. No precinct ballot counts were downloaded. Headerless field positions are inferred and explicitly documented, not a verified publisher layout. |
| North Carolina 2024 | Aggregate demographic registration file reduced to **2,703 county/precinct keys**, 100 counties, **7,854,464** registrations. | Registration snapshot only; no matched precinct ballot-count source. No inference that registration counts are ballots. |
| California 2024 | SR and SV registration totals **22,580,761** and ballot totals **16,140,918** agree exactly after removing aggregate rows from SV. | Candidate cells contain `***`: 1,974 suppressed SR rows and 4,748 suppressed SV rows for regular Senate candidates. Observed numeric sums are incomplete, not contradictory certified totals. |
| California 2020 | **21,346 SR precinct keys** with House/presidential candidate counts, registration and ballots; 17,241 pass basic arithmetic per office. | 357 rows exceed registration; zero-denominator rows and publisher errata remain. No U.S. Senate contest. Historical boundaries are not matched to 2024. |
| Minnesota 2016 | **4,120 precinct keys**, registration including election-day registrations **3,623,913**, ballots **2,968,281**; 4,083 pass basic arithmetic per office. | Six rows exceed registration; zero-denominator rows remain. No U.S. Senate contest and no boundary-matched panel. |
| Washington 2020 | **7,436 result keys**, 7,351 with turnout; turnout ballots **4,116,894** equal the result workbook's ballots. Presidential candidate counts normalized; all House columns and the candidate codebook exported. | Turnout registration exceeds the result workbook's matched registration by 5,290. Six turnout rows exceed registration; one presidential total exceeds ballots. House party classification has not been inferred from candidate ordering. |

Washington detail: [candidate comparisons](analysis/wa2024_candidate_reconciliation.csv)
and [county comparisons](analysis/wa2024_county_reconciliation.csv). The GIS-ready
registration total is **5,017,633**, versus **5,013,112** active voters in the
county reconciliation workbook and **5,017,620** in the previously recorded
published turnout table. King County alone differs by **5,108** registrations
from the earlier final King file, while its ballots and all Senate candidate
totals agree exactly. King is an overlapping source, never an additional sample.
The publisher's `G24C08GOWI` column is mapped to Schrier with its anomalous name
retained and its full candidate total checked; party labels come from the Clerk,
including the Republican-versus-Republican WA-4 race.

California detail: [SR/SV county comparisons](analysis/ca2024_sr_sv_reconciliation.csv),
[retained SV aggregate rows](analysis/ca2024_sv_aggregate_rows.csv.gz),
[registration joins](analysis/ca2024_registration_join_audit.csv.gz), and
[voter-history joins](analysis/ca2024_voters_join_audit.csv.gz). The auxiliary
registration and voters files each match **20,060** SR keys and leave **5,185**
SOV-only keys. Their values are not interchangeable with SOV registration or
accepted ballots. Masked cells are never filled with zero in normalized rows.

## PDF extraction

**117 source PDFs; 4,907 selected pages; 10,766 provisional transcribed rows**
(8,131 coalesced contest/unit/mode rows). All final effective batches completed
without API/schema failures; 69 county documents received contextual retries.
**119 of 229 source/office comparisons agree exactly** with their recorded
reference scope. 65 have nonzero numeric differences;
44 lack a comparable complete total, and
1 have a zero observed difference but incomplete or conflicting readings.
These categories describe reconciliation, not a fraud test.

There are **28 unlocated rows** and **1,117 arithmetic-eligible congressional
contest/unit rows**, which remain provisional and outside the primary sample.
Counts include multiple offices per precinct and must not be presented as
additional distinct physical precincts.

A completed batch means a response passed schema validation, not that every
printed cell was recovered. Some scanned tables still have missing contests,
partial columns or ambiguous units, explicitly listed in the source audit.
The upright-image calibration recovered all 19 Adams House precinct columns;
this check does not validate the remaining county cells.

- [Final summary](analysis/pdf_extraction_summary.json)
- [Page selection](analysis/pdf_selected_pages.csv), [original batch status](analysis/pdf_extraction_status.json), [county retry status](analysis/pdf_repair_status.json)
- [Raw transcribed rows](analysis/pdf_extracted_rows.csv.gz)
- [Every coalesced row and exclusion](analysis/pdf_precinct_join_audit.csv.gz), [coverage](analysis/pdf_extraction_coverage.csv)
- [Source/office totals, candidate components and reference scopes](analysis/pdf_source_reconciliation.csv)


Model transcriptions retain file SHA-256, PDF page, printed unit, reporting level,
contest, voting mode, numeric fields and uncertainty notes. The requested
OpenRouter model is `~openai/gpt-luna-latest`, low reasoning; the returned model is
recorded in each cache. Readable pages use their text layer; scanned pages are
rendered for vision. County-document retries address missing continuation
headers and mismatched major-candidate totals; candidate identity references
contain names and party labels, not expected vote counts.

The scope is registration/participation and regular federal congressional
contests. Relevant text pages, pages containing federal candidate names, and all
scanned pages are selected. Text pages containing only unrelated local/state
contests are excluded. Wyoming's 46 precinct PDFs use their equivalent Excel
source; original Coahoma/Pike are superseded by corrected PDFs, and the second
Union copy is byte-identical and is not added twice. Existing Clerk and Minnesota
hand-review extractions remain available in their earlier audited outputs.

Equal repeated readings coalesce; conflicting values remain flagged. Only exact
printed unit strings are joined. Printed county/state totals are not added to
precincts. Separate voting modes are retained rather than assumed disjoint.
Missing fields stay unknown. An `eligible_arithmetic_only` flag is a diagnostic
of the transcribed numbers; it does not certify OCR, source finality, physical
precinct geography or suitability for the primary sample. Source sums and
major-party component sums are compared with the preserved MEDSL county totals.
Hawaii uses the Clerk's statewide totals; small New Hampshire sources use a
printed source total where one unambiguous total is available, which is only an
internal arithmetic check. Each comparison records its reference scope and
whether the observation is a precinct/pool sum or only a printed aggregate;
unresolved mismatches and missing contests are explicit rows in the audit.
Rows without a printed precinct name retain their values under synthetic
unlocated identifiers and are excluded from precinct eligibility; they are not
joined to another anonymous row.

Not every reference difference is an OCR error. Union's separately verified
official precinct extraction contains **84 Senate write-ins and 21 House
write-ins**. Those explain its PDF-versus-MEDSL total differences, while the two
major candidates agree exactly. Missing write-in coverage must not be fixed by
deleting real source votes. Other remaining differences include incomplete
transcriptions, ambiguous reporting levels, conflicting readings and source
coverage/finality differences; they remain explicit rather than forced to match.

## Reproduction

Use the bundled Python runtime with `openpyxl`, `pandas` and `numpy`, plus Poppler
(`pdftotext`, `pdftoppm`):

```sh
python usa-2024/scripts/extract_downloads.py
python usa-2024/scripts/reconcile_downloads.py
python usa-2024/scripts/extract_precinct_pdfs.py
python usa-2024/scripts/reconcile_pdf_extractions.py
# Retry incomplete Mississippi tables with county-wide continuation context:
python usa-2024/scripts/extract_precinct_pdfs.py --repair-incomplete
python usa-2024/scripts/reconcile_pdf_extractions.py
```

The PDF script loads `OPENROUTER_KEY` inside the process from the environment or
repository `.env`; it never prints the key. Successful responses are cached.
API failures and schema violations remain explicit and can be retried by rerun.
A spending-limit rejection stops additional queued API calls. The temporary cap
exhaustion during this run was resumed after the user raised the limit.

Validation includes source hashes/CRCs, every worksheet's export, unique join
keys, 33 individual Washington candidate checks, Wyoming's 432 precinct ballot
identities, North Dakota's statewide ballot sum, unknown/invalid-value
self-checks, and PDF duplicate/conflict checks. No forensic tests or website
figures were regenerated; the published primary sample was not expanded.
