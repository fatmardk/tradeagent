-- TradeAgent canonical data model — Phase 1A
-- SQLite-compatible DDL. All *_at fields are ISO-8601 text.
-- Design rules:
--   * price_kind is NEVER merged into a single undifferentiated target.
--   * Individual-device fields (battery_health, condition, defects, parts)
--     stay NULL when not observed — never synthesized.
--   * Every economic observation carries provenance (source_id) and a
--     descriptive confidence_class — no arbitrary numeric weights.

CREATE TABLE IF NOT EXISTS source_registry (
    source_id              TEXT PRIMARY KEY,
    source_name            TEXT NOT NULL,
    source_type            TEXT NOT NULL,        -- e.g. KAGGLE_DATASET, OFFICIAL_PRICE_LIST, PUBLIC_PAGE, PARTNER_API
    source_url             TEXT,
    country                TEXT,                 -- ISO-3166 or NULL for global
    license                TEXT,
    license_url            TEXT,
    access_method          TEXT,                 -- OFFICIAL_API, PUBLIC_PAGE_MANUAL, LICENSED_FILE, PARTNER_FEED, SYNTHETIC
    legal_basis            TEXT,                 -- LICENSE_PERMITS, FAIR_USE_RESEARCH, PARTNER_AGREEMENT, NONE
    commercial_use_status  TEXT NOT NULL DEFAULT 'UNKNOWN'
                           CHECK (commercial_use_status IN ('PERMITTED','RESTRICTED','UNKNOWN','PARTNER_REQUIRED')),
    ml_training_status     TEXT NOT NULL DEFAULT 'UNKNOWN'
                           CHECK (ml_training_status IN ('PERMITTED','RESTRICTED','UNKNOWN','PARTNER_REQUIRED')),
    notes                  TEXT,
    created_at             TEXT NOT NULL,
    updated_at             TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS device_master (
    device_id       TEXT PRIMARY KEY,
    brand           TEXT NOT NULL,
    model           TEXT NOT NULL,
    model_family    TEXT,
    model_code      TEXT,
    release_date    TEXT,
    manufacturer    TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS device_variant (
    variant_id      TEXT PRIMARY KEY,
    device_id       TEXT NOT NULL REFERENCES device_master(device_id),
    storage_gb      INTEGER,                     -- canonical numeric; NULL only if truly unknown
    ram_gb          REAL,
    model_code      TEXT,
    sku             TEXT,
    gtin            TEXT,
    ean             TEXT,
    upc             TEXT,
    region          TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS device_alias (
    alias_id                TEXT PRIMARY KEY,
    source_id               TEXT REFERENCES source_registry(source_id),
    raw_brand               TEXT,
    raw_model               TEXT,
    raw_variant             TEXT,
    normalized_name         TEXT,
    device_id               TEXT REFERENCES device_master(device_id),
    variant_id              TEXT REFERENCES device_variant(variant_id),
    match_method            TEXT CHECK (match_method IN
                            ('EXACT_MODEL_CODE','EXACT_CANONICAL_NAME','RULE_BASED','MANUAL','FUZZY_CANDIDATE')),
    match_confidence_class  TEXT,                -- descriptive class only, e.g. HIGH/MEDIUM/LOW/NEEDS_REVIEW
    review_status           TEXT NOT NULL DEFAULT 'PENDING'
                            CHECK (review_status IN ('PENDING','APPROVED','REJECTED','NEEDS_REVIEW')),
    created_at              TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS price_observation (
    price_observation_id TEXT PRIMARY KEY,
    variant_id           TEXT REFERENCES device_variant(variant_id),
    device_id            TEXT REFERENCES device_master(device_id),
    source_id            TEXT NOT NULL REFERENCES source_registry(source_id),
    price                REAL NOT NULL,
    currency             TEXT NOT NULL,          -- ISO-4217
    country              TEXT NOT NULL,          -- ISO-3166
    price_kind           TEXT NOT NULL CHECK (price_kind IN
                         ('MSRP','NEW_LIST','USED_LIST','REFURBISHED_LIST','SOLD','BUYBACK_OFFER','WHOLESALE')),
    condition_grade      TEXT,                   -- canonical {S,A,B,C,D} or NULL; seller grades mapped upstream
    battery_health_pct   REAL,                   -- NULL when not observed — never synthesized
    is_from_price        INTEGER NOT NULL DEFAULT 0, -- 1 = model/category "starting from" price, NOT an exact variant quote
    seller_name          TEXT,                   -- merchant name where the page exposes it
    source_seller_id     TEXT,                   -- merchant id where the page exposes it
    product_url          TEXT,                   -- actual listing URL; category URL when listing URL unknown
    source_product_id    TEXT,                   -- source-side product/listing id where recoverable
    observed_at          TEXT NOT NULL,
    retrieved_at         TEXT NOT NULL,
    raw_reference        TEXT,                   -- listing id / row ref in source
    confidence_class     TEXT NOT NULL CHECK (confidence_class IN
                         ('OFFICIAL_MANUFACTURER','VERIFIED_TRANSACTION','AUTHORIZED_REFURBISHER',
                          'MARKETPLACE_LISTING','BUYBACK_OFFER','ACADEMIC_DATASET','PUBLIC_OBSERVATION','SYNTHETIC')),
    is_synthetic         INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS repair_cost_observation (
    repair_cost_observation_id TEXT PRIMARY KEY,
    variant_id           TEXT REFERENCES device_variant(variant_id),
    device_id            TEXT REFERENCES device_master(device_id),
    repair_type          TEXT NOT NULL,          -- screen, battery, rear_glass, rear_camera, charge_port, ...
    part_type            TEXT,
    part_quality         TEXT,                   -- ORIGINAL_SERVICE, OEM, AFTERMARKET_PREMIUM, AFTERMARKET, USED
    part_price           REAL,                   -- NULL when source gives only total service fee
    labor_cost           REAL,                   -- NULL when not separately published — never reverse-engineered
    total_repair_cost    REAL,
    currency             TEXT NOT NULL,
    country              TEXT NOT NULL,
    source_id            TEXT NOT NULL REFERENCES source_registry(source_id),
    observed_at          TEXT NOT NULL,
    retrieved_at         TEXT NOT NULL
);

-- Synthetic-scenario records (allowed only for tests/UI/engine validation) must
-- carry is_synthetic=1 plus generation metadata in a side table:
CREATE TABLE IF NOT EXISTS synthetic_provenance (
    entity_table        TEXT NOT NULL,
    entity_id           TEXT NOT NULL,
    generation_method   TEXT NOT NULL,
    source_distribution_version TEXT,
    created_at          TEXT NOT NULL,
    PRIMARY KEY (entity_table, entity_id)
);
