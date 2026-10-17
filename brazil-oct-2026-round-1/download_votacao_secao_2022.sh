#!/bin/bash
# Download of the CONTROL data: Brazil 2022 election at polling-station level
# (1st round 02.10.2022, 2nd round 30.10.2022). Source: TSE open-data portal,
# dataset "resultados-2022": https://dadosabertos.tse.jus.br/dataset/resultados-2022
#
# Run:  bash download_votacao_secao_2022.sh          # control set (~0.5 GB)
#       bash download_votacao_secao_2022.sh --all    # + 27 UF files (all offices, ~4 GB)
#
# Control set (what the 2026 analysis is built on):
#   votacao_secao_2022_BR.zip      — president for every station in the country (CSV latin-1, ";")
#   detalhe_votacao_secao_2022.zip — turnout/electorate and counting details per station
# A CSV row = (station × candidate): state, municipality, zone, section (NR_SECAO),
# office, candidate, votes; the round is distinguished by the NR_TURNO / DT_ELEICAO columns.
# The UF files (--all) contain governors/senators/deputies — not needed for the
# president analysis control.

set -euo pipefail

DEST="$(cd "$(dirname "$0")" && pwd)/data/votacao_secao_2022"
mkdir -p "$DEST"
BASE="https://cdn.tse.jus.br/estatistica/sead/odsele"

echo "==> President per station (national file)"
curl -L -C - --fail --retry 3 -o "$DEST/votacao_secao_2022_BR.zip" \
  "$BASE/votacao_secao/votacao_secao_2022_BR.zip"

echo "==> Turnout details per station"
curl -L -C - --fail --retry 3 -o "$DEST/detalhe_votacao_secao_2022.zip" \
  "$BASE/detalhe_votacao_secao/detalhe_votacao_secao_2022.zip"

if [ "${1:-}" = "--all" ]; then
  echo "==> Files for the 27 states (all offices)"
  UFS="AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO"
  for uf in $UFS; do
    echo "  $uf"
    curl -L -C - --fail --retry 3 -o "$DEST/votacao_secao_2022_${uf}.zip" \
      "$BASE/votacao_secao/votacao_secao_2022_${uf}.zip"
  done
fi

echo "==> Unpacking"
for z in "$DEST"/*.zip; do
  unzip -o -q "$z" -d "${z%.zip}"
done

echo "Done. Files in: $DEST"
ls -lh "$DEST"
