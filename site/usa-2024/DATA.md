# United States congressional elections, 5 November 2024

**18 October expanded analysis:** [EXPANDED_REPORT.md](EXPANDED_REPORT.md) uses the newly downloaded structured sources and historical controls in a fresh, jointly adjusted diagnostic family. It supersedes the earlier 25,682-unit coverage headline; earlier reports remain dated snapshots. See the expanded report for reproducible commands, source exclusions and Monte Carlo refinement.

Scope: latest completed **nationwide general election** as of 17 October 2026,
not subsequent individual special elections or the 2026 primaries. The next
nationwide general election is 3 November 2026. Separate Senate special contests
held on 5 November 2024 are preserved in the data but excluded from regular-race
screens. D.C. and territorial delegates are not voting House seats.

## Download extraction and reconciliation, 18 October 2026

[RECONCILIATION.md](RECONCILIATION.md) inventories the local files, verifies
download hashes, exports the downloaded spreadsheet/archive tables, and records
structured-source and PDF reconciliation, unmatched units, suppression and
registration differences. These supplemental audits do not expand the published
forensic sample or regenerate site figures. Raw exports and cached PDF
transcriptions are in the Git-ignored `data/extracted/` directory.

## Precinct update, 17 October 2026

[PRECINCT_REPORT.md](PRECINCT_REPORT.md) is the current primary report:
25,682 distinct eligible 2024 precinct identities, 60 current contest samples,
nine Minnesota 2020 controls, 276 new digit tests and 207 integer screens.
It documents every attempted source join, exclusions, Luna 6 OCR checks,
the Minnesota physical hand-review anchor and exact reproduction commands.
[PARADOXES.md](PARADOXES.md) now uses the House Clerk's complete official-source
contest inventory and ten arithmetic bounds instead of the earlier seven.
The files below describe the preserved nationwide MEDSL/county baseline, unless
explicitly marked as the new precinct update. Their separate test families must
not be pooled without a fresh multiplicity correction.

## Baseline data and reproduction

- [MIT Election Data + Science Lab](https://github.com/MEDSL/2024-elections-official),
  pinned commit `df531089c78e6d0098db1a6bfb3849a066a06995`: 51 state/D.C.
  ZIP archives, standardized from state and local results. See the downloaded
  `data/raw/README.md` for individual official sources and state caveats and
  `data/raw/codebook.md` for fields. This is a research compilation, not a new
  certification of the returns.
- [EAC EAVS 2024, version 2](https://www.eac.gov/research-and-data/studies-and-reports),
  released February 2026: official jurisdiction-level registration (`A1a`, total
  active plus inactive registrants; `A1b`, active registrants retained for future
  sensitivity checks) and participation (`F1a`, total voters). Original ZIP and
  Excel codebook retained. Negative missing-value codes are excluded by the
  eligibility conditions, never converted to zero.
- `data/source_tree.json` and `data/download_urls.txt`: pinned file inventory
  and download URLs. `data/manifest.csv`: bytes and SHA-256 of each state archive.
- `data/congress_candidate_units.csv.gz`: candidate × reported unit × contest
  results after choosing voting modes and adding fusion ballot lines. Keeps
  special status, election date, district, and original reporting-unit names.

```sh
sh usa-2024/scripts/download.sh
cd analysis-tool && uv sync && cd ..
analysis-tool/.venv/bin/python usa-2024/scripts/analyze.py
analysis-tool/.venv/bin/python usa-2024/scripts/turnout.py
```

The scripts reuse `analysis-tool` directly and add no dependencies. The first
script runs assert-based checks of TOTAL-versus-subtotal handling and suppressed
counts. Every expected archive must have the exact pinned size before analysis.
Raw downloads and the compressed derived dataset are ignored by Git.

## Earlier baseline: what the files support

| Method in root documents | Implemented output | Interpretation / missing data |
|---|---|---|
| Second-digit Benford and last digits | `analysis/digit_tests.csv` | State × office × major party; at least 100 eligible counts, counts ≥10 or ≥100; theoretical and fitted-lognormal Monte Carlo nulls; BH adjustment across the full theoretical test family |
| Shpilkin / turnout distribution | `analysis/county_metrics.json` and turnout PNGs | Matched county-level sensitivity analysis; own-data 99.5th percentile tail, **not fraudulent votes**; no prior-election calibration |
| Klimek fingerprints | `analysis/county_metrics.json` | Two Gaussian clusters are descriptive geographic heterogeneity, not a fraud classification |
| Integer turnout / result peaks | `analysis/county_integer_peaks.csv` | Existing binomial Monte Carlo implementation, county level; party result denominator is all participants |
| Turnout–party correlations | `analysis/county_correlations.csv` | Within states; party votes divided by all participants, which includes contest nonvoting |
| Similar-unit comparisons | `analysis/county_within_state_outliers.csv` | State-median/MAD county outliers; **not geographic neighbors**, no boundary files or socioeconomic matching |
| ML anomalies | Same outlier file, isolation columns | Isolation Forest on turnout, leader share, log registration; 1% contamination is imposed, not an estimated fraud rate |
| Serial/batch forensics | Not identifiable | Need ballot batch/serial records and custody documentation |
| Turnout/counting dynamics | Not identifiable | Final totals have no time sequence; counting order is not voting order |
| Documentary anchors | Not collected | Need audits, recounts, ballot reconciliation, parallel counts or protocol copies |
| Nonmajority winners / potential spoilers | `analysis/race_screens.csv` | Arithmetic exposure only, based on reported totals; other-candidate votes exceeding top-two margin does **not** establish a spoiler |
| Condorcet, frustrated majority, center squeeze, cloning, best-is-worst | Not identifiable from these aggregate returns | Need within-contest preference rankings or a defensible preference survey; cross-office voting does not reveal them |
| Lesser-evil / strategic voting | Not identifiable | Need sincere-preference evidence, not just vote shares |
| No-show, monotonicity, later preferences | Rule properties / ranked ballots needed | Most races use plurality; Alaska/Maine ranked-choice races are excluded from plurality screens |
| Multiple-district / gerrymander counterfactual | Not tested | Need precinct geometry, population, district assignments, legally constrained alternative maps; seats-votes imbalance alone is insufficient |

## Coverage and exclusions

`analysis/coverage.csv` reports source rows, modes, suppressed/invalid values, and
candidate-unit coverage for **every state**, including states with no Senate race.
`analysis/office_inventory.csv` inventories all raw offices and modes; some states
also publish registration and ballot counts, available in the preserved archives
for a future state-specific precinct turnout join. Digit tests exclude Senate special
contests, so simultaneous regular/special ballots are not duplicated in that pool.

For each candidate ballot line, use `TOTAL` when present; otherwise sum the
reported modes. A suppressed, negative, or noninteger count invalidates that line.
Fusion lines for the same candidate are added. Unknown candidate totals stay
unknown. Unnamed candidate rows and noncandidate totals are excluded from race
screens; they cannot be assigned an assumed preference. Minor fusion lines are
assigned to their named major-party candidate for the diagnostic screens. State-specific overlapping categories or repeated aggregate rows can
still require additional reconciliation; these standardized screens are not
certified precinct audits.

Indiana (documented straight-ticket overcount), New Jersey (mixed municipality
and precinct totals), Louisiana (missing precinct early votes), Alaska and Maine
(ranked-choice / first-round complications), Oregon (unlabeled candidates and
ballot totals), and Rhode Island (House votes without district assignments) are excluded from diagnostic screening.
Their raw data and reported race summaries remain available. This exclusion is
conservative; it is not a claim that those states have election irregularities.

The county-turnout script uses a county-name/FIPS crosswalk from MEDSL's Senate
county table; consequently House turnout coverage is limited to states in that
crosswalk. It joins only ten-digit EAVS county jurisdiction codes ending `00000`.
Municipal jurisdictions, including Wisconsin's five-digit **municipality** codes,
are not silently relabeled as counties. Suppressed county results, missing or
nonpositive registration/participation, participation above registration, and
valid votes above participation are excluded and retained in the join audit.
State-office diagnostics require at least 20 matched counties. Small states and
states reporting EAVS at municipal level may therefore have no turnout output.
County aggregation loses precinct detail and cannot replace precinct tests.

Official [Alaska](https://www.elections.alaska.gov/election-results/e/?id=24genr)
and [Maine](https://www.maine.gov/sos/elections-voting/election-results-data/election-results-2024)
pages advertise 2024 congressional cast-vote records. Those pages could not be
retrieved through the download tools in this run; no ranked ballots were obtained
or pairwise conclusions invented. Ordinary plurality ballots cannot supply lower
preferences retrospectively.

Read `REPORT.md` and `PARADOXES.md` for the actual run results and limitations.


The website’s figure builder also runs two bounded supplemental checks: exact
county-vector repetition and a fixed-boundary Shpilkin response to synthetic
additive ballots in Pennsylvania Senate. See the supplement in `REPORT.md`;
these do not provide precinct-level or historical calibration.

## Precinct turnout source search

See [PRECINCT_DATA_SOURCES.md](PRECINCT_DATA_SOURCES.md) for the October 2026
search of official 2024 precinct registration/participation sources and Kaggle,
verified sample schemas, and outstanding joins. The validated subset now supplies the new precinct analysis in
[PRECINCT_REPORT.md](PRECINCT_REPORT.md); the county analysis is retained separately.

Additional official source downloads, checksums, coverage and failures are
recorded in [PRECINCT_DOWNLOADS.md](PRECINCT_DOWNLOADS.md).

## Turnout-source expansion, 18 October 2026

[TURNOUT_EXPANSION.md](TURNOUT_EXPANSION.md) documents newly downloaded current
and historical precinct inputs, checksums, Washington source-join checks and
remaining access/extraction gaps. These files have not yet been incorporated
into the primary statistical results or site figures.

The continued download pass added 162 data files (31.9 MB) across seven more
states: IA, WV, OH, VA, KY, SC and VT. See the provenance and coverage table in
[TURNOUT_EXPANSION.md](TURNOUT_EXPANSION.md); 159 files are pinned public-mirror
copies, three are direct official downloads. Nationwide precinct coverage remains
incomplete.
