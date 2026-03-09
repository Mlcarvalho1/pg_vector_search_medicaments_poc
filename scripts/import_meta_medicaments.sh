#!/usr/bin/env bash
set -e

CONTAINER="${CONTAINER:-postgres-local}"
PGUSER="${PGUSER:-postgres}"
PGDATABASE="${PGDATABASE:-postgres}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CSV_FILE="${1:-$SCRIPT_DIR/../meta_medicaments.csv}"

echo "Copying files into container..."
docker cp "$SCRIPT_DIR/../db/01_migrate_meta_medicaments.sql" "$CONTAINER:/tmp/migrate_meta_medicaments.sql"
docker cp "$CSV_FILE" "$CONTAINER:/tmp/meta_medicaments.csv"

echo "Creating table..."
docker exec "$CONTAINER" psql -U "$PGUSER" -d "$PGDATABASE" \
    -f /tmp/migrate_meta_medicaments.sql

echo "Importing CSV (via temp table to skip manufacturer_id)..."
docker exec -i "$CONTAINER" psql -U "$PGUSER" -d "$PGDATABASE" <<'SQL'
TRUNCATE meta_medicaments;

CREATE TEMP TABLE meta_medicaments_tmp (
    id integer,
    name text,
    presentation text,
    description text,
    classification text,
    drug_leaflet text,
    medicament_type text,
    defined_price boolean,
    high_cost boolean,
    price double precision,
    min_price double precision,
    max_price double precision,
    special_control boolean,
    prescription text,
    type text,
    category text,
    indications text,
    pediatric_dosage text,
    adults_dosage text,
    elderly_dosage text,
    adverse_reactions text,
    contraindications text,
    pregnancy text,
    lactation text,
    recommendations text,
    exams text,
    posology text,
    composition text,
    characteristics text,
    physical_form text,
    administration_via character varying(255),
    is_deleted boolean,
    ans character varying(25),
    indice_pesquisa tsvector,
    opensearch_index character varying(255),
    is_antimicrobial boolean,
    ai_enrichment text,
    embedding text,
    ai_description text,
    ai_tags text
);

COPY meta_medicaments_tmp FROM '/tmp/meta_medicaments.csv'
WITH (FORMAT csv, HEADER true, NULL '', QUOTE '"', ESCAPE '"');

INSERT INTO meta_medicaments (
    id, name, presentation, description, classification, drug_leaflet,
    medicament_type, defined_price, high_cost, price, min_price, max_price,
    special_control, prescription, type, category, indications,
    pediatric_dosage, adults_dosage, elderly_dosage, adverse_reactions,
    contraindications, pregnancy, lactation, recommendations, exams,
    posology, composition, characteristics, physical_form,
    administration_via, is_deleted, ans, indice_pesquisa,
    opensearch_index, is_antimicrobial, ai_enrichment,
    embedding, ai_description, ai_tags
)
SELECT
    id, name, presentation, description, classification, drug_leaflet,
    medicament_type, defined_price, high_cost, price, min_price, max_price,
    special_control, prescription, type, category, indications,
    pediatric_dosage, adults_dosage, elderly_dosage, adverse_reactions,
    contraindications, pregnancy, lactation, recommendations, exams,
    posology, composition, characteristics, physical_form,
    administration_via, is_deleted, ans, indice_pesquisa,
    opensearch_index, is_antimicrobial, ai_enrichment,
    NULLIF(embedding, '')::vector, ai_description, ai_tags
FROM meta_medicaments_tmp;

SELECT setval(pg_get_serial_sequence('meta_medicaments', 'id'), MAX(id)) FROM meta_medicaments;
SQL

echo "Done."
