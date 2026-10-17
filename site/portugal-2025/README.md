# Portugal legislative elections 18.05.2025 — statistical fraud check

Раздел сайта репозитория (`<репо>/site/portugal-2025/`): статическая одностраничка
по отчёту [REPORT_statistical_fraud_analysis.md](../../portugal-2025/REPORT_statistical_fraud_analysis.md)
и анализу парадоксов [PARADOXES.md](../../portugal-2025/PARADOXES.md).
Без сборки и зависимостей: `index.html` + `img/<lang>/*.png` (комплект графиков на
каждый язык строит `scripts/build_site_figures.py` португальского проекта из
`data/legislativas2025_mai/results_all.csv` — freguesias, level=3; парадокс-графики
(px_rules, px_counterfactuals, px_autarquicas, px_runoff) — из
`analysis/paradoxes/metrics.json`; подписи внутри картинок переведены,
контрольные суммы сверены с метриками анализа).

Языки: Português, English — переключатель в шапке, при первом входе выбирается
язык браузера, выбор запоминается в localStorage (ключ общий с титульной
страницей `site/index.html`); вместе с текстом подменяются и картинки
(`img/<lang>/…`).
Структура — пирамида Минто: вердикт (+ карточка «те же голоса, другие правила»)
→ ситуация (итоги выборов, проценты партий) → парадоксы (те же голоса при других
правилах подсчёта) → результаты тестов обнаружения манипуляций (структура как у
Словении: сводный график каждого теста — внутри его раскрывающейся карточки,
«outliers vs neighbours» и ML объединены в одну карточку) → ограничения → данные.

## Публикация на Vercel

Сайт репозитория деплоится целиком от корня `site/` — разделы-страны лежат рядом
(`site/sloveniya-referendum-2026/`, `site/portugal-2025/`). Статика без конфига,
любой из способов — см. [README раздела Словении](../sloveniya-referendum-2026/README.md).
