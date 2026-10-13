#!/bin/zsh
# Полный цикл election forensics по четырём референдумам Словении 11.10.2026:
# адаптация данных → штатный пайплайн analysis-tool (4 референдума, остальные
# три как контроля) → кросс-проверки. Запуск:
#
#     ../analysis-tool/run_forensics_slovenia.sh   # или любой cwd
#
# Выход: sloveniya-referendum-2026/analysis/<референдум>/ и analysis/cross/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"          # analysis-tool/
SLO="$ROOT/../sloveniya-referendum-2026"
EF="$SLO/data/ef"

cd "$ROOT"
uv sync

echo "== 1/3 адаптация данных в формат analysis-tool =="
uv run python "$SLO/scripts/build_ef_csv.py"

echo "== 2/3 ef-analyze по каждому референдуму (контроль — остальные три) =="
declare -a REFS=(preiskava socialna_pomoc volilna_pravica rtv_prispevek)
declare -A TITLE=(
  [preiskava]="Словения, референдум ZPPre-B 11.10.2026 (участки)"
  [socialna_pomoc]="Словения, референдум о соцпомощи 11.10.2026 (участки)"
  [volilna_pravica]="Словения, референдум об избирательном праве 11.10.2026 (участки)"
  [rtv_prispevek]="Словения, референдум о взносе RTV 11.10.2026 (участки)"
)
for ref in $REFS; do
  controls=""
  for other in $REFS; do
    [[ "$other" != "$ref" ]] && controls+="$EF/$other,"
  done
  echo "--- $ref ---"
  uv run ef-analyze \
    --data "$EF/$ref" \
    --out "$SLO/analysis/$ref" \
    --title "${TITLE[$ref]}" \
    --controls "${controls%,}"
done

echo "== 3/3 кросс-референдумные проверки, второй вариант, досрочные точки =="
uv run python "$SLO/scripts/analyze_extra.py"

echo "готово: $SLO/analysis/"
