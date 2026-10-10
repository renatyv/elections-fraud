# AGENTS.md

Данные парламентских выборов Португалии (AR 2025, 18.05.2025) с официальных источников.
Подробный отчёт со ссылками и методикой — `ОТЧЁТ_португальские_выборы.md`.

## Структура

```
ОТЧЁТ_португальские_выборы.md   — главный отчёт: источники, ссылки, итоги, проверки
AGENTS.md                        — этот файл
data/
  cne/                           — официальные итоги CNE:
                                   2025_ar_mapa_resultados.xlsx/.ods (по 22 округам),
                                   2025_ar_mapa_oficial_dr.pdf (карта-официальный документ)
  legislativas2025_mai/          — полная выгрузка портала MAI (eleicoes.mai.gov.pt):
                                   territory-results/*.json   — результаты 3458 территорий
                                   territory-children/*.json  — дерево территорий
                                   territory-tree.json        — собранное дерево (parent/level/name)
                                   results_all.csv            — сводный датасет (все уровни)
                                   results_circulos.csv / results_concelhos.csv /
                                   results_freguesias.csv     — по округам/муниципалитетам/приходам
                                   results_all_previous.csv   — те же территории, выборы-2024
  <slug>_mai/ (ещё 10 каталогов) — ВСЕ всенародные выборы 2021–2026, тот же формат:
                                   presidenciais2021, autarquicas2021, legislativas2022,
                                   regionais2024 (Азоры, суффикс RA), legislativas2024,
                                   regionais-madeira2024 (суффикс RM!), europeias2024 (PE),
                                   autarquicas2025, presidenciais2026_1S, presidenciais2026_2S
                                   (см. раздел «Выборы предыдущих лет» в отчёте)
  legislacao/                   — официальные тексты законов (правовая база подсчёта):
                                   lei14-79_LEAR_consolidada_CNE_2026-07.pdf (Lei 14/79,
                                   выборы в AR, консолидированная ред. 23-07-2026),
                                   lei13-99_recenseamento_consolidada_CNE_2024-02.pdf
                                   (Lei 13/99, регистрация избирателей)
  seccoes_test/                 — образцы секционных данных (AR-2025):
                                   Alcácer do Sal MAPA POR SECÇÃO DE VOTO (PDF, распарсен),
                                   AR_2025_Globais.xlsx (официальная таблица SGMAI, до фрегезии)
scripts/
  fetch_mai_results.py           — скачивание выборов со СТАРОГО портала (до осени 2025)
  fetch_mai_results_v2.py        — НОВЫЙ портал (осень 2025+): числовые territoryId/organId,
                                   electionId из app-settings.json (PR=3; CM=4/AM=5/AF=6)
  build_csv.py                   — сборка сводных CSV из выгрузки (оба формата портала)
  verify_downloads.py            — проверка всех выгрузок: суммы листьев vs национальный итог
  download_queue.sh / _v2.sh     — очереди последовательного скачивания (как качали коллекцию)
  local_receiver.py              — локальный HTTP-приёмник (запасной путь)
  browser_loader.js              — лоадер для консоли браузера (запасной путь)
```

## Уровни данных

`GLOBAL-990000` (итог) → `LOCAL-500000` (страна) → округа (`LOCAL-0X0000`) →
муниципалитеты (`LOCAL-0XYZ00`) → приходы (`LOCAL-0XYZAB`); заграница: `FOREIGN-8*/9*`.
По секциям (участкам) официальных данных нет — нижний уровень freguesia.
Подсчёт при этом по закону идёт по секциям (Lei 14/79, ст. 40, 100–106; раздел
«Правовая база подсчёта голосов» в отчёте): итог фрегезии = сумма акт её секций.
Секционные данные публично публикуют câmaras municipais («MAPA POR SECÇÃO DE VOTO»,
проверено на AR-2025: Alcácer do Sal — живой PDF; Сабугал — все выборы с 2017) —
каталог ссылок и методика сбора: раздел «Данные по участкам (secções): где и что качать» в отчёте.

## Типовые команды

```bash
python3 scripts/fetch_mai_results.py legislativas2022 --leaf-level 3    # старый формат (докачивает)
python3 scripts/fetch_mai_results.py regionais-madeira2024 --suffix RM  # Мадейра — суффикс RM, не RA!
python3 scripts/fetch_mai_results_v2.py presidenciais2026_2S --organs 3 # новый формат (2025+)
python3 scripts/build_csv.py data/legislativas2024_mai                  # пересобрать CSV
python3 scripts/verify_downloads.py                                     # проверить все выгрузки
```

## Важное

- CDN портала (Akamai) банит массовые запросы (Access Denied): темп ≤2–3 req/s,
  паузы при бане; если curl не проходит — запасной путь через браузер:
  `local_receiver.py` + `browser_loader.js` (см. отчёт).
- Файлы результатов содержат и `previousResults` (прошлые выборы) — не потерять при обработке.
- Суммы по приходам сходятся с национальным итогом MAI; итоги CNE чуть отличаются
  (исправление по Viana do Castelo) — это норма, не ошибка данных.
