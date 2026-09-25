"""Cold-start strategy comparison — unseen-variant prediction.

Evaluation: GroupKFold by canonical_variant on the combined S1+S2
market snapshot (grade A) — every test variant is fully unseen in train.
Secondary: temporal flavour — train S1, test on S2-new variants.

Baselines:
  A brand_median
  B brand+storage median (fallback: brand)
  C model median across other storages (fallback: B)
  D current-new-price ratio (needs exact variant new-price anchor)
  E ColdStartValueModel (per-brand HistGBR)

Usage: python -m src.model.cold_start_eval
"""
from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from src.model.cold_start import ColdStartValueModel

warnings.filterwarnings("ignore", message="X does not have valid feature names")

ROOT = Path(__file__).resolve().parents[2]
MARKET = ROOT / "data/processed/market_snapshot_combined.parquet"
OFFER = ROOT / "data/processed/offer_level_combined.parquet"
GRADE = "A"


def new_price_map(offer_df: pd.DataFrame) -> dict:
    """canonical_variant -> latest exact current-new price (MSRP or
    CURRENT_NEW_LIST; never from-price rows)."""
    d = offer_df[offer_df.price_kind.isin(["MSRP", "CURRENT_NEW_LIST"])
                 & offer_df.exact_variant_price].copy()
    d = d.dropna(subset=["canonical_variant"])
    latest = (d.sort_values("observed_at")
              .groupby("canonical_variant").price.last())
    return latest.to_dict()


def metrics(y, p):
    m = np.isfinite(p)
    y, p = y[m], p[m]
    if len(y) == 0:
        return (0, np.nan, np.nan, np.nan)
    mae = np.mean(np.abs(y - p))
    rmse = float(np.sqrt(np.mean((y - p) ** 2)))
    mape = np.mean(np.abs(y - p) / y) * 100
    smape = np.mean(2 * np.abs(y - p) / (np.abs(y) + np.abs(p))) * 100
    return (len(y), mae, rmse, mape, smape)


def predict_baselines(tr, te, nmap):
    out = {}
    brand_med = tr.groupby("canonical_brand").price_median.median()
    bs_med = tr.groupby(["canonical_brand", "storage_gb"]).price_median.median()
    model_med = tr.groupby("canonical_model").price_median.median()
    glob = tr.price_median.median()

    out["A_brand"] = te.canonical_brand.map(brand_med).fillna(glob)
    p = te.set_index(["canonical_brand", "storage_gb"]).index.map(bs_med)
    out["B_brand_storage"] = np.where(np.isfinite(p), p,
                                      out["A_brand"].values)
    pm = te.canonical_model.map(model_med)
    out["C_model"] = np.where(np.isfinite(pm), pm, out["B_brand_storage"])

    # D: refurb/new ratio learned per brand on train rows WITH an anchor
    trn = tr.copy()
    trn["new_price"] = trn.canonical_variant.map(nmap)
    anchored = trn.dropna(subset=["new_price"])
    anchored = anchored[anchored.new_price > 0]
    ratio = (anchored.price_median / anchored.new_price) \
        .groupby(anchored.canonical_brand).median()
    glob_ratio = float((anchored.price_median / anchored.new_price).median()) \
        if len(anchored) else np.nan
    np_te = te.canonical_variant.map(nmap)
    r = te.canonical_brand.map(ratio).fillna(glob_ratio)
    out["D_newprice_ratio"] = np_te * r  # NaN where no anchor
    return out


def evaluate(tr, te, nmap, label):
    preds = predict_baselines(tr, te, nmap)
    cs = ColdStartValueModel().fit(tr)
    preds["E_coldstart_ml"] = cs.predict(te).values
    y = te.price_median.values
    print(f"\n=== {label} (n={len(te)}) ===")
    print(f"{'strategy':22} {'n':>5} {'MAE':>9} {'RMSE':>9} {'MAPE':>7} {'sMAPE':>7}")
    for k, v in preds.items():
        n, mae, rmse, mape, smape = metrics(y, np.asarray(v, dtype=float))
        print(f"{k:22} {n:>5} {mae:9,.0f} {rmse:9,.0f} {mape:6.1f}% {smape:6.1f}%")
    te = te.copy()
    for k, v in preds.items():
        te["pred_" + k] = v
    return te


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", default=str(MARKET))
    ap.add_argument("--offer", default=str(OFFER))
    args = ap.parse_args()

    m = pd.read_parquet(args.market)
    df = m[m.grade_segment == GRADE].copy()
    nmap = new_price_map(pd.read_parquet(args.offer))
    print(f"grade-A market rows: {len(df)} | variants: "
          f"{df.canonical_variant.nunique()} | new-price anchors: "
          f"{df.canonical_variant.isin(nmap).sum()}")

    # --- CV: unseen-variant (grouped by variant) ---
    gkf = GroupKFold(5)
    cols = ["A_brand", "B_brand_storage", "C_model",
            "D_newprice_ratio", "E_coldstart_ml"]
    oof = {c: np.full(len(df), np.nan) for c in cols}
    for tr_i, te_i in gkf.split(df, groups=df.canonical_variant):
        tr, te = df.iloc[tr_i], df.iloc[te_i]
        pr = predict_baselines(tr, te, nmap)
        cs = ColdStartValueModel().fit(tr)
        for c in cols[:4]:
            oof[c][te_i] = np.asarray(pr[c], dtype=float)
        oof["E_coldstart_ml"][te_i] = cs.predict(te).values

    y = df.price_median.values
    print("\n=== unseen-variant CV (GroupKFold by canonical_variant) ===")
    print(f"{'strategy':22} {'n':>5} {'MAE':>9} {'RMSE':>9} {'MAPE':>7} {'sMAPE':>7}")
    for c in cols:
        n, mae, rmse, mape, smape = metrics(y, oof[c])
        print(f"{c:22} {n:>5} {mae:9,.0f} {rmse:9,.0f} {mape:6.1f}% {smape:6.1f}%")

    df2 = df.copy()
    for c in cols:
        df2["oof_" + c] = oof[c]
    df2.to_parquet(ROOT / "data/processed/coldstart_cv.parquet", index=False)

    # breakdowns for the ML strategy
    df2["ape_E"] = np.abs(df2.oof_E_coldstart_ml - df2.price_median) \
        / df2.price_median * 100
    df2["has_anchor"] = df2.canonical_variant.isin(nmap)
    for dim, lab in [("canonical_brand", "brand"), ("has_anchor", "new-price anchor")]:
        t = df2.groupby(dim).ape_E.agg(["count", "mean", "median"]).round(1)
        print(f"\n--- E_coldstart_ml MAPE by {lab} ---\n{t.to_string()}")

    # --- temporal: S1 train -> S2-new variants ---
    s1 = df[df.snapshot_id == "S1"]
    s2new = df[(df.snapshot_id == "S2")
               & ~df.canonical_variant.isin(set(s1.canonical_variant))]
    if len(s2new):
        evaluate(s1, s2new, nmap, "S1->S2-new temporal cold-start")


if __name__ == "__main__":
    main()
