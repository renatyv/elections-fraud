#!/bin/bash
# Download of the new portal-format elections (2025+) — run AFTER download_queue.sh,
# so as not to double the request rate to the CDN (Akamai bans).
cd "$(dirname "$0")/.." || exit 1
LOG=logs_download_v2.txt
: > "$LOG"
run() {  # run <slug> <organs>
  echo "=== [$(date +%H:%M:%S)] START $1 (organs $2)" >> "$LOG"
  python3 scripts/fetch_mai_results_v2.py "$1" --organs "$2" --leaf-level 3 >> "$LOG" 2>&1 && \
    echo "=== [$(date +%H:%M:%S)] DONE  $1" >> "$LOG" || \
    echo "=== [$(date +%H:%M:%S)] FAIL  $1" >> "$LOG"
}
run presidenciais2026_1S 3   # 18.01.2026, 1st round
run presidenciais2026_2S 3   # 08.02.2026, 2nd round
run autarquicas2025      4   # 12.10.2025, municipalities (câmara CM)
echo "=== [$(date +%H:%M:%S)] V2 QUEUE FINISHED" >> "$LOG"
