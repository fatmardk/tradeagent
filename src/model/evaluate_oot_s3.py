"""OOT evaluation v2 — train/learn on S1+S2 combined, test on Snapshot 3.

Mirrors the production engine: history = combined market snapshots +
offer level. Predictors:
  variant_median        : latest per-variant market median (market path)
  last_price            : latest offer price for the variant
  cold_start_fallback   : median hierarchy (model->brand+storage->brand)
  brand_median          : brand median
  V1 (HistGBR)          : per-brand model, trained on history A rows only

Seen variants report persistence baselines; unseen variants report the
fallback chain + V1. Error vs observation age is bucketed by
days_since_last_observation (S3 date - latest history obs for the
variant): answers whether stale S1 medians degrade vs fresh S2 medians.

Usage: python -m src.model.evaluate_oot_s3
"""
from __future__ import annotations

import argparse
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from src.market.cold_start import FallbackEstimator
from src.market.valuation import MarketEstimator

GRADE = "A"
warnings.filterwarnings("ignore", message="X does not have valid feature names")


def metrics(y, p):
    m = np.isfinite(p)
    y, p = y[m], p[m]
    return (len(y), np.mean(np.abs(y - p)),
            float(np.sqrt(np.mean((y - p) ** 2))),
            np.mean(np.abs(y - p) / y) * 100)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hist-snap",
                    default="data/processed/market_snapshot_combined.parquet")
    ap.add_argument("--hist-offer",
                    default="data/processed/offer_level_combined.parquet")
    ap.add_argument("--test-snap",
                    default="data/processed/market_snapshot_s3.parquet")
    ap.add_argument("--out",
                    default="data/processed/oot_eval_hist_s3.parquet")
    args = ap.parse_args()

    hist = pd.read_parquet(args.hist_snap)
    test = pd.read_parquet(args.test_snap)
    ah = hist[hist.grade_segment == GRADE].copy()
    at = test[test.grade_segment == GRADE].copy()
    test_date = at.observed_date.max()

    vh, vt = set(ah.canonical_variant), set(at.canonical_variant)
    shared, new_v = vh & vt, vt - vh
    print(f"history dates: {sorted(str(d) for d in ah.observed_date.unique())}"
          f"  test date: {test_date}")
    print(f"hist variants(A): {len(vh)}  test variants(A): {len(vt)}")
    print(f"shared: {len(shared)}  new-in-S3: {len(new_v)}  "
          f"disappeared: {len(vh - vt)}")

    # ---- latest market observation per variant (production path) ----
    est = MarketEstimator(hist, max_obs_age_days=10_000)  # no staleness cut
    latest_obs = est.latest.reset_index()
    latest_obs = latest_obs[latest_obs.grade_segment == GRADE] \
        .set_index("canonical_variant")

    j = at[at.canonical_variant.isin(shared)].copy()
    j = j.merge(latest_obs[["price_median", "observed_date"]],
                left_on="canonical_variant", right_index=True,
                suffixes=("", "_hist"))
    j["days_since_obs"] = (test_date - j.observed_date).map(
        lambda d: d.days)

    # ---- baselines on shared ----
    j["pred_var_med"] = j.price_median_hist
    o = pd.read_parquet(args.hist_offer)
    o = o[o.grade_segment == GRADE]
    last = (o.sort_values("observed_at")
             .groupby("canonical_variant").price.last())
    j["pred_last"] = j.canonical_variant.map(last)
    brand_med = ah.groupby("canonical_brand").price_median.median()
    j["pred_brand"] = j.canonical_brand.map(brand_med)

    # V1 per-brand HistGBR on history
    ah["model_ord"] = ah.groupby("canonical_brand")["canonical_model"] \
                        .transform(lambda s: s.astype("category").cat.codes)
    models = {}
    for brand, g in ah.groupby("canonical_brand"):
        cats = g["canonical_model"].astype("category").cat.categories
        m = HistGradientBoostingRegressor(
            categorical_features=[0], max_iter=300, learning_rate=0.08,
            min_samples_leaf=5, random_state=0).fit(
            g[["model_ord", "storage_gb"]], np.log(g.price_median))
        models[brand] = (m, cats)
    gm = HistGradientBoostingRegressor(
        max_iter=300, learning_rate=0.08, min_samples_leaf=5,
        random_state=0).fit(ah[["storage_gb"]], np.log(ah.price_median))

    def predict_v1(brand, model, gb):
        pack = models.get(brand)
        if pack is None:
            return float(np.exp(gm.predict([[gb]])[0]))
        m, cats = pack
        try:
            code = list(cats).index(model)
        except ValueError:
            return float(np.exp(gm.predict([[gb]])[0]))
        return float(np.exp(m.predict([[code, gb]])[0]))

    j["pred_v1"] = j.apply(
        lambda r: predict_v1(r.canonical_brand, r.canonical_model,
                             r.storage_gb), axis=1)

    y = j.price_median.values
    print(f"\n--- SEEN variants: history -> S3 (n={len(j)}) ---")
    print(f"{'predictor':22} {'n':>4} {'MAE':>10} {'RMSE':>10} {'MAPE':>7}")
    for c, lab in [("pred_var_med", "variant_median(latest)"),
                   ("pred_last", "last_price"),
                   ("pred_brand", "brand_median"),
                   ("pred_v1", "V1 HistGBR")]:
        n, mae, rmse, mape = metrics(y, j[c].values)
        print(f"{lab:22} {n:>4} {mae:10,.0f} {rmse:10,.0f} {mape:6.1f}%")

    # ---- error vs observation age ----
    print("\n--- error vs days_since_last_market_observation "
          "(variant_median) ---")
    j["abs_err"] = np.abs(j.pred_var_med - j.price_median)
    j["ape"] = j.abs_err / j.price_median * 100
    t = j.groupby("days_since_obs").agg(
        n=("abs_err", "size"), mae=("abs_err", "mean"),
        mape=("ape", "mean")).round(1)
    print(t.to_string())

    # ---- UNSEEN variants ----
    new = at[~at.canonical_variant.isin(vh)].copy()
    if len(new):
        fb = FallbackEstimator(hist)
        fb_preds = [fb.estimate(r.canonical_brand, r.canonical_model,
                                r.storage_gb) for r in new.itertuples()]
        new["pred_fb"] = [e.market_value_point for e in fb_preds]
        new["fb_method"] = [e.valuation_method for e in fb_preds]
        new["pred_v1"] = new.apply(
            lambda r: predict_v1(r.canonical_brand, r.canonical_model,
                                 r.storage_gb), axis=1)
        new["pred_brand"] = new.canonical_brand.map(brand_med)
        print(f"\n--- UNSEEN variants in S3 (n={len(new)}) ---")
        print(new.fb_method.value_counts().to_string())
        for c, lab in [("pred_fb", "cold_start_fallback"),
                       ("pred_v1", "V1 HistGBR"),
                       ("pred_brand", "brand_median")]:
            n, mae, rmse, mape = metrics(new.price_median.values,
                                         new[c].values)
            print(f"{lab:22} {n:>4} {mae:10,.0f} {rmse:10,.0f} {mape:6.1f}%")
        seen_model = new.canonical_model.isin(set(ah.canonical_model))
        ns = new[seen_model]
        if len(ns):
            for c, lab in [("pred_fb", "cold_start_fallback"),
                           ("pred_v1", "V1 HistGBR")]:
                n, mae, rmse, mape = metrics(ns.price_median.values,
                                             ns[c].values)
                print(f"{lab} on seen-model subset n={n}: "
                      f"MAE={mae:,.0f} MAPE={mape:.1f}%")

    # ---- drift shared S2->S3 (intra-day) ----
    j["delta_pct"] = (j.price_median - j.price_median_hist) \
        / j.price_median_hist * 100
    print(f"\n--- drift latest-hist-median -> S3 (shared, n={len(j)}) ---")
    print(f"median % {j.delta_pct.median():+.2f} | mean % "
          f"{j.delta_pct.mean():+.2f} | unchanged "
          f"{(j.delta_pct == 0).mean():.0%} | |%|<=5 "
          f"{(j.delta_pct.abs() <= 5).mean():.0%}")

    j.to_parquet(args.out, index=False)
    if len(new):
        new.to_parquet(args.out.replace(".parquet", "_new.parquet"),
                       index=False)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
