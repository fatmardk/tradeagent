# Snapshot 3 — Hybrid Engine v1 Validation (2026-09-25)

## Snapshot 3 collection (same methodology as S1/S2, immutable)

| item | value |
|---|---|
| sitemap phone URLs | 839 (S2: 839 — identical set) |
| product offers | 2.167, 0 failures |
| non-A category rows | 68 (S2: 101 — İyi 34 + Premium Plus 34; **Çok İyi/B inventory absent site-wide today**) |
| Apple MSRP / EasyCep base | 25 + 6 (prices re-verified unchanged) |
| `price_observation_s3` | 2.266 rows |
| `market_snapshot_s3` | 415 rows, 378 variants (A 362, S 15, C 18, UNKNOWN 20) |
| offer-level | 2.266 |

S1/S2 untouched (2.252 / 2.227 obs verified). Combined set regenerated:
1.297 market rows / 6.745 offer rows, `snapshot_id` preserved.

**Critical caveat:** S3 collected the same calendar day as S2
(~1.5h apart). This validates collection reproducibility and intra-day
stability — it does **not** measure multi-day temporal generalization.
A future S4, collected days later, is required for that.

## Out-of-time: history (S1+S2) -> S3

Seen/shared grade-A variants, n=361:

| predictor | MAE | RMSE | MAPE |
|---|---:|---:|---:|
| **variant_median (latest obs)** | **₺143** | ₺636 | **0.4%** |
| last_price | ₺1,221 | ₺4,435 | 3.8% |
| V1 HistGBR | ₺10,753 | ₺18,792 | 30.3% |
| brand_median | ₺16,366 | ₺25,442 | 59.7% |

Intra-day drift: median 0.0%, mean −0.13%, 86% unchanged, 98% within
±5%. Market is extraordinarily stable intra-day; the 8-day S1→S2 result
(4.3% MAPE) remains the meaningful short-horizon benchmark.

## Unseen variants

Only **1** new variant in S3 (`xiaomi|14t|512`): cold-start fallback
₺10.4k error (COLD_START_BRAND_STORAGE, 37.7% APE) vs V1 ₺26.8k (97.1%)
vs brand ₺15.2k (55.0%). Direction confirms the fallback hierarchy but
n=1 — no statistical claim.

## Error vs observation age

**Cannot be measured from S3.** Every S3 grade-A variant was also
observed in S2 the same day → days_since_obs = 0 for all 361 rows.
No stale-age data point exists; the 45-day `max_obs_age_days` remains
an uncalibrated placeholder. Needs S4+ with real date separation.

## Decision

- Persistence/market-median routing: **confirmed** (0.4% intra-day,
  4.3% over 8 days) — remains the primary estimator.
- Cold-start fallback: **meaningful** — outperformed V1 on the single
  unseen variant; keep as default fallback, V1 stays a candidate.
- Freshness: no new evidence; placeholder kept, no new threshold set.
- Condition-aware modelling: not started (B grade inventory actually
  shrank to zero in S3 — coverage argument strengthened).
- **Hybrid Market Valuation Engine v1: FREEZE-READY** for the current
  scope (grade-A market value + repair lookup + explicit-input
  acquisition). Unfreeze triggers: >2× error degradation on a future
  snapshot, or schema/methodology change.
- Backend/API phase: **GO** — recommended next phase: Spring Boot API
  + simple demo integration.
