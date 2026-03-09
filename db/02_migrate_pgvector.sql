-- Run this once to enable pgvector and prepare the meta_medicaments table.
-- Requires pgvector extension to be installed (brew install pgvector on macOS).

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE meta_medicaments
  ADD COLUMN IF NOT EXISTS embedding vector(768);

CREATE INDEX ON meta_medicaments
  USING hnsw (embedding vector_cosine_ops);
