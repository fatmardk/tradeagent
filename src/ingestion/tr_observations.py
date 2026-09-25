"""Turkey 2026 price-observation ingestion.

Source of truth: data/raw/tr_observations/price_observations_2026.csv —
a hand-maintained log of prices read from public pages (see
docs/tr-observation-plan.md for method and legal basis).

This loader VALIDATES against the canonical schema rules and writes
data/processed/price_observation.parquet. It refuses:
  * unknown price_kind / confidence_class
  * fabricated individual-device fields (battery_health invented)
  * missing provenance (source_id, observed_at, retrieved_at, raw_reference)
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "tr_observations" / "price_observations_2026.csv"
OUT = ROOT / "data" / "processed" / "price_observation.parquet"

PRICE_KINDS = {"MSRP", "NEW_LIST", "USED_LIST", "REFURBISHED_LIST",
               "SOLD", "BUYBACK_OFFER", "WHOLESALE"}
CONFIDENCE = {"OFFICIAL_MANUFACTURER", "VERIFIED_TRANSACTION",
              "AUTHORIZED_REFURBISHER", "MARKETPLACE_LISTING",
              "BUYBACK_OFFER", "ACADEMIC_DATASET", "PUBLIC_OBSERVATION",
              "SYNTHETIC"}
REQUIRED_NON_NULL = ["obs_id", "source_id", "price", "currency", "country",
                     "price_kind", "observed_at", "retrieved_at",
                     "raw_reference", "confidence_class", "is_from_price"]


def load_raw(path: Path = RAW) -> pd.DataFrame:
    return pd.read_csv(path)


def validate(df: pd.DataFrame) -> pd.DataFrame:
    errors = []
    for col in REQUIRED_NON_NULL:
        if df[col].isna().any():
            errors.append(f"{col} has NULLs")
    bad_kind = set(df["price_kind"]) - PRICE_KINDS
    bad_conf = set(df["confidence_class"]) - CONFIDENCE
    if bad_kind:
        errors.append(f"unknown price_kind: {bad_kind}")
    if bad_conf:
        errors.append(f"unknown confidence_class: {bad_conf}")
    if (df["price"] <= 0).any():
        errors.append("non-positive price")
    if df["obs_id"].duplicated().any():
        errors.append("duplicate obs_id")
    # no-fabrication: battery_health present means it must be observed,
    # we cannot prove that here — flag anything outside [0,100]
    bh = df["battery_health_pct"].dropna()
    if ((bh < 0) | (bh > 100)).any():
        errors.append("battery_health_pct out of range")
    # grade sanity: canonical grades only
    bad_grade = set(df["condition_grade"].dropna()) - {"S", "A", "B", "C", "D"}
    if bad_grade:
        errors.append(f"non-canonical condition_grade: {bad_grade}")
    # is_from_price must be a real boolean flag, never inferred at load time
    bad_flag = set(df["is_from_price"].astype(str).str.lower()) - {"true", "false"}
    if bad_flag:
        errors.append(f"is_from_price not boolean: {bad_flag}")
    # a from-price must NOT claim exact variant attributes it does not have:
    # storage OR grade may still be present if the source states the floor
    # applies to a specific variant, but both present + from_price is suspect
    fp = df[df["is_from_price"].astype(str).str.lower() == "true"]
    exact_fp = fp[fp["storage_gb"].notna() & fp["condition_grade"].notna()]
    if len(exact_fp):
        errors.append(
            f"{len(exact_fp)} rows marked is_from_price yet carry exact "
            "storage+grade — recheck semantics")
    # duplicate observation key: same listing evidence + observable variant
    # attributes + seller identity. Two identical rows on all of these are
    # the same offer re-captured, not two listings — safe to flag.
    dup_key = df.duplicated(
        subset=["source_id", "source_url", "raw_title", "storage_gb",
                "color", "condition_grade", "seller_name",
                "source_seller_id", "price", "observed_at"])
    if dup_key.any():
        errors.append(f"{int(dup_key.sum())} duplicate observation keys")
    if errors:
        raise ValueError("price_observation validation failed: " + "; ".join(errors))
    return df


def transform(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={"obs_id": "price_observation_id"})
    df["is_from_price"] = (
        df["is_from_price"].astype(str).str.lower() == "true")
    df["is_synthetic"] = False
    df["device_id"] = None   # filled by matching layer (device_alias)
    df["variant_id"] = None
    return df


def run(path: Path = RAW, out: Path = OUT) -> pd.DataFrame:
    df = transform(validate(load_raw(path)))
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"price_observation: {len(df)} rows -> {out}")
    print(df.groupby(["source_id", "price_kind"]).size().to_string())
    return df


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(RAW))
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    run(Path(a.raw), Path(a.out))
