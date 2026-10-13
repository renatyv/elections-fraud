# AGENTS.md

Репозиторий сбора и анализа официальных данных выборов: Португалия (все всенародные
выборы 2021–2026, базовый кейс — парламентские AR 18.05.2025) и октябрь-2026:
Бразилия, Болгария, Сербия, Словения. Общий инструмент статистического анализа
фальсификаций (election forensics) — `analysis-tool/`; методический обзор —
`методы_выявления_фальсификаций_выборов.md` (корень).

## Раскладка репозитория

```
portugal-2025/               — Португалия (самый большой каталог, подробно ниже):
                              11 выгрузок MAI 2021–2026, итоги CNE, законы,
                              секционные карты муниципалитетов, отчёты, парсеры
brazil-oct-2026/             — Бразилия, туры 04/25.10.2026: финальные итоги TSE по
                              секциям (data/votacao_secao, ~23 ГБ CSV; описание —
                              ОПИСАНИЕ_ДАННЫХ.md) + контрольные выборы-2022 на тех же
                              секциях (data/votacao_secao_2022, оба тура,
                              download_votacao_secao_2022.sh), статистический анализ
                              фальсификаций → ОТЧЁТ_стат_анализ_фальсификаций.md
                              (analysis/, scripts/; контроль-2022 — раздел 12)
bulgaria-oct-2026/           — Болгария, президентские 25.10.2026: съём results.cik.bg
                              (scrape_cik.py + run_every_15min.sh) → REPORT.md
serbia-oct-2026/             — Сербия, скупщина 25.10.2026: JSON-API РИК, съём каждые
                              15 минут → ОТЧЁТ.md
sloveniya-referendum-2026/   — Словения, 4 референдума 11.10.2026: uv-проект `sloref`
                              (портал DVK): финальные итоги и все 3 083 участка
                              (data/latest/<реф>/volisca_*.json, сводный
                              data/derived/volisca_all.csv), итоги Википедии с
                              поголосовой сверкой и динамика ночи подсчёта
                              (data/wikipedia/) → README.md, report.md;
                              статанализ фальсификаций поучастковых итогов
                              (2 984 участка) штатным пайплайном analysis-tool →
                              ОТЧЁТ_стат_анализ_фальсификаций.md
                              (data/ef/ — адаптация к формату MAI; analysis/ —
                              выход; run_forensics_slovenia.sh в analysis-tool);
                              графики для сайта — scripts/build_site_figures.py
site/                        — публичный сайт для Vercel (статика, деплой от
                              корня site/): титульная site/index.html + разделы
                              по странам; словенский раздел
                              site/sloveniya-referendum-2026/ — пирамида Минто,
                              5 языков (SL/EN/HR/IT/HU), подмена картинок
                              img/<lang>/ по языку → site/sloveniya-referendum-2026/README.md
analysis-tool/               — election forensics (pandas/sklearn, uv): Шпилькин,
                              отпечатки Klimek, целочисленные пики Kobak, Бенфорд/
                              последняя цифра, выбросы против соседей, Isolation
                              Forest; CLI `ef-analyze`
методы_выявления_фальсификаций_выборов.md — обзор методов, по которому написан analysis-tool
```

Каталоги стран октября-2026 — подвижные скрейперы промежуточных результатов;
детали эндпоинтов и текущий статус — в их REPORT/ОТЧЁТ/README.

## portugal-2025/

Данные парламентских выборов Португалии (AR 2025, 18.05.2025) с официальных источников.
Подробный отчёт со ссылками и методикой — `portugal-2025/ОТЧЁТ_португальские_выборы.md`.
Статистический анализ фальсификаций (метод Шпилькина и др.) —
`portugal-2025/ОТЧЁТ_стат_анализ_фальсификаций.md`; инструмент — `analysis-tool/`,
выход анализа — `portugal-2025/analysis/` (figures/, tables/, metrics.json),
секционный уровень (91 участок) — `portugal-2025/analysis_seccoes/` (раздел 13 отчёта).
Команды ниже запускать из `portugal-2025/`.

### Структура

```
ОТЧЁТ_португальские_выборы.md   — главный отчёт: источники, ссылки, итоги, проверки
ОТЧЁТ_стат_анализ_фальсификаций.md — статистические методы проверки (раздел 13 — секции)
analysis/                        — выход analysis-tool: figures/*.png, tables/*.csv,
                                   metrics.json
logs_download.txt / _v2.txt / logs_seccoes_crawl.txt — журналы скачивания/обхода
data/
  cne/                           — официальные итоги CNE: 2025_ar_mapa_resultados.xlsx/.ods
                                   (по 22 округам), 2025_ar_mapa_oficial_dr.pdf
  legislativas2025_mai/          — полная выгрузка портала MAI (eleicoes.mai.gov.pt):
                                   territory-results/*.json — результаты 3458 территорий,
                                   territory-children/*.json + territory-tree.json — дерево,
                                   results_all.csv (все уровни), results_circulos.csv /
                                   results_concelhos.csv / results_freguesias.csv,
                                   results_all_previous.csv (выборы-2024 на тех же территориях)
  <slug>_mai/ (ещё 10 каталогов) — ВСЕ всенародные выборы 2021–2026, тот же формат:
                                   presidenciais2021, autarquicas2021, legislativas2022,
                                   regionais2024 (Азоры, суффикс RA), legislativas2024,
                                   regionais-madeira2024 (суффикс RM!), europeias2024 (PE),
                                   autarquicas2025, presidenciais2026_1S, presidenciais2026_2S
  legislacao/                    — законы (правовая база подсчёта): lei14-79_LEAR
                                   (консолидированная ред. 23-07-2026), lei13-99 (реестр)
  seccoes_test/                  — образцы секционных данных: Alcácer do Sal (PDF,
                                   распарсен), AR_2025_Globais.xlsx (SGMAI, до фрегезии)
  seccoes/                       — СЕКЦИИ: обход сайтов камар + распарсенный датасет
                                   AR-2025 (см. «Секции AR-2025» ниже)
scripts/
  fetch_mai_results.py           — скачивание со СТАРОГО портала MAI (до осени 2025)
  fetch_mai_results_v2.py        — НОВЫЙ портал (осень 2025+): числовые territoryId/
                                   organId, electionId из app-settings.json (PR=3; CM=4/AM=5/AF=6)
  build_csv.py                   — сборка сводных CSV из выгрузки (оба формата портала)
  verify_downloads.py            — проверка всех выгрузок: суммы листьев vs нац. итог
  download_queue.sh / _v2.sh     — очереди последовательного скачивания коллекции
  local_receiver.py + browser_loader.js — запасной путь через браузер (при бане CDN)
  build_concelhos_sites.py       — все 308 конселью с официальными сайтами
  crawl_election_pages.py        — полуавтоматический обход разделов выборов на сайтах камар
  recatalog_seccoes.py           — пересборка data/seccoes/catalog.csv
  parse_seccoes_ar2025.py        — парсинг секционных PDF AR-2025 в единый CSV + сверка с MAI
  analyze_seccoes.py             — election forensics на 91 секции (analysis-tool, раздел 13
                                   ОТЧЁТ_стат_анализ): Шпилькин, отпечатки, пики, цифры,
                                   соседи, самотест → analysis_seccoes/
  llm_seccoes.py                 — LLM-парсинг секционных PDF через OpenRouter
                                   (uv, PEP 723; openai/gpt-6-luna, ~$0.002/PDF):
                                   PDF+промпт → CSV по участкам, rich-progress, резюм,
                                   sum-проверки; результат — <имя_pdf>.csv рядом с PDF,
                                   сводный data/seccoes/llm/llm_seccoes.csv (см. ВАЛИДАЦИЯ.md);
                                   --check — проверочный проход gemini-3.8-flash (~$0.04/файл)
                                   с клеточным сравнением (<имя_pdf>.check.csv, авто-рэтрай
                                   при усечении; готовые check-CSV пересравниваются бесплатно)
```

### Уровни данных

`GLOBAL-990000` (итог) → `LOCAL-500000` (страна) → округа (`LOCAL-0X0000`) →
муниципалитеты (`LOCAL-0XYZ00`) → приходы (`LOCAL-0XYZAB`); заграница: `FOREIGN-8*/9*`.
MAI секции не отдаёт — нижний уровень портала freguesia. По закону подсчёт идёт по
секциям (Lei 14/79, ст. 40, 100–106: итог фрегезии = сумма акт её секций), и секционные
итоги («MAPA POR SECÇÃO DE VOTO») публично выкладывают отдельные câmaras municipais.

### Секции AR-2025 (обновлено 12.10.2026)

`data/seccoes/` — результат обхода сайтов муниципалитетов: `crawl/` — сырые данные
обхода (301 отчёт), `catalog.csv` (668 публикаций — журнал обнаружения, URL всех
файлов), `КАТАЛОГ_публикаторов.md` (кто и что публикует),
`СТАТУС_скачивания_секций.md` (статус сбора, что осталось на будущие сессии).
После чистки 12.10.2026 на диске только PDF итогов AR-2025: 11 файлов в 11
каталогах (6 секционных + Gouveia + 4 по фрегезиям — Almeida, Amarante,
Valença, Vouzela); прочие выборы удалены, восстановление — по URL из catalog.csv.

Секционные карты AR-2025 нашлись у шести муниципалитетов, распарсены
(`scripts/parse_seccoes_ar2025.py`) в единый датасет `data/seccoes/ar2025_seccoes.csv`:
Benavente 27 секций, Alcácer do Sal 21, Vendas Novas 16, Ferreira do Alentejo 14,
Borba 8, Sousel 5 (скан — транскрипция, `1215_sousel/ocr/`) — итого **91 участок,
60 711 избирателей (0,66% электората)**; плюс Gouveia — 16 строк, где секции = приходы
(независимая транскрипция камары).

Сверка с MAI по всем 22 приходам: электорат, явка, бланковые, недействительные и голоса
каждого списка сходятся **до единого голоса** (журнал — `ar2025_seccoes_validation.txt`).
Единственная нестыковка — сводная строка самого PDF Ferreira do Alentejo
(«resultados corrigidos»): бланковых 31 вместо 34 (разбивка по месам и MAI дают 34).

Статистические тесты на 91 секции — `scripts/analyze_seccoes.py` (analysis-tool,
раздел 13 ОТЧЁТ_стат_анализ): явка 51,8–76,9% (0 секций выше нац. границы 78,6%),
пики явки и долей всех топ-6 чисты, дубликатов протоколов 0, арифметика строк —
0 расхождений, ML-кандидаты и выбросы соседей — крошечные секции без паттерна
(CH последняя цифра p=0,006 без профиля 0/5 — пограничное); самотест: вброс ×44
виден, рисовка ~9% протоколов при n=91 целочисленный тест не ловит.
Выход — `analysis_seccoes/`.

`data/seccoes/llm/` — LLM-транскрипция всех 11 PDF тем же форматом
(`scripts/llm_seccoes.py`, openai/gpt-6-luna, 188 строк, $0.023): 4 секционных
файла клеточно совпадают с `ar2025_seccoes.csv`, остальные сходятся с MAI по
суммам (у Amarante — пофрегезионно). Два расхождения У ИСТОЧНИКОВ (транскрипция
верна): Valença/Boivão B.E.↔E один голос, Vouzela/Cambra 1255/18/3 (PDF) против
1254/17/4 (MAI) — детали в `data/seccoes/llm/ВАЛИДАЦИЯ.md`. Batch-API OpenRouter
файлы в запросах не принимает — только прямой chat completions.

### Типовые команды

```bash
python3 scripts/fetch_mai_results.py legislativas2022 --leaf-level 3    # старый портал (докачивает)
python3 scripts/fetch_mai_results.py regionais-madeira2024 --suffix RM  # Мадейра — суффикс RM, не RA!
python3 scripts/fetch_mai_results_v2.py presidenciais2026_2S --organs 3 # новый портал (2025+)
python3 scripts/build_csv.py data/legislativas2024_mai                  # пересобрать CSV
python3 scripts/verify_downloads.py                                     # проверить все выгрузки
python3 scripts/parse_seccoes_ar2025.py                                 # секции AR-2025 + сверка с MAI
cd ../analysis-tool && uv run python ../portugal-2025/scripts/analyze_seccoes.py  # форензика 91 секции
uv run scripts/llm_seccoes.py data/seccoes/*/*.pdf                      # LLM-парсинг секционных PDF
uv run scripts/llm_seccoes.py --check data/seccoes/*/*.pdf              # + проверка gemini-3.8-flash
```

## analysis-tool

```bash
cd analysis-tool && uv sync
uv run ef-analyze \
  --data ../portugal-2025/data/legislativas2025_mai \
  --out ../portugal-2025/analysis \
  --title "Португалия AR 2025 (freguesias)" \
  --merge "votes:PPD/PSD.CDS-PP<-votes:PPD/PSD.CDS-PP.PPM" \
  --controls ../portugal-2025/data/legislativas2022_mai,../portugal-2025/data/legislativas2024_mai
uv run pytest
```

## Важное

- CDN портала MAI (Akamai) банит массовые запросы (Access Denied): темп ≤2–3 req/s,
  паузы при бане; если curl не проходит — запасной путь через браузер:
  `local_receiver.py` + `browser_loader.js` (см. отчёт).
- Файлы результатов MAI содержат и `previousResults` (прошлые выборы) — не потерять
  при обработке.
- Суммы по приходам сходятся с национальным итогом MAI; итоги CNE чуть отличаются
  (исправление по Viana do Castelo) — это норма, не ошибка данных.
- Секции покрывают лишь 0,66% электората (шесть малых конселью): сверка с MAI
  сходится до голоса, статтесты на 91 участке чисты (раздел 13), но это не база
  для общенациональных секционных выводов — самотест показывает, что при n=91
  целочисленный тест не ловит рисовку ~9% протоколов, последняя цифра имеет
  мощность лишь у трёх партий.
