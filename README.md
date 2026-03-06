# postgres-local

Local development stack with PostgreSQL (pgvector), MongoDB, and Ollama — all running in Docker.

---

## Services

| Container | Image | Port | Purpose |
|---|---|---|---|
| `postgres-local` | `pgvector/pgvector:pg16` | `5432` | PostgreSQL with pgvector extension |
| `ollama-local` | `ollama/ollama` | `11434` | Local LLM / embedding inference |
| `mongodb-local` | `mongo:7` | `27017` | MongoDB |

---

## First-time Setup

### 1. Start the stack

```bash
docker compose up -d postgres ollama mongodb
```

### 2. Run the pgvector migration

Adds the `vector` extension, an `embedding` column, and an HNSW index to `meta_medicaments`:

```bash
docker exec -i postgres-local psql -U postgres -d postgres -f - < migrate_pgvector.sql
```

### 3. Pull the embedding model

Downloads `nomic-embed-text` (~270 MB) into the `ollama_data` volume (one-time only):

```bash
docker exec ollama-local ollama pull nomic-embed-text
```

### 4. Build the search image

```bash
docker compose build pgvector-search
```

---

## Semantic Search on meta_medicaments

Semantic search is powered by [pgvector](https://github.com/pgvector/pgvector) and [nomic-embed-text](https://ollama.com/library/nomic-embed-text) (768-dimensional embeddings generated locally via Ollama — no API keys required).

### How it works

1. **Backfill** — `pgvector_search.py` reads every row in `meta_medicaments` where `embedding IS NULL`, concatenates the text fields (`name`, `description`, `indications`, `contraindications`, `composition`, `characteristics`, `adverse_reactions`, `recommendations`), sends the text to Ollama, and stores the resulting 768-dim vector in the `embedding` column.
2. **Search** — A query string is embedded the same way, then PostgreSQL finds the nearest rows using cosine distance (`<=>`) via the HNSW index.

### Backfill existing rows

```bash
docker compose run --rm pgvector-search backfill
```

Progress is committed every 50 rows so it is safe to interrupt and resume.

### Run a search query

```bash
docker compose run --rm pgvector-search search "antibiotico para criancas"
docker compose run --rm pgvector-search search "hipertensao arterial"
docker compose run --rm pgvector-search search "dor de cabeca"
```

Output example:

```
Top 10 results for: "dor de cabeca"

Rank  Similarity   ID         Name / Description
--------------------------------------------------------------------------------
1     0.9231       42         Paracetamol 500mg  —  Analgésico e antipirético...
2     0.8974       17         Ibuprofeno 400mg  —  Anti-inflamatório não esteroidal...
...
```

### Verify embeddings were stored

```bash
docker exec -it postgres-local psql -U postgres -d postgres \
  -c "SELECT COUNT(*) FROM meta_medicaments WHERE embedding IS NOT NULL;"
```

---

## Connecting to Postgres

**psql via Docker:**
```bash
docker exec -it postgres-local psql -U postgres -d postgres
```

**Connection string (for apps / Postico / DBeaver):**
```
host=localhost port=5432 dbname=postgres user=postgres password=postgres
```

---

## File Reference

| File | Purpose |
|---|---|
| `docker-compose.yml` | Defines all services and volumes |
| `migrate_pgvector.sql` | One-time migration: enables `vector` extension, adds `embedding` column and HNSW index |
| `pgvector_search.py` | Backfill and semantic search CLI |
| `Dockerfile` | Image for running `pgvector_search.py` inside Docker |

---

## Environment Variables

`pgvector_search.py` reads these from the environment (defaults work for local Docker):

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `host=localhost ...` | libpq connection string |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API base URL |

When running via `docker compose run`, these are set automatically from `docker-compose.yml`.
