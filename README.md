# TradeAgent

Used/refurbished smartphone **valuation and acquisition-decision engine** for the
Turkish market. The validated Hybrid Market Valuation Engine v1
(freeze-ready, see `docs/s3-validation-report.md`) is exposed through a
Spring Boot REST API in `backend/` — see `backend/README.md`.

## What this project estimates (long-term)

```
expected market/refurbished value
  − expected repair cost
  − operational cost
  − risk buffer
  − required profit
  = recommended maximum acquisition price
```

The acquisition price is produced by a **deterministic engine**, not by a model
trained on weak/fabricated targets.

## Data philosophy

- **Real data or no data.** Missing fields stay `NULL`; we never synthesize
  individual-device attributes (battery health, defects, repair history).
- **`price_kind` is sacred.** MSRP / new listing / used listing / refurbished
  listing / sold / buyback-offer / wholesale are different economic quantities
  and are never merged into one target.
- **Listing ≠ sold.** Current public sources give listing prices; we say
  "list-price model", never "market-clearing price model".
- **Joins are typed.** `EXACT JOIN` (shared key), `ENRICHMENT` (model-level
  attribute), `STATISTICAL PRIOR` (different population — no row join),
  `NEVER MERGE`.
- **Old data teaches structure, not price.** Foreign/2021 data may inform
  depreciation *ratios*; 2026 TRY levels come only from our own observation
  table.
- **Time is explicit.** T0 offered → T1 inspected → T2 refurbished →
  T3 listed → T4 sold. Features may only use information available at the
  decision stage they serve.

## Repository layout

```
data/
  raw/            # immutable originals (git-ignored)
  interim/        # cleaned, typed (git-ignored)
  processed/      # canonical tables (git-ignored)
  manifests/      # committed JSON manifests: hash, source, license, rows
docs/             # research report, strategy, dictionary, quality report
schemas/          # canonical_schema.sql
src/
  ingestion/      # per-source loaders -> interim parquet + manifest
  normalization/  # deterministic name/storage normalization
  matching/       # rule-based alias resolution (fuzzy => NEEDS_REVIEW)
  quality/        # profiling + focused EDA -> docs/phase1a-data-quality-report.md
tests/
```

## Current datasets (see docs/phase1a-data-quality-report.md)

| Dataset | Role | Verdict |
|---|---|---|
| ReCell / ahsan81 | structural depreciation reference | APPROVED_FOR_EXPLORATION_ONLY — R²(ratio~days_used)=0.90 suggests modeled prices |
| mizan121 | was: condition/battery effects | **REJECTED for training** — battery⊥age, storage/RAM have zero price signal: synthetic-generation evidence |

## Reproduce

```bash
pip install -r requirements.txt
# place raw files per data/raw/README.md, then:
python -m src.ingestion.recell
python -m src.ingestion.mizan121
python -m src.quality.profile   # writes docs/phase1a-data-quality-report.md
python -m src.quality.eda       # appends focused EDA tables
pytest tests -q
```

## Known limitations (Phase 1A)

- No Turkey 2026 observations collected yet — `price_observation` is schema-ready
  but intentionally **not fake-populated**.
- ReCell prices are normalized (≈EUR-scale); usable for ratio structure only.
- mizan121 fails realness checks; kept for reference/EDA illustration only.
- Repair cost is a lookup knowledge base (`repair_cost_observation`), not ML.

## Roadmap

- **Phase 1B (proposed):** TR price-observation collection (permitted sources),
  baseline ratio model with chronological split, κ-calibration design.
- **Company-data path:** inspection/acquisition/refurbishment/sales fields slot
  into the same schema (see `docs/data-strategy.md` §upgrade path).
