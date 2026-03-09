-- GIN index on indice_pesquisa for fast full-text search (hybrid search).
CREATE INDEX IF NOT EXISTS meta_medicaments_indice_pesquisa_gin
  ON meta_medicaments USING gin(indice_pesquisa);
