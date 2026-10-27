#!/bin/zsh
# Rebuild Serbia's archived analysis without fetching or replacing source data.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SRB="$ROOT/../serbia-oct-2026"
EF="$SRB/data/ef"
cd "$ROOT"
uv sync
uv run python "$SRB/scripts/build_ef_csv.py"
uv run python "$SRB/scripts/build_ef_csv.py" --grain stations
uv run python "$SRB/scripts/analyze_trends.py"
uv run python "$SRB/scripts/analyze_paradoxes.py"
uv run ef-analyze --data "$EF/serbia2023_mun" --out "$SRB/analysis/ef/mun2023_control" --title "Serbia 2023 — municipalities (ballots cast)"
uv run ef-analyze --data "$EF/serbia2026_mun" --out "$SRB/analysis/ef/mun2026" --title "Serbia 2026 — municipalities (ballots cast)" --controls "$EF/serbia2023_mun" --prev-party 'votes:Vučić'
uv run ef-analyze --data "$EF/serbia2023_stn" --out "$SRB/analysis/ef/stn2023_control" --title "Serbia 2023 — polling stations (ballots cast)"
uv run ef-analyze --data "$EF/serbia2026_stn" --out "$SRB/analysis/ef/stn2026" --title "Serbia 2026 — polling stations (ballots cast)"
uv run ef-analyze --data "$EF/serbia2026_stn" --out "$SRB/analysis/ef/stn2026_controlled" --title "Serbia 2026 — processed territorial stations, 16:55 CET" --controls "$EF/serbia2023_stn"
uv run python "$SRB/scripts/analyze_diagnostics.py"
uv run pytest "$ROOT/tests" "$SRB/tests" -q
