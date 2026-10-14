# Portugal legislative elections 18.05.2025 — statistical fraud check

Раздел сайта репозитория (`<репо>/site/portugal-2025/`): статическая одностраничка
по отчёту [REPORT_statistical_fraud_analysis.md](../../portugal-2025/REPORT_statistical_fraud_analysis.md).
Без сборки и зависимостей: `index.html` + `img/<lang>/*.png` (комплект графиков на
каждый язык строит `scripts/build_site_figures.py` португальского проекта из
`data/legislativas2025_mai/results_all.csv` — freguesias, level=3; подписи внутри
картинок переведены, контрольные суммы сверены с `analysis/metrics.json`).

Языки: Português, English — переключатель в шапке, при первом входе выбирается
язык браузера, выбор запоминается в localStorage (ключ общий с титульной
страницей `site/index.html`); вместе с текстом подменяются и картинки
(`img/<lang>/…`).
Структура — пирамида Минто: вердикт → ситуация (итоги выборов, проценты партий)
→ три аргумента → графики и методы → ограничения → данные.

## Публикация на Vercel

Сайт репозитория деплоится целиком от корня `site/` — разделы-страны лежат рядом
(`site/sloveniya-referendum-2026/`, `site/portugal-2025/`). Статика без конфига,
любой из способов — см. [README раздела Словении](../sloveniya-referendum-2026/README.md).
