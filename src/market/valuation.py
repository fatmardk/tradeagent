"""Market-based valuation: the primary estimator when recent real
observations exist for a canonical variant.

Empirical basis (S1→S2 out-of-time, shared grade-A variants):
- S1 variant median → S2 median: MAPE 4.3% — far better than any ML model.
- Even single-offer S1 variants: mean MAPE ~4.5%. There is NO sharp
  coverage cliff, so routing uses descriptive flags, not fake thresholds.

Output: market_value_point (median), market_value_low/high (observed
p25/p75 quartiles — real market spread, not invented confidence),
plus provenance metadata.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MARKET = ROOT / "data/processed/market_snapshot_combined.parquet"

# Provisional — NOT validated yet (S1→S2 gap is 9 days). Snapshot 3+ must
# measure error vs observation age before this becomes a real threshold.
DEFAULT_MAX_OBS_AGE_DAYS = 45


@dataclass
class MarketEstimate:
    valuation_method: str          # RECENT_MARKET_MEDIAN / MARKET_MEDIAN_LOW_COVERAGE / NONE
    market_value_point: float | None
    market_value_low: float | None   # observed p25
    market_value_high: float | None  # observed p75
    relative_iqr: float | None
    n_offers: int | None
    n_sellers: int | None
    observed_at: str | None
    days_since_observation: int | None
    grade_segment: str
    notes: list[str] = field(default_factory=list)


class MarketEstimator:
    """Latest real market statistics per canonical variant + grade."""

    def __init__(self, market_df: pd.DataFrame,
                 max_obs_age_days: int = DEFAULT_MAX_OBS_AGE_DAYS):
        self.df = market_df.copy()
        self.df["observed_date"] = pd.to_datetime(self.df["observed_date"])
        self.max_age = max_obs_age_days
        # latest row per (variant, grade)
        self.latest = (self.df.sort_values("observed_date")
                       .groupby(["canonical_variant", "grade_segment"])
                       .last().reset_index())
        self._idx = {(r.canonical_variant, r.grade_segment): r
                     for r in self.latest.itertuples()}

    @classmethod
    def load(cls, path: str | Path = MARKET, **kw) -> "MarketEstimator":
        return cls(pd.read_parquet(path), **kw)

    def estimate(self, canonical_variant: str, grade_segment: str = "A",
                 as_of: dt.date | None = None) -> MarketEstimate:
        row = self._idx.get((canonical_variant, grade_segment))
        if row is None:
            return MarketEstimate("NONE", None, None, None, None,
                                  None, None, None, None, grade_segment,
                                  ["no market observation for variant+grade"])
        age = None
        if as_of is not None:
            age = (pd.Timestamp(as_of) - row.observed_date).days
        notes = []
        method = "RECENT_MARKET_MEDIAN"
        if age is not None and age > self.max_age:
            method = "NONE"
            notes.append(f"observation is {age}d old, beyond provisional "
                         f"{self.max_age}d freshness window")
            return MarketEstimate(method, None, None, None, None,
                                  int(row.n_offers), int(row.n_sellers),
                                  str(row.observed_date.date()), age,
                                  grade_segment, notes)
        if int(row.n_offers) == 1 or int(row.n_sellers) < 2:
            method = "MARKET_MEDIAN_LOW_COVERAGE"
            notes.append("single offer/seller — point estimate is real but "
                         "spread is not market-derived")
        if int(row.n_offers) < 2:
            lo = hi = riqr = None  # quartiles undefined with one offer
        else:
            lo, hi = float(row.price_q25), float(row.price_q75)
            med = float(row.price_median)
            riqr = (hi - lo) / med if med else None
        return MarketEstimate(
            method, float(row.price_median), lo, hi, riqr,
            int(row.n_offers), int(row.n_sellers),
            str(row.observed_date.date()), age, grade_segment, notes)
