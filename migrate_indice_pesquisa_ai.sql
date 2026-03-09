-- Rebuild indice_pesquisa to include ai_description and ai_tags (with unaccent),
-- then add a trigger to keep it in sync on every INSERT/UPDATE.

-- 0. Enable unaccent extension
CREATE EXTENSION IF NOT EXISTS unaccent;

-- 1. Rebuild all existing rows
UPDATE meta_medicaments
SET indice_pesquisa = to_tsvector('portuguese', unaccent(
    COALESCE(name, '') || ' ' ||
    COALESCE(description, '') || ' ' ||
    COALESCE(composition, '') || ' ' ||
    COALESCE(ai_description, '') || ' ' ||
    COALESCE(ai_tags, '')
));

-- 2. Trigger function
CREATE OR REPLACE FUNCTION update_indice_pesquisa()
RETURNS trigger AS $$
BEGIN
    NEW.indice_pesquisa := to_tsvector('portuguese', unaccent(
        COALESCE(NEW.name, '') || ' ' ||
        COALESCE(NEW.description, '') || ' ' ||
        COALESCE(NEW.composition, '') || ' ' ||
        COALESCE(NEW.ai_description, '') || ' ' ||
        COALESCE(NEW.ai_tags, '')
    ));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. Attach trigger
DROP TRIGGER IF EXISTS trg_update_indice_pesquisa ON meta_medicaments;
CREATE TRIGGER trg_update_indice_pesquisa
BEFORE INSERT OR UPDATE ON meta_medicaments
FOR EACH ROW EXECUTE FUNCTION update_indice_pesquisa();
