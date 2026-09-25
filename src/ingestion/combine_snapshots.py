"""Combine per-snapshot market snapshots into one analytical parquet.

Preserves snapshot_id and observed_date — time is never collapsed.
Inputs are read-only; Snapshot 1 files are never modified.

Usage: python -m src.ingestion.combine_snapshots
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MARKET_IN = [
    (ROOT / "data/processed/market_snapshot.parquet", "s1"),
    (ROOT / "data/processed/market_snapshot_s2.parquet", "s2"),
    (ROOT / "data/processed/market_snapshot_s3.parquet", "s3"),
]
OFFER_IN = [
    (ROOT / "data/processed/offer_level.parquet", "s1"),
    (ROOT / "data/processed/offer_level_s2.parquet", "s2"),
    (ROOT / "data/processed/offer_level_s3.parquet", "s3"),
]
OUT = ROOT / "data/processed/market_snapshot_combined.parquet"
OUT_OFFER = ROOT / "data/processed/offer_level_combined.parquet"


def combine(inputs: list[tuple[Path, str]], out: Path = OUT) -> pd.DataFrame:
    frames = []
    for path, snap_id in inputs:
        df = pd.read_parquet(path)
        if "snapshot_id" not in df.columns:
            df["snapshot_id"] = snap_id
        frames.append(df)
    out_df = pd.concat(frames, ignore_index=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_parquet(out, index=False)
    return out_df


if __name__ == "__main__":
    df = combine(MARKET_IN, OUT)
    print(f"market: rows={len(df)} "
          f"variants={df.canonical_variant.nunique()} "
          f"dates={sorted(str(d) for d in df.observed_date.unique())}")
    od = combine(OFFER_IN, OUT_OFFER)
    print(f"offer : rows={len(od)}")
