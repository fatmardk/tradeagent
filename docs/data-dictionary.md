# Data Dictionary — canonical fields

See `schemas/canonical_schema.sql` for DDL. Semantics below.

## source_registry

| Field | Meaning |
|---|---|
| source_id | stable key, e.g. `kaggle_ahsan81`, `apple_tr_service` |
| source_type | KAGGLE_DATASET / OFFICIAL_PRICE_LIST / PUBLIC_PAGE / PARTNER_API / ... |
| access_method | OFFICIAL_API / PUBLIC_PAGE_MANUAL / LICENSED_FILE / PARTNER_FEED / SYNTHETIC |
| legal_basis | LICENSE_PERMITS / FAIR_USE_RESEARCH / PARTNER_AGREEMENT / NONE |
| commercial_use_status, ml_training_status | PERMITTED / RESTRICTED / UNKNOWN / PARTNER_REQUIRED — never assumed |

## device_master / device_variant

- `device_master` = device family (e.g. "iPhone 13"). Kept thin: identity + release_date only.
- `device_variant` = economically distinct config (iPhone 13 / 128 GB).
  `storage_gb` is canonical numeric (128, not "128GB"), `NULL` only if truly unknown.

## device_alias

- `match_method`: EXACT_MODEL_CODE / EXACT_CANONICAL_NAME / RULE_BASED / MANUAL / FUZZY_CANDIDATE.
- FUZZY_CANDIDATE never auto-joins: `review_status=NEEDS_REVIEW` until human-approved.
- `match_confidence_class` is descriptive (HIGH/MEDIUM/LOW), not a probability.

## price_observation

| Field | Meaning |
|---|---|
| price_kind | MSRP / NEW_LIST / USED_LIST / REFURBISHED_LIST / SOLD / BUYBACK_OFFER / WHOLESALE — distinct economic quantities, never merged |
| condition_grade | canonical S(premium-plus) A(like-new) B(good) C(fair) D(poor); NULL if unobserved |
| battery_health_pct | individual-device measurement; NULL if unobserved — never synthesized |
| is_from_price | 1 = source shows only a model/category "starting from" price (storage/grade of the floor price unknown); 0 = exact listing quote. From-prices must never be treated as exact variant prices |
| seller_name | merchant name where the page exposes it; NULL otherwise |
| source_seller_id | merchant id where the page exposes it; NULL otherwise |
| product_url | actual listing URL; category URL when the listing URL is not recoverable |
| source_product_id | source-side product/listing id where recoverable (e.g. id in Getmobil product URL slug) |
| offer_role (raw offers file) | listing_vendor = the vendor whose listing the product page represents; marketplace_offer = alternative seller offer on the same product spec |
| notes | free-text evidence flags: `stock:N`, `buybox_winner`, `fast_delivery`, preorder dates |
| observed_at | when the price was true at the source |
| retrieved_at | when we captured it (snapshot freshness) |
| confidence_class | OFFICIAL_MANUFACTURER / VERIFIED_TRANSACTION / AUTHORIZED_REFURBISHER / MARKETPLACE_LISTING / BUYBACK_OFFER / ACADEMIC_DATASET / PUBLIC_OBSERVATION / SYNTHETIC |
| is_synthetic | 1 only for generated test rows; they never enter training |

## repair_cost_observation

- `repair_type` ∈ screen, battery, rear_glass, rear_camera, charge_port, speaker, mic, biometric, mainboard, frame; Samsung TR also emits `screen_module` / `screen_eco` / `frame_eco_screen` / `outer_screen` / `frame` mirroring the official column names.
- `part_quality` ∈ ORIGINAL_SERVICE / OEM / AFTERMARKET_PREMIUM / AFTERMARKET / USED.
- `part_price`, `labor_cost` may be NULL when the official source publishes only a total service fee; we do not back out fake labor values.
- Samsung TR rows (`source_id=samsung_tr_support`): `device_id` = SM- model code; series-level rows (battery) have `device_id=NULL` and `series` set. Note: per Samsung's footnote, screen_module/frame_eco_screen/frame prices for S and Z series already include battery replacement.
- Populated by `src/ingestion/repair_kb.py` from the saved raw page `data/raw/tr_observations/samsung_repair_tr_2026-09-25.txt` (Samsung-only so far; Apple TR publishes no public repair table).

## Derived fields (interim layer)

- `used_to_new_ratio = used_price / new_price` (ReCell) — structural ratio; normalized units cancel.
- `resale_to_original_ratio` (mizan121) — kept for reference; source rejected for training.
- `device_age_months = observed_at − release_date` — computed only where both dates are real.

## Analytical layer (processed)

### `offer_level.parquet`
One row per observed seller offer. All `price_observation` fields plus:
- `canonical_brand`, `canonical_model`, `canonical_variant` (`brand|model-slug|gb`; NULL when storage unknown)
- `observed_date`, `grade_segment` (`condition_grade` or `UNKNOWN`), `exact_variant_price` (= `not is_from_price`)

### `market_snapshot.parquet`
One row per `(observed_date, canonical_variant, grade_segment)`, exact variant prices only.
- `n_offers`, `n_sellers`, `n_products`, `n_sources`, `pct_missing_seller`
- `price_median` (primary V1 target), `price_mean`, `price_min/max`, `price_q25/q75`

Builder: `python -m src.ingestion.build_analytical`. Canonicalization: `src/normalization/variant.py` (deterministic alias table; unresolvable names kept as-is, never merged by guessing).

### `market_snapshot_s2.parquet` / `market_snapshot_combined.parquet`
Snapshot-2 (2026-09-25) equivalent of `market_snapshot.parquet`, and the S1+S2 union (882 rows, 426 variants, `snapshot_id` + `observed_date` preserved — time is never collapsed). Builder: `python -m src.ingestion.combine_snapshots` (inputs read-only; S1 never rewritten).

### `repair_cost_observation.parquet`
Official Samsung TR repair fees — 172 rows, 89 model-level `device_id`s + 5 series-level battery rows (`device_id` NULL). `repair_type`: screen_module / screen_eco / outer_screen / frame / frame_eco_screen / battery. `total_repair_cost` only; part/labor split is not published and is never inferred. Builder: `python -m src.ingestion.repair_kb`.

### `oot_eval_s1_s2.parquet`
S1-trained predictions evaluated on S2 — one row per S2 market row with predictor columns (`last_price`, `variant_median`, `brand_median`, `v1_histgbr`) and errors. Builder: `python -m src.model.evaluate_oot`.

## Valuation / acquisition layer

- `src/market/valuation.py` — `MarketEstimator`: latest-observation median + p25/p75/IQR spread, freshness window configurable.
- `src/market/cold_start.py` — `FallbackEstimator`: median hierarchy (model → brand+storage → brand → global), selected over ML by leakage-safe eval.
- `src/market/engine.py` — `HybridValuer`: routing, `valuation_method` + `source` stamped on every output.
- `src/model/cold_start.py` — HistGBR cold-start candidate (evaluated, not default).
- `src/repair/lookup.py` — `RepairKB`: EXACT / SERIES_LEVEL / NO_REPAIR_DATA tiers.
- `src/acquisition/engine.py` — `compute_acquisition` + `full_valuation`: deterministic price = value − repair − operational − risk − profit; business inputs labelled, never learned.
