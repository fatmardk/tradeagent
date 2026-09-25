"""Hybrid market valuation — routes between real market evidence and
cold-start fallback, and stamps every output with its method.

Routing (descriptive, evidence-based):
  RECENT_MARKET_MEDIAN        — fresh obs, multi-offer spread available
  MARKET_MEDIAN_LOW_COVERAGE  — fresh obs, but single offer/seller
  COLD_START_*                — no usable observation -> median hierarchy

The freshness window is a *config*, not a learned constant — only two
snapshots exist, so staleness cannot be calibrated yet.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.market.cold_start import ColdStartEstimate, FallbackEstimator
from src.market.valuation import (DEFAULT_MAX_OBS_AGE_DAYS, MarketEstimator,
                                  MarketEstimate)

ROOT = Path(__file__).resolve().parents[2]
MARKET = ROOT / "data/processed/market_snapshot_combined.parquet"


@dataclass
class ValuationConfig:
    grade_segment: str = "A"
    max_obs_age_days: int = DEFAULT_MAX_OBS_AGE_DAYS  # provisional


class HybridValuer:
    def __init__(self, market_df: pd.DataFrame, config: ValuationConfig):
        self.cfg = config
        self.market = MarketEstimator(market_df, config.max_obs_age_days)
        self.fallback = FallbackEstimator(market_df, config.grade_segment)

    @classmethod
    def load(cls, path: str | Path = MARKET,
             config: ValuationConfig | None = None) -> "HybridValuer":
        return cls(pd.read_parquet(path), config or ValuationConfig())

    def valuate(self, brand: str, model: str, storage_gb,
                canonical_variant: str | None = None,
                as_of: dt.date | None = None) -> dict:
        if canonical_variant is None:
            slug = "".join(c if c.isalnum() else "-" for c in model.lower())
            slug = "-".join(p for p in slug.split("-") if p)
            canonical_variant = (f"{brand.lower()}|{slug}|{int(storage_gb)}"
                                 if pd.notna(storage_gb) else None)
        est: MarketEstimate | None = None
        if canonical_variant:
            est = self.market.estimate(canonical_variant,
                                       self.cfg.grade_segment, as_of)
        if est is not None and est.market_value_point is not None:
            return {"value": est.market_value_point,
                    "method": est.valuation_method,
                    "source": "REAL_MARKET_OBSERVATION",
                    "observed_at": est.observed_at,
                    "days_since_observation": est.days_since_observation,
                    "offer_count": est.n_offers,
                    "seller_count": est.n_sellers,
                    "market_p25": est.market_value_low,
                    "market_p75": est.market_value_high,
                    "relative_iqr": est.relative_iqr,
                    "grade_segment": est.grade_segment,
                    "notes": est.notes}
        fb: ColdStartEstimate = self.fallback.estimate(brand, model,
                                                       storage_gb)
        return {"value": fb.market_value_point,
                "method": fb.valuation_method,
                "source": "FALLBACK_ESTIMATE",
                "observed_at": None,
                "days_since_observation": None,
                "offer_count": None, "seller_count": None,
                "market_p25": None, "market_p75": None,
                "relative_iqr": None,
                "grade_segment": self.cfg.grade_segment,
                "support_rows": fb.support_rows,
                "notes": (est.notes if est else []) + fb.notes}
