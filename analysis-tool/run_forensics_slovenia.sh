#!/bin/zsh
# Full election forensics cycle over the four Slovenia referendums of 11.10.2026:
# data adaptation → the standard analysis-tool pipeline (4 referendums, the
# other three as controls) → cross-checks. Run:
#
#     ../analysis-tool/run_forensics_slovenia.sh   # or any cwd
#
# Output: sloveniya-referendum-2026/analysis/<referendum>/ and analysis/cross/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"             # analysis-tool/
SLO="$ROOT/../sloveniya-referendum-2026"
EF="$SLO/data/ef"

cd "$ROOT"
uv sync

echo "== 1/3 adapting data to the analysis-tool format =="
uv run python "$SLO/scripts/build_ef_csv.py"

echo "== 2/3 ef-analyze for each referendum (controls — the other three) =="
declare -a REFS=(preiskava socialna_pomoc volilna_pravica rtv_prispevek)
declare -A TITLE=(
  [preiskava]="Slovenia, ZPPre-B referendum 11.10.2026 (precincts)"
  [socialna_pomoc]="Slovenia, social welfare referendum 11.10.2026 (precincts)"
  [volilna_pravica]="Slovenia, voting rights referendum 11.10.2026 (precincts)"
  [rtv_prispevek]="Slovenia, RTV contribution referendum 11.10.2026 (precincts)"
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

echo "== 3/3 cross-referendum checks, second variant, early-voting points =="
uv run python "$SLO/scripts/analyze_extra.py"

echo "done: $SLO/analysis/"
