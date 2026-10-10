#!/bin/bash
# Последовательное скачивание выборок за предыдущие годы с портала MAI.
# Каждый вызов fetch_mai_results.py докачиваемый: уже скачанные файлы пропускаются.
cd "$(dirname "$0")/.." || exit 1
LOG=logs_download.txt
: > "$LOG"
run() {  # run <slug> <suffix>
  echo "=== [$(date +%H:%M:%S)] START $1 (suffix $2)" >> "$LOG"
  python3 scripts/fetch_mai_results.py "$1" --suffix "$2" --leaf-level 3 >> "$LOG" 2>> "$LOG" && \
    echo "=== [$(date +%H:%M:%S)] DONE  $1" >> "$LOG" || \
    echo "=== [$(date +%H:%M:%S)] FAIL  $1" >> "$LOG"
}
run legislativas2024  AR   # 10.03.2024 парламент
run legislativas2022  AR   # 30.01.2022 парламент
run europeias2024     PE   # 09.06.2024 европарламент
run presidenciais2021 PR   # 24.01.2021 президент
run regionais2024     RA   # 04.02.2024 Азорские острова (суффикс RA)
run regionais-madeira2024 RM # 26.05.2024 Мадейра (суффикс RM!)
run autarquicas2021   CM   # 26.09.2021 муниципалитеты (камара)
echo "=== [$(date +%H:%M:%S)] QUEUE FINISHED" >> "$LOG"
