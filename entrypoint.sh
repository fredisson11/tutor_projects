#!/bin/sh

set -e

echo "Applying database migrations..."
python /app/manage.py migrate --noinput

echo "Collecting static files..."
python /app/manage.py collectstatic --noinput

echo "Starting server..."
exec "$@"
