# Data card — Uttar Pradesh polling-station results, Lok Sabha 2024 (Form 20 recovery)

- **Dataset**: per-polling-station candidate votes for the 2024 Indian general
  election (Lok Sabha) in Uttar Pradesh, recovered from the official Form 20
  "Final Result Sheet" documents.
- **Version / date**: 1.0, 15 October 2026.
- **Compiler**: independent researcher (renatyv.org); recovery, OCR and parsing
  pipelines are open source in this repository (`india-2024/scripts/`).

## Files

| file | rows | description |
|---|---|---|
| `up_booths_2024.csv.gz` | 1,161,433 | long table: one row per (assembly segment × polling station × candidate) — `district, pc_name, ac_no, ac_name, ps_serial, ps_no, candidate, votes, valid, rejected, nota, total, tendered, pdf`. Candidate numbers index the PC's ballot order (see "Party labels"). |
| `up_assembly_segments_2024.csv` | 297 | assembly-segment aggregates with party columns (`votes:BJP/SP/INC/BSP/RLD/…`, `registered_voters` where the form header carried it, `voted`, `nota`, others) — analysis-tool ready. |
| `pc_results_2024.csv` | 542 | national constituency-level MAI-format table built from the official ECI in-rolls export (context / cross-check file). |
| `up_form20_manifest.csv` | 315 | source PDFs: district, label, URL, destination file. |

## Provenance

1. **Sources.** Form 20 for each assembly segment is published by the district
   administration (district `*.nic.in` sites) — 315 PDFs, ~813 MB, a mix of
   Encore-generated digital forms and scans. Live sites are unreachable from
   most networks; everything was recovered from the Wayback Machine pages and
   `cdn.s3waas.gov.in` (the government CDN that still serves the files).
   Collection scripts: `download_up_form20*.py`, idempotent; the manifest
   lists every kept file and its URL.
2. **Transcription.** Digital PDFs: `pdftotext -layout`. Scans: pages
   rendered at 200 DPI and transcribed by an LLM OCR pass
   (`form20_extract_text.py`, `form20_ocr_rows.py`); degraded Farrukhabad
   scans re-read as numbers-only rows.
3. **Parsing.** `form20_parse_text.py`: every row must satisfy
   `sum(candidate votes) == valid` and `valid + NOTA + rejected == total`
   under exactly one reading of the column layout; rows that fail any single
   reading are dropped and counted, never guessed. `form20_clean.py`:
   AC identity resolution, multi-AC file splitting, duplicate-copy merging,
   Hindi-layout NOTA repair.
4. **Validation** (`form20_validate.py` → `parsed/validation_form20.txt`):
   aggregation vs the official ECI constituency results: 297 of 403 ACs,
   109,952 stations; every delta ≤ 0 (the recovery never exceeds the official
   count); 11 fully-covered constituencies match within ±0.5%; larger
   shortfalls are partial source files (fewer stations than the AC has).

## Coverage and known limitations

- 297 of 403 ACs; 68 of 80 PCs touched, 50 complete. Missing districts are
  listed in `data/form20/README.md`.
- **No per-station electors**: Form 20 carries electors only in the AC header
  (and only for 81 of 297 recovered ACs — mostly non-Encore forms). Booth-level
  *turnout* is therefore not computable from this dataset; pair it with
  Form 17C / per-station electorate data to unlock turnout methods.
- **Party labels** are not in Form 20. They were assigned by rank-matching
  each constituency's Form-20 candidate-column sums to the official ECI
  candidate totals (same ballot order in all stations of a constituency).
  Validated <5% deviation for parties ≥1 lakh votes wherever station coverage
  ≥90%; approximate in four low-coverage constituencies (Amroha, Farrukhabad,
  Kannauj, Mainpuri) — see `data/mai_up_ac_2024/party_matching_diagnostics.csv`.
  `candidate` in the long table is the *unlabeled* column index; apply the
  map in `data/mai_up_ac_2024/pc_candidate_party_map.csv` to label it.
- 7 guard-flagged Farrukhabad files (degraded scans) contributed no rows;
  5 Firozabad files could not be identified.

## Uniqueness — has this been published before? (checked 15.10.2026)

**No. To the best available evidence this is the first public,
machine-readable polling-station-level dataset of candidate votes for the
Indian 2024 Lok Sabha in any state, and specifically for Uttar Pradesh.**

- The ECI's central publications for GE-2024 (results portal, statistical
  reports) stop at candidate-per-constituency; the portal itself stated that
  "the final data for each AC/PC will be shared in Form-20" — i.e. the ECI
  defers to exactly the district-level documents this dataset is built from.
  The ECI moreover resisted court-supervised publication of booth-level
  Form 17C data through 2024–2026 (ADR v. ECI, Supreme Court).
- The only prior polling-station dataset of this kind — Jensenius, Chhibber,
  Alam, Gupta, Somanathan, "Indian election data for polling stations and
  villages", *Scientific Data* 2025 (Harvard Dataverse,
  [doi:10.7910/DVN/KKOWNJ](https://doi.org/10.7910/DVN/KKOWNJ)) — covers
  2009 and 2014 (11 states, incl. UP) and 2019 (UP only). It contains **no
  2024 data**; this dataset is the 2024-UP continuation of that series.
- No booth-level 2024 dataset exists on Kaggle, GitHub, Hugging Face, Zenodo
  or Dataverse; the finest open 2024 granularity found elsewhere is the
  assembly-segment level (OpenCity). No booth-level academic or journalistic
  analysis of UP-2024 has been published.
- The underlying records are public documents (Form 20 is a public electoral
  record); the novelty is the recovery, transcription, checksum validation
  and consolidation — not access to restricted information.

## License and attribution

Underlying data: public electoral records of India (district administrations /
ECI), collected from public archives (Wayback Machine, s3waas CDN). The
compilation, cleaning code and this card are released with this repository —
cite as: *Uttar Pradesh polling-station results GE-2024 (Form 20 recovery),
v1.0, 2026, renatyv.org*, and link the repository. If you use the 2014/2019
booth data as controls, cite Jensenius et al. 2025 (DVN/KKOWNJ) as well.
