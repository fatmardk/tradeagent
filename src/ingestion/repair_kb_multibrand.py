"""Merge the multi-brand real repair dataset into a unified repair KB.

Inputs
------
* data/repair/real_repair_observations.csv — Telefon Profesörü (FULL_REPAIR,
  INDEPENDENT_REPAIR_SERVICE) + ErCorp (PART_ONLY, PART_SUPPLIER), all real
  public-page observations with provenance preserved.
* data/processed/repair_cost_observation.parquet — Samsung TR authorized
  service table (FULL_REPAIR, AUTHORIZED_SERVICE), built by repair_kb.py.

Output: data/processed/repair_cost_observation_multibrand.parquet — one
superset table; the Samsung-only parquet stays untouched for its own
ingestion tests.

Canon
-----
* repair_type: lower snake canonical ids (screen_module, battery, ...).
* repair_price_type: FULL_REPAIR | PART_ONLY — never mixed; PART_ONLY is
  never expanded into a full repair cost.
* source_type provenance order (see rules/dedup_and_provenance.md):
  OFFICIAL_MANUFACTURER < AUTHORIZED_SERVICE < INDEPENDENT_REPAIR_SERVICE
  < PART_SUPPLIER.
* part/labor split stays NULL unless the source publishes it — never
  reverse-engineered.

Usage: python -m src.ingestion.repair_kb_multibrand
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OBS = ROOT / "data/repair/real_repair_observations.csv"
SAMSUNG = ROOT / "data/processed/repair_cost_observation.parquet"
OUT = ROOT / "data/processed/repair_cost_observation_multibrand.parquet"

REPAIR_TYPE_MAP = {
    "BATTERY": "battery",
    "SCREEN_MODULE": "screen_module",
    "SCREEN_ECO": "screen_eco",
    "OUTER_SCREEN": "outer_screen",
    "BACK_GLASS": "back_glass",
    "FRAME": "frame",
    "HOUSING": "frame",
    "CHARGING_PORT": "charging_port",
    "CAMERA": "camera_rear",
    "CAMERA_REAR": "camera_rear",
    "CAMERA_FRONT": "camera_front",
    "EARPIECE": "earpiece",
    "SPEAKER": "speaker",
    "MAINBOARD": "mainboard",
    "BUTTON_FLEX": "other",
    "OTHER": "other",
}

CANONICAL_QUALITY = {
    "ORIGINAL", "SERVICE", "HIGH_QUALITY", "COMPATIBLE",
    "PREMIUM", "PULLED", "REFURBISHED", "UNKNOWN",
}


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(name).strip().lower())
    return s.strip("-")


def model_key(brand: str, model_name: str) -> str:
    return f"{brand}::{slugify(model_name)}"


def load_new_observations(path: Path = OBS) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df = df[df.price.str.strip() != ""]
    df["total_repair_cost"] = df.price.astype(float)
    df = df[df.total_repair_cost > 0]
    df["repair_type"] = df.repair_type.map(REPAIR_TYPE_MAP)
    df = df[df.repair_type.notna()]
    df["brand"] = df.brand.str.upper()
    df["model_key"] = [model_key(b, m)
                       for b, m in zip(df.brand, df.model_name)]
    df["repair_price_type"] = df.repair_price_type.str.upper()
    df["includes_labor"] = df.includes_labor.str.lower() == "true"
    df["repair_quality"] = df.repair_quality.str.upper()
    df.loc[~df.repair_quality.isin(CANONICAL_QUALITY),
           "repair_quality"] = "UNKNOWN"
    return df


def load_samsung(path: Path = SAMSUNG) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["brand"] = "SAMSUNG"
    df["model_code"] = df.device_id
    df["model_key"] = [model_key("SAMSUNG", m) for m in df.model_name]
    df["repair_price_type"] = "FULL_REPAIR"
    df["includes_labor"] = True  # page states part+labor included
    df["repair_quality"] = "SERVICE"
    df["source_name"] = "Samsung TR Destek"
    df["source_type"] = "AUTHORIZED_SERVICE"
    df["source_reference"] = df.source_url
    df["source_quality_label"] = df.part_quality
    df["variant"] = ""
    df["model_name_src"] = df.model_name
    return df


def unify(sam: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "variant_id", "device_id", "model_name", "model_year", "series",
        "repair_type", "part_type", "part_quality",
        "part_price", "labor_cost", "total_repair_cost",
        "repair_price_type", "includes_labor",
        "repair_quality", "source_quality_label",
        "brand", "model_code", "model_key", "variant",
        "currency", "country", "source_id", "source_name", "source_type",
        "source_url", "source_reference",
        "observed_at", "retrieved_at", "is_synthetic", "notes",
    ]
    sam2 = sam.copy()
    new2 = pd.DataFrame({
        "variant_id": None,
        "device_id": new.model_code.where(new.model_code != "", None),
        "model_name": new.model_name,
        "model_year": None,
        "series": new.series,
        "repair_type": new.repair_type,
        "part_type": None,
        "part_quality": new.repair_quality,
        # part/labor split unknown unless published; PART_ONLY rows put the
        # part price in part_price AND total so `price` stays the observed
        # quantity in both read paths.
        "part_price": new.total_repair_cost.where(
            new.repair_price_type == "PART_ONLY"),
        "labor_cost": None,
        "total_repair_cost": new.total_repair_cost,
        "repair_price_type": new.repair_price_type,
        "includes_labor": new.includes_labor,
        "repair_quality": new.repair_quality,
        "source_quality_label": new.source_quality_label,
        "brand": new.brand,
        "model_code": new.model_code.where(new.model_code != "", None),
        "model_key": new.model_key,
        "variant": new.variant,
        "currency": new.currency,
        "country": "TR",
        "source_id": new.source_name,
        "source_name": new.source_name,
        "source_type": new.source_type,
        "source_url": new.source_reference,
        "source_reference": new.source_reference,
        "observed_at": new.observed_at,
        "retrieved_at": new.observed_at,
        "is_synthetic": 0,
        "notes": new.notes.where(new.notes != "", None),
    })
    sam2["repair_quality"] = sam2.get("repair_quality", "SERVICE")
    out = pd.concat([sam2[cols], new2[cols]], ignore_index=True)
    out.insert(0, "repair_cost_observation_id",
               [f"rep-mb-{i:05d}" for i in range(1, len(out) + 1)])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--obs", default=str(OBS))
    ap.add_argument("--samsung", default=str(SAMSUNG))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    sam = load_samsung(Path(args.samsung))
    new = load_new_observations(Path(args.obs))
    out = unify(sam, new)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(args.out, index=False)
    print(f"{len(out)} rows -> {args.out}")
    print(out.groupby("brand").size())
    print(out.repair_price_type.value_counts())
    print(out.source_type.value_counts())


if __name__ == "__main__":
    main()
