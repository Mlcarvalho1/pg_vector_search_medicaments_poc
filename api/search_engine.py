"""
Search engine core — shared by CLI (tools/pgvector_search.py) and the API.
Returns structured data instead of printing.
"""

import os
import re
import psycopg2
import ollama

_EXCLUSION_PATTERNS = [
    r'al[eé]rgic[oa]s?\s+a\s+([\w]+)',
    r'alergia\s+a\s+([\w]+)',
    r'intoler[aâ]nte\s+a\s+([\w]+)',
    r'n[aã]o\s+(?:pod[eo]|consig[ao])\s+tomar?\s+([\w]+)',
]

DB_DSN = os.environ.get(
    "DATABASE_URL",
    "host=localhost dbname=postgres user=postgres password=postgres port=5432",
)
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = "nomic-embed-text"
MAX_CHARS = 4_000

_ollama_client = ollama.Client(host=OLLAMA_HOST)


def extract_exclusions(query: str) -> list[str]:
    exclusions = []
    for pattern in _EXCLUSION_PATTERNS:
        for match in re.finditer(pattern, query, re.IGNORECASE):
            exclusions.append(match.group(1))
    return exclusions


def clean_query(query: str) -> str:
    for pattern in _EXCLUSION_PATTERNS:
        query = re.sub(pattern, "", query, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", query).strip()


def get_embedding(text: str) -> list[float]:
    response = _ollama_client.embeddings(model=OLLAMA_MODEL, prompt=text[:MAX_CHARS])
    return response["embedding"]


def search(conn, query: str, limit: int = 10) -> list[dict]:
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
    rows = cur.fetchall()
    cur.close()

    return [
        {
            "rank": rank,
            "id": row_id,
            "name": name,
            "description": description,
            "score": float(score),
        }
        for rank, (row_id, name, description, score) in enumerate(rows, start=1)
    ]


def search_hybrid(conn, query: str, limit: int = 10) -> tuple[list[dict], list[str]]:
    exclusions = extract_exclusions(query)
    fts_query = clean_query(query)
    embedding = get_embedding(query)
    vec_str = str(embedding)

    exclusion_sql = ""
    exclusion_params = []
    for substance in exclusions:
        exclusion_sql += " AND NOT (indice_pesquisa @@ plainto_tsquery('portuguese', unaccent(%s)))"
        exclusion_params.append(substance)

    cur = conn.cursor()
    cur.execute(
        f"""
        WITH semantic AS (
            SELECT id,
                   ROW_NUMBER() OVER (ORDER BY embedding <=> %s::vector) AS rank
            FROM meta_medicaments
            WHERE is_deleted = false
              AND embedding IS NOT NULL
              {exclusion_sql}
            LIMIT 200
        ),
        fts AS (
            SELECT id,
                   ROW_NUMBER() OVER (ORDER BY ts_rank(indice_pesquisa, query) DESC) AS rank
            FROM meta_medicaments,
                 plainto_tsquery('portuguese', unaccent(%s)) query
            WHERE is_deleted = false
              AND indice_pesquisa @@ query
              {exclusion_sql}
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
        [vec_str] + exclusion_params + [fts_query] + exclusion_params + [limit],
    )
    rows = cur.fetchall()
    cur.close()

    results = [
        {
            "rank": rank,
            "id": row_id,
            "name": name,
            "description": description,
            "score": float(score),
        }
        for rank, (row_id, name, description, score) in enumerate(rows, start=1)
    ]
    return results, exclusions
