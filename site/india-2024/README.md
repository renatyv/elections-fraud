# India, Lok Sabha 2024 — statistical fraud check

Раздел сайта репозитория (`<repo>/site/india-2024/`): статическая одностраничка
по отчётам [india-2024/REPORT.md](../../india-2024/REPORT.md) (fraud check) и
[india-2024/PARADOXES.md](../../india-2024/PARADOXES.md) (voting paradoxes).
Без сборки и зависимостей: `index.html` + `img/<lang>/*.png`.

Языки: English, हिन्दी — переключатель в шапке, при первом входе выбирается
язык браузера (`hi`/`mr` → हिन्दी), выбор запоминается в localStorage (ключ
общий с титульной страницей `site/index.html`). Вместе с текстом подменяются
и главные иллюстрации (`img/<lang>/…`: turnout, comet, booths — строит
`india-2024/scripts/build_site_figures.py`; spoilers, transfer —
`india-2024/scripts/build_paradox_figures.py`; хинди — шрифтом Devanagari
Sangam MN). Детальные иллюстрации_methods (`img/details/en/…`) — копии
выводов `ef-analyze` (`analysis_pc/`, `analysis_up_booth_2014/`,
`analysis_booth/`), для обоих языков общие, подписи переведены.

Структура — пирамида Минто (как у Словении): вердикт + flip-вердикт про
парадоксы в хиро → ситуация (итоги, доли партий) → «Same votes, different
rules» (FPTP против большинства с таблицей трёх циклов, контрфакты блоков
NDA/INDIA, UP booth-transfer по Form 20) → результаты тестов на
манипуляцию (7 фолдаутов; главные графики размещены внутри фолдаутов) →
ограничения → данные. Особенность раздела: честно вынесенная вверх
granular-предел — booth-уровень 2024 не имеет явного electors, поэтому
вердикт формулируется «на доступных уровнях».

## Публикация на Vercel

Сайт репозитория деплоится целиком от корня `site/` — разделы-страны лежат
рядом. Статика без конфига; см. [README раздела Словении](../sloveniya-referendum-2026/README.md).
