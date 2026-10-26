#!/bin/bash
# Download of the Brazil 2026 RUNOFF (2nd round, October 25, 2026) data at
# polling-station level. Source: TSE open-data portal, dataset "resultados-2026"
# (files "atualizado ao final de cada turno" — regenerated after each round, so
# the local 1st-round copies must NOT be resumed: download fresh).
#
# Run:  bash download_votacao_secao_T2.sh
#
# Fetches only what the presidential-runoff analysis needs:
#   votacao_secao_2026_BR.zip      — president, every station, BOTH rounds
#                                    (NR_TURNO=1 + NR_TURNO=2)
#   detalhe_votacao_secao_2026.zip — turnout/electorate details per station
# CSVs: latin-1, ";" separator. The files are huge — do not open in Excel.

set -euo pipefail

DEST="$(cd "$(dirname "$0")" && pwd)/data/votacao_secao"
mkdir -p "$DEST"
BASE="https://cdn.tse.jus.br/estatistica/sead/odsele"

echo "==> President per station (national file, both rounds)"
curl -L --fail --retry 3 -o "$DEST/votacao_secao_2026_BR.zip" \
  "$BASE/votacao_secao/votacao_secao_2026_BR.zip"

echo "==> Turnout details per station"
curl -L --fail --retry 3 -o "$DEST/detalhe_votacao_secao_2026.zip" \
  "$BASE/detalhe_votacao_secao/detalhe_votacao_secao_2026.zip"

echo "==> Unpacking"
for z in "$DEST/votacao_secao_2026_BR.zip" "$DEST/detalhe_votacao_secao_2026.zip"; do
  unzip -o -q "$z" -d "${z%.zip}"
done

echo "Done. Round 2 present if the CSVs now contain NR_TURNO=2 rows:"
awk -F';' 'NR>1 && $0 ~ /;2;/' "$DEST/votacao_secao_2026_BR/votacao_secao_2026_BR.csv" 2>/dev/null | head -2 || true
ls -lh "$DEST/votacao_secao_2026_BR.zip" "$DEST/detalhe_votacao_secao_2026.zip"
