# Bulgaria — presidential first round, 25 October 2026

Static analysis in **Bulgarian and English**, updated 27 October 2026.

The national card uses the official **100% processed** table stamped
**26 October, 15:00 EET**: Yotova 34.759%, Gyurov 31.952%, 1,521,711 listed
votes. The six historical night charts deliberately retain the ten original
snapshots ending at **98.99%**, 09:03 EET. Do not combine those endpoints.

All **12,719 numeric section protocols** reconcile candidate by candidate with
the national table. There are **22 signature/register balance discrepancies**.
The forensic screen uses **10,616 domestic sections**, excluding abroad,
domestic balance discrepancies and final registers below 100 electors.

The page reports Shpilkin-style tail sensitivity, comet/fingerprint diagnostics,
integer peaks, second/last digit tests with Holm correction, municipal outliers,
Isolation Forest and synthetic injection. **No historical control is included.**
Tail votes, mixture components and ML flags are not estimated fraudulent votes.
See the full reasoning in
`bulgaria-oct-2026/REPORT_statistical_fraud_analysis.md`.

Reproduce from the repository root (the capture needs network access):

```bash
bulgaria-oct-2026/.venv/bin/python bulgaria-oct-2026/scripts/check_official_results.py --sections
bulgaria-oct-2026/.venv/bin/python bulgaria-oct-2026/scripts/build_ef_csv.py
MPLCONFIGDIR=/tmp/bulgaria-mpl analysis-tool/.venv/bin/ef-analyze \
  --data bulgaria-oct-2026/data/ef --out bulgaria-oct-2026/analysis/ef \
  --title 'Bulgaria 2026 R1 — domestic sections, exploratory'
analysis-tool/.venv/bin/python bulgaria-oct-2026/scripts/summarize_forensics.py
MPLCONFIGDIR=/tmp/bulgaria-mpl analysis-tool/.venv/bin/python \
  bulgaria-oct-2026/scripts/build_site_figures.py
node --test site/tests/*.test.js
bulgaria-oct-2026/.venv/bin/python -m unittest discover -s bulgaria-oct-2026/tests
```

`build_site_figures.py` renders seven localized charts per language and bundles
reports, metrics, source reconciliation, eligibility, the eligible section CSV,
exclusions and a ZIP of the toolkit's English figures/tables under `downloads/`.
The dated raw HTML cache is gitignored and retained locally. Change the capture
cache directory before checking a later publication, preserving this observation.

The shared homepage and sitemap already link this section. No deployment was
performed by this update.
