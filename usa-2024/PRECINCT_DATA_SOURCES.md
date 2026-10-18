# Поучастковые данные США, всеобщие выборы 5 ноября 2024 года

Проверка источников: 17 октября 2026 года.

**Докачанные файлы и точные статусы:** [PRECINCT_DOWNLOADS.md](PRECINCT_DOWNLOADS.md).
Каталог ниже отражает первоначальную проверку; новые проверки схем Idaho и
California и результаты массовой загрузки приведены в этом журнале. Это каталог доступности данных,
а не новый результат проверки выборов. Поиск охватывал официальный федеральный,
штатный и местный веб, MEDSL, Kaggle и исследовательские каталоги. Отсутствие
подтверждённого источника ниже **не означает отсутствия данных**.

Для Шпилькина нужна тройка на одной географии: зарегистрированные избиратели,
число участвовавших/поданных бюллетеней и голоса по кандидатам. Нельзя подменять
бюллетени суммой голосов за Конгресс: есть недействительные бюллетени и пропуски
конкретной гонки. Precinct, split precinct, ward, town и центральный пул почтовых
бюллетеней также не взаимозаменяемы. Данные регистрации должны относиться к дате
выборов и иметь определённую базу: active либо active + inactive.

## Скачанные и проверенные таблицы

| Источник | Реально проверено | Пригодность и оставшаяся работа |
|---|---|---|
| [Minnesota SOS — official precinct spreadsheet](https://sos.mn.gov/elections-voting/election-results/2024/2024-general-election-results/2024-precinct-results-spreadsheet/) | XLSX, 4 103 строки участков. `VTDID`, `REG7AM`, `EDR`, `TOTVOTING`, голоса Сената и Палаты представителей | Лучший новый кандидат для полного анализа. Определить знаменатель с регистрацией в день выборов; проверить примечания и сверить итоги. Таблица отдельно перечисляет основные партии Палаты, а не гарантированно всех малых кандидатов. |
| [Maryland SBE — updated official turnout CSV](https://elections.maryland.gov/press_room/2024_stats/PG24/Updated-Official_by_Party_and_Precinct.csv) | 13 874 строки, 1 982 ключа `LBE` + `PRECINCT`; поля `PARTY`, `POLLS`, `EARLY_VOTING`, `VBM`, `PROVISIONAL`, `ELIGIBLE_VOTERS`, округа Конгресса | Есть числитель и знаменатель по участкам. Категории регистрации партий нужно агрегировать один раз; проверить трактовку provisional и сопоставить с кандидатскими результатами. Обновлённая версия опубликована в разделе отчётов 2024 года. |
| [Kaggle — November 2024 General Election Precinct Results](https://www.kaggle.com/datasets/irakozekelly/november-2024-general-election-precinct-results) | ZIP/CSV, 489 491 строка, 2 756 различных значений `Precinct`; `CounterType` содержит `Registered Voters`, `Times Counted`, under/overvotes и кандидатов; Сенат и House districts 1, 7, 8, 9 | **Только King County, Washington**, не весь штат и не США. Описание и имя CSV говорят election-night. Для итогового анализа заменить официальной финальной версией ниже. Число строк — не число участков. |
| [King County — final precinct results](https://data.kingcounty.gov/Voting-Elections/November-2024-General-Election-Final-Precinct-Resu/uuda-pmuy) | Официальный CSV скачан: 489,491 строк, 2,756 значений Precinct; есть Registered Voters и Times Counted | Предпочтительнее копии Kaggle. Соединение с другими источниками пока не выполнено. На официальной карте явки знаменатель — active registered voters. |

Скачанные образцы находятся в игнорируемом `data/raw/`: `mn2024_official_precinct.xlsx`,
`md2024_official_precinct_turnout.csv`, `kaggle_king_county_2024.zip` и
`wa_king2024_official_final.csv`. Хеши завершённых загрузок —
`data/source_search/download_manifest.csv`. Таблицы не преобразованы в новый
общенациональный набор: сопоставление ключей и итогов ещё не выполнено.

Уже сохранённые MEDSL-архивы также содержат потенциальную тройку в Alabama,
Arizona и Iowa. Предварительно совпадают 2 084, 1 333 и 1 653 ключа соответственно;
это охват полей, **не число проверенных пригодных участков**. Например, центральные
absentee/provisional pools могут иметь нулевую регистрацию.

## Дополнительные официальные источники

Статус «публикация» означает, что найден официальный документ или ссылка;
это не подтверждение полноты всего штата и не завершённое соединение таблиц.

| Штат | Источник и детализация | Что ещё мешает готовому анализу |
|---|---|---|
| New Mexico | [Официальная таблица явки](https://electionresults.sos.nm.gov/VoterTurnoutDetails.aspx?eid=2882): ballots / eligible voters по участкам внутри округов; 2 169 reported precincts | Уточнить определение eligible voters и соединение с голосами, учитывая подавленные значения MEDSL |
| Kentucky | [General Voter Turnout by Precinct](https://elect.ky.gov/Resources/Pages/Turnout.aspx), 2024; [регистрация по участкам](https://elect.ky.gov/Resources/Pages/Registration-Statistics.aspx?lv=true) | Сам SBE предупреждает: отчёты явки неофициальные, построены после открытия реестра и могут отличаться от результатов из-за переездов/удалений. Нужна сверка с County Clerk |
| Hawaii | [2024 General Election](https://elections.hawaii.gov/2024-general-election/), Statewide Precinct Detail / Statement of Vote; [precinct report](https://elections.hawaii.gov/wp-content/results/precinct.pdf) содержит раздел PRECINCT REGISTRATION AND TURNOUT | PDF требует извлечения; URL `precinct.pdf` изменяемый, нужно проверить заголовок 2024 и зафиксировать копию |
| Oregon | [Архив SOS](https://sos.oregon.gov/elections/pages/historical-data.aspx); [Wasco certified statement of votes cast](https://records.sos.state.or.us/ORSOSWebDrawer/Record/10575034/File/document) показывает registration, ballots, turnout и кандидатов по участкам | Подтверждён пример округа, не унифицированное покрытие всех округов; PDF |
| Mississippi | [County recapitulation reports 2024](https://sos.ms.gov/elections/electionresults_aspx/elections_results_2024_county.aspx); [Union County](https://sos.ms.gov/elections/electionresults/2024General/County%20Results/Union.pdf) содержит регистрацию, бюллетени и результаты по участкам | Проверить каждый округ, извлечь PDF; один пример не доказывает наличие всех полей во всех 82 округах |
| Utah | [2024 election information](https://vote.utah.gov/2024-election-information/); [Summit County official canvass](https://vote.utah.gov/wp-content/uploads/sites/42/2024/11/G24_Canvass_Summit.pdf) содержит precinct table registration / ballots / turnout | Подтверждён округ, общештатное покрытие и единый формат не проверены |
| Kansas | [Cherokee County official precinct results](https://cherokeecountyks.gov/main/images/clerk/Full_Official_Results_by_Precinct.pdf): registered voters, ballots cast, turnout | Только подтверждённый местный пример; остальные округа отдельно |
| Washington | Помимо King County, [Island County official returns](https://www.islandcountywa.gov/DocumentCenter/View/8680/Results_110524?bidId=) содержат precinct registration / ballots / turnout | Не общештатный унифицированный набор |
| California | [Statewide Database G24](https://statewidedatabase.org/d20/g24.html): SOV, registration, voters и voting-mode files с несколькими вариантами географии | Не государственная сертификация новой сводки. SV/SR/RG/RR precincts нельзя соединять по похожим названиям; есть маскирование малых групп и замечания по Madera. Скачан SOV codebook, но наличие matched ballots во всём штате не подтверждено |
| North Carolina | [Registration snapshots](https://www.ncsbe.gov/results-data/voter-registration-data), в том числе 5 ноября 2024, с precinct; [turnout methods](https://www.ncsbe.gov/results-data/voter-turnout/2024-general-election-turnout) | Для полной тройки нужно агрегировать участие по residential precinct; early-voting site не домашний участок |
| Delaware | [2024 general results](https://elections.delaware.gov/reports/GE2024.html); [registration/participation report](https://elections.delaware.gov/voter/registrationtotals/reports/pdfs/agprpt_2024.pdf) по election district | Дата реестра и семантика voted должны быть согласованы с certified ballots |
| Massachusetts | [Statistics Hub](https://www.sec.state.ma.us/divisions/elections/research-and-statistics/statistics-hub.htm): регистрация 2024 по precinct; [ballot statistics](https://www.sec.state.ma.us/divisions/elections/research-and-statistics/early-voting-statistics.htm) | Общештатная таблица ballots подтверждена только по municipalities / method, а не precinct |
| Maine | [November 2024 enrollment](https://www.maine.gov/sos/elections-voting/voter-data/enrolled-layout-11-2024), ward/precinct active и inactive | Нужны сопоставимые precinct ballots и отдельная обработка ranked choice |
| New Hampshire | [Dover general election](https://www.dover.nh.gov/government/open-government/election-information/previous-elections/2024-general-election/) — ward results и turnout; [Keene](https://keenenh.gov/sites/default/files/2024_State_General-Presidential.pdf) — registration by ward | Подтверждены местные источники; town/ward не автоматически физический polling precinct |
| Florida | [Официальные precinct ZIP](https://dos.fl.gov/elections/data-statistics/elections-data/precinct-level-election-results/) за 2024 general | Precinct candidate votes подтверждены; matched registration / total ballots statewide в этом поиске не подтверждены |
| Pennsylvania | [Bulk election data](https://www.pa.gov/agencies/dos/resources/voting-and-elections-resources/voting-and-election-statistics/bulk-election-data.html): precinct returns | Требуется отдельная проверка registration + ballots и единых границ |
| Idaho | [Election results](https://voteidaho.gov/election-results/) публикует results XLSX и turnout XLSX; [turnout dashboard](https://voteidaho.gov/data-and-dashboards/voter-turnout/) обозначает County Turnout XLSX | Докачано: raw_stats_general.xlsx действительно содержит County, Precinct, registration и ballots; подробности в PRECINCT_DOWNLOADS.md |
| Ohio | [Текущий портал](https://data.ohiosos.gov/portal/past-election-results) и [окружные источники](https://www.ohiosos.gov/directories/local-election-results) | Старые ссылки SOS перенаправлены; точный рабочий файл precinct turnout 2024 не подтверждён. Не использовать угаданные URL |
| Virginia | [2024 official results portal](https://enr.elections.virginia.gov/results/public/Virginia/elections/2024NovemberGeneral) | Precinct results есть; точный turnout export с регистрацией не проверен |
| Missouri | [SOS precinct election results](https://www.sos.mo.gov/elections/results), general 1996–2024 | SOS определяет general turnout через наиболее популярную state race/issue; это не обязательно все ballots. Registration по precinct ещё не подтверждена |
| North Dakota | [SOS election results](https://www.sos.nd.gov/elections/election-results): precinct ballots; eligible population estimates для явки | Нет обычного сопоставимого регистрационного знаменателя; published eligible voters основан на Census 18+ и не должен подменять registration |
| Wyoming | [General results 2024](https://sos.wyo.gov/Elections/Docs/2024/2024GeneralResults.aspx?os=0): precinct summary и ballots summary | Не подтверждено, что registration и ballots доступны на одной precinct географии |

Для **Alaska, Arkansas, Colorado, Connecticut, Georgia, Illinois, Indiana,
Louisiana, Michigan, Montana, Nebraska, Nevada, New Jersey, New York,
Oklahoma, Rhode Island, South Carolina, South Dakota, Tennessee, Texas,
Vermont, West Virginia, Wisconsin и D.C.** новый готовый источник полной
поучастковой тройки в этой проверке не подтверждён. Это перечень незакрытых
задач, а не отрицательный результат о существовании данных. Candidate returns
из MEDSL сохранены; их административные уровни и исключения описаны в README.
Общештатные county totals, текущая регистрация и результаты primaries не
выдавались за precinct turnout всеобщих выборов 2024.

## Что дал Kaggle

Проверен публичный API каталога по восьми запросам: `2024 election`, `precinct`,
`us election`, `voter turnout`, `2024 precinct`, `2024 senate`, `2024 house`,
`2024 general`. Ответы поиска и метаданные выбранных наборов сохранены в
`data/source_search/kaggle_*.json`; это снимки выдачи, не полный архив Kaggle.

- **Подходит частично:** King County, описанный выше. Архив действительно скачан
  и проверен, но election-night версия не должна заменять certified final.
- [Open Elections Data: USA](https://www.kaggle.com/datasets/paultimothymooney/open-elections-data-usa)
  обновлён 2 декабря 2019 года; это историческая копия OpenElections, не набор
  итогов 2024 года. Сам upstream OpenElections следует оценивать отдельно.
- [2024 US Presidential Election, jpmiller/elections](https://www.kaggle.com/datasets/jpmiller/elections)
  описывает преимущественно опросы, кандидатов, primaries и обновления кампании;
  не подтверждён как nationwide precinct congressional turnout.
- [US 2024 Presidential Election, willianoliveiragibin](https://www.kaggle.com/datasets/willianoliveiragibin/us-2024-presidential-election)
  обновлён ещё в январе 2024 года, описание про favorability polls; не результаты
  ноябрьского голосования.
- Найденные карты 2020 года и Senate Polymarket datasets не решают задачу 2024.

**Общенациональный Kaggle-набор с precinct registration + ballots + Senate/House
votes в этом поиске не найден.** Это ограниченный поиск публичного каталога,
не доказательство, что такого набора нигде на Kaggle нет.

Дополнительные исследовательские каталоги: [MEDSL 2024 precinct returns](https://doi.org/10.7910/DVN/NYTPDU),
[Redistricting Data Hub](https://redistrictingdatahub.org/), [UF Election Lab](https://election.lab.ufl.edu/data-archive/).
Они полезны для результатов/границ, но наличие голосов не доказывает наличие
регистрации и участия. Сторонний `turnout_collection_lead.md` сохранён как
список наводок: его числа и выводы без проверки первоисточника не использовались.

## Практический следующий шаг

Сначала Minnesota и Maryland: сделать проверяемые precinct joins, сверить
state/county totals, отдельно учесть split precincts и почтовые пулы, затем
запустить Шпилькина, fingerprints, integer peaks, digits и outliers на участках.
Для Washington использовать final King County, а не Kaggle election-night.
Далее New Mexico и документальные источники Kentucky/Hawaii/Oregon/Mississippi.
Новые расчёты по этим источникам ещё не выполнялись; опубликованные графики
явки на сайте по-прежнему относятся к округам.
