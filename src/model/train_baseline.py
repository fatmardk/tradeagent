"""V1 baseline: predict market median price per canonical variant.

Scope: grade-A segment of MARKET_SNAPSHOT (dominant, 371 variants).
B/C/S/UNKNOWN excluded — coverage too thin to support condition effects.

Leakage control: GroupKFold by canonical_model, so no storage variant of a
model seen in train leaks into test. Rows are unique variants within the A
segment, so offer-level leakage is structurally impossible here.

Usage: python -m src.model.train_baseline
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold

SNAP = "data/processed/market_snapshot.parquet"
REPORT = "docs/v1-baseline-report.md"

FEATURES = ["canonical_brand", "canonical_model", "storage_gb"]
CATS = ["canonical_brand", "canonical_model"]


def metrics(y, p):
    mae = np.mean(np.abs(y - p))
    rmse = float(np.sqrt(np.mean((y - p) ** 2)))
    mape = np.mean(np.abs(y - p) / y) * 100
    return mae, rmse, mape


def fit_predict_naive(train, test, cols):
    """Median of `cols` on train; fallback to broader levels then global."""
    out = []
    for _, r in test.iterrows():
        pred = np.nan
        for level in [cols, cols[:-1], ["canonical_brand"]]:
            mask = np.ones(len(train), bool)
            for c in level:
                mask &= train[c].values == r[c]
            if mask.any():
                pred = train.loc[mask, "price_median"].median()
                break
        if np.isnan(pred):
            pred = train.price_median.median()
        out.append(pred)
    return np.array(out)


def main() -> None:
    s = pd.read_parquet(SNAP)
    df = s[s.grade_segment == "A"].copy()
    df["y"] = np.log(df["price_median"])
    print(f"V1 dataset: {len(df)} variants (grade A), "
          f"{df.canonical_model.nunique()} models, {df.canonical_brand.nunique()} brands")

    X = df[FEATURES].astype({"canonical_brand": "category",
                             "canonical_model": "category"})

    def new_gbr():
        return HistGradientBoostingRegressor(
            categorical_features=[0, 1], max_iter=300,
            learning_rate=0.08, min_samples_leaf=5, random_state=0)

    # strict: GroupKFold by model — every test variant is an unseen model
    gkf = GroupKFold(n_splits=5)
    oof = np.zeros(len(df))
    oof_nb, oof_nm = np.zeros(len(df)), np.zeros(len(df))
    for tr, te in gkf.split(df, groups=df["canonical_model"]):
        trd, ted = df.iloc[tr], df.iloc[te]
        m = new_gbr().fit(X.iloc[tr], trd["y"])
        oof[te] = np.exp(m.predict(X.iloc[te]))
        oof_nb[te] = fit_predict_naive(trd, ted, ["canonical_brand"])
        oof_nm[te] = fit_predict_naive(trd, ted,
                                       ["canonical_brand", "canonical_model"])

    # interpolation: random split — seen models, unseen variants (common case)
    from sklearn.model_selection import KFold
    oof_interp = np.zeros(len(df))
    for tr, te in KFold(n_splits=5, shuffle=True, random_state=0).split(df):
        m = new_gbr().fit(X.iloc[tr], df.iloc[tr]["y"])
        oof_interp[te] = np.exp(m.predict(X.iloc[te]))

    y = df.price_median.values
    res = {
        "global_median": metrics(y, np.full(len(y), np.median(y))),
        "brand_median": metrics(y, oof_nb),
        "model_median (unseen-model eval)": metrics(y, oof_nm),
        "HistGBR — unseen model (strict)": metrics(y, oof),
        "HistGBR — unseen variant (interp)": metrics(y, oof_interp),
    }
    print(f"{'model':38} {'MAE':>10} {'RMSE':>10} {'MAPE':>8}")
    for k, (mae, rmse, mape) in res.items():
        print(f"{k:38} {mae:10,.0f} {rmse:10,.0f} {mape:7.1f}%")

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("# V1 Baseline — Market Median Price (Grade A, Snapshot 1)\n\n")
        f.write(f"- Rows: {len(df)} canonical variants, grade segment A only\n")
                # noqa
        f.write(f"- {df.canonical_model.nunique()} models, "
                f"{df.canonical_brand.nunique()} brands\n")
        f.write("- Target: median seller offer per "
                "(date, canonical_variant, grade)\n")
        f.write("- Eval: GroupKFold(5) grouped by canonical_model — "
                "cross-sectional, NOT chronological\n\n")
        f.write("| model | MAE (TRY) | RMSE (TRY) | MAPE |\n|---|---|---|---|\n")
        for k, (mae, rmse, mape) in res.items():
            f.write(f"| {k} | {mae:,.0f} | {rmse:,.0f} | {mape:.1f}% |\n")
    print("report ->", REPORT)


if __name__ == "__main__":
    main()
