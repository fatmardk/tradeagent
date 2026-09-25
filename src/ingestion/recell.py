"""ReCell / ahsan81 "Used Phones & Tablets Pricing" ingestion.

Raw file: data/raw/recell/used_phone_data.csv (immutable).
Source mirror: github.com/JesusTorres98/ReCell (same lineage as Kaggle
ahsan81/used-handheld-device-data; collected 2021; CC0 on Kaggle page).

Produces data/interim/recell.parquet with canonical column names plus the
derived ratio column used_to_new_ratio — a STRUCTURAL learning target only,
never a 2026 TRY price.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ingestion.manifest import write_manifest

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "recell" / "used_phone_data.csv"
OUT = ROOT / "data" / "interim" / "recell.parquet"
SOURCE_URL = "https://www.kaggle.com/datasets/ahsan81/used-handheld-device-data"

EXPECTED_COLUMNS = {
    "brand_name", "os", "screen_size", "4g", "5g", "main_camera_mp",
    "selfie_camera_mp", "int_memory", "ram", "battery", "weight",
    "release_year", "days_used", "new_price", "used_price",
}


def load_raw(path: Path = RAW) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = EXPECTED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"ReCell schema drift — missing columns: {missing}")
    return df


def transform(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={
        "brand_name": "brand",
        "4g": "has_4g",
        "5g": "has_5g",
        "int_memory": "storage_gb",
        "battery": "battery_capacity_mah",
    })
    df["brand"] = df["brand"].str.strip().str.title()
    df["has_4g"] = df["has_4g"].str.lower().eq("yes")
    df["has_5g"] = df["has_5g"].str.lower().eq("yes")
    # Structural ratio — same-period same-model prices cancel out currency/inflation.
    df["used_to_new_ratio"] = df["used_price"] / df["new_price"]
    df["price_kind"] = "ACADEMIC_NORMALIZED"  # NOT a market price kind
    df["is_synthetic"] = False
    return df


def run() -> pd.DataFrame:
    df = transform(load_raw())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    write_manifest(
        dataset_name="recell",
        raw_path=RAW,
        source_url=SOURCE_URL,
        license="CC0 (Kaggle page); GitHub mirror used for file",
        record_count=len(df),
        notes="Normalized prices (~EUR scale per community notes). "
              "used_to_new_ratio is a structural target, NOT a currency price.",
    )
    return df


if __name__ == "__main__":
    run()
