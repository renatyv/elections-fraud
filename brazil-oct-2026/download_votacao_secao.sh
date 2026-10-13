#!/bin/bash
# Скачивание данных выборов Бразилии 2026 по избирательным участкам (1-й тур, 4 октября 2026)
# Источник: портал открытых данных TSE, датасет "resultados-2026"
# https://dadosabertos.tse.jus.br/dataset/resultados-2026
#
# Запуск:  bash download_votacao_secao.sh
#
# Файлы содержат CSV (кодировка latin-1, разделитель ";"):
#   votacao_secao_2026_BR.zip     — голосование за президента по всем участкам страны
#   votacao_secao_2026_<UF>.zip   — все должности по штатам, по участкам
#   detalhe_votacao_secao_2026.zip — явка/неявка и детали подсчёта по участкам
# Строка CSV = (участок × кандидат): штат, муниципалитет, зона, номер участка (NR_SECAO),
# должность, кандидат, число голосов. Файлы огромные — открывать не в Excel.

set -euo pipefail

DEST="$(cd "$(dirname "$0")" && pwd)/data/votacao_secao"
mkdir -p "$DEST"
BASE="https://cdn.tse.jus.br/estatistica/sead/odsele"

echo "==> Национальный файл (президент, все участки)"
curl -L -C - --fail --retry 3 -o "$DEST/votacao_secao_2026_BR.zip" \
  "$BASE/votacao_secao/votacao_secao_2026_BR.zip"

echo "==> Файлы по 27 штатам (все должности)"
UFS="AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO"
for uf in $UFS; do
  echo "  $uf"
  curl -L -C - --fail --retry 3 -o "$DEST/votacao_secao_2026_${uf}.zip" \
    "$BASE/votacao_secao/votacao_secao_2026_${uf}.zip"
done

echo "==> Детали явки по участкам"
curl -L -C - --fail --retry 3 -o "$DEST/detalhe_votacao_secao_2026.zip" \
  "$BASE/detalhe_votacao_secao/detalhe_votacao_secao_2026.zip"

echo "==> Распаковка"
for z in "$DEST"/*.zip; do
  unzip -o -q "$z" -d "${z%.zip}"
done

echo "Готово. Файлы в: $DEST"
ls -lh "$DEST"
