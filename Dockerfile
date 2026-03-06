FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir psycopg2-binary ollama

COPY pgvector_search.py .

ENTRYPOINT ["python", "pgvector_search.py"]
