"""V1.1 — true out-of-time evaluation: train on Snapshot 1, test on Snapshot 2.

Compares against persistence baselines:
  last_price     : most recent S1 offer price for the variant
  variant_median : S1 market median for the variant
  brand_median   : S1 median across the brand
  V1 (HistGBR)   : trained on ALL S1 grade-A market rows

Usage: python -m src.model.evaluate_oot \
    [--s1-snap market_snapshot.parquet] [--s2-snap market_snapshot_s2.parquet]
    [--s1-offer offer_level.parquet] [--s2-offer offer_level_s2.parquet]
"""
from __future__ import annotations

import argparse
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

FEATURES = ["canonical_brand", "canonical_model", "storage_gb"]
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
    ap.add_argument("--s1-snap", default="data/processed/market_snapshot.parquet")
    ap.add_argument("--s2-snap", default="data/processed/market_snapshot_s2.parquet")
    ap.add_argument("--s1-offer", default="data/processed/offer_level.parquet")
    ap.add_argument("--s2-offer", default="data/processed/offer_level_s2.parquet")
    args = ap.parse_args()

    s1 = pd.read_parquet(args.s1_snap)
    s2 = pd.read_parquet(args.s2_snap)
    a1 = s1[s1.grade_segment == GRADE].copy()
    a2 = s2[s2.grade_segment == GRADE].copy()

    v1_set = set(a1.canonical_variant)
    v2_set = set(a2.canonical_variant)
    shared = v1_set & v2_set
    print(f"S1 variants(A): {len(v1_set)}  S2 variants(A): {len(v2_set)}")
    print(f"shared: {len(shared)}  new-in-S2: {len(v2_set - v1_set)}  "
          f"disappeared: {len(v1_set - v2_set)}")

    # ---- drift on shared variants ----
    j = a1.merge(a2, on="canonical_variant", suffixes=("_s1", "_s2"))
    j["delta"] = j.price_median_s2 - j.price_median_s1
    j["delta_pct"] = j.delta / j.price_median_s1 * 100
    print(f"\n--- drift (shared A variants, S1 median -> S2 median) ---")
    print(f"mean {j.delta.mean():+,.0f} TRY | median {j.delta.median():+,.0f} | "
          f"mean % {j.delta_pct.mean():+.2f} | median % {j.delta_pct.median():+.2f}")
    print(f"unchanged: {(j.delta == 0).mean():.0%}  "
          f"|abs|%<=5: {(j.delta_pct.abs() <= 5).mean():.0%}")

    # ---- train V1 on ALL S1 A rows ----
    # canonical_model has 262 levels > HistGBR's 255-category limit on the
    # full-S1 fit (folds stayed under). Fit one model per brand instead —
    # model cardinality within a brand is always <255. Same features/target.
    def new_gbr():
        return HistGradientBoostingRegressor(
            categorical_features=[0], max_iter=300,
            learning_rate=0.08, min_samples_leaf=5, random_state=0)

    models = {}
    a1["model_ord"] = a1.groupby("canonical_brand")["canonical_model"] \
                        .transform(lambda s: s.astype("category").cat.codes)
    for brand, g in a1.groupby("canonical_brand"):
        cats = g["canonical_model"].astype("category").cat.categories
        m = new_gbr().fit(g[["model_ord", "storage_gb"]],
                          np.log(g.price_median))
        models[brand] = (m, cats)
    global_model = HistGradientBoostingRegressor(
        max_iter=300, learning_rate=0.08, min_samples_leaf=5,
        random_state=0).fit(a1[["storage_gb"]], np.log(a1.price_median))

    # ---- predict S2 shared variants ----
    def predict_v1(row):
        pack = models.get(row["canonical_brand_s2"])
        if pack is None:
            return float(np.exp(global_model.predict(
                [[row["storage_gb_s2"]]])[0]))
        m, cats = pack
        try:
            code = list(cats).index(row["canonical_model_s2"])
        except ValueError:
            return float(np.exp(global_model.predict(
                [[row["storage_gb_s2"]]])[0]))
        return float(np.exp(m.predict([[code, row["storage_gb_s2"]]])[0]))

    j["pred_v1"] = j.apply(predict_v1, axis=1)

    # baselines
    o1 = pd.read_parquet(args.s1_offer)
    o1 = o1[o1.grade_segment == GRADE]
    last = (o1.sort_values("observed_at")
              .groupby("canonical_variant").price.last())
    j["pred_last"] = j.canonical_variant.map(last)
    j["pred_var_med"] = j.price_median_s1
    brand_med = a1.groupby("canonical_brand").price_median.median()
    j["pred_brand"] = j.canonical_brand_s1.map(brand_med)

    # ---- new-in-S2 variants: persistence baselines can't predict; V1 can ----
    new = a2[~a2.canonical_variant.isin(v1_set)].copy()
    s1_models = set(a1.canonical_model)
    if len(new):
        new["model_ord"] = new["canonical_model"].map(
            {m: i for i, m in enumerate(sorted(s1_models))})
        new["pred_v1"] = new.apply(
            lambda r: predict_v1({"canonical_brand_s2": r.canonical_brand,
                                  "canonical_model_s2": r.canonical_model,
                                  "storage_gb_s2": r.storage_gb}), axis=1)
        new["pred_brand"] = new.canonical_brand.map(brand_med)
        seen = new.canonical_model.isin(s1_models)
        print(f"\n--- new-in-S2 variants (n={len(new)}, "
              f"{seen.sum()} with S1-seen model) ---")
        for col, lab in [("pred_v1", "V1 HistGBR"), ("pred_brand", "brand_median")]:
            n, mae, rmse, mape = metrics(new.price_median.values, new[col].values)
            print(f"{lab:22} {n:>4} {mae:10,.0f} {rmse:10,.0f} {mape:6.1f}%")
        ns = new[seen]
        if len(ns):
            n, mae, rmse, mape = metrics(ns.price_median.values, ns.pred_v1.values)
            print(f"V1 on S1-seen models only: n={n} MAE={mae:,.0f} MAPE={mape:.1f}%")

    y = j.price_median_s2.values
    print("\n--- OOT metrics (S2 shared variants, n=%d) ---" % len(j))
    print(f"{'predictor':22} {'n':>4} {'MAE':>10} {'RMSE':>10} {'MAPE':>7}")
    for c, lab in [("pred_last", "last_price"),
                   ("pred_var_med", "variant_median"),
                   ("pred_brand", "brand_median"),
                   ("pred_v1", "V1 HistGBR")]:
        n, mae, rmse, mape = metrics(y, j[c].values)
        print(f"{lab:22} {n:>4} {mae:10,.0f} {rmse:10,.0f} {mape:6.1f}%")

    # ---- breakdowns ----
    j["band"] = pd.qcut(j.price_median_s1, 4,
                        labels=["<12k", "12-22k", "22-51k", ">51k"])
    j["cov"] = pd.cut(j.n_offers_s2, [0, 1, 4, 1e9],
                      labels=["1 offer", "2-4", "5+"])
    for dim in ["canonical_brand_s1", "band", "cov"]:
        print(f"\n--- MAE by {dim} (V1) ---")
        t = j.groupby(dim, observed=True).apply(
            lambda g: pd.Series({"n": len(g),
                                 "mae": np.abs(g.pred_v1 - g.price_median_s2).mean(),
                                 "mape": (np.abs(g.pred_v1 - g.price_median_s2)
                                          / g.price_median_s2 * 100).mean()}),
            include_groups=False).sort_values("mae", ascending=False)
        print(t.head(15).round(0).to_string())

    j.to_parquet("data/processed/oot_eval_s1_s2.parquet", index=False)
    print("\nwrote data/processed/oot_eval_s1_s2.parquet")


if __name__ == "__main__":
    main()
