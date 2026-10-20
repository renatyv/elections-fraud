# r/dataisbeautiful — English draft

Визуализация: `site/brazil-oct-2026-round-1/img/en/control.png`. Формат согласно доступной wiki: ссылка на оригинальную страницу с визуализацией; `[OC]` и первый комментарий об источнике/инструментах. Перед публикацией проверить актуальные правила и обновлённую публичную страницу.

## Title

[OC] Polling-section turnout distributions in Brazil: the two rounds of 2022 and the first round of 2026

## Submission URL

[ANALYSIS_URL]

## First top-level comment

I made this visualization using Python, pandas, NumPy and Matplotlib.

Data: the Brazilian electoral authority’s section-level result files for [2022](https://dadosabertos.tse.jus.br/dataset/resultados-2022) and [2026](https://dadosabertos.tse.jus.br/dataset/resultados-2026).

The horizontal axis is turnout as a percentage of registered voters. The vertical axis shows the voter share on a logarithmic scale; it is not a raw count of sections. The lines compare the two rounds of 2022 with the first round of 2026. Vertical reference lines show descriptive turnout thresholds based on the 99.5th percentile.

The similar shapes are descriptive evidence. They do not establish that either election was free of manipulation, and the percentile thresholds do not classify votes as legitimate or fraudulent.

This figure is part of a larger set of statistical diagnostics. The project also fits a transfer model to aggregate section totals, but that model does not track individual voters. I welcome feedback on the visualization and on the assumptions behind the comparisons.

[Source code for the figures](https://github.com/renatyv/elections-fraud/blob/main/brazil-oct-2026-round-1/scripts/build_site_figures.py) · [Data description](https://github.com/renatyv/elections-fraud/blob/main/brazil-oct-2026-round-1/DATA_DESCRIPTION.md) · Full analysis: [ANALYSIS_URL]
