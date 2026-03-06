-- Adds ai_enrichment column for LLM-generated descriptions on sparse rows.
ALTER TABLE meta_medicaments
  ADD COLUMN IF NOT EXISTS ai_enrichment TEXT;
