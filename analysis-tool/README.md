# analysis-tool: election forensics

Статистические методы обнаружения фальсификаций на выборах — реализация
методов из обзора «Метод Шпилькина и другие статистические методы обнаружения
фальсификаций на выборах» (корень репозитория).

## Методы

| Модуль | Метод | Источник |
|---|---|---|
| `shpilkin` | гистограмма явки, «честное ядро», оценка аномальных голосов | Шпилькин |
| `fingerprints` | электоральные отпечатки пальцев, смесь 2D-гауссиан | Klimek et al., PNAS 2012 |
| `integer_peaks` | целочисленные пики явки/результата (МК-ноль) | Kobak et al., AOAS 2016 |
| `correlations` | 2D-корреляции явка × результат по партиям и округам | Kobak et al., arXiv:1205.0741 |
| `digit_tests` | вторая цифра (Бенфорд) и последняя цифра | Mebane 2006; Beber–Scacco 2012 |
| `neighbors` | выбросы против соседей + скачки к прошлым выборам | Myagkov–Ordeshook–Shakin 2009 |
| `anomaly_ml` | Isolation Forest, рейтинг аномальных территорий | Zhang et al., PLOS ONE 2019 |
| `selftest` | синтетическая валидация: «вброс» и «круглые явки» | — |

## Запуск

```bash
uv sync
uv run ef-analyze --data ../portugal-2025/data/legislativas2025_mai \
                  --out ../portugal-2025/analysis \
                  --title "Португалия AR 2025 (freguesias)" \
                  --controls ../portugal-2025/data/legislativas2022_mai,../portugal-2025/data/legislativas2024_mai
```

Выход: `analysis/figures/*.png`, `analysis/tables/*.csv`, `analysis/metrics.json`.

Вход — выгрузка портала MAI (`results_freguesias.csv` + `results_all_previous.csv`);
уровень анализа — приходы (freguesias), нижний доступный официальный уровень.

## Тесты

```bash
uv run pytest
```
