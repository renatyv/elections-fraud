# Slovenia referendums 11.10.2026 — statistical fraud check

Раздел сайта репозитория (`<репо>/site/sloveniya-referendum-2026/`): статическая
одностраничка по отчёту
[statistical_fraud_analysis.md](../../sloveniya-referendum-2026/statistical_fraud_analysis.md).
Без сборки и зависимостей: `index.html` + `img/<lang>/*.png` (комплект графиков
на каждый язык строит `scripts/build_site_figures.py` словенского проекта из
`data/derived/volisca_all.csv`; подписи внутри картинок переведены).

Языки: Slovenščina, English, Hrvatski, Italiano, Magyar — переключатель в шапке,
при первом входе выбирается язык браузера, выбор запоминается в localStorage
(ключ общий с титульной страницей `site/index.html`); вместе с текстом
подменяются и картинки (`img/<lang>/…`).
Структура — пирамида Минто: два вердикта в «шапке»-герое (✓ нет следов
манипуляций + ⇄ найденные парадоксы) → ситуация (итоги 4 референдумов) →
методы (8 семей тестов; графики turnout/comet/cross вложены в первые три
раскрывающихся блока) → парадоксы → ограничения → данные.

## Раздел парадоксов (в составе index.html)

Единая страница включает и анализ парадоксов голосования по отчёту
[PARADOXES.md](../../sloveniya-referendum-2026/PARADOXES.md) — секция
`#paradoxes` «Same votes, different rules»: что из каталога `paradoxes.md`
проверяемо на бинарном референдуме и что показало. Подача в простых словах —
«меняются правила, а не голоса»: три карточки-вывода, таблица разрезов
(страна / 8 единиц / 88 округов / 3.083 участка) и четыре «правила» —
территориальное большинство, только день голосования, winner-take-all округа
(джерримендер), кворум 90-й статьи. Картинки —
`img/<lang>/{territory,decomposition,quorum}.png` (тоже `build_site_figures.py`).
Карточка на титульной странице ведёт на `index.html#paradoxes`; ранее
существовавшая отдельная `paradoxes.html` влита в index.html и удалена.

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
