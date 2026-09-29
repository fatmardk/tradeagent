# TradeAgent Backend — Hybrid Market Valuation Engine v1 API

Spring Boot REST API exposing the validated Hybrid Market Valuation
Engine v1 (see `docs/hybrid-valuation-report.md` and
`docs/s3-validation-report.md`). The Python side stays the offline
research/data pipeline; this service is the application layer.

## Run

```bash
# 1. refresh canonical exports (from repo root)
python -m src.ingestion.export_backend

# 2. start the API
cd backend
mvn spring-boot:run          # http://localhost:8080

mvn test                     # 16 tests
```

## Architecture

```
controller/   REST endpoints, thin
service/      ValuationService (routing) — RepairService (KB)
              — AcquisitionService (formula)
repository/   MarketSnapshotRepository / RepairKbRepository interfaces
              + JsonMarketSnapshotRepository / JsonRepairKbRepository
domain/       records + enums (ValuationMethod, SourceType)
dto/          request/response records
config/       BackendProperties (data-dir, freshness, as-of, grade)
exception/    ApiException + GlobalExceptionHandler (structured errors)
```

### Data source

The backend consumes **canonical analytical exports only** — never raw
scrape files:

- `data/export/market_snapshot.json` ← `market_snapshot_combined.parquet`
- `data/export/repair_kb.json` ← `repair_cost_observation.parquet`

Repository interfaces isolate persistence: a `PgMarketSnapshotRepository`
can replace the JSON implementation later without touching valuation
logic.

## Hybrid Engine v1 routing (unchanged)

`ValuationService` is a faithful Java replica of
`src/market/{engine,valuation,cold_start}.py`:

| method | condition |
|---|---|
| `RECENT_MARKET_MEDIAN` | fresh obs, ≥2 offers AND ≥2 sellers |
| `MARKET_MEDIAN_LOW_COVERAGE` | fresh obs, single offer or seller |
| `COLD_START_MODEL_MEDIAN` | same model, other storages, median |
| `COLD_START_BRAND_STORAGE` | brand+storage median |
| `COLD_START_BRAND` | brand median |
| `COLD_START_GLOBAL` | all-rows median |

- Freshness `backend.valuation.max-obs-age-days: 45` — **placeholder**,
  in `application.yml`, not in code. `daysSinceObservation` is exposed.
- `backend.valuation.as-of`: empty → latest observed_date in the data
  (correct while data carries periodic snapshot dates).
- No ML in the default path — empirical result: market median 4.3% MAPE
  vs HistGBR 31.6% (S1→S2 OOT).

## Endpoints

### `GET /api/devices?brand=&model=&grade=&storageGb=`

Latest canonical variants with filters.

### `POST /api/valuation`

```json
{"brand": "Samsung", "model": "Galaxy S23", "storageGb": 256}
```

```json
{
  "device": {"brand":"Samsung","model":"Galaxy S23","storageGb":256,
             "canonicalVariant":"samsung|galaxy-s23|256"},
  "valuation": {
    "valuationMethod": "RECENT_MARKET_MEDIAN",
    "marketValue": 34124.5, "currency": "TRY",
    "sourceType": "REAL_MARKET_OBSERVATION",
    "observedAt": "2026-09-25", "daysSinceObservation": 0,
    "offerCount": 12, "sellerCount": 9,
    "marketP25": 31874.75, "marketP75": 34649.0,
    "relativeIqr": 0.0813, "gradeSegment": "A",
    "notes": []
  }
}
```

### `GET /api/repair-costs?repairType=&modelName=&modelCode=&series=`

Samsung TR official KB. `repairType` optional → all types. Aliases:
`screen_replacement→screen_module`, `battery_replacement→battery`.
Unknown type → 400 `INVALID_REPAIR_TYPE`.

### `POST /api/acquisition/quote`

```json
{"brand":"Samsung","model":"Galaxy S23","storageGb":256,
 "requiredRepairs":["screen_module"],
 "operationalCost":1500,"riskBuffer":1000,"requiredMargin":0.15}
```

`requiredMargin` (fraction of market value) overrides `requiredProfit`
(absolute TRY). Response carries `explanation` with per-number
provenance (`REAL_MARKET_OBSERVATION` / `OFFICIAL_REPAIR_DATA` /
`BUSINESS_INPUT` / `MODEL_ESTIMATE`) — identical to the Python engine,
including `recommended_max_price: 16605.83` for the example above.

## Error handling

Structured body `{"error": {"code", "message", "details"}}`:

- `VALIDATION_FAILED` 400 — missing/invalid fields, negative money
- `INVALID_REPAIR_TYPE` 400 — unknown repair type (lists valid ones)
- `NO_REPAIR_DATA` in quotes — null cost, never fabricated
- `INTERNAL_ERROR` 500 — no stack traces leaked

## Known limitations

- Grade-A segment only (96% of observations); B/C/S preserved but not
  routed by condition.
- REPAIR_KB is Samsung-only (Apple TR publishes no equivalent table).
- 45-day freshness window is an uncalibrated placeholder.
- `n_sellers`=0 rows (non-A categories) surface as low-coverage.
- No auth/frontend/persistence — JSON file repo by design.
- Disappeared variants are "not observed", not "sold".
