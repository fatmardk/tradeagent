"""Build the analytical datasets from price_observation.parquet.

OFFER_LEVEL      : one row per observed seller offer (canonical fields added).
MARKET_SNAPSHOT  : one row per (observed_date, canonical_variant, grade segment);
                   median price is the primary V1 target.

Usage: python -m src.ingestion.build_analytical
"""
from __future__ import annotations

import pandas as pd

from src.normalization.variant import (
    canonical_brand,
    canonical_model,
    canonical_variant_key,
)

SRC = "data/processed/price_observation.parquet"
OUT_OFFER = "data/processed/offer_level.parquet"
OUT_MARKET = "data/processed/market_snapshot.parquet"


def build_offer_level(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["canonical_brand"] = df["brand"].map(canonical_brand)
    df["canonical_model"] = [
        canonical_model(b, m) for b, m in zip(df["brand"], df["model"])
    ]
    df["canonical_variant"] = [
        canonical_variant_key(b, m, s)
        for b, m, s in zip(df["brand"], df["model"], df["storage_gb"])
    ]
    df["observed_date"] = pd.to_datetime(df["observed_at"]).dt.date
    df["grade_segment"] = df["condition_grade"].fillna("UNKNOWN")
    df["exact_variant_price"] = ~df["is_from_price"].astype(bool)
    return df


def build_market_snapshot(offers: pd.DataFrame) -> pd.DataFrame:
    # only exact variant prices with a resolvable canonical variant
    base = offers[offers["exact_variant_price"] & offers["canonical_variant"].notna()]
    grp = base.groupby(["observed_date", "canonical_variant", "grade_segment"], as_index=False)
    snap = grp.agg(
        canonical_brand=("canonical_brand", "first"),
        canonical_model=("canonical_model", "first"),
        storage_gb=("storage_gb", "first"),
        n_offers=("price", "size"),
        price_median=("price", "median"),
        price_mean=("price", "mean"),
        price_min=("price", "min"),
        price_max=("price", "max"),
        price_q25=("price", lambda s: s.quantile(0.25)),
        price_q75=("price", lambda s: s.quantile(0.75)),
        n_sellers=("source_seller_id", lambda s: s.notna().nunique() and s.nunique()),
        n_sources=("source_id", "nunique"),
        n_products=("source_product_id", lambda s: s.nunique()),
        pct_missing_seller=("source_seller_id", lambda s: s.isna().mean()),
    )
    snap["n_sellers"] = (
        base.groupby(["observed_date", "canonical_variant", "grade_segment"])["source_seller_id"]
        .apply(lambda s: s.dropna().nunique())
        .values
    )
    return snap


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=SRC)
    ap.add_argument("--out-offer", default=OUT_OFFER)
    ap.add_argument("--out-market", default=OUT_MARKET)
    a = ap.parse_args()
    df = pd.read_parquet(a.src)
    offers = build_offer_level(df)
    offers.to_parquet(a.out_offer, index=False)
    snap = build_market_snapshot(offers)
    snap.to_parquet(a.out_market, index=False)
    print(f"offer_level     : {len(offers)} rows -> {a.out_offer}")
    print(f"market_snapshot : {len(snap)} rows -> {a.out_market}")
    print(f"  unique canonical variants: {snap.canonical_variant.nunique()}")
    print(f"  grade segments: {snap.grade_segment.value_counts().to_dict()}")
    print(f"  variants with >=3 offers: {(snap.n_offers>=3).sum()}")
    print(f"  variants with >=2 sellers: {(snap.n_sellers>=2).sum()}")


if __name__ == "__main__":
    main()
