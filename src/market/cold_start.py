"""Cold-start fallback estimator — used only when no usable recent market
observation exists for the exact variant.

Selected by evidence, not by preference. Unseen-variant CV (n=737,
GroupKFold by canonical_variant, grade A, S1+S2 combined):

  same-model median (other storages)      MAPE 11.8%  <- model seen
  brand+storage median                    MAPE 30.0%  <- model unseen
  brand median                            MAPE ~58-64%
  HistGBR cold-start ML                   MAPE ~49-57% <- loses to medians
  new-price ratio                         n too small (5 anchors)

So the production fallback is a deterministic median hierarchy —
COLD_START_MODEL_MEDIAN -> COLD_START_BRAND_STORAGE -> COLD_START_BRAND
-> COLD_START_GLOBAL. The ML model is kept in src/model/cold_start.py as
an evaluated candidate, not the default path.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

METHODS = ("COLD_START_MODEL_MEDIAN", "COLD_START_BRAND_STORAGE",
           "COLD_START_BRAND", "COLD_START_GLOBAL")


@dataclass
class ColdStartEstimate:
    valuation_method: str
    market_value_point: float | None
    support_rows: int                 # market rows feeding the estimate
    notes: list[str] = field(default_factory=list)


class FallbackEstimator:
    """Median-hierarchy fallback fit on MARKET_SNAPSHOT rows only."""

    def __init__(self, market_df: pd.DataFrame, grade: str = "A"):
        df = market_df[market_df.grade_segment == grade]
        self.model_med = df.groupby("canonical_model").price_median.agg(
            ["median", "count"])
        self.bs_med = df.groupby(
            ["canonical_brand", "storage_gb"]).price_median.agg(
            ["median", "count"])
        self.brand_med = df.groupby("canonical_brand").price_median.agg(
            ["median", "count"])
        self.global_med = float(df.price_median.median())
        self.n_rows = len(df)

    def estimate(self, brand: str, model: str,
                 storage_gb: float | None) -> ColdStartEstimate:
        if model is not None and model in self.model_med.index:
            r = self.model_med.loc[model]
            return ColdStartEstimate(
                "COLD_START_MODEL_MEDIAN", float(r["median"]),
                int(r["count"]),
                ["same-model median across its observed storages"])
        if storage_gb is not None and pd.notna(storage_gb):
            key = (brand, storage_gb)
            if key in self.bs_med.index:
                r = self.bs_med.loc[key]
                return ColdStartEstimate(
                    "COLD_START_BRAND_STORAGE", float(r["median"]),
                    int(r["count"]))
        if brand is not None and brand in self.brand_med.index:
            r = self.brand_med.loc[brand]
            return ColdStartEstimate("COLD_START_BRAND",
                                     float(r["median"]), int(r["count"]))
        return ColdStartEstimate("COLD_START_GLOBAL", self.global_med,
                                 self.n_rows,
                                 ["no brand/model coverage — global median"])
