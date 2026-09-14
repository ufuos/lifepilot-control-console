# ==========================================================
# LifePilot Control Console
# Django + Daphne + Channels + PostgreSQL + Redis
# Python 3.12
# ==========================================================


# ==========================================================
# BUILDER STAGE
# ==========================================================

FROM python:3.12-slim AS builder


ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive


WORKDIR /app


# Build dependencies
RUN apt-get update -o Acquire::Retries=5 \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*



# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt


RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip setuptools wheel \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt




# ==========================================================
# RUNTIME STAGE
# ==========================================================

FROM python:3.12-slim AS runner


ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PATH="/opt/venv/bin:$PATH"



WORKDIR /app



# Runtime packages
RUN apt-get update -o Acquire::Retries=5 \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        netcat-openbsd \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*




# Copy virtual environment
COPY --from=builder /opt/venv /opt/venv



# Copy Django project
COPY backend/ /app/



# Create startup script
RUN printf '%s\n' \
'#!/bin/sh' \
'set -e' \
'' \
'echo "Waiting for PostgreSQL..."' \
'until nc -z ${DB_HOST:-postgres} ${DB_PORT:-5432}; do' \
'    sleep 1' \
'done' \
'echo "PostgreSQL ready"' \
'' \
'echo "Waiting for Redis..."' \
'until nc -z ${REDIS_HOST:-redis} ${REDIS_PORT:-6379}; do' \
'    sleep 1' \
'done' \
'echo "Redis ready"' \
'' \
'exec "$@"' \
> /app/entrypoint.sh \
&& chmod +x /app/entrypoint.sh




EXPOSE 8000



ENTRYPOINT ["/app/entrypoint.sh"]



CMD ["python","-m","daphne","-b","0.0.0.0","-p","8000","config.asgi:application"]