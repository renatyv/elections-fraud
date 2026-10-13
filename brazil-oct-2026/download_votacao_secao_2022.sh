#!/bin/bash
# Скачивание КОНТРОЛЬНЫХ данных: выборы Бразилии 2022 по избирательным участкам
# (1-й тур 02.10.2022, 2-й тур 30.10.2022). Источник: портал открытых данных TSE,
# датасет "resultados-2022": https://dadosabertos.tse.jus.br/dataset/resultados-2022
#
# Запуск:  bash download_votacao_secao_2022.sh          # контрольный набор (~0,5 ГБ)
#          bash download_votacao_secao_2022.sh --all    # + 27 UF-файлов (все должности, ~4 ГБ)
#
# Контрольный набор (то, на чём построен анализ 2026):
#   votacao_secao_2022_BR.zip      — президент по всем участкам страны (CSV latin-1, ";")
#   detalhe_votacao_secao_2022.zip — явка/электорат и детали подсчёта по участкам
# Строка CSV = (участок × кандидат): штат, муниципалитет, зона, секция (NR_SECAO),
# должность, кандидат, голоса; тур различается колонками NR_TURNO / DT_ELEICAO.
# UF-файлы (--all) содержат губернаторов/сенаторов/депутатов — для контроля
# президентского анализа не нужны.

set -euo pipefail

DEST="$(cd "$(dirname "$0")" && pwd)/data/votacao_secao_2022"
mkdir -p "$DEST"
BASE="https://cdn.tse.jus.br/estatistica/sead/odsele"

echo "==> Президент по участкам (национальный файл)"
curl -L -C - --fail --retry 3 -o "$DEST/votacao_secao_2022_BR.zip" \
  "$BASE/votacao_secao/votacao_secao_2022_BR.zip"

echo "==> Детали явки по участкам"
curl -L -C - --fail --retry 3 -o "$DEST/detalhe_votacao_secao_2022.zip" \
  "$BASE/detalhe_votacao_secao/detalhe_votacao_secao_2022.zip"

if [ "${1:-}" = "--all" ]; then
  echo "==> Файлы по 27 штатам (все должности)"
  UFS="AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO"
  for uf in $UFS; do
    echo "  $uf"
    curl -L -C - --fail --retry 3 -o "$DEST/votacao_secao_2022_${uf}.zip" \
      "$BASE/votacao_secao/votacao_secao_2022_${uf}.zip"
  done
fi

echo "==> Распаковка"
for z in "$DEST"/*.zip; do
  unzip -o -q "$z" -d "${z%.zip}"
done

echo "Готово. Файлы в: $DEST"
ls -lh "$DEST"
