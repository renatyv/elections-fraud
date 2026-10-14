#!/bin/bash
# Alternative to the --loop mode: run the scraper via cron every 15 minutes.
# Setup: crontab -e  and add the line
#   */15 * * * * /Users/renatyuldashev/Documents/elections\ analysis/bulgaria-oct-2026/run_every_15min.sh
set -u
cd "$(dirname "$0")"
exec .venv/bin/python scrape_cik.py --once "$@"
