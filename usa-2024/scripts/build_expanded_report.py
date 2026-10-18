"""Publish reproducible expanded diagnostics without rewriting the retained snapshot."""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

from expanded_analysis import ROOT, OUT, SITE
from precincts import VOTES
from election_forensics.data import ElectionData
from election_forensics.selftest import run_selftest


def table(frame: pd.DataFrame) -> str:
    labels = {'sample':'Source / office','district':'District','party':'Bloc','n_numbers':'Counts','p_value':'Theoretical p','q_bh':'Adjusted q','p_mc_refined':'Fitted-model p','q_mc_refined_bh':'Fitted adjusted q','rows':'Rows','eligible':'Eligible','unknown':'Unknown','zero_denominator':'Zero denominator','over_registration':'Above registration','contest_over_ballots':'Votes > ballots','source_exclusion':'Source limits','metric':'Metric','n_units':'Units','observed_integer':'Integer hits','z_score':'z','q_joint_normal_approx':'Adjusted q (approx.)','state_po':'State','office':'Office','margin':'Margin','other_votes':'Other votes','minimum_transfer_if_rest_abstain':'Needed if rest abstain','minimum_transfer_if_rest_back_leader':'Needed if rest back leader'}
    return '<div class="table-wrap">'+frame.rename(columns=labels).to_html(index=False, border=0, classes='data-table',escape=True,na_rep='unknown')+'</div>'


def main() -> None:
    audit = pd.read_csv(OUT/'precinct_join_audit.csv.gz',dtype={'key':str,'county':str},low_memory=False)
    coverage = pd.read_csv(OUT/'precinct_coverage.csv')
    digits = pd.read_csv(OUT/'precinct_digits.csv')
    peaks = pd.read_csv(OUT/'precinct_integer_peaks.csv')
    metrics = json.loads((OUT/'precinct_metrics.json').read_text())
    outliers = pd.read_csv(OUT/'precinct_outliers.csv.gz',low_memory=False)
    duplicates = pd.read_csv(OUT/'precinct_duplicate_vectors.csv')
    reconciliation = pd.read_csv(OUT/'clerk_bloc_reconciliation.csv',dtype={'district':str})
    current = audit[audit.eligible & audit['sample'].str.contains('2024')].copy()
    current['state'] = current['sample'].str[:2]
    unique = len(current[['state','key']].drop_duplicates())
    tested = [m for m in metrics if '2024' in m['sample']]
    historical = [m for m in metrics if '2024' not in m['sample']]
    flagged = digits[digits.q_bh < .05]
    robust = digits[(digits.q_bh < .05)&(digits.q_mc_refined_bh < .05)]
    robust_current = int(robust['sample'].str.contains('2024').sum())
    robust_historical = len(robust)-robust_current
    refined_count = int((digits.refined_simulations > 0).sum())
    peakflags = peaks[(peaks.q_joint_normal_approx < .05)|(peaks.q_mult5_joint_normal_approx < .05)]
    # Narrative below names this snapshot's surviving case; fail rather than publish stale claims.
    current_flags = robust[robust['sample'].str.contains('2024')]
    assert current_flags[['sample','party','test']].to_dict('records') == [{'sample':'OH2024 SENATE','party':'REP','test':'benford2'}]
    assert robust_historical == 7 and len(peakflags) == 0
    assert not digits[(digits.test == 'last') & ((digits.q_bh < .05)|(digits.q_mc_refined_bh < .05))].shape[0]
    baseline = audit[audit.eligible & audit['sample'].eq('MN2024 SENATE')].copy().reset_index(drop=True)
    baseline['blank_votes'] = baseline.voted-baseline[VOTES].sum(axis=1)
    baseline['null_votes'] = 0
    experiment = asdict(run_selftest(ElectionData('MN2024 Senate',baseline,VOTES),'votes:REP'))
    (OUT/'precinct_selftest.json').write_text(json.dumps(experiment,indent=2)+'\n')
    races = pd.read_csv(ROOT/'analysis/clerk_race_screens.csv',dtype={'district':str})
    # Recalculate the bounds, rather than trusting the previously printed flag.
    selected = races[races.plurality_eligible & (races.other_votes > races.margin)].copy()
    assert len(selected) == 10
    assert (selected.minimum_transfer_if_rest_abstain == selected.margin+1).all()
    assert (selected.minimum_transfer_if_rest_back_leader == (selected.other_votes+selected.margin)//2+1).all()
    selected['runner_up_fraction_if_rest_abstain_pct'] = (100*(selected.margin+1)/selected.other_votes).round(2)
    selected.to_csv(OUT/'paradox_bounds.csv',index=False)
    assert len(metrics)*3 == len(peaks)
    assert not audit.duplicated(['sample','district','key']).any()
    assert not audit['sample'].eq('WA-King2024 SENATE').any()
    assert not current['sample'].eq('VT2024 HOUSE').any()
    summary = dict(date='2026-10-18',eligible_2024_reporting_units=unique,current_contest_samples=len(tested),
                   historical_contest_samples=len(historical),tested_current_unit_contest_observations=sum(m['n'] for m in tested),
                   digit_tests=len(digits),digit_theoretical_bh_flags=len(flagged),digit_mc_bh_flags=int((digits.q_mc_refined_bh<.05).sum()),
                   digit_flags_under_both_nulls=len(robust),digit_both_nulls_current=robust_current,digit_both_nulls_historical=robust_historical,integer_screens=len(peaks),integer_approx_bh_flagged_screens=len(peakflags),
                   mad_flags=int(outliers.mad_flag.sum()),isolation_flags=int(outliers.isolation_flag.sum()),
                   duplicate_unit_contest_rows=len(duplicates),spoiler_bounds=len(selected),selftest=experiment)
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    fig, axes = plt.subplots(2,3,figsize=(13,8))
    for ax,sample in zip(axes.flat,['WA2024 SENATE','WV2024 SENATE','OH2024 SENATE','IA2024 HOUSE','SC2024 HOUSE','VA2024 SENATE']):
        d = current[current['sample'].eq(sample)]
        ax.hexbin(100*d.voted/d.registered_voters,100*d['votes:REP']/d.voted,gridsize=40,mincnt=1,cmap='Blues',bins='log')
        ax.set(title=f'{sample}: {len(d):,} eligible units',xlabel='Ballots / registration (%)',ylabel='Republican votes / ballots (%)',xlim=(0,100),ylim=(0,100))
    fig.tight_layout();fig.savefig(SITE/'img/expanded_fingerprints.png',dpi=150);plt.close(fig)
    correlations = pd.DataFrame([dict(sample=m['sample'],district=m['district'],units=m['n'],
        republican_weighted_r=round(m['weighted_r_rep'],4),county_demeaned_r=round(m['county_demeaned_r_rep'],4),
        turnout_pct=round(m['turnout'],3),tail_share_pct=round(m['tail']['tail_share_of_party'],4)) for m in metrics])
    correlations.to_csv(OUT/'correlations_and_tails.csv',index=False)
    peakdisplay = peaks.sort_values('z_score',ascending=False).head(10)[['sample','district','metric','n_units','observed_integer','z_score','q_joint_normal_approx']].round(5)
    digitdisplay = digits[(digits.q_bh<.05)|(digits.q_mc_refined_bh<.05)][['sample','district','party','test','n_numbers','p_value','q_bh','p_null_mc','q_mc_bh','p_mc_refined','q_mc_refined_bh']].copy()
    for col in digitdisplay:
        if col.startswith(('p_', 'q_')): digitdisplay[col] = digitdisplay[col].map(lambda x: f'{x:.3g}')
    checks = reconciliation[reconciliation.difference.fillna(0).ne(0)]
    tailmax = max(m['tail']['tail_share_of_party'] for m in tested)
    verdict = 'Digit deviations persist under two nulls; no fraud inference' if len(robust) else 'No digit flags agree under both nulls; coverage remains partial'
    intro = (f'{unique:,} eligible 2024 reporting units, {len(tested)} current contest samples and {len(historical)} historical samples. '
             f'{len(digits)} digit tests: {len(flagged)} theoretical-null flags, {int((digits.q_mc_refined_bh<.05).sum())} refined fitted-lognormal flags, '
             f'{len(robust)} in common ({robust_current} current, {robust_historical} historical), after separate Benjamini–Hochberg adjustments. These are model-dependent screens, not a finding of fraud.')
    methods = [
        ('Shpilkin / turnout tails', f'The own-sample registration-weighted 99.5th-percentile tails contain 0–{tailmax:.3f}% of leading-bloc votes in current samples. No honest-core model is established, so there is no defensible stuffed-vote total or corrected outcome. Historical samples are comparisons, not matched-precinct controls.'),
        ('Turnout × result correlations', 'Weighted and county-demeaned correlations are exported for every tested contest. Geographic gradients and the sign changing between states make a national fraud interpretation unjustified. Support uses candidate votes / all ballots, including contest nonvoting.'),
        ('Klimek fingerprints', 'Two Gaussian components are fitted within each eligible contest. This is a descriptive surrogate for population heterogeneity, not the paper’s mechanistic fraud model; component weights are not fraud rates.'),
        ('Kobak integer peaks', f'{len(peaks)} metric screens, each with 1,000 binomial simulations; integer and multiple-of-five excesses form a jointly adjusted family of {2*len(peaks)} approximate one-sided normal-tail tests. {len(peakflags)} metric screens flag in that approximation. Sparse discrete tails and endogenous binomial probabilities require calibration; the table is a follow-up queue.'),
        ('Benford second digits and last digits', f'{len(digits)} tests; counts must be ≥10 / ≥100, with ≥100 eligible counts per test. {len(flagged)} theoretical and {int((digits.q_mc_refined_bh<.05).sum())} lognormal-null flags after separate BH adjustments; {len(robust)} overlap. The initial fitted-lognormal null uses 400 simulations. All theoretical BH flags and all minimum-p Monte Carlo hits ({refined_count} tests) are rechecked with 20,000 simulations (minimum p=1/20,001); unselected tests receive p=1 before a fresh full-family BH adjustment. This avoids interpreting a coarse simulation floor as absence of a signal. Neither null models all election heterogeneity.'),
        ('Similar precincts and machine learning', f'{int(outliers.mad_flag.sum()):,} county median/MAD flags; {int(outliers.isolation_flag.sum()):,} Isolation Forest flags over current and historical unit–contest observations. County peers are not physical neighbors or socioeconomic matches. Isolation Forest uses 1% imposed contamination and no labeled fraud training set.'),
        ('Repeated vectors', f'{len(duplicates):,} repeated-vector rows (registration, ballots, DEM, REP, other). Repetition is not itself improbable without a conditional null; small precincts can match by chance. Splits and overlapping Washington sources are not counted as independent precincts.'),
        ('Ballot serials / batches and voting dynamics', 'Not identifiable: the downloads contain final aggregates, not ballot identifiers, batch custody records, time-stamped voting records or independent snapshots. XML file-generation timestamps are not voting or counting dynamics.'),
        ('Documentary / physical anchor', 'The existing Minnesota official hand review remains the physical anchor: all 657 precinct–contest tables across 219 precinct identities were acceptable under the official thresholds. It does not validate every state, the newly added precincts, or every ballot.'),
        ('Synthetic precinct sensitivity', f"Minnesota Senate: a fixed original cutoff of {experiment['t_cut']:.2f}% gives {experiment['clean_tail_party']:,} Republican tail votes before injection and {experiment['injected_tail_party']:,} after {experiment['injected_added_ballots_party']:,} synthetic Republican votes are added. Rounded-turnout injection into {experiment['n_rounded_units']} units changes z from {experiment['peaks_z_clean']:.2f} to {experiment['peaks_z_rounded']:.2f}. The rounded scenario does not flag, so detection power is limited. The tail also counts pre-existing votes moved above the cutoff; it does not recover the injection size. These scenarios do not calibrate a fraud rate.")]
    methodhtml = '\n'.join(f'<details class="m"><summary><span class="m-head"><h3>{title}</h3><p>{body}</p></span></summary><div class="m-details"><p>Reproducible outputs: <a href="analysis/expanded/precinct_metrics.json">metrics</a>, <a href="analysis/expanded/precinct_digits.csv">digit tests</a>, <a href="analysis/expanded/precinct_integer_peaks.csv">integer screens</a>, <a href="analysis/expanded/precinct_outliers.csv.gz">outliers</a>, <a href="analysis/expanded/precinct_selftest.json">self-test</a>.</p></div></details>' for title,body in methods)
    exclusions = '''<p><strong>Source limits retained:</strong> Washington statewide data replaces King County, with registration differences of 13 versus the recorded statewide table and 4,521 versus the active-voter reconciliation workbook; every county ballot total and all 33 congressional candidate columns reconcile. Iowa, West Virginia and Ohio are pinned mirror copies, not freshly retrieved official files. Ohio write-ins are missing (640 Senate, 4 House district 2 and 29 House district 11 votes versus the Clerk); named-candidate digits remain observable. West Virginia’s other-candidate pool is short by 15 Senate and 174 House district 1 votes. None is filled with inferred precinct counts.</p>
<p><strong>Geography and exclusions:</strong> split House precinct rows are excluded when full-precinct turnout cannot be assigned to a fragment. California suppression, above-registration counts, zero denominators and missing joins remain excluded. Virginia and South Carolina use name joins with numeric padding removed, collision checks and outer-join audits; unmatched rows stay unknown. South Carolina precinct ballots and registration sum exactly to its county/state Election History totals; VREMS voter-history denominators are not substituted. Vermont’s 247 town rows contain partial district results in multi-district towns and incomplete statewide candidate totals, so all are excluded from the combined diagnostics. Maryland administrative participation is still incompatible. Wyoming and North Dakota lack registration; Pennsylvania lacks ballots; North Carolina supplies registration only. Provisional OCR rows and Kentucky’s new four PDFs remain outside the sample: transcript arithmetic alone does not validate the needed joins, and Kentucky’s published turnout has an unofficial/roll-timing caveat.</p>'''
    paradoxtext = (ROOT/'PARADOXES.md').read_text()
    matrix = paradoxtext.split('## Every root paradox family: observed status\n\n')[1].split('\n\nRule properties')[0]
    lines = matrix.splitlines()
    paradoxrows = [line.strip('|').split('|') for line in lines if line.startswith('|')][2:]
    paradoxframe = pd.DataFrame([[c.strip() for c in row] for row in paradoxrows],columns=['Criterion','What the evidence establishes'])
    boundscols = ['state_po','office','district','margin','other_votes','minimum_transfer_if_rest_abstain','minimum_transfer_if_rest_back_leader']
    paradoxsection = f'''<h3 id="expanded-paradoxes">All paradox families rechecked</h3><p>The new downloads add first-choice totals and denominators, not same-contest preference rankings. Recalculating the nationwide Clerk inventory still yields <strong>ten arithmetic bounds among 448 screenable plurality contests</strong>. All 435 House and 33 regular Senate contests are inventoried. Ranked-choice Alaska/Maine and Louisiana majority-rule races require separate rules and are excluded from plurality claims. Iowa House 1’s two major totals agree exactly in the newly parsed county XML. The ten bounds remain possibilities, with no observed preference transfer.</p><p>With top-two margin M and other-candidate votes O, O &gt; M allows a strict reversal if at least M+1 voters transfer to the runner-up while the rest abstain, or floor((O+M)/2)+1 if the rest support the leader. Both thresholds were recomputed and checked; pooled write-ins are not assumed to be a single candidate. These are conditional counterfactuals with fixed top-two votes.</p><details><summary>Every criterion in paradoxes.md, including rule properties and unidentified preferences</summary>{table(paradoxframe)}</details><details><summary>Recomputed ten-race bounds</summary>{table(selected[boundscols])}<p><a href="analysis/expanded/paradox_bounds.csv">Download bounds and required transfer fractions</a></p></details>'''
    section = f'''<!-- EXPANDED UPDATE START -->
<section id="expanded-analysis" aria-labelledby="expanded-title">
<h2 id="expanded-title">18 October update: expanded precinct analysis</h2>
<p class="sub">{intro}</p>
<p><strong>Current follow-up: Ohio Senate Republican second digits.</strong> This is the only current test that survives both null comparisons. Seven historical second-digit tests also survive, showing why a rejection is not specific to manipulation. No last-digit test flags. The fitted lognormal is only one smooth-count reference; it does not account for every precinct-size or demographic pattern.</p>
<p>Scope: 2024 Senate and House, following this page’s congressional focus. California 2020 and Washington 2020 presidential data are explicitly labeled auxiliary historical comparisons; no presidential-electoral-college analysis is inferred. Reporting units include consolidated precincts and central voting pools, not necessarily physical polling places. Units counted in the headline may be below the 100-unit or two-major-bloc threshold for contest testing.</p>
<figure><img src="img/expanded_fingerprints.png" alt="Six panels of turnout against Republican votes per ballot in newly analyzed state sources" width="1950" height="1200" loading="lazy"><figcaption>Observed geographic patterns in the expanded sources. Iowa and South Carolina panels pool House districts for display only; statistical tests separate districts.</figcaption></figure>
<div class="methods">{methodhtml}</div>
<details><summary>Expanded coverage, exclusions and source reconciliation</summary>{table(coverage)}{exclusions}<h3>Nonzero Clerk reconciliation differences</h3>{table(checks)}<p>Absent Clerk minor-party categories are unknown in the reconciliation table rather than treated as a source mismatch. Complete source rows, unmatched keys and every exclusion are retained in <a href="analysis/expanded/precinct_join_audit.csv.gz">the join audit</a>.</p></details>
<details><summary>Flagged digit tests and largest integer screens</summary><p>Digit table includes every flag under either null, with both comparisons. Integer q-values use a normal approximation and joint integer/multiple-of-five adjustment, not exact Monte Carlo tail probabilities.</p>{table(digitdisplay.drop(columns=['test','p_null_mc','q_mc_bh']))}{table(peakdisplay)}</details>
<details><summary>Historical comparisons and turnout correlations</summary>{table(correlations[correlations.district.eq('STATEWIDE')])}<p>Historical precincts are not a matched panel: redistricting, reporting boundaries, pandemic voting and registration definitions differ. Minnesota 2016/2020, California 2020 and Washington 2020 cannot by themselves define a nationwide honest-election null.</p></details>
{paradoxsection}
<p><a href="EXPANDED_REPORT.md">Full expanded report and method coverage</a> · <a href="analysis/expanded/summary.json">Machine-readable summary</a> · <a href="RECONCILIATION.md">Extraction/source audit</a> · <a href="TURNOUT_EXPANSION.md">Download provenance</a></p>
<p>Sources: <a href="https://clerk.house.gov/member_info/electionInfo/2024/statistics2024.pdf">House Clerk official-source statistics</a>; local publisher files and pinned mirror manifests, with download hashes retained. Integer-screen reference: <a href="https://arxiv.org/abs/1410.6059">Kobak, Shpilkin and Pshenichnikov</a>. The earlier 17 October results below are retained as a separate snapshot and are not pooled into another independent test family.</p>
</section>
<!-- EXPANDED UPDATE END -->'''
    page = (SITE/'index.html').read_text()
    # The integrated site narrative is edited independently of report snapshots.
    if '<meta name="report-layout" content="editorial">' not in page:
        page = page.replace('href="#paradoxes">Paradoxes ↓','href="#expanded-paradoxes">Paradoxes ↓')
        page = re.sub(r'<!-- EXPANDED UPDATE START -->.*?<!-- EXPANDED UPDATE END -->\s*','',page,flags=re.S)
        page = page.replace('<!-- PRECINCT UPDATE START -->',section+'\n<!-- PRECINCT UPDATE START -->')
        page = page.replace('Analysis snapshot: 17 October 2026.', 'Expanded analysis: 18 October 2026; retained earlier snapshots: 17 October 2026.')
        page = page.replace('Current precinct report (Markdown)', 'Retained 17 October precinct report (Markdown)')
        page = page.replace('What the precinct data shows','17 October snapshot: what the earlier precinct data showed')
        page = page.replace('Nine method cards using the current precinct analysis','Retained 17 October snapshot: nine method cards using the earlier precinct analysis')
        page = re.sub(r'<div><h2>.*?</h2>\s*<p>.*?</p></div>',f'<div><h2>{verdict}</h2>\n<p>{intro} <a href="#expanded-analysis" style="color:inherit">Read the 18 October update</a>.</p></div>',page,count=1,flags=re.S)
        page = page.replace('No robust digit flag in the new sample','Expanded diagnostics have limited calibration')
        page = re.sub(r'(<h4>Expanded diagnostics have limited calibration</h4>\s*)<p>.*?</p>',r'\g<1>'+f'<p>One current second-digit case survives both null comparisons: Ohio Senate Republican counts. Seven historical cases also survive. No last-digit or family-adjusted integer-peak flag survives; model deviations alone do not establish manipulation.</p>',page,count=1,flags=re.S)
        page = re.sub(r'(<meta name="description" content=")[^"]*',r'\g<1>'+f'U.S. congressional 2024: {unique:,} eligible reporting units, expanded statistical diagnostics, historical comparisons and ten arithmetic vote-splitting bounds.',page)
        assert page.count('<!-- EXPANDED UPDATE START -->') == 1
        assert page.count('id="expanded-analysis"') == 1
        (SITE/'index.html').write_text(page)
    report = '# U.S. congressional 2024: expanded analysis, 18 October 2026\n\n'+intro+'\n\n'
    report += 'The earlier 17 October results remain a separate reproducible snapshot. Do not combine their test counts with this family: this rerun already includes their nonoverlapping units.\n\n'
    report += '\n\n'.join('## '+title+'\n\n'+body for title,body in methods)
    report += '\n\n## Flagged digit tests\n\n```csv\n'+digitdisplay.to_csv(index=False)+'```\n\n## Largest integer screens (approximate adjusted q)\n\n```csv\n'+peakdisplay.to_csv(index=False)+'```\n'
    report += '\n\n## Coverage and source limitations\n\n'+re.sub('<[^>]+>','',exclusions)+'\n\n'+coverage.to_csv(index=False)
    report += '\n\n## Voting paradoxes\n\nTen Clerk bounds were recalculated from the full contest inventory; the new inputs do not provide preference rankings.\n\n'+matrix+'\n\n'+selected[boundscols].to_csv(index=False)
    report += '\n## Reproduction\n\n```sh\npython3 usa-2024/scripts/check_turnout_continuation.py\nMPLCONFIGDIR=/tmp/usa-matplotlib OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 analysis-tool/.venv/bin/python usa-2024/scripts/expanded_analysis.py\nMPLCONFIGDIR=/tmp/usa-matplotlib OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 analysis-tool/.venv/bin/python usa-2024/scripts/refine_digit_nulls.py\nMPLCONFIGDIR=/tmp/usa-matplotlib OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 analysis-tool/.venv/bin/python usa-2024/scripts/build_expanded_report.py\n```\n\nPrerequisite: existing extraction/reconciliation outputs described in RECONCILIATION.md. No raw source is modified. Fixed random seeds: toolkit defaults; self-test seed 7. Digit Monte Carlo: 400 initial replicates, then 20,000 for theoretical BH flags or minimum-p hits, unselected p=1 for the refined full-family adjustment; integer peaks: 1,000 replicates. Every tested sample has ≥100 eligible rows and both major blocs.\n\nOutputs in analysis/expanded/ include all eligible/excluded joins, coverage, digit nulls and BH adjustments, mixtures/tails/correlations, integer screens, outliers, repeated vectors, source totals, synthetic tests and exact paradox bounds.\n'
    report += '\nSources: [Clerk](https://clerk.house.gov/member_info/electionInfo/2024/statistics2024.pdf), [integer percentages paper](https://arxiv.org/abs/1410.6059), and the linked local download manifests in TURNOUT_EXPANSION.md.\n'
    (ROOT/'EXPANDED_REPORT.md').write_text(report)
    (SITE/'EXPANDED_REPORT.md').write_text(report)
    shutil.copy2(ROOT/'README.md',SITE/'DATA.md')
    for name in ['RECONCILIATION.md','TURNOUT_EXPANSION.md','PARADOXES.md']:
        shutil.copy2(ROOT/name,SITE/name)
    shutil.copytree(OUT,SITE/'analysis/expanded',dirs_exist_ok=True)
    # The copied source audits link to these local downloads, too.
    for file in (ROOT/'analysis').iterdir():
        if file.suffix in {'.csv','.gz','.json'}: shutil.copy2(file,SITE/'analysis'/file.name)
    for file in (ROOT/'data/source_search').glob('turnout_*.json'):
        shutil.copy2(file,SITE/'data/source_search'/file.name)
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    main()
