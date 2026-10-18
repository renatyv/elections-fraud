"""Prepare MEDSL congressional returns and run supported diagnostic screens.
Run with analysis-tool/.venv/bin/python usa-2024/scripts/analyze.py.
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'analysis-tool/src'))
from election_forensics.data import ElectionData
from election_forensics.digit_tests import digit_test

UNIT = ['state_po', 'county_name', 'jurisdiction_name', 'precinct']
RACE = ['state_po', 'office', 'district', 'special', 'date']
LINE = UNIT + ['office', 'district', 'special', 'date', 'candidate', 'party_detailed', 'party_simplified']


def collapse_modes(df: pd.DataFrame) -> pd.DataFrame:
    """Prefer reported TOTAL per ballot line; otherwise sum reported modes."""
    df = df.copy()
    total = df['mode'].str.upper().eq('TOTAL')
    has_total = total.groupby([df[c] for c in LINE], dropna=False).transform('any')
    df = df[total | ~has_total]
    # Unknown/suppressed counts invalidate the line instead of becoming zero.
    return df.groupby(LINE, dropna=False, as_index=False)['votes'].agg(
        lambda x: x.sum() if x.notna().all() else np.nan)


def selfcheck() -> None:
    base = {c: 'x' for c in LINE}
    rows = pd.DataFrame([{**base, 'mode': m, 'votes': v} for m, v in
                         [('TOTAL', 30), ('MAIL', 10), ('ELECTION DAY', 20)]])
    assert collapse_modes(rows)['votes'].tolist() == [30]
    assert collapse_modes(rows.iloc[1:])['votes'].tolist() == [30]
    rows.loc[0, 'votes'] = np.nan
    assert collapse_modes(rows)['votes'].isna().all()


def main() -> None:
    selfcheck()
    out = ROOT / 'analysis'
    out.mkdir(exist_ok=True)
    expected = [x for x in json.loads((ROOT / 'data/source_tree.json').read_text())['tree']
                if x['path'].endswith('.zip')]
    for item in expected:
        p = ROOT / 'data/raw' / Path(item['path']).name
        assert p.stat().st_size == item['size'], f'Incomplete download: {p}'
    audits, prepared, offices, manifest = [], [], [], []
    for item in expected:
        p = ROOT / 'data/raw' / Path(item['path']).name
        manifest.append({'file': p.name, 'bytes': p.stat().st_size,
                         'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
        with zipfile.ZipFile(p) as z:
            names = [n for n in z.namelist() if n.endswith('.csv') and not n.startswith('__MACOSX')]
            assert len(names) == 1, names
            with z.open(names[0]) as f:
                chunks = []
                for chunk in pd.read_csv(f, dtype=str, keep_default_na=False, chunksize=200_000):
                    chunk = chunk.apply(lambda s: s.str.strip())
                    inv = chunk.groupby(['state_po', 'office', 'mode']).size().reset_index(name='rows')
                    offices.append(inv)
                    chunks.append(chunk[chunk.office.isin(['US HOUSE', 'US SENATE'])].copy())
                raw = pd.concat(chunks, ignore_index=True)
        numeric = pd.to_numeric(raw.votes, errors='coerce')
        invalid = numeric.isna() | (numeric < 0) | (numeric % 1 != 0)
        raw['votes'] = numeric.mask(invalid)
        collapsed = collapse_modes(raw)
        # Fusion ballot lines are additive for the same named candidate.
        candkeys = UNIT + ['office', 'district', 'special', 'date', 'candidate']
        candidates = collapsed.groupby(candkeys, dropna=False, as_index=False).agg(
            votes=('votes', lambda x: x.sum() if x.notna().all() else np.nan),
            party=('party_simplified', lambda x: '|'.join(sorted(set(x) - {''}))))
        candidates['source_state'] = p.stem[:2].upper()
        prepared.append(candidates)
        audits.append({'state': p.stem[:2].upper(), 'raw_congress_rows': len(raw),
                       'invalid_raw_counts': int(invalid.sum()), 'candidate_units': len(candidates),
                       'unknown_candidate_units': int(candidates.votes.isna().sum()),
                       'modes': '|'.join(sorted(raw['mode'].unique()))})
        print(p.name, len(candidates), flush=True)
    data = pd.concat(prepared, ignore_index=True)
    data.to_csv(ROOT / 'data/congress_candidate_units.csv.gz', index=False)
    pd.DataFrame(manifest).to_csv(ROOT / 'data/manifest.csv', index=False)
    pd.concat(offices).groupby(['state_po', 'office', 'mode'], as_index=False)['rows'].sum().to_csv(out / 'office_inventory.csv', index=False)
    pd.DataFrame(audits).to_csv(out / 'coverage.csv', index=False)
    reconcile_senate(data, out)
    analyze_results(data, out)


def reconcile_senate(data: pd.DataFrame, out: Path) -> None:
    senate = data[(data.office == 'US SENATE') & data.special.str.upper().eq('FALSE')]
    senate = senate[~senate.candidate.str.contains('UNDER|OVER|BLANK|TOTAL|NO CANDIDATE|^CAST VOTES$|^$')]
    counted = senate.groupby(['state_po', 'candidate'], as_index=False).votes.agg(
        lambda x: x.sum() if x.notna().all() else np.nan)
    reference = pd.read_csv(ROOT / 'data/raw/2024-senate-state.csv', dtype=str, keep_default_na=False)
    reference = reference[reference.special.str.upper().eq('FALSE') & reference['mode'].eq('TOTAL')].copy()
    reference['votes'] = pd.to_numeric(reference.votes, errors='raise')
    reference = reference.groupby(['state_po', 'candidate'], as_index=False).agg(
        reference_votes=('votes', 'sum'), unofficial=('unofficial', lambda x: '|'.join(sorted(set(x)))))
    check = counted.merge(reference, on=['state_po', 'candidate'], how='outer', indicator=True)
    check['difference'] = check.votes - check.reference_votes
    check.to_csv(out / 'senate_reference_reconciliation.csv', index=False)


def analyze_results(data: pd.DataFrame, out: Path) -> None:
    data = data.copy()
    # A candidate's minor-party fusion line belongs to that same major-party candidate.
    for party in ['DEMOCRAT', 'REPUBLICAN']:
        other = 'REPUBLICAN' if party == 'DEMOCRAT' else 'DEMOCRAT'
        mask = data.party.str.split('|').map(lambda x: party in x and other not in x)
        data.loc[mask, 'party'] = party
    data = data[data.special.str.upper().eq('FALSE')]
    digits = []
    # shortcut: diagnostic reported units may include centralized absentee pools;
    # replace with state-specific reconciled geographic precincts before inference.
    excluded = {'IN', 'NJ', 'LA', 'AK', 'ME', 'OR', 'RI'}
    for (state, office, party), group in data.groupby(['state_po', 'office', 'party']):
        if state in excluded or party not in {'DEMOCRAT', 'REPUBLICAN'}:
            continue
        print(f'digits: {state} {office} {party}', flush=True)
        counts = group.votes.dropna()
        frame = pd.DataFrame({'votes:party': counts.to_numpy()})
        election = ElectionData(f'{state} {office}', frame, ['votes:party'])
        for test, minimum in [('last', 100), ('benford2', 10)]:
            if (counts >= minimum).sum() < 100:
                continue
            result = asdict(digit_test(election, 'votes:party', test, n_sim=200))
            result.update(state=state, office=office, party=party)
            digits.append(result)
    tests = pd.DataFrame(digits)
    # Benjamini-Hochberg adjustment across both offices, parties, states and tests.
    order = np.argsort(tests.p_value.to_numpy())
    adjusted = np.minimum.accumulate((tests.p_value.to_numpy()[order] * len(tests) /
                                      np.arange(1, len(tests) + 1))[::-1])[::-1]
    tests['q_bh'] = np.nan
    tests.loc[order, 'q_bh'] = np.minimum(adjusted, 1)
    tests.to_csv(out / 'digit_tests.csv', index=False)
    races = []
    regular = data[data.special.str.upper().eq('FALSE') & data.date.eq('2024-11-05')]
    for key, group in regular.groupby(RACE, dropna=False):
        tally = group.groupby('candidate', as_index=False).agg(
            votes=('votes', lambda x: x.sum() if x.notna().all() else np.nan),
            party=('party', lambda x: '|'.join(sorted(set(x)))))
        tally = tally[~tally.candidate.str.upper().str.contains('UNDER|OVER|BLANK|TOTAL|NO CANDIDATE|^CAST VOTES$|^$', regex=True)]
        ranked = tally.sort_values('votes', ascending=False)
        if len(ranked) < 2 or ranked.votes.isna().any() or ranked.votes.sum() == 0:
            continue
        a, b = ranked.iloc[0], ranked.iloc[1]
        other = ranked.votes.sum() - a.votes - b.votes
        races.append(dict(zip(RACE, key), winner=a.candidate, party=a.party,
                          winner_votes=a.votes, runner_up=b.candidate, runner_up_votes=b.votes,
                          valid_reported_votes=ranked.votes.sum(), margin=a.votes-b.votes,
                          other_votes=other, below_majority=bool(a.votes*2 < ranked.votes.sum()),
                          spoiler_capacity=bool(other > a.votes-b.votes),
                          usable_screen=key[0] not in excluded))
    race_df = pd.DataFrame(races)
    race_df.to_csv(out / 'race_screens.csv', index=False)
    summary = {'archives': len(pd.read_csv(ROOT / 'data/manifest.csv')), 'candidate_units': len(data), 'digit_tests': len(tests),
               'digit_tests_q_below_005': int((tests.q_bh < .05).sum()),
               'regular_reported_races': len(race_df),
               'usable_screen_races': int(race_df.usable_screen.sum()),
               'below_majority_usable': int((race_df.below_majority & race_df.usable_screen).sum()),
               'spoiler_capacity_usable': int((race_df.spoiler_capacity & race_df.usable_screen).sum())}
    (out / 'metrics.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(summary)


if __name__ == '__main__':
    main()
