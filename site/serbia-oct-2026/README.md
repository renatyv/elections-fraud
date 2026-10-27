# Serbia — parliamentary election, 25 October 2026

Static report page in **Serbian (sr, Cyrillic)** and **English (en)**. Uses the
shared country-page layout, language runtime and expandable sections. Serbian
browser locales select Serbian directly; the Croatian alias remains available
on other pages that do not support Serbian.

The latest checked trend source stamp is **26 October, 21:15 CET**, 97.60%
processed. Forensics and the legal seat projection use the separately
reconciled **16:55 CET**, 97.24%-processed capture. Results are interim.
The page is a saved analysis, not a live election-results feed.

The screening does not establish ballot stuffing and does not quantify what
manipulation could go undetected. Accounting gaps, imposed mixture fits,
digit deviations and outliers are disclosed. No physical audit is claimed.

Wording and charts reviewed 27 October 2026 without refreshing source data.
The fingerprint now has separate 2026 Students, 2026 incumbent and 2023
incumbent panels. Two Gaussian components are imposed in each; the legacy
`separated` field is a directional rule, not a cluster-separation test.
Other diagnostic charts show 2026 only. The Shpilkin cutoff alone comes from
2023. Digit panels show the three actual tested lists individually.

Rebuild figures and download copies from the repository root:

```bash
MPLCONFIGDIR=/tmp/serbia-mpl analysis-tool/.venv/bin/python serbia-oct-2026/scripts/build_site_figures.py
```

- `img/{en,sr}/{margin,seats,map,comparison}.png`: localized figures from
  captured trends, paradox tables and matched-station diagnostics.
- `img/details/{en,sr}/stn2026_controlled/*.png`: diagnostic plots rebuilt
  from archived data/statistics with neutral labels. English labels appear
  in both languages, stated on the page. The path name is an archive-run
  identifier; it does not imply that every plot uses 2023 observations.
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
