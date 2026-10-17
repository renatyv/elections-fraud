#!/bin/bash
# Download of the Brazil 2026 election data at polling-station level (1st round, October 4, 2026)
# Source: TSE open-data portal, dataset "resultados-2026"
# https://dadosabertos.tse.jus.br/dataset/resultados-2026
#
# Run:  bash download_votacao_secao.sh
#
# The files contain CSVs (latin-1 encoding, ";" separator):
#   votacao_secao_2026_BR.zip     — president voting for every station in the country
#   votacao_secao_2026_<UF>.zip   — all offices by state, per station
#   detalhe_votacao_secao_2026.zip — turnout/abstentions and counting details per station
# A CSV row = (station × candidate): state, municipality, zone, station number (NR_SECAO),
# office, candidate, number of votes. The files are huge — do not open in Excel.

set -euo pipefail

DEST="$(cd "$(dirname "$0")" && pwd)/data/votacao_secao"
mkdir -p "$DEST"
BASE="https://cdn.tse.jus.br/estatistica/sead/odsele"

echo "==> National file (president, all stations)"
curl -L -C - --fail --retry 3 -o "$DEST/votacao_secao_2026_BR.zip" \
  "$BASE/votacao_secao/votacao_secao_2026_BR.zip"

echo "==> Files for the 27 states (all offices)"
UFS="AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO"
for uf in $UFS; do
  echo "  $uf"
  curl -L -C - --fail --retry 3 -o "$DEST/votacao_secao_2026_${uf}.zip" \
    "$BASE/votacao_secao/votacao_secao_2026_${uf}.zip"
done

echo "==> Turnout details per station"
curl -L -C - --fail --retry 3 -o "$DEST/detalhe_votacao_secao_2026.zip" \
  "$BASE/detalhe_votacao_secao/detalhe_votacao_secao_2026.zip"

echo "==> Unpacking"
for z in "$DEST"/*.zip; do
  unzip -o -q "$z" -d "${z%.zip}"
done

echo "Done. Files in: $DEST"
ls -lh "$DEST"
