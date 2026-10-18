# U.S. congressional 2024 precinct analysis update

17 October 2026. **No fraud conclusion follows from these screens.** This update
supersedes the earlier county-only coverage and seven-race bound. The older
county and nationwide digit outputs remain a separate exploratory baseline.

## What is now checked

**25,682 distinct eligible 2024 reporting precincts** across Minnesota,
California, Idaho, King County (Washington) and Union County (Mississippi).
Units retain each source's geography: CA uses SR precincts, not physical polling
places. This is partial coverage, not a nationwide precinct audit. Each unit is
counted once in this headline even when both congressional offices are examined.
The 20 Union precincts are an extraction/reconciliation case; they do not meet
the 100-unit minimum for the new statistical screens.

**60 2024 contest samples, 46,328 unit–contest
observations**, plus nine Minnesota 2020 control samples. House tests are split
by congressional district. Samples need at least 100 eligible units and nonzero
Democratic and Republican totals. California same-party contests do not support
this two-party diagnostic and are omitted. The historical districts are not
matched through redistricting; these are within-state historical comparisons,
not a same-precinct panel or an independently certified clean null.

### Input audit

| sample | rows | eligible | unknown | zero_denominator | over_registration | contest_over_ballots | source_exclusion |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CA2024 HOUSE | 25245 | 17870 | 1974 | 5431 | 409 | 0 | 78 |
| CA2024 SENATE | 25245 | 17867 | 1974 | 5431 | 409 | 3 | 78 |
| ID2024 HOUSE | 986 | 974 | 1 | 11 | 10 | 1 | 0 |
| MD2024 SENATE | 2227 | 0 | 514 | 4 | 16 | 335 | 2227 |
| MN2020 HOUSE | 4110 | 4075 | 0 | 33 | 2 | 0 | 0 |
| MN2020 SENATE | 4110 | 4075 | 0 | 33 | 2 | 0 | 0 |
| MN2024 HOUSE | 4103 | 4075 | 0 | 28 | 0 | 0 | 0 |
| MN2024 SENATE | 4103 | 4075 | 0 | 28 | 0 | 0 | 0 |
| MS-Union2024 HOUSE | 20 | 20 | 0 | 0 | 0 | 0 | 0 |
| MS-Union2024 SENATE | 20 | 20 | 0 | 0 | 0 | 0 | 0 |
| WA-King2024 SENATE | 2756 | 2743 | 0 | 13 | 0 | 0 | 0 |

Exclusion columns overlap. `eligible` requires known nonnegative integer counts,
positive registration and ballots, ballots no greater than registration, and
included congressional votes no greater than ballots. A failed check is a
source/join review issue, not evidence of illegal ballots. All rejected rows
are preserved in [the join audit](analysis/precinct_join_audit.csv.gz).

- **Minnesota:** 4,103 real 2024 precinct rows (the spreadsheet's final worksheet
  marker is not a precinct). Registration = `REG7AM + EDR`; `EDR` includes
  registrations when voting, including absentee. Dividing by `REG7AM` alone
  falsely puts **80 rows above 100% turnout**. With the combined denominator,
  none do; 28 zero-ballot/zero-registration units are excluded. House columns
  cover major parties and write-ins, not every possible minor candidate; the
  residual to ballots is contest nonvoting **plus any unlisted votes**, not a
  measured invalid-ballot count. The 2020 file has two over-registration rows,
  retained as exclusions; changed boundaries prevent a precinct panel.
- **Idaho:** drop the 44 county `Total` rows, outer-join exact County/Precinct
  keys and verify cutoff registrations + election-day registrations = total.
  The extra zero row `Bingham County / BONNEVILLE 27` has no race counterpart.
  **Overvotes/undervotes are ballot categories, not OTHER candidate votes.**
  Central absentee pools can have no registration denominator and remain
  excluded; no redistribution to residential precincts is invented.
- **California:** use only the single SR SOV file, whose registration, ballots
  and votes share the same key. Never add SV and SR tables or join registration
  files by similar names. Masked `*` cells remain unknown. Exclude all Madera
  rows because the publisher says its data do not match certified totals.
  The publisher also warns of processing artifacts; arithmetic eligibility is
  not a statewide certification, and excluded/zero units make totals partial.
- **King County:** use the official final Senate `Total` rows once. All 2,756
  rows satisfy votes + under-votes + over-votes = Times Counted; 13 empty units
  do not enter diagnostics. This is one county, not all Washington.
- **Maryland:** reject the **entire turnout join** from primary tests, rather
  than retaining only the superficially plausible subset. The official guide
  describes voter-history participation including rejected ballots and changed
  registrations, not accepted contest ballots. The attempted 2,227-key outer
  join has 514 unknown records and 335 candidate-sum-over-participation records.
  These counts overlap. Direct official candidate CSV was also obtained;
  its 117,875 records are not a replacement for a compatible ballot denominator.
- **Union County:** Luna 6 extracted all 20 precinct report pages from the
  55-page scanned recapitulation. Each extracted number was cross-checked
  against the PDF's separate OCR text layer, allowing only explicit name/case
  and thousands-separator OCR variants. Registration sums to **17,084**, ballots
  to **12,533**, exactly matching the printed county totals. Senate counts:
  Pinkins 1,779; Wicker 10,484; write-ins 84. House: Black 1,714; Kelly 10,646;
  write-ins 21. The residual to ballots is not assigned an invented cause.

### Statistical results

- **Digits:** 276 tests across these 69 samples (including controls),
  two parties and two tests. Last digits use counts ≥100; second digits ≥10;
  each pool needs at least 100 numbers. BH correction covers all 276 theoretical
  tests; a second BH family covers the 276 lognormal Monte Carlo p-values.
  **Zero last-digit flags; one second-digit flag**: King County Senate Democrats,
  theoretical q ≈ 0.000366, but lognormal-null p ≈
  0.264, adjusted q ≈ 0.834.
  No test flags under the adjusted lognormal family. The theoretical flag is
  not robust to the null model. Monte Carlo uses 400 simulations (resolution
  1/401). This family is separate from the earlier 284 nationwide MEDSL tests;
  no joint 560-test error-rate guarantee is claimed.
- **Integer peaks:** 207 turnout/Democratic-share/Republican-share
  screens, 1,000 binomial simulations each. Largest unadjusted integer z ≈
  2.70, CA House 29 Republican share (6
  observations among 135 units). These are descriptive z
  rankings, not family-adjusted p-values. No manipulation conclusion follows
  from selecting the maximum of 207 screens.
- **Turnout correlations:** both ordinary geographical effects and historical
  controls matter. Party support uses votes / all ballots, not valid votes.
  County-demeaned values use unweighted Pearson on residuals after county means;
  they are not comparable estimands to the registration/ballot weighted values
  and do not control for demographics or local spatial adjacency.

| Sample | Units | Weighted r (R) | County-demeaned r (R) |
| --- | --- | --- | --- |
| CA2024 SENATE | 17867 | 0.118 | 0.303 |
| MN2020 SENATE | 4075 | 0.381 | 0.485 |
| MN2024 SENATE | 4075 | 0.315 | 0.401 |
| WA-King2024 SENATE | 2743 | -0.285 | -0.289 |

- **Shpilkin:** the same-source registration-weighted 99.5th percentile is a
  descriptive boundary; 2024 leading-party tail shares range from
  0.000% to 1.376%. Neither fitting a mixture nor obtaining a
  historical file turns this boundary into a calibrated count of fraudulent
  votes. No election result is recomputed after deleting these observations.
- **Klimek-style fingerprints:** the toolkit fits two resampled Gaussian
  clusters; this is a descriptive surrogate, not a fitted mechanistic
  ballot-stuffing model. Geographic clusters are not fraudulent components.
- **Similar-unit / ML:** county-median/MAD flags 748
  unit–contest observations across current/control samples. Isolation Forest
  flags 577; its 1% contamination is imposed
  per sample. Scores are review leads, not probabilities or a fraud-rate estimate.
  These are county peers, not nearest geographic or socioeconomic neighbors.
- **Exact vectors:** 171 unit–contest rows belong to repeated
  registration/ballots/Dem/Rep/other vectors within a contest. They are not
  171 repeated ballots. All repeated vectors have ≤121
  ballots, and very small units naturally repeat. No chance-match model was
  fitted and no copied-protocol allegation is made.

## Documentary anchor: Minnesota hand review

Downloaded the official **438-page** post-election review. All **657
precinct–contest tables** across **219 county/precinct identities** carry
**ACCEPTABLE** status. There are **115** tables with a nonzero raw total
candidate/category difference and **24** with a nonzero adjusted difference.
The report's summed difference totals are **365 raw / 28 adjusted**; they are
not counts of unique disputed voters or ballots. One ballot can affect more
than one candidate/category and more than one office. ACCEPTABLE does not mean
exact equality: official thresholds allow small differences.

Every table's status and totals were parsed, with arithmetic assertions. Luna 6
(`openai/gpt-6-luna`, reasoning `low`) separately transcribed images of pages
1, 4 and 5, confirming four tables including discrepancies. This checks selected
page transcription, **not all 438 pages by visual OCR**. This official physical
check is stronger evidence about the reviewed sample than a digit model, but
cannot certify all Minnesota precincts or other states. See
[all review tables](analysis/mn_hand_review.csv) and
[summary](analysis/mn_hand_review_summary.json).

## All root fraud-method families: applicability

| Method | Actual extent / missing evidence |
|---|---|
| Shpilkin, turnout histogram and 2D correlation | Computed on precincts and retained county baseline; no calibrated fraudulent-vote estimate |
| Klimek fingerprints / mixture | Two-cluster descriptive surrogate on each eligible contest, not a validated fraud model |
| Integer peaks | 207 screens, 1,000 simulations; unadjusted z, no familywise significance claim |
| Benford / last digits | 276 new tests with theoretical and lognormal BH families; matched-state 2020 context |
| ML | Unsupervised Isolation Forest; not a supervised synthetic/honest classifier with measured accuracy |
| Similar precincts | County peers and county-demeaned correlation; no spatial adjacency/demographic matching |
| Serial numbers / ballot batches | No serials, custody logs or batch physical records; exact aggregate vectors do not substitute |
| Within-day voting dynamics | Final returns and mode categories cannot recover the order ballots were cast; no time-series claim |
| Independent documentary checks | Minnesota hand-review tables; Union scanned official totals; Clerk national compiled official results |
| Exit polls / parallel protocol counts / webcams | No comparable independent sample acquired; cannot infer absence of fraud |

## National outcome correction and voting paradoxes

The Clerk PDF inventories **435 House + 33 regular Senate contests**. Its
candidate totals combine fusion lines and exclude blank/void/over/under ballots
and Nevada's noncandidate “None of These Candidates” from candidate sums.
The two unopposed contests with no vote count printed retain unknown votes;
no zero is invented. Alaska/Maine ranked rules and Louisiana majority elections
are excluded from plurality bounds. **448** plurality contests with at least two
reported records can be screened; pooled write-ins are not treated as a single
person or as observed lower preferences.

**Ten races meet the arithmetic bound**, replacing the earlier seven.
Arizona Senate no longer qualifies: the official margin is 80,574 versus 76,818
other candidate votes. Iowa House 1, Michigan Senate, Nevada Senate and Oregon
House 5 are added. Pennsylvania's Clerk margin is 15,115, not the old MEDSL
16,910. Some Clerk figures can differ from later source revisions; source pages
and the snapshot checksum are retained. This is an official-source compilation,
not an independent ballot recount of every race.

After conservative key normalization, **387** previously prepared
race records match a Clerk race; **101** have different top-two margins.
Names are not fuzzy-matched and unmapped district codes remain unmatched in the
[reconciliation](analysis/clerk_medsl_race_reconciliation.csv). This is a
race-total comparison, not a candidate-level certification of every MEDSL unit.
All ten bounds plus the rejected Arizona Senate case were independently checked
by Luna 6 against **11 rendered Clerk pages**; all four numerical fields match.
See [PARADOXES.md](PARADOXES.md) for thresholds and every preference limitation.

## What remains outside the analysis

An inventory covers **166 downloaded precinct PDFs / 9,990
pages**. Only 29
files have both registration and ballot text mentions; text availability does
not establish schema correctness. All files retain hashes and page counts in
[the PDF inventory](analysis/precinct_pdf_inventory.csv). Other Mississippi,
Utah, Wyoming, Hawaii, Delaware and local PDFs have **not** been converted into
validated comparable precinct datasets. Corrected reports must supersede their
originals, and absent text mentions can be an OCR failure, not absent fields.
This is not a claim of maximum possible nationwide coverage.

Alaska's election page returned a human-verification screen and Maine's page
returned an access-denied response in the renewed download attempt. No CVR
ballots were obtained. No preference rankings, serial records, geographically
matched historical panel, census covariates or legal alternative district maps
were fabricated. Official-source links and the raw failures in the older
source-search logs remain available. Further expansion requires state-specific
extraction and reconciliation, particularly for centralized absentee pools.

## Reproduction and new downloads

Run the workbook exporter with the bundled Python containing openpyxl; all
analysis uses the existing analysis-tool environment:

```sh
# Replace bundled-python with the runtime path returned by load_workspace_dependencies.
bundled-python usa-2024/scripts/prepare_precinct_tables.py
analysis-tool/.venv/bin/python usa-2024/scripts/review_audit.py
analysis-tool/.venv/bin/python usa-2024/scripts/scan_union.py
analysis-tool/.venv/bin/python usa-2024/scripts/clerk_results.py
analysis-tool/.venv/bin/python usa-2024/scripts/verify_clerk.py
analysis-tool/.venv/bin/python usa-2024/scripts/inventory_precinct_pdfs.py
MPLCONFIGDIR=/tmp/usa-mpl analysis-tool/.venv/bin/python usa-2024/scripts/precincts.py
MPLCONFIGDIR=/tmp/usa-mpl analysis-tool/.venv/bin/python usa-2024/scripts/build_precinct_report.py
MPLCONFIGDIR=/tmp/usa-mpl analysis-tool/.venv/bin/python usa-2024/scripts/build_site_figures.py
```

OpenRouter scripts use cached outputs after the first successful extraction.
They load `OPENROUTER_KEY` programmatically from the root `.env` without printing
it. Inputs are public election pages. Request/returned model IDs, low reasoning,
page lists, source hashes and usage are retained in `data/source_search/luna_*.json`.
OCR numbers pass arithmetic and second-path text checks before use; selected
Clerk races also pass an independent model/image calculation. These checks do
not make model output infallible. Raw files are ignored by Git: restore them
from the URL/hash manifests, not from an expectation that `git clone` includes them.

- [mn2020_official_precinct.xlsx](https://www.sos.mn.gov/media/4373/2020-general-federal-state-results-by-precinct-official.xlsx), 1,396,119 bytes; SHA-256 `ea2b7a7c9c8203f56f44d94dede6b2df398eb1f590bf35e527431fba6021517a`.
- [mn2024_post_election_review.pdf](https://www.sos.mn.gov/media/ixzn1dkx/2024-post-election-review-results.pdf), 1,642,847 bytes; SHA-256 `5bc0e90c33dbbeff92167a6113231e4a6d2e54f8311c79a83b35e1e3051cccfc`.
- [md2024_official_results.csv](https://elections.maryland.gov/elections/archive/2024/election_data/PG24_AllPrecincts.csv), 17,317,785 bytes; SHA-256 `fa25069f8504691c03528c70c2a76240b06514ab54b491fd624229867018aacc`.
- [clerk_statistics2024.pdf](https://clerk.house.gov/member_info/electionInfo/2024/statistics2024.pdf), 608,100 bytes; SHA-256 `d4ba800fc17135b616ae556c92861080ab962d95916ace34b546c5aac824aec4`.

Other source definitions:
[Minnesota 2024](https://sos.mn.gov/elections-voting/election-results/2024/2024-general-election-results/2024-precinct-results-spreadsheet/),
[Idaho](https://voteidaho.gov/election-results/),
[California caveats](https://www.statewidedatabase.org/d20/g24.html),
[Maryland turnout semantics](https://elections.maryland.gov/press_room/Navigating_Official_Turnout_Statistics.pdf),
[Union official PDF](https://sos.ms.gov/elections/electionresults/2024General/County%20Results/Union.pdf).

No deployment was performed.
