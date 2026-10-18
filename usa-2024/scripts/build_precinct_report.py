"""Build the precinct report, updated paradox report and the static page sections."""
from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from precincts import plot_fingerprints

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT.parent/'site/usa-2024'
OUT=ROOT/'analysis'


def mdtable(frame: pd.DataFrame) -> str:
    return '\n'.join(['| '+' | '.join(map(str,frame.columns))+' |',
                      '| '+' | '.join(['---']*len(frame.columns))+' |']+
                     ['| '+' | '.join(map(str,row))+' |' for row in frame.itertuples(index=False,name=None)])


def main() -> None:
    coverage=pd.read_csv(OUT/'precinct_coverage.csv')
    digits=pd.read_csv(OUT/'precinct_digits.csv')
    peaks=pd.read_csv(OUT/'precinct_integer_peaks.csv')
    metrics=json.loads((OUT/'precinct_metrics.json').read_text())
    audit=pd.read_csv(OUT/'precinct_join_audit.csv.gz',dtype={'key':str,'county':str},low_memory=False)
    plot_fingerprints(audit)
    review=json.loads((OUT/'mn_hand_review_summary.json').read_text())
    races=pd.read_csv(OUT/'clerk_race_screens.csv',dtype={'district':str})
    selected=races[races.plurality_eligible&races.spoiler_capacity].copy()
    summary=json.loads((OUT/'clerk_summary.json').read_text())
    duplicates=pd.read_csv(OUT/'precinct_duplicate_vectors.csv')
    outliers=pd.read_csv(OUT/'precinct_outliers.csv.gz')
    inventory=pd.read_csv(OUT/'precinct_pdf_inventory.csv')
    reconciliation=pd.read_csv(OUT/'clerk_medsl_race_reconciliation.csv')
    current=audit[audit['sample'].str.contains('2024')&audit.eligible].copy()
    current['state']=current['sample'].str.split('2024').str[0]
    unique=current[['state','key']].drop_duplicates().shape[0]
    primary=[x for x in metrics if '2024' in x['sample']]
    assert len(metrics)==69 and len(primary)==60 and len(digits)==276
    assert len(selected)==10 and unique==25682
    known=digits[digits.q_bh<.05]
    assert len(known)==1 and known.iloc[0]['sample']=='WA-King2024 SENATE'
    flags_mc=int((digits.q_mc_bh<.05).sum())
    max_peak=peaks.loc[peaks.z_score.idxmax()]
    compared=reconciliation[reconciliation._merge.eq('both')]
    different=int(compared.difference_margin.ne(0).sum())
    # Keep the existing broad county screens as a separate historical analysis family.
    public_summary={'unique_eligible_2024_units':unique,'2024_contest_samples':len(primary),
        '2024_unit_contest_observations':sum(x['n'] for x in primary),'control_2020_contest_samples':len(metrics)-len(primary),
        'digit_tests_including_controls':len(digits),'digit_theoretical_bh_flags':len(known),
        'digit_mc_bh_flags':flags_mc,'integer_screens':len(peaks),'max_integer_z':float(max_peak.z_score),
        'duplicate_unit_contest_rows':len(duplicates),'mad_flags':int(outliers.mad_flag.sum()),
        'isolation_flags':int(outliers.isolation_flag.sum()),'clerk_matched_medsl_races':len(compared),
        'clerk_medsl_differing_margins':different,'hand_review':review,'spoiler_bounds':len(selected)}
    (OUT/'precinct_summary.json').write_text(json.dumps(public_summary,indent=2)+'\n')
    corr=pd.DataFrame([{'Sample':x['sample'],'Units':x['n'],'Weighted r (R)':f"{x['weighted_r_rep']:.3f}",
                        'County-demeaned r (R)':f"{x['county_demeaned_r_rep']:.3f}"} for x in metrics if x['district']=='STATEWIDE'])
    tails=[x['tail']['tail_share_of_party'] for x in primary]
    sources={
        'mn2020_official_precinct.xlsx':'https://www.sos.mn.gov/media/4373/2020-general-federal-state-results-by-precinct-official.xlsx',
        'mn2024_post_election_review.pdf':review['source_url'],
        'md2024_official_results.csv':'https://elections.maryland.gov/elections/archive/2024/election_data/PG24_AllPrecincts.csv',
        'clerk_statistics2024.pdf':summary['source']}
    provenance=[]
    for name,url in sources.items():
        file=ROOT/'data/raw'/name
        provenance.append({'file':name,'url':url,'download_date':'2026-10-17','bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
    (ROOT/'data/source_search/analysis_extra_downloads.json').write_text(json.dumps(provenance,indent=2)+'\n')
    source_links='\n'.join(f'- [{p["file"]}]({p["url"]}), {p["bytes"]:,} bytes; SHA-256 `{p["sha256"]}`.' for p in provenance)
    report=f'''# U.S. congressional 2024 precinct analysis update

17 October 2026. **No fraud conclusion follows from these screens.** This update
supersedes the earlier county-only coverage and seven-race bound. The older
county and nationwide digit outputs remain a separate exploratory baseline.

## What is now checked

**{unique:,} distinct eligible 2024 reporting precincts** across Minnesota,
California, Idaho, King County (Washington) and Union County (Mississippi).
Units retain each source's geography: CA uses SR precincts, not physical polling
places. This is partial coverage, not a nationwide precinct audit. Each unit is
counted once in this headline even when both congressional offices are examined.
The 20 Union precincts are an extraction/reconciliation case; they do not meet
the 100-unit minimum for the new statistical screens.

**{len(primary)} 2024 contest samples, {sum(x['n'] for x in primary):,} unit–contest
observations**, plus nine Minnesota 2020 control samples. House tests are split
by congressional district. Samples need at least 100 eligible units and nonzero
Democratic and Republican totals. California same-party contests do not support
this two-party diagnostic and are omitted. The historical districts are not
matched through redistricting; these are within-state historical comparisons,
not a same-precinct panel or an independently certified clean null.

### Input audit

{mdtable(coverage)}

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

- **Digits:** {len(digits)} tests across these 69 samples (including controls),
  two parties and two tests. Last digits use counts ≥100; second digits ≥10;
  each pool needs at least 100 numbers. BH correction covers all 276 theoretical
  tests; a second BH family covers the 276 lognormal Monte Carlo p-values.
  **Zero last-digit flags; one second-digit flag**: King County Senate Democrats,
  theoretical q ≈ {known.iloc[0].q_bh:.6f}, but lognormal-null p ≈
  {known.iloc[0].p_null_mc:.3f}, adjusted q ≈ {known.iloc[0].q_mc_bh:.3f}.
  No test flags under the adjusted lognormal family. The theoretical flag is
  not robust to the null model. Monte Carlo uses 400 simulations (resolution
  1/401). This family is separate from the earlier 284 nationwide MEDSL tests;
  no joint 560-test error-rate guarantee is claimed.
- **Integer peaks:** {len(peaks)} turnout/Democratic-share/Republican-share
  screens, 1,000 binomial simulations each. Largest unadjusted integer z ≈
  {max_peak.z_score:.2f}, CA House 29 Republican share ({int(max_peak.observed_integer)}
  observations among {int(max_peak.n_units)} units). These are descriptive z
  rankings, not family-adjusted p-values. No manipulation conclusion follows
  from selecting the maximum of 207 screens.
- **Turnout correlations:** both ordinary geographical effects and historical
  controls matter. Party support uses votes / all ballots, not valid votes.
  County-demeaned values use unweighted Pearson on residuals after county means;
  they are not comparable estimands to the registration/ballot weighted values
  and do not control for demographics or local spatial adjacency.

{mdtable(corr)}

- **Shpilkin:** the same-source registration-weighted 99.5th percentile is a
  descriptive boundary; 2024 leading-party tail shares range from
  {min(tails):.3f}% to {max(tails):.3f}%. Neither fitting a mixture nor obtaining a
  historical file turns this boundary into a calibrated count of fraudulent
  votes. No election result is recomputed after deleting these observations.
- **Klimek-style fingerprints:** the toolkit fits two resampled Gaussian
  clusters; this is a descriptive surrogate, not a fitted mechanistic
  ballot-stuffing model. Geographic clusters are not fraudulent components.
- **Similar-unit / ML:** county-median/MAD flags {int(outliers.mad_flag.sum())}
  unit–contest observations across current/control samples. Isolation Forest
  flags {int(outliers.isolation_flag.sum())}; its 1% contamination is imposed
  per sample. Scores are review leads, not probabilities or a fraud-rate estimate.
  These are county peers, not nearest geographic or socioeconomic neighbors.
- **Exact vectors:** {len(duplicates)} unit–contest rows belong to repeated
  registration/ballots/Dem/Rep/other vectors within a contest. They are not
  {len(duplicates)} repeated ballots. All repeated vectors have ≤{int(duplicates.voted.max())}
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

After conservative key normalization, **{len(compared)}** previously prepared
race records match a Clerk race; **{different}** have different top-two margins.
Names are not fuzzy-matched and unmapped district codes remain unmatched in the
[reconciliation](analysis/clerk_medsl_race_reconciliation.csv). This is a
race-total comparison, not a candidate-level certification of every MEDSL unit.
All ten bounds plus the rejected Arizona Senate case were independently checked
by Luna 6 against **11 rendered Clerk pages**; all four numerical fields match.
See [PARADOXES.md](PARADOXES.md) for thresholds and every preference limitation.

## What remains outside the analysis

An inventory covers **{len(inventory)} downloaded precinct PDFs / {int(inventory.pages.sum()):,}
pages**. Only {int(((inventory.registration_mentions>0)&(inventory.ballots_mentions>0)).sum())}
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

{source_links}

Other source definitions:
[Minnesota 2024](https://sos.mn.gov/elections-voting/election-results/2024/2024-general-election-results/2024-precinct-results-spreadsheet/),
[Idaho](https://voteidaho.gov/election-results/),
[California caveats](https://www.statewidedatabase.org/d20/g24.html),
[Maryland turnout semantics](https://elections.maryland.gov/press_room/Navigating_Official_Turnout_Statistics.pdf),
[Union official PDF](https://sos.ms.gov/elections/electionresults/2024General/County%20Results/Union.pdf).

No deployment was performed.
'''
    (ROOT/'PRECINCT_REPORT.md').write_text(report)
    table=selected[['state_po','office','district','winner','margin','other_votes','minimum_transfer_if_rest_abstain','minimum_transfer_if_rest_back_leader']].copy()
    table.columns=['State','Office','District','Leader','Margin','Other votes','Runner-up votes needed if rest abstain','Runner-up votes needed if rest back leader']
    paradox=f'''# U.S. congressional voting paradoxes, 2024: official-source update

17 October 2026. **Ten arithmetic spoiler bounds; no demonstrated preference
paradox.** This replaces the previous seven-race MEDSL-only screen.
Source: [House Clerk 2024 official-source statistics]({summary['source']}).
All 435 House and 33 regular Senate contests are inventoried; 448 plurality
contests with two or more records are screenable. Alaska/Maine ranked choice
and Louisiana majority-rule races are excluded; unopposed contests without
printed vote counts retain missing values. Candidate fusion lines are combined.
Blank, void, over/under-votes and Nevada “None of These Candidates” are excluded.
Pooled write-ins, “Scattering”, “All Others” and “Miscellaneous” remain pooled
candidate categories, not fictitious individual candidates.

## Exact counterfactual bounds

{mdtable(table)}

For top-two margin M and other-candidate pool O, the bound is O > M. If x
other voters move to the runner-up and the rest abstain, x ≥ M+1 reverses the
result. If all remaining other voters back the leader, x ≥ floor((O+M)/2)+1.
These are integer strict-win thresholds, not transfer estimates. Existing top-two
votes are held fixed; no turnout changes or sincere preferences are observed.
For Iowa House 1 the 967 pooled write-ins exceed the margin of 799, but no
assumption that they are one candidate or would vote as a bloc is justified.

The earlier Arizona Senate bound disappears (official M=80,574, O=76,818).
Iowa House 1, Michigan Senate, Nevada Senate and Oregon House 5 enter the list.
Pennsylvania's margin becomes 15,115 rather than 16,910. Luna 6, reasoning low,
independently calculated the four fields of all ten rows plus Arizona Senate
from 11 rendered PDF pages; the parser and model agree. This validates those
transcriptions, not voters' hypothetical behavior. Retain source PDF hash and
page locators in the downloadable tables because the compilation is a snapshot.

## Every root paradox family: observed status

| Root criterion | What the actual returns establish |
|---|---|
| Frustrated majority / Condorcet winner | Unknown: candidate totals do not contain same-contest pairwise preferences |
| Condorcet loser / absolute loser | Unknown: an elected plurality leader need not be pairwise winner or loser |
| Condorcet cyclical majorities | Unknown without a pairwise matrix |
| Center squeeze | Unknown: requires lower preferences and, for elimination claims, the relevant rounds |
| Spoiler / independence of irrelevant alternatives / SCC | Ten arithmetic bounds only; withdrawals and preference transfers are unobserved |
| Cloning | Unknown: party labels do not establish preference clones |
| Best-is-worst | Unknown: reverse rankings are absent |
| Lesser-evil / strategic voting | Unknown: votes do not reveal sincere favorites or voting incentives |
| Absolute majority | No new empirical violation: ten leaders lack a majority of included candidate votes; this is not proof a different candidate had a majority of first preferences |
| Pareto dominance | Unknown from totals; ordinary plurality with complete strict rankings cannot elect a universally dominated candidate |
| Later-no-harm / later-no-help | Ordinary plurality ignores later rankings, satisfying both; no empirical ranking test is possible |
| Perverse response / monotonicity | Ordinary plurality is monotonic for fixed candidates and tie-breaking; no observed ranked-rule violation established |
| No-show / participation / twin | Ordinary plurality satisfies participation for fixed candidates and tie-breaking; no Alaska/Maine ranked-ballot counterfactual computed |
| Multiple-district paradox / map effects | No legal alternative-map test: need geometry, population, district rules and map constraints; seat/vote imbalance alone does not establish the specific root pathology |
| Reinforcement / consistency | Ordinary plurality is consistent with a fixed candidate set and coherent tie-breaking; preference aggregation not inferred from cross-office totals |
| Truncation | Ordinary plurality never reads lower ranks, so truncating them cannot change the tally |
| Path independence | No empirical candidate-removal experiment; no lower preferences assumed |

Rule properties are conditional mathematical statements about the ordinary
plurality rule, not empirical declarations that U.S. elections have no paradoxes.
Alaska/Maine require their own ranked-ballot rules and data; Louisiana requires
its own majority threshold. Cross-office split tickets cannot replace rankings
among candidates in the same contest. Final results have no chronology or
candidate similarity metric.

## Evidence limits and reproducibility

[Candidate totals with PDF pages](analysis/clerk_candidate_totals.csv),
[all official-source race screens](analysis/clerk_race_screens.csv),
[MEDSL comparison](analysis/clerk_medsl_race_reconciliation.csv), and
[precinct/statistical report](PRECINCT_REPORT.md). Code:
`scripts/clerk_results.py`, `scripts/verify_clerk.py`.

The Clerk source aggregates official returns, not an independent ballot-level
recount. Maine House 2 totals reflect a ranked count while Alaska's reported
candidate totals do not reconstruct all ranked transfers; both are excluded
from plurality claims. Renewed Alaska/Maine downloads returned verification/
access-denied pages; no CVR ballots or full preference rankings were acquired.
No Condorcet, cloning, no-show or sincere lesser-evil claim is inferred from
unavailable evidence. No deployment was performed.
'''
    (ROOT/'PARADOXES.md').write_text(paradox)
    # Compact figure summarizing the new test families, separate from the county baseline.
    fig,axes=plt.subplots(1,3,figsize=(12,3.8))
    family=digits.groupby('test').agg(tests=('q_bh','size'),flags=('q_bh',lambda s:(s<.05).sum()))
    axes[0].bar(['Benford 2nd','Last digit'],family.loc[['benford2','last'],'tests'],color='#dce6ee')
    axes[0].bar(['Benford 2nd','Last digit'],family.loc[['benford2','last'],'flags'],color='#966017')
    axes[0].set(title=f'{len(digits)} digit tests: one theoretical flag',ylabel='Tests (one joint theoretical BH family)')
    for i,k in enumerate(['benford2','last']):axes[0].text(i,family.loc[k,'tests']+2,f"{family.loc[k,'flags']} / {family.loc[k,'tests']}",ha='center')
    top=peaks.nlargest(8,'z_score').iloc[::-1]
    labels=[f"{r.sample.split()[0]} {r.district} {r.metric.replace('share:votes:','')}" for r in top.itertuples()]
    axes[1].barh(labels,top.z_score,color='#3b82c4');axes[1].set(title=f'{len(peaks)} integer screens',xlabel='Largest unadjusted z scores');axes[1].tick_params(axis='y',labelsize=7)
    axes[2].bar(['Exact raw match','Raw discrepancy'],[review['tables']-review['tables_nonzero_raw_total'],review['tables_nonzero_raw_total']],color=['#3b82c4','#966017'])
    axes[2].set(title='Minnesota: all 657 tables acceptable',ylabel='Precinct–contest tables');axes[2].tick_params(axis='x',labelsize=9)
    for ax in axes:ax.title.set_fontsize(11)
    fig.tight_layout();fig.savefig(SITE/'img/precinct_checks.png',dpi=160,bbox_inches='tight');plt.close(fig)
    rows=''.join(f'<tr><th scope="row">{html.escape(r.sample)}</th><td class="number">{r.rows:,}</td><td class="number">{r.eligible:,}</td></tr>' for r in coverage.itertuples())
    precinct_html=f'''<!-- PRECINCT UPDATE START -->
<section id="precincts">
<h2>What the precinct data shows</h2>
<p class="sub">{unique:,} eligible precincts · {len(primary)} congressional samples · Minnesota 2020 control. Coverage is partial; King and Union are county samples.</p>
<p>We checked registration, ballots and candidate votes on the same reporting geography. The {unique:,} distinct 2024 units include California SR precincts, Minnesota, Idaho, King County and Union County. Office-specific exclusions differ. The 20 Union precincts are verified extraction data, below the 100-unit minimum for the statistical screens.</p>
<figure class="fig"><a href="img/precinct_fingerprints.png" target="_blank" rel="noopener"><img src="img/precinct_fingerprints.png" alt="Precinct turnout versus Republican vote share for Minnesota 2024 and 2020, California, Union County, King County and Idaho" loading="lazy" width="1920" height="1120"></a><figcaption>Ballots / registered voters versus party votes / all ballots. Minnesota registration includes registrations when voting. Idaho is pooled for this figure only; its House tests are split by district. The Union sample has only 20 precincts. Geographic patterns are not evidence of their cause.</figcaption></figure>
<details class="m"><summary><span class="m-head">Precinct coverage and exclusions</span></summary><div class="m-details"><div class="table-wrap"><table><caption>All attempted source–office joins, including rejected data</caption><thead><tr><th scope="col">Sample</th><th scope="col" class="number">Input units</th><th scope="col" class="number">Eligible</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>Rows for different offices can refer to the same precinct. The headline counts distinct eligible 2024 identities once; the tests use {sum(x['n'] for x in primary):,} 2024 unit–contest observations. Zero units, unknowns, ballots above registration and votes above ballots remain in the downloadable audit. Arithmetic eligibility does not certify completeness.</p></div></details>
<details class="m"><summary><span class="m-head">What changed in the source handling</span></summary><div class="m-details"><p><strong>Minnesota:</strong> use REG7AM + EDR. Omitting EDR creates 80 artificial above-100% turnout rows. The control is an earlier statewide sample, not a boundary-matched panel. House totals cover the listed major-party/write-in fields.</p><p><strong>Idaho:</strong> remove county totals, join exact keys, exclude under/over-votes from candidate votes, and preserve central absentee pools without registration as exclusions.</p><p><strong>California:</strong> use one SR table only; preserve masked cells, exclude Madera and retain the publisher’s warning about processing artifacts. Do not add SR and SV results.</p><p><strong>King County:</strong> all 2,756 source rows balance candidates + under/over-votes to Times Counted; 13 empty units are omitted from diagnostics.</p><p><strong>Union County:</strong> Luna 6, reasoning low, extracted all 20 relevant scanned precinct pages. Cross-checked registration 17,084 and ballots 12,533 match the printed county totals. No 20-unit digit claim is made.</p></div></details>
<figure class="fig"><img src="img/precinct_checks.png" alt="276 digit tests with one theoretical second-digit flag, the largest of 207 unadjusted integer-screen z scores, and 657 Minnesota hand-review statuses" loading="lazy" width="1920" height="608"><figcaption>One theoretical digit flag is not robust to the null model. Maximum integer z ≈ {max_peak.z_score:.2f} is unadjusted across 207 screens. Hand-review difference totals are candidate/category differences, not unique disputed ballots.</figcaption></figure>
<details class="m"><summary><span class="m-head">All forensic methods: results and evidence limits</span></summary><div class="m-details"><p><strong>Shpilkin:</strong> own-data 99.5th percentile tails are descriptive, not fraudulent-vote counts. <strong>Fingerprints:</strong> two Gaussian clusters describe heterogeneity and are not a mechanistic fraud fit. <strong>Correlations:</strong> Republican weighted r is +0.315 for Minnesota 2024 Senate, +0.381 for Minnesota 2020, +0.118 for California Senate and −0.285 in King County.</p><p><strong>Integer peaks:</strong> 207 screens, 1,000 simulations; unadjusted rankings only. <strong>Digits:</strong> separate BH corrections for theoretical and lognormal Monte Carlo tests; no adjusted lognormal flags. These new tests and the earlier nationwide family have separate multiplicity corrections.</p><p><strong>Peer outliers:</strong> {int(outliers.mad_flag.sum())} county-median/MAD and {int(outliers.isolation_flag.sum())} Isolation Forest flags across current/control unit–contest observations. The forest imposes 1% contamination per sample. No spatial adjacency or demographic matching was performed.</p><p><strong>Exact vectors:</strong> {len(duplicates)} unit–contest rows are in repeated vectors, all with at most {int(duplicates.voted.max())} ballots. Small counts repeat naturally; no copy-paste claim or chance-match model follows.</p><p><strong>Physical anchor:</strong> the complete Minnesota report totals were parsed; Luna verified four tables on three selected page images. <strong>Missing:</strong> ballot serials/custody batches, within-day voting chronology, exit-poll/parallel-count samples and supervised-classifier validation. Final mode totals cannot supply voting chronology.</p></div></details>
<div class="note"><p><strong>Partial coverage remains.</strong> {len(inventory)} downloaded precinct PDFs contain {int(inventory.pages.sum()):,} pages. The remaining state/county scans are inventoried, not validated precinct datasets. Alaska/Maine CVR downloads remain unavailable; sincere rankings and legally constrained alternative maps are not inferred.</p></div>
<details class="m"><summary><span class="m-head">Precinct sources and downloads</span></summary><div class="m-details"><p><a href="PRECINCT_REPORT.md" download>Full precinct report and reproduction</a> · <a href="analysis/precinct_join_audit.csv.gz" download>All joined and rejected rows (CSV.gz)</a> · <a href="analysis/precinct_digits.csv" download>Digit tests</a> · <a href="analysis/precinct_integer_peaks.csv" download>Integer screens</a> · <a href="analysis/precinct_metrics.json" download>Tail, mixture and correlation results</a> · <a href="analysis/precinct_outliers.csv.gz" download>Outlier rankings</a> · <a href="analysis/precinct_duplicate_vectors.csv" download>Repeated vectors</a> · <a href="analysis/mn_hand_review.csv" download>Hand-review tables</a> · <a href="analysis/ms_union_precincts.csv" download>Union extraction</a> · <a href="analysis/precinct_pdf_inventory.csv" download>PDF inventory</a></p>
<p>Primary sources: <a href="https://sos.mn.gov/elections-voting/election-results/2024/2024-general-election-results/2024-precinct-results-spreadsheet/">Minnesota</a> · <a href="https://voteidaho.gov/election-results/">Idaho</a> · <a href="https://www.statewidedatabase.org/d20/g24.html">California and caveats</a> · <a href="https://data.kingcounty.gov/api/views/uuda-pmuy/rows.csv?accessType=DOWNLOAD">King County final CSV</a> · <a href="{review['source_url']}">Minnesota hand review</a> · <a href="https://elections.maryland.gov/press_room/Navigating_Official_Turnout_Statistics.pdf">Maryland definitions</a>. <a href="data/analysis_extra_downloads.json" download>New download checksums</a>.</p></div></details>
</section>
<!-- PRECINCT UPDATE END -->'''
    page=SITE/'index.html'
    content=page.read_text()
    if '<!-- PRECINCT UPDATE START -->' in content:
        content=re.sub(r'<!-- PRECINCT UPDATE START -->.*?<!-- PRECINCT UPDATE END -->',lambda _:precinct_html,content,flags=re.S)
    else:content=content.replace('<section id="coverage">',precinct_html+'\n<section id="coverage">')
    race_rows=''.join(f'<tr><th scope="row">{html.escape(r.state_po)} · {"Senate" if r.office=="US SENATE" else "House "+str(int(r.district))}</th><td class="number">{r.margin:,}</td><td class="number">{r.other_votes:,}</td><td class="number">{r.minimum_transfer_if_rest_abstain:,}</td></tr>' for r in selected.itertuples())
    paradox_html=f'''<section id="paradoxes"><h2>Ten official-source races meet a vote-splitting bound</h2><p class="sub">All 435 House and 33 regular Senate contests are inventoried; 448 plurality contests with multiple records enter the screen. This is a counterfactual bound, not observed voter transfers.</p><p>The screen uses the House Clerk’s compilation of official returns. It excludes majority-rule and ranked-choice contests, non-candidate ballots and Nevada’s “None of These Candidates”.</p><figure class="fig"><img src="img/spoilers.png" alt="Ten official-source races where other candidate votes exceed the top-two margin" loading="lazy"><figcaption>Official returns compiled by the House Clerk. Other votes include pooled write-ins; they do not imply shared voter preferences.</figcaption></figure><details class="m"><summary><span class="m-head">Race totals and transfer thresholds</span></summary><div class="m-details"><div class="table-wrap"><table><caption>Strict-win bounds, holding the two leaders’ existing votes fixed</caption><thead><tr><th scope="col">Contest</th><th scope="col" class="number">Margin</th><th scope="col" class="number">Other votes</th><th scope="col" class="number">Needed if rest abstain</th></tr></thead><tbody>{race_rows}</tbody></table></div><p>For margin M and other-vote pool O, O &gt; M shows arithmetic capacity. If the rest abstain, M+1 voters transferring to the runner-up reverses the result. If every remaining other voter backs the leader, the threshold is floor((O+M)/2)+1. Neither scenario is an estimate of what those voters would do.</p></div></details><div class="note"><p><strong>No preference paradox established.</strong> Vote totals do not reveal voters’ lower preferences, so they cannot establish an actual spoiler effect or a Condorcet paradox. Ranked-ballot and alternative-map analyses remain outside this study.</p></div><p><a href="PARADOXES.md" download>Every root paradox criterion and both thresholds</a> · <a href="analysis/clerk_candidate_totals.csv" download>Candidate totals with PDF pages</a> · <a href="analysis/clerk_race_screens.csv" download>All race screens</a> · <a href="analysis/clerk_medsl_race_reconciliation.csv" download>MEDSL reconciliation</a> · <a href="{summary['source']}">Official Clerk PDF</a>.</p></section>'''
    content=re.sub(r'<section id="paradoxes">.*?</section>',lambda _:paradox_html,content,flags=re.S)
    replacements={
        'Seven races meet a vote-splitting bound':'Ten races meet a vote-splitting bound',
        'Seven reported races could reverse under an extreme transfer assumption.':'Ten official-source races could reverse under an extreme transfer assumption.',
        '<b>284</b> digit tests':'<b>276</b> new precinct digit tests',
        '<b>19</b> states in county diagnostics':f'<b>{unique:,}</b> eligible 2024 precincts',
        '<b>349</b> screened contests':'<b>448</b> official-source plurality screens',
        '<a href="#coverage">Coverage</a>':'<a href="#precincts">Precinct update</a><a href="#coverage">Coverage</a>',
        '<h2>Nationwide collection, partial analytical coverage</h2>':'<h2>Nationwide sources and the earlier county baseline</h2>',
        'Vote-splitting screening includes 323 of 435 House races and 26 of 33 regular Senate races.':'Updated official-source vote-splitting screen includes 416 House and 32 Senate contests.',
        '349 contests pass the screening criteria. This is not a complete reconstruction of all congressional results. Single-record races, unknown totals and source exclusions limit coverage; omitted races are not negative findings.':'The updated Clerk screen has 416 House and 32 Senate plurality contests with multiple records. All 435 House and 33 regular Senate contests are inventoried; ranked/majority rules, single-record races and missing printed totals limit this screen.',
        '<h2>Manipulation detection test results</h2>':'<h2>Earlier county and nationwide reported-unit diagnostics</h2>',
        'Eight families of checks, with the measured result, explanation and figures for each. Turnout-based methods use matched counties; digit tests use candidate counts from reported units. Open a card to inspect the evidence.':'Earlier-stage baseline, retained separately from the precinct update above. Turnout methods here use counties; 284 digit tests use nationwide MEDSL reported-unit counts. These older figures do not describe the new precinct sample.',
        'Final returns do not supply ballot serials, custody records, independent audits or election-night time series.':'Final returns do not supply ballot serials, custody records or election-night time series. The new Minnesota hand-review report provides a limited physical anchor for 219 reviewed precincts.',
        'Some totals do not reconcile.':'The MEDSL source does not fully reconcile.',
        'Seven states are excluded from screening.':'Earlier MEDSL diagnostics exclude seven states.',
        '21 of the 22 adjusted flags come from second digits. Only one comes from last digits. Precinct sizes and reporting practices can produce such departures without fraud.':'In 276 new precinct/control tests, no last-digit test flags. The single theoretical second-digit flag is not robust to the lognormal null.',
        'Most flags are Benford deviations':'No robust digit flag in the new sample',
        'Turnout and Republican support correlate negatively in Washington House returns and positively in Pennsylvania Senate returns. A correlation cannot identify its cause.':'Minnesota Senate has positive Republican turnout correlation in both 2024 and the 2020 control; King County has a negative correlation. A gradient alone cannot identify manipulation.',
        '<ul><li><a href="REPORT.md" download>Statistical report (Markdown)</a>':'<ul><li><a href="PRECINCT_REPORT.md" download>Current precinct report (Markdown)</a> · <a href="REPORT.md" download>Earlier baseline and update notice (Markdown)</a>',
        'No nationwide official House reconciliation was completed.':f'The new Clerk race-total comparison matches {len(compared)} MEDSL contests; {different} margins differ. This does not certify all underlying precinct records.',
    }
    for before,after in replacements.items():content=content.replace(before,after)
    content=re.sub(r'(?:<a href="#precincts">Precinct update</a>)+','<a href="#precincts">Precinct update</a>',content)
    content=re.sub(r'<meta name="description" content="[^"]*">','<meta name="description" content="U.S. congressional 2024: 25,682 eligible precinct units, 276 new digit tests, Minnesota hand-review evidence and ten official-source vote-splitting bounds.">',content)
    content=content.replace('Statistical flags need follow-up. Explore the findings, seven vote-splitting bounds, and the limits of the available data.','Precinct-level diagnostics, Minnesota hand-review evidence, ten official-source vote-splitting bounds and explicit coverage limits.')
    # Preserve the integrated narrative while rebuilding snapshot downloads.
    if '<meta name="report-layout" content="editorial">' not in content:
        page.write_text(content)
    # Explicitly supersede the earlier report without deleting its reproducible baseline.
    old=ROOT/'REPORT.md'
    note='<!-- PRECINCT REPORT NOTICE -->\n**Update, 17 October 2026:** [Precinct analysis](PRECINCT_REPORT.md) supersedes the county-only coverage and seven-race bound below: 25,682 eligible 2024 units, 276 new digit tests, Minnesota hand-review evidence and ten official-source bounds. The following is the retained earlier baseline.\n<!-- END PRECINCT REPORT NOTICE -->\n\n'
    text=old.read_text()
    text=re.sub(r'<!-- PRECINCT REPORT NOTICE -->.*?<!-- END PRECINCT REPORT NOTICE -->\n\n','',text,flags=re.S)
    old.write_text(note+text)
    for name in ['PRECINCT_REPORT.md','PARADOXES.md','REPORT.md']:
        shutil.copy2(ROOT/name,SITE/name)
    for name in ['luna_mn_audit_verification.json','luna_union_precincts.json','luna_clerk_verification.json','analysis_extra_downloads.json']:
        shutil.copy2(ROOT/'data/source_search'/name,SITE/'data'/name)
    for path in OUT.iterdir():
        if path.suffix in {'.csv','.gz','.json'}:shutil.copy2(path,SITE/'analysis'/path.name)
    print(json.dumps(public_summary,indent=2))


if __name__=='__main__':main()
