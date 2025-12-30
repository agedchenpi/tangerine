FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir psycopg2-binary  # Add more deps as needed, e.g., for AI agents

CMD ["python", "some_main_script.py"]  # Placeholder; update later
