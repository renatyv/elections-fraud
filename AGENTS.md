
```
portugal-2025/               — Португалия, legislativas 2021–2026: 11 выгрузок MAI,
                              итоги CNE, законы, секционные карты муниципалитетов,
                              отчёты, парсеры
brazil-oct-2026/             — Бразилия, туры 04/25.10.2026: итоги TSE по секциям
                              (data/votacao_secao, ~23 ГБ CSV; описание —
                              ОПИСАНИЕ_ДАННЫХ.md) + контроль-2022 на тех же секциях
                              (data/votacao_secao_2022); статанализ фальсификаций →
                              ОТЧЁТ_стат_анализ_фальсификаций.md (контроль-2022 —
                              раздел 12)
bulgaria-oct-2026/           — Болгария, президентские 25.10.2026: съём results.cik.bg
                              (scrape_cik.py + run_every_15min.sh) → REPORT.md
serbia-oct-2026/             — Сербия, скупщина 25.10.2026: JSON-API РИК, съём каждые
                              15 минут → ОТЧЁТ.md
sloveniya-referendum-2026/   — Словения, 4 референдума 11.10.2026: uv-проект `sloref`
                              (портал DVK): итоги и все 3 083 участка, сверка с
                              Википедией и динамика ночи подсчёта → README.md,
                              report.md; статанализ фальсификаций (2 984 участка,
                              пайплайн analysis-tool) →
                              ОТЧЁТ_стат_анализ_фальсификаций.md; графики для
                              сайта — scripts/build_site_figures.py
india-2024/                  — Индия, Лок Сабха-2024: uv-проект `india2024`;
                              результаты по округам (data/results_pc), явка
                              (data/turnout), Form20 Уттар-Прадеш (data/form20),
                              wayback-снимки (data/wayback); контроли 2014/2019
                              (data/control_*); scripts/ — скачивание и разбор
site/                        — публичный сайт для Vercel (статика, деплой от
                              корня site/): титульная site/index.html + разделы
                              по странам — пирамида Минто, подмена картинок
                              img/<lang>/ по языку: словенский (5 языков
                              SL/EN/HR/IT/HU), бразильский (PT/EN/ES/RU),
                              португальский (PT/EN) → README.md в каждом разделе
analysis-tool/               — election forensics (pandas/sklearn, uv): Шпилькин,
                              отпечатки Klimek, целочисленные пики Kobak, Бенфорд/
                              последняя цифра, выбросы против соседей, Isolation
                              Forest; CLI `ef-analyze`
методы_выявления_фальсификаций_выборов.md — обзор методов, по которому написан analysis-tool
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

# Good software architecture principles

- reverse call: a module uses a its parent
- parallel call: a module uses another one on the same level
- downstream call: a module uses a function or a module which is at least 2 levels below it
- functions should use simple data classes in and simple data classes out.
- Side effects should be encapsulated in a separate modules: one can read from the database, but not directly change it
- module should not save history of calls to control its operations
- module only does one thing, completely
- major decision making should be pushed to the highest possible level. Typically, the main decisions are made by the head module (at the first level). This head module serves as a succinct "summary" of the entire program.
- a lower-level module should not make decisions for higher-level modules. Therefore, a module shouldn't perform actions that directly alter the program's operation.
- errors should bubble up until level where the control flow descition can be made

# Парсинг PDF и сканов

Для парсинга PDF используй openrouter + [GPT-luna-latest](https://openrouter.ai/~openai/gpt-luna-latest), reasoning=off или reasoning=low если качество страдает.
Ключ `OPENROUTER_KEY=...` лежит  `.env`. Его сам не читай никогда, но можешь использовать в скриптах.
