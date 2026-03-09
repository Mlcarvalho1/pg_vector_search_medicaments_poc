ALTER TABLE meta_medicaments
  ADD COLUMN IF NOT EXISTS ai_description TEXT,
  ADD COLUMN IF NOT EXISTS ai_tags TEXT;
