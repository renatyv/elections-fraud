# Brazil, presidential 1st round 04.10.2026 — statistical fraud check

Раздел сайта репозитория (`<репо>/site/brazil-oct-2026-round-1/`): статическая одностраничка
по отчёту [REPORT_statistical_fraud_analysis.md](../../brazil-oct-2026-round-1/REPORT_statistical_fraud_analysis.md).
Без сборки и зависимостей: `index.html` + `img/<lang>/*.png` (комплект графиков
на каждый язык строит `brazil-oct-2026-round-1/scripts/build_site_figures.py` из
`data/secoes_presidente_2026.csv` и контрольных
`data/secoes_presidente_2022.csv`; подписи внутри картинок переведены).

Языки: Português, English, Español, Русский — переключатель в шапке, при первом
входе выбирается язык браузера, выбор запоминается в localStorage (ключ общий
с титульной страницей `site/index.html`); вместе с текстом подменяются и
картинки (`img/<lang>/…`).
Структура — пирамида Минто: вердикт (+ карточка парадоксов) → ситуация
(итоги 1-го тура) → парадоксы голосования (`#paradoxes`: раскол блока,
переносы 2022, прогноз 2-го тура, дезертирство — по
[PARADOXES.md](../../brazil-oct-2026-round-1/PARADOXES.md)) → результаты тестов
на манипуляции (графики — внутри раскрывающихся карточек) → ограничения →
данные.

## Публикация на Vercel

Сайт репозитория деплоится целиком от корня `site/` — разделы-страны лежат
рядом (`site/sloveniya-referendum-2026/`, `site/brazil-oct-2026-round-1/`).
Статика без конфига, любой из способов:

```bash
cd site
npx vercel            # из каталога site/ (прод: npx vercel --prod)
```

или drag-and-drop каталога `site/` на [vercel.com/new](https://vercel.com/new),
или импорт Git-репозитория с Root Directory = `site`.
