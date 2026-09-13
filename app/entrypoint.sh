#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
while ! nc -z postgres 5432; do
sleep 0.5
done
echo "PostgreSQL started"

echo "Waiting for Redis..."
while ! nc -z redis 6379; do
sleep 0.5
done
echo "Redis started"

exec "$@"
