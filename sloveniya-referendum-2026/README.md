# Словения — референдумы 11.10.2026: мониторинг и анализ

Python-проект (uv) для регулярного скачивания официальных данных четырёх
общенациональных референдумов Словении 11 октября 2026 года с портала
Государственной избирательной комиссии (DVK): `https://volitve.dvk-rs.si`,
и последующего анализа трендов (pandas, matplotlib).

Контекст и разбор источников — в [report.md](report.md); официальное описание
форматов данных DVK — в [docs/Referendumi_2026_-_datoteke_s_podatki.docx](docs/Referendumi_2026_-_datoteke_s_podatki.docx).

## Быстрый старт

Нужен [uv](https://docs.astral.sh/uv/). Зависимости ставятся одной командой:

```bash
uv sync
```

Команды (консольный скрипт `sloref`):

```bash
uv run sloref fetch                 # один опрос: 4 референдума × 5 файлов
uv run sloref fetch --loop          # цикл каждые 15 минут
uv run sloref fetch --loop --interval 300 --volisca   # свой интервал + участки
uv run sloref summary               # сводная таблица текущих цифр (pandas)
uv run sloref plot                  # PNG-графики трендов → data/plots/
```

Фоновый сбор на день голосования:

```bash
nohup uv run sloref fetch --loop > /dev/null 2>&1 &
```

или cron (`crontab -e`):

```
*/15 * * * * cd "/Users/renatyuldashev/Documents/elections analysis/sloveniya-referendum-2026" && uv run sloref fetch
```

## Что скачивается

Для каждого референдума (slug: `referendum-preiskava`,
`referendum-socialna-pomoc`, `referendum-volilna-pravica-tujcev`,
`referendum-rtv-prispevek`) — файлы `udelezba.json/csv` (явка),
`rezultati.json/csv` (итоги ЗА/ПРОТИ), `izvoz.xlsx`; опционально `--volisca` —
итоги по каждому участку (`volisca_01_01.json … volisca_08_11.json`, 88 файлов
на референдум).

Нюансы формата: проценты в JSON — доли (0.4825); доля посчитанных бюллетеней =
`rezultati.glas / udelezba.slovenija.gl`; метки времени — словенское локальное
время в Zulu-форме; CSV — разделитель `;` и десятичная запятая; до публикации
данных файлы содержат только поле `datum` — это нормально.

## Куда сохраняются данные

| Путь | Содержимое |
|---|---|
| `data/latest/<референдум>/` | последние версии файлов (перезаписываются) |
| `data/raw/<дата>/<время>/<референдум>/` | снимки **только изменившихся** файлов |
| `data/timeseries.csv` | хронология общенациональных цифр (строка — при изменении цифр) |
| `data/derived/volisca_all.csv` | сводный датасет по всем участкам: 3 083 участка × 4 референдума, 12 332 строки (`scripts/build_volisca_csv.py`) |
| `data/derived/nacionalni_pregled.csv` | агрегаты DVK: страна / 8 единиц / 88 округов на каждый референдум |
| `data/ef/<референдум>/` | участки в формате analysis-tool (`results_freguesias.csv`) + журнал валидации |
| `data/wikipedia/` | данные Википедии: викитекст статьи, таблица итогов + поголосовая сверка с DVK, восстановленная динамика ночи подсчёта |
| `data/plots/` | PNG-графики трендов (`sloref plot`) |
| `analysis/` | election forensics: figures/tables/metrics.json по каждому референдуму + `analysis/cross/` |
| `data/scrape.log` | журнал опросов |

Ключи референдумов: `preiskava` (законодательный о ZPPre-B), `socialna_pomoc`,
`volilna_pravica`, `rtv_prispevek`. Каталог данных можно переопределить
переменной `SLOREF_DATA_DIR`.

## Структура проекта

```
src/sloref/
  config.py      референдумы, файлы, URL, пути
  httpclient.py  клиент httpx2: повторы, 404 = «ещё нет данных», IPv4-only
  models.py      Aggregates — общенациональные показатели из JSON
  storage.py     Store: latest/raw-снимки, timeseries.csv, журнал
  scraper.py     poll_once / run_loop
  analysis.py    pandas: загрузка трендов, сводная таблица
  plotting.py    matplotlib: PNG-графики трендов
  cli.py         argparse-CLI (fetch / summary / plot)
scripts/
  build_ef_csv.py     адаптация участков к формату analysis-tool (results_freguesias.csv)
                      + валидация (data/ef/ВАЛИДАЦИЯ.txt)
  analyze_extra.py    кросс-референдумные проверки, второй вариант (ПРОТИ),
                      досрочные точки, дубликаты протоколов
tests/           pytest: извлечение показателей, дедупликация снимков и трендов
```

## Статистический анализ фальсификаций

Election forensics по поучастковым итогам (2 984 участка × 4 референдума) —
штатный пайплайн [`analysis-tool`](../analysis-tool/); отчёт —
[ОТЧЁТ_стат_анализ_фальсификаций.md](ОТЧЁТ_стат_анализ_фальсификаций.md),
выход — `analysis/<референдум>/` и `analysis/cross/`. Полный цикл одной
командой:

```bash
../analysis-tool/run_forensics_slovenia.sh
# или по шагам:
cd ../analysis-tool && uv sync
uv run python ../sloveniya-referendum-2026/scripts/build_ef_csv.py     # адаптация + валидация
uv run ef-analyze --data ../sloveniya-referendum-2026/data/ef/preiskava \
  --out ../sloveniya-referendum-2026/analysis/preiskava \
  --title "Словения, референдум ZPPre-B 11.10.2026 (участки)" \
  --controls ../sloveniya-referendum-2026/data/ef/socialna_pomoc,../sloveniya-referendum-2026/data/ef/volilna_pravica,../sloveniya-referendum-2026/data/ef/rtv_prispevek
uv run python ../sloveniya-referendum-2026/scripts/analyze_extra.py    # кросс-проверки
```

Контрольные выборы для метода Шпилькина — три остальных референдума (те же
участки, то же распределение явки). Досрочные точки (номера ≥ 900, `upr` = 0)
в turnout-пайплайн не входят: их проверяет `analyze_extra.py` (цифровые тесты).

## Разработка

```bash
uv run pytest        # тесты
uv run ruff check .  # линтер
uv lock --upgrade    # обновить зависимости
PYTHONPATH=src uv run python scripts/build_volisca_csv.py  # сводный CSV по участкам + сверка
```
