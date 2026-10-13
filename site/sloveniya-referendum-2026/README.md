# Slovenia referendums 11.10.2026 — statistical fraud check

Раздел сайта репозитория (`<репо>/site/sloveniya-referendum-2026/`): статическая
одностраничка по отчёту
[ОТЧЁТ_стат_анализ_фальсификаций.md](../../sloveniya-referendum-2026/ОТЧЁТ_стат_анализ_фальсификаций.md).
Без сборки и зависимостей: `index.html` + `img/<lang>/*.png` (комплект графиков
на каждый язык строит `scripts/build_site_figures.py` словенского проекта из
`data/derived/volisca_all.csv`; подписи внутри картинок переведены).

Языки: Slovenščina, English, Hrvatski, Italiano, Magyar — переключатель в шапке,
при первом входе выбирается язык браузера, выбор запоминается в localStorage
(ключ общий с титульной страницей `site/index.html`); вместе с текстом
подменяются и картинки (`img/<lang>/…`).
Структура — пирамида Минто: вердикт → ситуация (итоги 4 референдумов) → три
аргумента → графики и методы → ограничения → данные.

## Публикация на Vercel

Сайт репозитория деплоится целиком от корня `site/` — разделы-страны лежат
рядом (`site/sloveniya-referendum-2026/`, дальше добавятся прочие).
Статика без конфига, любой из способов:

```bash
cd site
npx vercel            # из каталога site/ (прод: npx vercel --prod)
```

или drag-and-drop каталога `site/` на [vercel.com/new](https://vercel.com/new),
или импорт Git-репозитория с Root Directory = `site`.
