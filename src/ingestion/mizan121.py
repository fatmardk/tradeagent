"""mizan121 used-phone-dataset ingestion.

Raw file: data/raw/mizan121/used_phone.csv (immutable).
Source: kaggle.com/datasets/mizan121/used-phone-dataset — uploader states the
file came from a Google Drive share; provenance is UNVERIFIED. Prices are INR
(Indian market). Use for condition/battery relationship experiments; flag as
unverified-real until profiling confirms plausibility.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ingestion.manifest import write_manifest

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "mizan121" / "used_phone.csv"
OUT = ROOT / "data" / "interim" / "mizan121.parquet"
SOURCE_URL = "https://www.kaggle.com/datasets/mizan121/used-phone-dataset"

EXPECTED_COLUMNS = {
    "brand", "model", "ram_gb", "storage_gb", "condition",
    "battery_health", "age_years", "original_price", "resale_price",
}

# Canonical grade map — seller/source vocabularies differ, we keep one axis.
CONDITION_MAP = {
    "like new": "A",
    "good": "B",
    "fair": "C",
    "poor": "D",
}


def load_raw(path: Path = RAW) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = EXPECTED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"mizan121 schema drift — missing columns: {missing}")
    return df


def transform(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["brand"] = df["brand"].str.strip().str.title()
    df["model"] = df["model"].str.strip()
    df["condition_grade"] = df["condition"].str.strip().str.lower().map(CONDITION_MAP)
    df["resale_to_original_ratio"] = df["resale_price"] / df["original_price"]
    df["currency"] = "INR"
    df["country"] = "IN"
    df["price_kind"] = "USED_LIST"  # listing-level resale prices, not verified sales
    df["is_synthetic"] = False  # provisional — quality report must confirm
    return df


def run() -> pd.DataFrame:
    df = transform(load_raw())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    write_manifest(
        dataset_name="mizan121",
        raw_path=RAW,
        source_url=SOURCE_URL,
        license="Unspecified (Kaggle page); provenance unverified",
        record_count=len(df),
        notes="Indian used-market rows. Condition/battery effects only; "
              "never a TRY target.",
    )
    return df


if __name__ == "__main__":
    run()
