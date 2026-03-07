#!/usr/bin/env python3
"""
LLM enrichment for meta_medicaments.

Generates two AI fields for every non-deleted row:
  ai_description  — technical pharmacological text (for professional searches)
  ai_tags         — colloquial terms and use cases (for patient searches)

Usage:
  docker compose --profile tools run --rm pgvector-search llm_enrich.py

Requirements:
  ollama pull llama3.2   (run once in the ollama container)
"""

import os
import re
import threading
import psycopg2
import ollama
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_DSN = os.environ.get(
    "DATABASE_URL",
    "host=localhost dbname=postgres user=postgres password=postgres port=5432",
)
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL = "llama3.2"
BATCH_SIZE = 10
MAX_WORKERS = 3

_client = ollama.Client(host=OLLAMA_HOST)

PROMPT_DESCRIPTION = """\
Você é um farmacêutico especialista. Com base no nome e composição abaixo, escreva em português um parágrafo técnico-farmacêutico (máximo 120 palavras) cobrindo classe terapêutica, mecanismo de ação, indicações clínicas e contraindicações principais. Responda apenas com o parágrafo, sem títulos nem marcadores.

Medicamento: {name}
Composição: {composition}
"""

PROMPT_TAGS = """\
Você é um farmacêutico especialista. Com base no nome e composição abaixo, liste em português termos separados por vírgula que um paciente usaria para buscar este medicamento: nomes populares da doença tratada, sintomas, situações de uso cotidiano, perfis de paciente. Responda apenas com os termos separados por vírgula, sem frases, sem títulos, sem marcadores.

Medicamento: {name}
Composição: {composition}
"""


def _generate(prompt: str) -> str:
    response = _client.generate(model=LLM_MODEL, prompt=prompt, options={"num_predict": 200})
    return response["response"].strip()


def enrich_row(name: str, composition: str) -> tuple[str, str]:
    name = name or ""
    composition = composition or ""
    description = _generate(PROMPT_DESCRIPTION.format(name=name, composition=composition))
    tags_raw = _generate(PROMPT_TAGS.format(name=name, composition=composition))
    # Normalize bullet points to comma-separated just in case
    tags_cleaned = re.sub(r"[\•\-\*]\s*", "", tags_raw)
    tags = ", ".join(t.strip() for t in re.split(r"[,\n]+", tags_cleaned) if t.strip())
    return description, tags


def enrich(conn):
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, name, composition
        FROM meta_medicaments
        WHERE is_deleted = false
          AND (ai_description IS NULL OR ai_tags IS NULL)
        ORDER BY id
        """
    )
    rows = cur.fetchall()

    if not rows:
        print("All rows already enriched.")
        return

    total = len(rows)
    print(f"Enriching {total} rows with {LLM_MODEL} (workers={MAX_WORKERS})…")

    cache: dict[tuple[str, str], tuple[str, str]] = {}
    cache_lock = threading.Lock()

    def process_row(row):
        row_id, name, composition = row
        key = (name or "", composition or "")
        with cache_lock:
            if key in cache:
                return row_id, name, cache[key], True
        result = enrich_row(name, composition)
        with cache_lock:
            cache.setdefault(key, result)
        return row_id, name, result, False

    completed = 0
    batch = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_row, row): row for row in rows}
        for future in as_completed(futures):
            completed += 1
            try:
                row_id, name, (description, tags), cached = future.result()
            except Exception as e:
                row = futures[future]
                print(f"  [{completed}/{total}] id={row[0]} — LLM error: {e}")
                continue

            cur.execute(
                """
                UPDATE meta_medicaments
                SET ai_description = %s,
                    ai_tags = %s,
                    embedding = NULL
                WHERE id = %s
                """,
                (description, tags, row_id),
            )

            batch += 1
            if batch % BATCH_SIZE == 0:
                conn.commit()
                print(f"  committed batch at row {completed}/{total}")

            suffix = " (cached)" if cached else ""
            print(f"  [{completed}/{total}] id={row_id} — {name}{suffix}")

    conn.commit()
    print("Enrichment complete. Run backfill to embed the updated rows.")
    cur.close()


def main():
    conn = psycopg2.connect(DB_DSN)
    try:
        enrich(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
