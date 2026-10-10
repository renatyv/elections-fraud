#!/bin/sh
# Разовый проход скрейпера — рассчитан на cron с шагом 15 минут:
#   */15 * * * * "/Users/renatyuldashev/Documents/elections analysis/serbia-oct-2026/scripts/run_scraper.sh" >> "/Users/renatyuldashev/Documents/elections analysis/serbia-oct-2026/data/cron.log" 2>&1
# Для встроенного цикла вместо cron используйте:
#   python3 scripts/scrape_rik.py --loop --interval 900

DIR="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$DIR/scripts/scrape_rik.py" --levels national,regions "$@"
