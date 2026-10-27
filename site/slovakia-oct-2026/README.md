# Slovakia — municipal (OSO) & regional (OSK) elections, 24 October 2026

Static report page. Languages: **Slovak (sk)** and **English (en)** —
`translations.js` carries both; figures live in `img/{sk,en}/` and
`img/details/{lang}/…`.

## Verdict

The tests do not establish statistical traces of manipulation, using the
2022 races as references. This does not rule out all manipulation. The
paradox section shows plurality winners (32.0% in Košický kraj), changes
in bloc totals, and different participation between elections: a net
79,290 more municipal participants across 3,556 comparable precincts
(2022: 99,229 across a separate 3,417-precinct sample). These aggregate
gaps do not establish clientelism or individual voter motives. Foreign
permanent residents can vote in both elections; see the official
eligibility source linked on the page.

## Figures

Section figures are rebuilt from the analysis outputs by
`slovakia-oct-2026/scripts/build_site_figures.py`:

    analysis-tool/.venv/bin/python slovakia-oct-2026/scripts/build_site_figures.py

`img/{sk,en}/{turnout,blocs,winners,dual,intraday,swing}.png` — drawn from
`data/ef/` (MAI adaptation), `data/official/` and `data/trends/`.
`img/details/{lang}/{kosicky,mayors}/*.png` — copies of the analysis-tool
outputs (`analysis/ef/osk2026_k8/figures/`, `analysis/ef/oso2026/figures/`);
the ef-analyze plots are labelled in English, so the same files serve both
languages.

## Full analysis

- `slovakia-oct-2026/REPORT_statistical_fraud_analysis.md` — forensics
  (per-kraj + nationwide runs, cross-checks, limitations)
- `slovakia-oct-2026/PARADOXES.md` — voting paradoxes
- `slovakia-oct-2026/DATA_DESCRIPTION.md` — datasets and provenance
- reproduce: `analysis-tool/run_forensics_slovakia.sh`
