FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y curl gnupg lsb-release && \
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/postgresql-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    apt-get update && apt-get install -y cron postgresql-client-18 && rm -rf /var/lib/apt/lists/*

# Install dependencies first (better caching)
COPY requirements/base.txt /app/requirements/base.txt
RUN pip install --no-cache-dir -r requirements/base.txt

# Copy application code
COPY . /app

# Create log directory with proper permissions
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import psycopg2; import os; conn = psycopg2.connect(os.getenv('DB_URL')); conn.close()" || exit 1

# Make entrypoint script executable
RUN chmod +x /app/scripts/entrypoint.sh

# Use entrypoint to start cron daemon and apply crontab
ENTRYPOINT ["/app/scripts/entrypoint.sh"]