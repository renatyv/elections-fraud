# United States — Senate and House 2024

The English-only `index.html` presents one integrated analysis: findings,
statistical tests, Minnesota hand review, coverage, vote-splitting bounds,
limitations, and sources. The main text uses plain English. Charts, statistical methods, detailed audit
tables, and references are collapsed by default; historical
snapshots remain available as Markdown downloads. Shared styling is in
`../styles.css`. Serve `site/` with any static HTTP server.

## Updating the analysis

The narrative is maintained by hand. Its `report-layout: editorial` meta tag
prevents the report builders from restoring dated update sections or overwriting
the page. After regenerating data, reconcile the headline counts, method results,
ten-race table and limitations with `analysis/expanded/summary.json` and the reports.

From the repository root, use the analysis-tool Python runtime to run
`usa-2024/scripts/expanded_analysis.py`, `refine_digit_nulls.py`, then
`build_expanded_report.py`. See [EXPANDED_REPORT.md](EXPANDED_REPORT.md) for the
full commands, source limits and reproduction order.

`build_precinct_report.py` rebuilds the archived precinct report;
`build_site_figures.py` rebuilds figures and copies tables and provenance.
These downloads retain their snapshot dates. No raw election archives are bundled.

Run the page and builder-preservation checks with:

```sh
python3 -m unittest discover -s site/tests -p 'test_usa_page.py'
```

Rebuild the Ohio explanation and second-digit figures with
`analysis-tool/.venv/bin/python usa-2024/scripts/build_ohio_figures.py`
from the repository root. This uses the retained expanded audit and checks the
8,798-count sample and test statistic against the published digit results.
