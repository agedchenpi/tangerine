FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir psycopg2-binary

# Updated to run the DB utils for testing
CMD ["python", "common/db_utils.py"]