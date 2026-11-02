# Bulgaria — presidential runoff, 1 November 2026

English and Bulgarian report, prepared 2 November 2026, for the existing static Vercel site.
Open `index.html` through the site's HTTP preview; no build step is required.

The official table is stamped 2 November, 09:15 EET, at 100% processing.
All 12,717 numeric section protocols reconcile exactly with national candidate and
“nobody” totals. Fourteen protocols have internal balance discrepancies. Screening
covers 10,656 eligible domestic sections, with round 1 as a reference rather than a
validated honest baseline. Tail and integer tests do not establish ballot stuffing;
Yotova's second-digit flag survives Holm adjustment over four digit tests (p ≈0.010).

The three overview figures are localized in `img/en/` and `img/bg/`. Each of the ten
manipulation-detection methods has its own independent foldable and plot, localized
in `img/details/en/` and `img/details/bg/`. District charts aggregate
registers ≥100 with positive signatures independently in each round; forensic figures
use the stricter eligible sample. Each denominator and exclusion is explained on the page.
Downloads include eligible sections, exclusions, source reconciliation, eligibility,
metrics, sensitivity, the full report and a ZIP of all toolkit figures/tables.

Reproduction commands are in
`bulgaria-oct-2026/REPORT_statistical_fraud_analysis_round2.md` from the repository root.
The capture reuses its dated raw HTML cache; preserve it when collecting later updates.

Checks:

```bash
node --test site/tests/*.test.js
python3 -m unittest discover -s site/tests -p 'test_*.py'
bulgaria-oct-2026/.venv/bin/python -m unittest discover -s bulgaria-oct-2026/tests
MPLCONFIGDIR=/tmp/bulgaria-mpl analysis-tool/.venv/bin/python -m pytest analysis-tool/tests -q
```

The homepage lists the runoff first, and the sitemap includes its canonical path.
Publication is handled by the existing site's deployment workflow; this change does
not create a separate hosted Site.
