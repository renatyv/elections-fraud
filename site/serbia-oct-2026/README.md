# Serbia — parliamentary election, 25 October 2026

Static report page in **Serbian (sr, Cyrillic)** and **English (en)**. Uses the
shared country-page layout, language runtime and expandable sections. Serbian
browser locales select Serbian directly; the Croatian alias remains available
on other pages that do not support Serbian.

The latest checked trend source stamp is **26 October, 21:15 CET**, 97.60%
processed. Forensics and the legal seat projection use the separately
reconciled **16:55 CET**, 97.24%-processed capture. Results are interim.
The page is a saved analysis, not a live election-results feed.

The verdict is limited: no convergent statistical evidence of large-scale
stuffing is established. The ballot-accounting gap, fingerprint separation,
digit deviations, outlier flags and missing physical audit are disclosed.

Rebuild figures and download copies from the repository root:

```bash
MPLCONFIGDIR=/tmp/serbia-mpl analysis-tool/.venv/bin/python serbia-oct-2026/scripts/build_site_figures.py
```

- `img/{en,sr}/{margin,seats,map,comparison}.png`: localized figures from
  captured trends, paradox tables and matched-station diagnostics.
- `img/details/{en,sr}/stn2026_controlled/*.png`: original
  forensic plots; English labels in both languages, stated on the page.
- `downloads/`: English reports, seat/threshold CSVs and trend/diagnostic JSON.
  These copies are served within the existing static Vercel site.
- Full analysis: `serbia-oct-2026/REPORT_statistical_fraud_analysis.md`,
  `PARADOXES.md`, `analysis/trends/README.md`.
- Reproduce analysis: `zsh analysis-tool/run_forensics_serbia.sh`.

The homepage and sitemap link this page. No new hosting project is required.

```bash
node --test site/tests/*.test.js
python3 -m http.server 8000 --directory site
```
