# ==========================================================
# LifePilot Control Console Backend
# Multi-stage Dockerfile
# Python 3.12 + Django + Daphne + Channels
# ==========================================================


# ==========================================================
# BUILDER STAGE
# ==========================================================

FROM python:3.12-slim AS builder


ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive


WORKDIR /app


# Install build dependencies
RUN apt-get update -o Acquire::Retries=5 \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*


# Copy requirements
COPY backend/requirements.txt /app/requirements.txt


# Create virtual environment and install packages
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip setuptools wheel \
    && /opt/venv/bin/pip install --no-cache-dir -r /app/requirements.txt



# ==========================================================
# RUNNER STAGE
# ==========================================================

FROM python:3.12-slim AS runner


ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PATH="/opt/venv/bin:$PATH"


WORKDIR /app


# Runtime dependencies
RUN apt-get update -o Acquire::Retries=5 \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        netcat-openbsd \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*


# Copy Python environment
COPY --from=builder /opt/venv /opt/venv


# Copy Django project
COPY backend /app


# Create startup script
RUN printf '#!/bin/sh\n\
set -e\n\
\n\
echo "Waiting for PostgreSQL ($DB_HOST:$DB_PORT)..."\n\
while ! nc -z $DB_HOST $DB_PORT; do\n\
    sleep 1\n\
done\n\
echo "PostgreSQL started"\n\
\n\
echo "Waiting for Redis ($REDIS_HOST:$REDIS_PORT)..."\n\
while ! nc -z $REDIS_HOST $REDIS_PORT; do\n\
    sleep 1\n\
done\n\
echo "Redis started"\n\
\n\
exec "$@"\n' > /app/entrypoint.sh \
&& chmod +x /app/entrypoint.sh



EXPOSE 8000


ENTRYPOINT ["/app/entrypoint.sh"]


CMD [
    "python",
    "-m",
    "daphne",
    "-b",
    "0.0.0.0",
    "-p",
    "8000",
    "config.asgi:application"
]