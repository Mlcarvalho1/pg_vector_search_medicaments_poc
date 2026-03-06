#!/usr/bin/env python3
"""
LLM enrichment for sparse rows in meta_medicaments.

Generates a Portuguese pharmacological description for rows that have no
description, indications, or adverse_reactions — storing the result in the
ai_enrichment column and resetting embedding so the backfill re-embeds them.

Usage:
  docker compose run --rm pgvector-search python llm_enrich.py

Requirements:
  ollama pull llama3.2   (run once in the ollama container)
"""

import os
import sys
import psycopg2
import ollama

DB_DSN = os.environ.get(
    "DATABASE_URL",
    "host=localhost dbname=postgres user=postgres password=postgres port=5432",
)
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL = "llama3.2"
BATCH_SIZE = 10

_client = ollama.Client(host=OLLAMA_HOST)

PROMPT_TEMPLATE = """\
Você é um farmacêutico especialista. Com base apenas no nome e composição do medicamento abaixo, escreva em português um texto curto (máximo 150 palavras) cobrindo:
- Classe terapêutica
- Principais indicações clínicas
- Perfil do paciente (adulto, criança, idoso, gestante...)
- Contraindicações mais comuns

Responda apenas com o texto descritivo, sem títulos ou marcadores.

Nome: {name}
Composição: {composition}
"""


def enrich_row(name: str, composition: str) -> str:
    prompt = PROMPT_TEMPLATE.format(
        name=name or "",
        composition=composition or "",
    )
    response = _client.generate(model=LLM_MODEL, prompt=prompt)
    return response["response"].strip()


def enrich(conn):
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, name, composition
        FROM meta_medicaments
        WHERE is_deleted = false
          AND ai_enrichment IS NULL
          AND (description IS NULL OR description = '')
          AND (indications IS NULL OR indications = '')
          AND (adverse_reactions IS NULL OR adverse_reactions = '')
        ORDER BY id
        """
    )
    rows = cur.fetchall()

    if not rows:
        print("No sparse rows to enrich.")
        return

    print(f"Enriching {len(rows)} sparse rows with {LLM_MODEL}…")
    batch = 0

    for i, (row_id, name, composition) in enumerate(rows, start=1):
        try:
            text = enrich_row(name, composition)
        except Exception as e:
            print(f"  [{i}/{len(rows)}] id={row_id} — LLM error: {e}")
            continue

        # Store enrichment and reset embedding so backfill re-embeds this row
        cur.execute(
            """
            UPDATE meta_medicaments
            SET ai_enrichment = %s,
                embedding = NULL
            WHERE id = %s
            """,
            (text, row_id),
        )

        batch += 1
        if batch % BATCH_SIZE == 0:
            conn.commit()
            print(f"  committed batch at row {i}")

        print(f"  [{i}/{len(rows)}] id={row_id} — {name}")

    conn.commit()
    print("Enrichment complete. Run backfill to re-embed the updated rows.")
    cur.close()


def main():
    conn = psycopg2.connect(DB_DSN)
    try:
        enrich(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
