#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi
if ! .venv/bin/python -c 'import django, reportlab' >/dev/null 2>&1; then
  .venv/bin/python -m pip install -r requirements.txt
fi
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py cleanup_resumes
exec .venv/bin/python manage.py runserver "127.0.0.1:${1:-3001}" --noreload
