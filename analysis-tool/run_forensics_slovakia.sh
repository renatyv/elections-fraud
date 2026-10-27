#!/bin/zsh
# Full election forensics cycle over the Slovak local elections of 24.10.2026:
# data adaptation → the standard analysis-tool pipeline (8 governor races, the
# same kraj in 2022 as the control; the mayor race nationwide) → done.
# Run:
#
#     ../analysis-tool/run_forensics_slovakia.sh   # or any cwd
#
# Output: slovakia-oct-2026/analysis/ef/<race>/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"             # analysis-tool/
SVK="$ROOT/../slovakia-oct-2026"
EF="$SVK/data/ef"

cd "$ROOT"
uv sync

echo "== 1/2 adapting data to the analysis-tool format =="
uv run python "$SVK/scripts/build_ef_csv.py"

echo "== 2/2 ef-analyze: 8 governor races (kraj-level, 2022 controls) + mayors =="
for k in 1 2 3 4 5 6 7 8; do
  echo "--- kraj $k ---"
  uv run ef-analyze \
    --data "$EF/osk2026_k$k" \
    --out "$SVK/analysis/ef/osk2026_k$k" \
    --title "Slovensko, OSK 2026 — predseda, kraj $k (okrsky)" \
    --controls "$EF/osk2022_k$k"
done
echo "--- mayors (OSO, national) ---"
uv run ef-analyze \
  --data "$EF/oso2026" \
  --out "$SVK/analysis/ef/oso2026" \
  --title "Slovensko, OSO 2026 — starostovia (okrsky)" \
  --controls "$EF/oso2022"

echo "done: $SVK/analysis/ef/"
