# Hybrid Market Valuation Engine v1 — Report

## Architecture

```
DEVICE (brand, model, storage, optional grade, repairs, business rules)
  ↓
recent reliable market observation for the canonical variant?
  ├── YES → MARKET-BASED ESTIMATOR  (REAL_MARKET_OBSERVATION)
  │         RECENT_MARKET_MEDIAN / MARKET_MEDIAN_LOW_COVERAGE
  └── NO  → COLD-START FALLBACK     (FALLBACK_ESTIMATE)
            COLD_START_MODEL_MEDIAN → COLD_START_BRAND_STORAGE
            → COLD_START_BRAND → COLD_START_GLOBAL
  ↓
market value + spread (p25/p75/IQR)
  ↓
REPAIR_KB (EXACT_REPAIR_LOOKUP / SERIES_LEVEL_LOOKUP / NO_REPAIR_DATA)
  ↓
acquisition = value − repair − operational − risk_buffer − profit
```

Modules: `src/market/valuation.py` (market estimator), `src/market/cold_start.py`
(fallback hierarchy), `src/market/engine.py` (routing), `src/model/cold_start.py`
(ML candidate, evaluated but not default), `src/repair/lookup.py`,
`src/acquisition/engine.py`.

## Why market-first

S1→S2 OOT (shared grade-A variants): variant median MAPE **4.3%**, last
price 6.5%, HistGBR 31.6%, brand median 56.1%. Recent real market
evidence beats ML by ~7× on known variants — ML is demoted to a
cold-start *candidate*, not the default path.

## Cold-start comparison (leakage-safe, unseen-variant GroupKFold, n=737)

| strategy | MAE | MAPE |
|---|---:|---:|
| C_model — same-model median (model seen in train) | ₺5,076 | 21.4% |
| D_newprice_ratio | n=5, ₺13,962 | 15.0% (too few anchors) |
| B_brand_storage | ₺11,463 | 36.3% |
| A_brand | ₺15,941 | 60.9% |
| E_coldstart_ml (HistGBR) | ₺12,894 | 49.1% |

When the **model itself is unseen** (the hard subproblem): B+C chain
₺5,962 / 30.0% vs ML ₺9,543 / 56.8%. S1→S2 temporal new variants
(n=41): brand+storage chain 43.8% vs ML 85.3%.

**Decision: the fallback is a deterministic median hierarchy; ML is not
the default anywhere.** Same-model evidence >> brand+storage >> brand >>
ML. New-price ratio is promising (9.6% MAPE on 3 new variants) but
coverage is too thin to rely on.

## Routing logic

- `RECENT_MARKET_MEDIAN`: fresh obs for `(variant, grade)`, ≥2 offers
  and ≥2 sellers at latest observation.
- `MARKET_MEDIAN_LOW_COVERAGE`: fresh obs but latest row is
  single-offer or single-seller.
- `COLD_START_*`: no observation within `max_obs_age_days` (config,
  provisional 45d — **not** calibrated; staleness needs S3+).
- Spread = observed market p25/p75 + relative IQR (mean 0.086, median
  0.066 on RECENT_MARKET rows). No invented confidence percentages.

Current routing distribution (all 410 grade-A variants, as_of
2026-09-26): RECENT_MARKET_MEDIAN 220, MARKET_MEDIAN_LOW_COVERAGE 190.

## Data

Combined analytical set: 882 market rows, 426 variants, dates
2026-09-16/17/25, `snapshot_id` preserved, market-grain training
(no offer-count weighting).

## REPAIR_KB

172 rows / 89 Samsung models (S 61, A 55, Z 43, M 12, Note 1) +
5 series-level battery fees, official `samsung_tr_support` source.
Lookup tiers: EXACT (device_id/model name) → SERIES (e.g. battery) →
NO_REPAIR_DATA (never fabricated). Apple TR publishes no structured
repair table → not included.

## Example (CASE A+C+D combined)

Galaxy S23 256GB, grade A, screen replacement required,
rules: op ₺1,500, risk ₺1,000, margin 15%:

- market_value ₺34,124.50 — RECENT_MARKET_MEDIAN, 12 offers / 9 sellers,
  p25 ₺31,875 / p75 ₺34,649
- repair ₺9,900 — EXACT_REPAIR_LOOKUP, SM-S911, samsung_tr_support
- **max acquisition ₺16,605.83** = 34,124.50 − 9,900 − 1,500 − 1,000 − 5,118.68

## New-price coverage

Exact current-new anchors: 5/410 variants (Apple only). Samsung TR
buy pages are JS-gated; list pages carry no server-rendered prices —
documented as zero, not fabricated. "From" prices never attach to
storage variants.

## Evidence categories (never blurred)

| component | evidence |
|---|---|
| market median, p25/p75, offer/seller counts | REAL MARKET OBSERVATIONS |
| cold-start medians | REAL MARKET OBSERVATIONS (aggregated) |
| COLD_START_ML path | ML ESTIMATE (candidate only) |
| repair totals | OFFICIAL REPAIR DATA (Samsung TR) |
| operational / risk / profit | BUSINESS INPUT — not learned |

## Limitations

- Freshness threshold is a config placeholder; S3 must measure error
  vs observation age.
- Low coverage dominates: 190/410 variants ride on a single offer.
- Disappeared ≠ sold; no sell-through signal.
- Repair→condition mapping does not exist publicly; repairs are
  explicit inputs until inspection data arrives.
- Condition-aware modelling deferred (grade A = ~96% of offers).

## What Snapshot 3 should validate

- Persistence stability & drift beyond 8 days.
- Error vs observation age → data-driven freshness threshold.
- Market spread (IQR) stability.
- Cold-start error on S3-new variants for the median hierarchy.

## Future company fields

- Inspection outcome (defect→repair mapping) → automates repair input.
- Cost ledger → operational_cost; margin policy → required_profit.
- Sale price + days-on-market → realized margin, liquidity, sell-through.
