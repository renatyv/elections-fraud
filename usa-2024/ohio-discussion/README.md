# Ohio Senate 2024: discussion packet

Start with [REPORT.md](REPORT.md) or the [six-page PDF](output/pdf/ohio_senate_discussion.pdf). The report is in English for researchers and journalists.

The packet includes aggregated precinct returns, second-digit frequencies, the complete multiple-testing family, provenance, two figures and reproduction scripts. No personal voter data is included.

## Reproduce

From this directory, using Python 3 with numpy, pandas, scipy and matplotlib:

```bash
python build_plots.py
```

This reruns the Ohio statistic and 20,000 fitted-lognormal simulations, checks the published result and both BH adjustments, then rebuilds figures and summary files. For the PDF, with reportlab installed:

```bash
python build_pdf.py
```

The reference scripts under data/ preserve the original repository implementation for inspection; they are not standalone entry points. The source XLSX is linked and checksum-identified rather than bundled. The finding is model-dependent and does not establish election fraud or a changed winner.
