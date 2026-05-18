#!/bin/sh
set -e

# flask db upgrade
# flask seed-apply --path /seeds/permissions.yml # --prune

exec gunicorn --config gunicorn_config.py --log-level info --access-logfile - wsgi:app
