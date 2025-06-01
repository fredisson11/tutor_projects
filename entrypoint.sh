#!/bin/sh

set -e

# 🔧 Replace __SPACE__ with spaces
export EMAIL_HOST_PASSWORD=$(python3 -c "import os; print(os.environ['EMAIL_HOST_PASSWORD'].replace('__SPACE__', ' '))")

# Uncomment for verification of the EMAIL_HOST_PASSWORD value in the pod logs.
# echo "[DEBUG] EMAIL_HOST_PASSWORD after replace: >>>$EMAIL_HOST_PASSWORD<<<"

echo "Applying database migrations..."
python /app/manage.py migrate --noinput

echo "Collecting static files..."
python /app/manage.py collectstatic --noinput

echo "Starting server..."
exec "$@"
