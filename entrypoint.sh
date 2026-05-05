#!/bin/sh
set -e

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Starting Django development server on 0.0.0.0:8001..."
exec python manage.py runserver 0.0.0.0:8001
