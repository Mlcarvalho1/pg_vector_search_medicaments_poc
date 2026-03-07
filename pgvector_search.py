#!/usr/bin/env python3
"""
Semantic and hybrid search on meta_medicaments using pgvector + Ollama.

Usage:
  python pgvector_search.py backfill
  python pgvector_search.py search "antibiotico para criancas"
  python pgvector_search.py search-hybrid "antibiotico para criancas"

Requirements:
  pip install psycopg2-binary ollama
  ollama pull nomic-embed-text-8k
"""

import sys
import os
import psycopg2
import ollama

# ---------------------------------------------------------------------------
# Connection — adjust to your local Postgres setup
# ---------------------------------------------------------------------------
DB_DSN = os.environ.get(
    "DATABASE_URL",
    "host=localhost dbname=postgres user=postgres password=postgres port=5432",
)

OLLAMA_MODEL = "nomic-embed-text"
BATCH_SIZE = 50

# Columns used to build the text that will be embedded
TEXT_FIELDS = [
    "name",
    "composition",
    "ai_description",
    "ai_tags",
]


_ollama_client = ollama.Client(host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))


# nomic-embed-text max context is 8192 tokens (~4 chars/token) → ~32k chars.
# Truncate to 6000 chars (~1500 tokens) as a hard safe limit.
MAX_CHARS = 4_000


def get_embedding(text: str) -> list[float]:
    response = _ollama_client.embeddings(model=OLLAMA_MODEL, prompt=text[:MAX_CHARS])
    return response["embedding"]


def build_text(row: dict) -> str:
    parts = [str(row[f]) for f in TEXT_FIELDS if row.get(f)]
    return "\n".join(parts)


def backfill(conn):
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, name, composition, ai_description, ai_tags
        FROM meta_medicaments
        WHERE embedding IS NULL
          AND is_deleted = false
          AND ai_description IS NOT NULL
          AND ai_tags IS NOT NULL
        """
    )
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]

    if not rows:
        print("No rows to backfill.")
        return

    print(f"Backfilling {len(rows)} rows…")
    batch = 0

    for i, raw in enumerate(rows, start=1):
        row = dict(zip(columns, raw))
        text = build_text(row)
        if not text.strip():
            print(f"  [{i}/{len(rows)}] id={row['id']} — skipped (empty text)")
            continue

        embedding = get_embedding(text)

        cur.execute(
            "UPDATE meta_medicaments SET embedding = %s::vector WHERE id = %s",
            (str(embedding), row["id"]),
        )

        batch += 1
        if batch % BATCH_SIZE == 0:
            conn.commit()
            print(f"  committed batch at row {i}")

        print(f"  [{i}/{len(rows)}] id={row['id']} embedded")

    conn.commit()
    print("Backfill complete.")
    cur.close()


def search(conn, query: str, limit: int = 10):
    embedding = get_embedding(query)
    vec_str = str(embedding)

    cur = conn.cursor()
    cur.execute(
        """
        SELECT id,
               name,
               description,
               1 - (embedding <=> %s::vector) AS similarity
        FROM meta_medicaments
        WHERE is_deleted = false
          AND embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (vec_str, vec_str, limit),
    )
    results = cur.fetchall()
    cur.close()

    if not results:
        print("No results found.")
        return

    print(f"\nTop {len(results)} results for: \"{query}\"\n")
    print(f"{'Rank':<5} {'Similarity':<12} {'ID':<10} Name / Description")
    print("-" * 80)
    for rank, (row_id, name, description, similarity) in enumerate(results, start=1):
        desc_preview = (description or "")[:60].replace("\n", " ")
        print(f"{rank:<5} {similarity:<12.4f} {row_id:<10} {name}  —  {desc_preview}")


def search_hybrid(conn, query: str, limit: int = 10):
    """
    Combines pgvector semantic search and tsvector full-text search using
    Reciprocal Rank Fusion (RRF, k=60). Results appear even when only one
    source finds a match, covering both sparse and rich rows.
    """
    embedding = get_embedding(query)
    vec_str = str(embedding)

    cur = conn.cursor()
    cur.execute(
        """
        WITH semantic AS (
            SELECT id,
                   ROW_NUMBER() OVER (ORDER BY embedding <=> %s::vector) AS rank
            FROM meta_medicaments
            WHERE is_deleted = false
              AND embedding IS NOT NULL
            LIMIT 200
        ),
        fts AS (
            SELECT id,
                   ROW_NUMBER() OVER (ORDER BY ts_rank(indice_pesquisa, query) DESC) AS rank
            FROM meta_medicaments,
                 plainto_tsquery('portuguese', %s) query
            WHERE is_deleted = false
              AND indice_pesquisa @@ query
            LIMIT 200
        ),
        rrf AS (
            SELECT
                COALESCE(s.id, f.id) AS id,
                COALESCE(1.0 / (60 + s.rank), 0) +
                COALESCE(1.0 / (60 + f.rank), 0) AS score
            FROM semantic s
            FULL OUTER JOIN fts f ON s.id = f.id
        )
        SELECT m.id, m.name, m.description, r.score
        FROM rrf r
        JOIN meta_medicaments m ON m.id = r.id
        ORDER BY r.score DESC
        LIMIT %s
        """,
        (vec_str, query, limit),
    )
    results = cur.fetchall()
    cur.close()

    if not results:
        print("No results found.")
        return

    print(f"\nTop {len(results)} hybrid results for: \"{query}\"\n")
    print(f"{'Rank':<5} {'RRF Score':<12} {'ID':<10} Name / Description")
    print("-" * 80)
    for rank, (row_id, name, description, score) in enumerate(results, start=1):
        desc_preview = (description or "")[:60].replace("\n", " ")
        print(f"{rank:<5} {score:<12.4f} {row_id:<10} {name}  —  {desc_preview}")


def main():
    commands = ("backfill", "search", "search-hybrid")
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    conn = psycopg2.connect(DB_DSN)

    try:
        if command == "backfill":
            backfill(conn)
        elif command in ("search", "search-hybrid"):
            if len(sys.argv) < 3:
                print(f"Usage: python pgvector_search.py {command} <query>")
                sys.exit(1)
            query = " ".join(sys.argv[2:])
            if command == "search":
                search(conn, query)
            else:
                search_hybrid(conn, query)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
