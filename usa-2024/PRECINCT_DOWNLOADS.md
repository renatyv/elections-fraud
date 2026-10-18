# Докачанные участковые источники, 17 октября 2026

**Extraction follow-up, 18 October:** [RECONCILIATION.md](RECONCILIATION.md)
records extraction and reconciliation of the downloaded files, including the
PDF transcription status. The extraction backlog and check boundaries below
describe the earlier download pass.

**18 October 2026 follow-up:** [Additional current and historical turnout sources](TURNOUT_EXPANSION.md) adds Washington 2024/2020, California 2020 and Minnesota 2016, with a separate manifest and Washington join audit. The counts below describe the earlier download pass.

Сохранены **179 файлов данных и отчётов, 331 717 446 байт (331,7 MB)**,
плюс исходные страницы и таблица явки North Dakota в HTML. Это дополнительные
загрузки текущего прохода; ранее скачанные Minnesota, Maryland, финальный King
County и образец Kaggle находятся отдельно в `data/raw/`.

Исходники: `data/raw/precinct_sources/`. Каталог игнорируется Git, поэтому файлы
сейчас доступны локально, но не будут перенесены обычным `git clone`.

Полный реестр: [CSV](data/source_search/precinct_download_manifest.csv) и
[JSON](data/source_search/precinct_downloads.json). Для каждой загрузки записаны
URL, исходная страница, статус, размер, SHA-256 и ошибка при наличии. Старые
нерабочие ссылки, для которых найдены рабочие замены, имеют `superseded_by`.
Прежние четыре файла учтены в [отдельном реестре](data/source_search/download_manifest.csv).

| Штат / набор | Что скачано | Граница проверки |
|---|---|---|
| Mississippi | 84 PDF с официальной страницы: все **82 округа**, плюс исправленные Coahoma и Pike; отдельная ранее выбранная копия Union | Наличие всех ссылок проверено; схемы каждого PDF и полнота полей ещё не извлечены. Исправленные версии не складывать с исходными |
| Wyoming | 46 PDF: результаты и total ballots cast по всем **23 округам**; ZIP с тремя Excel-файлами | ZIP прошёл проверку CRC; регистрационный знаменатель ещё не подтверждён |
| Utah | **29 окружных canvass PDF** | Название файла Utah County прямо указывает `No-Precinct`; наличие округа в комплекте не означает участковую детализацию каждого документа |
| California, Statewide Database | SOV по SV и SR precinct; registration и voters по SR precinct; SOV codebook | В обоих SOV есть `TOTREG`, `TOTVOTE`, `CNG*`, `USS*`, `USP*`. SV — 51 299 строк, SR — 25 245; это строки файла, не число пригодных участков. Registration/voters — по 20 060 строк. Границы, типы строк и пропуски ещё не согласованы |
| Idaho | Два official XLSX: all races и turnout | 79 624 строки голосов, 985 ключей county/precinct; turnout — 1 030 строк **вместе с итоговыми строками**. Поля `Registration at Cutoff`, `Election Day Registrations`, `Total Registered Voters`, `Ballots Cast`, `Voter Turnout` |
| North Carolina | ZIP `voter_stats_20241105.zip`, регистрация на 5 ноября 2024 | ZIP содержит агрегатный TXT; для полной тройки всё ещё нужен precinct participation / ballots |
| Pennsylvania | Precinct election returns TXT, precinct registration TXT, county registration / vote-history XLSX | Прямые URL найдены через сторонний каталог и скачаны с официального pa.gov. County vote history нельзя выдавать за precinct ballots |
| Delaware | Official results CSV и registration/participation PDF | CSV на странице — общая сводка результатов, не подтверждён как precinct results. Precinct/election-district participation в отдельном PDF требует извлечения и сверки |
| Hawaii | Фиксированный URL Statewide Precinct Report от 6 ноября 2024, 19:30 | Загружен вместо удалённого изменяемого `precinct.pdf`; итоговую сертификацию и последующие исправления ещё проверить |
| Washington | Island County official returns PDF | Это дополнение к уже имеющемуся final King County, не весь штат |
| New Hampshire | Dover: all-wards election results и turnout; Keene: general election PDF | Town/ward geography, не автоматически физические polling precincts |
| North Dakota | HTML official precinct turnout | В сохранённой странице подтверждены заголовок 2024 General Election и дата 11/5/2024. Необычный denominator Census eligible voters нельзя смешивать с зарегистрированными избирателями |

## Что скачать не удалось

- **Kentucky:** прямые PDF precinct turnout / registration и XLS регистрации — HTTP 403.
  У регистрации по ссылке November General 2024 веб-индекс показывает заголовок
  September 2024: даже после получения файла дату знаменателя нужно уточнить.
- **Massachusetts:** оба прямых XLSX — registration и ballot statistics —
  зацикленные перенаправления, curl останавливается после 50 переходов.
- **Florida:** прямой official precinct ZIP — HTTP 403.
- **Oregon, Wasco:** архивный PDF — три таймаута соединения по 20 секунд.
- **Kansas, Cherokee:** precinct PDF — HTTP 525.
- **Maine, New Mexico, Ohio, Missouri:** найденные страницы возвращают HTTP 403;
  новые наборы данных из них не получены.
- **Virginia:** сохранена HTML-оболочка официального ENR, но выгрузка precinct
  turnout из API не получена. Это не считается скачанными участковыми данными.

Часть страниц доступна поисковому веб-инструменту, но это не означает, что удалось
скачать исходный файл. В реестре такие ошибки сохранены, а не заменены пустыми
файлами. Неудачная старая ссылка Summit исправлена ссылкой без `/sites/42/`;
Scott County скачан с официального www-хоста после ошибки основного хоста.

## Проверки

Проверены SHA-256 и размеры всех успешных загрузок, сигнатуры PDF и CRC ZIP/XLSX.
Заголовки таблиц Idaho и California сохранены в
[downloaded_table_schemas.json](data/source_search/downloaded_table_schemas.json).
PDF не распознавались и не разбирались. Новые forensic-тесты не запускались;
получение файла ещё не подтверждает корректное соединение участков или явки.
