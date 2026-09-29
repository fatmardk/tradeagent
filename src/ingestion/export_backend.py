"""Export canonical processed artifacts to JSON for the Spring Boot backend.

The backend consumes *canonical analytical outputs* only — never raw
scrape files. Two artifacts:

  data/export/market_snapshot.json  <- market_snapshot_combined.parquet
  data/export/repair_kb.json        <- repair_cost_observation.parquet

Re-run after any snapshot rebuild, before starting the backend.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data" / "export"

MARKET_COLS = ["observed_date", "canonical_variant", "grade_segment",
               "canonical_brand", "canonical_model", "storage_gb",
               "n_offers", "n_sellers", "n_sources",
               "price_median", "price_q25", "price_q75",
               "price_min", "price_max", "snapshot_id"]
REPAIR_COLS = ["repair_type", "device_id", "model_name", "series",
               "total_repair_cost", "part_type", "part_quality",
               "currency", "source_id", "source_url", "observed_at",
               "notes"]


def _records(df: pd.DataFrame) -> list[dict]:
    df = df.where(pd.notna(df), None)
    for c in df.columns:
        df[c] = df[c].map(
            lambda v: v.isoformat() if hasattr(v, "isoformat") else v)
    return df.to_dict("records")


def export() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    market = pd.read_parquet(
        ROOT / "data/processed/market_snapshot_combined.parquet")
    repair = pd.read_parquet(
        ROOT / "data/processed/repair_cost_observation.parquet")
    for path, df, cols in [
            (OUT_DIR / "market_snapshot.json", market, MARKET_COLS),
            (OUT_DIR / "repair_kb.json", repair, REPAIR_COLS)]:
        path.write_text(json.dumps(_records(df[cols]),
                                   ensure_ascii=False, indent=1),
                        encoding="utf-8")
        print(f"{len(df)} rows -> {path.relative_to(ROOT)}")
    return {"market_rows": len(market), "repair_rows": len(repair)}


if __name__ == "__main__":
    export()
