#!/bin/sh
# One-shot scraper pass — designed for cron at a 15-minute step:
#   */15 * * * * "/Users/renatyuldashev/Documents/elections analysis/serbia-oct-2026/scripts/run_scraper.sh" >> "/Users/renatyuldashev/Documents/elections analysis/serbia-oct-2026/data/cron.log" 2>&1
# For the built-in loop instead of cron use:
#   python3 scripts/scrape_rik.py --loop --interval 900

DIR="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$DIR/scripts/scrape_rik.py" --levels national,regions "$@"
