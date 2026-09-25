# V1.1 — Out-of-Time Evaluation: Snapshot 1 → Snapshot 2

- Train: Snapshot 1 only (observed 2026-09-16/17). Model, medians and
  baselines are fit exclusively on S1 — S2 was never used for fitting.
- Test: Snapshot 2 (observed 2026-09-25, ~8 days later).
- Scope: grade-A market rows (`price_median` per `(date, canonical_variant, grade=A)`).
- Script: `src/model/evaluate_oot.py`. Per-variant predictions:
  `data/processed/oot_eval_s1_s2.parquet`.

## Coverage

| | S1 | S2 |
|---|---:|---:|
| observations | 2,252 | 2,227 |
| grade-A canonical variants | 369 | 366 |

- **Shared** (in both): 325 variants → 327 eval rows (S1 spans two dates,
  so two variants carry two S1 rows each).
- **New in S2**: 41 variants (9 have an S1-seen canonical model).
- **Disappeared**: 44 variants. A disappeared listing is *not* assumed sold.

## Price drift (shared variants, S1 median → S2 median)

- Mean Δ **+61 TRY**, median Δ **0**; mean **+0.74%**, median **0.00%**.
- 40% of variants unchanged; 78% within ±5%.
- Largest movers are mostly thin-offer variants (single-offer medians):
  `galaxy-note-9|128` +98% (1 offer), `galaxy-a55|256` +55%,
  `galaxy-a73|128` −59%, `iphone-15|512` −40%.
- By brand, only Apple shows systematic drift (median +210 TRY, +0.5%);
  Huawei/Honor means are inflated by single-offer outliers.

## Out-of-time metrics — shared variants (n=327)

| predictor | n | MAE (₺) | RMSE (₺) | MAPE |
|---|---:|---:|---:|---:|
| variant_median (S1) | 327 | **1,333** | **3,797** | **4.3%** |
| last_price (S1) | 327 | 2,098 | 4,767 | 6.5% |
| V1 HistGBR (S1) | 327 | 10,338 | 16,250 | 31.6% |
| brand_median (S1) | 327 | 15,095 | 22,317 | 56.1% |

## New-in-S2 variants (n=41) — persistence baselines unavailable

| predictor | n | MAE (₺) | RMSE (₺) | MAPE |
|---|---:|---:|---:|---:|
| V1 HistGBR | 41 | 28,207 | 47,979 | 57.1% |
| brand_median | 41 | 30,815 | 48,042 | 96.1% |

## V1 error breakdowns (shared variants)

- **Brand**: best on Xiaomi ₺4.1k / Realme ₺3.8k / Tecno ₺3.3k; worst on
  Apple ₺19.7k (41% MAPE) and Huawei ₺12.7k (65%).
- **Price band**: MAE scales with price — `<12k` ₺2.5k, `12–22k` ₺4.2k,
  `22–51k` ₺12.0k, `>51k` ₺22.6k; MAPE roughly flat (27–40%).
- **Coverage**: thin S2 support hurts — `5+ offers` ₺17.1k MAE (expensive
  SKUs dominate this bucket), `2–4` ₺7.4k, `1 offer` ₺6.2k.

## Interpretation

1. **Persistence is the production answer for known variants.** S1 variant
   median predicts S2 with 4.3% MAPE — an 8-day-old market median is far
   more accurate than the cross-sectional model. V1's real role is
   *coverage gaps*: new/disappeared variants and unseen models.
2. **V1 on new variants is weak but beats the only alternative** (57% vs
   96% MAPE vs brand median). Error is dominated by premium new variants
   (iPhone 17 Pro/Pro Max entered S2 without S1 history).
3. **Drift is small and mostly stationary**: no broad repricing event in
   this window; movers are single-offer median noise, not market shifts.
4. Full-S1 V1 fit required per-brand HistGBR (262 model levels exceed
   HistGBR's 255-category cap) — a model-internal change only; features,
   target and training data are unchanged.

## Limitations

- Grade-A only; B/C/S preserved but not modelled (condition-aware work
  deferred per scope).
- Shared-variant population excludes new variants where the model is
  weakest; headline MAPE is therefore optimistic for coverage-gap use.
- 9 days is a short horizon; drift conclusions should not be extrapolated.
