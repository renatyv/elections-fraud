# Brazil, presidential 1st round 04.10.2026 — statistical fraud check

Раздел сайта репозитория (`<репо>/site/brazil-oct-2026/`): статическая одностраничка
по отчёту [ОТЧЁТ_стат_анализ_фальсификаций.md](../../brazil-oct-2026/ОТЧЁТ_стат_анализ_фальсификаций.md).
Без сборки и зависимостей: `index.html` + `img/<lang>/*.png` (комплект графиков
на каждый язык строит `brazil-oct-2026/scripts/build_site_figures.py` из
`data/secoes_presidente_2026.csv` и контрольных
`data/secoes_presidente_2022.csv`; подписи внутри картинок переведены).

Языки: Português, English, Español, Русский — переключатель в шапке, при первом
входе выбирается язык браузера, выбор запоминается в localStorage (ключ общий
с титульной страницей `site/index.html`); вместе с текстом подменяются и
картинки (`img/<lang>/…`).
Структура — пирамида Минто: вердикт → ситуация (итоги 1-го тура) → три
аргумента → графики и методы → ограничения → данные.

## Публикация на Vercel

Сайт репозитория деплоится целиком от корня `site/` — разделы-страны лежат
рядом (`site/sloveniya-referendum-2026/`, `site/brazil-oct-2026/`).
Статика без конфига, любой из способов:

```bash
cd site
npx vercel            # из каталога site/ (прод: npx vercel --prod)
```

или drag-and-drop каталога `site/` на [vercel.com/new](https://vercel.com/new),
или импорт Git-репозитория с Root Directory = `site`.
