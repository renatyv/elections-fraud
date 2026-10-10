#!/bin/bash
# Альтернатива режиму --loop: запуск скрейпера по cron каждые 15 минут.
# Установка: crontab -e  и добавить строку
#   */15 * * * * /Users/renatyuldashev/Documents/elections\ analysis/bulgaria-oct-2026/run_every_15min.sh
set -u
cd "$(dirname "$0")"
exec .venv/bin/python scrape_cik.py --once "$@"
