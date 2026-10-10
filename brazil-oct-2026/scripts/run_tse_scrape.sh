#!/bin/bash
# Обёртка для запуска ОДНОГО прохода скрейпера (для cron / launchd с интервалом 15 минут).
# Запускает через uv: зависимости скрипта (httpx, rich) объявлены в PEP 723-заголовке
# tse_scrape.py и ставятся uv-ом автоматически в кэшируемое окружение.
# Аргументы пробрасываются в tse_scrape.py (см. --help).
# Пример для крона (каждые 15 минут):
#   */15 * * * * "/Users/renatyuldashev/Documents/elections analysis/brazil-oct-2026/scripts/run_tse_scrape.sh" >> "/Users/renatyuldashev/Documents/elections analysis/brazil-oct-2026/data/cron.log" 2>&1

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UV="${UV:-$HOME/.local/bin/uv}"
command -v "$UV" >/dev/null 2>&1 || UV="$(command -v uv)"
mkdir -p "$ROOT/data"
exec "$UV" run --quiet "$ROOT/scripts/tse_scrape.py" --once "$@"
