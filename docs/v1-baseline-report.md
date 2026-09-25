# V1 Baseline — Market Median Price (Grade A, Snapshot 1)

- Rows: 371 canonical variants, grade segment A only
- 262 models, 16 brands
- Target: median seller offer per (date, canonical_variant, grade)
- Eval: GroupKFold(5) grouped by canonical_model — cross-sectional, NOT chronological

| model | MAE (TRY) | RMSE (TRY) | MAPE |
|---|---|---|---|
| global_median | 18,307 | 28,279 | 65.2% |
| brand_median | 15,019 | 22,062 | 60.4% |
| model_median (unseen-model eval) | 15,019 | 22,062 | 60.4% |
| HistGBR — unseen model (strict) | 9,717 | 15,459 | 32.0% |
| HistGBR — unseen variant (interp) | 10,181 | 16,110 | 34.0% |
