"""Cold-start market value model — used ONLY when no recent real market
observation exists for a canonical variant (new variant, unseen model,
stale or insufficient coverage).

Empirical role (S1→S2 OOT): on already-observed variants the S1 market
median achieves 4.3% MAPE vs this model's 31.6% — so this model is a
fallback, not the primary estimator. On new variants it beats the only
available naive alternative (57% vs 96% MAPE vs brand median).

Implementation: one HistGradientBoostingRegressor per brand
(canonical_model has 262 levels > HistGBR's 255-category cap), with a
global storage-only fallback for unseen brands/models.
Training grain: MARKET_SNAPSHOT rows (one per variant×grade×date) —
never raw seller offers, so heavily-observed variants don't dominate.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[2]
MARKET = ROOT / "data/processed/market_snapshot_combined.parquet"


class ColdStartValueModel:
    def __init__(self, max_iter: int = 300):
        self.max_iter = max_iter
        self.models: dict = {}       # brand -> (gbr, model_categories)
        self.global_model = None
        self.brand_medians: pd.Series | None = None
        self.global_median: float | None = None

    def _new_gbr(self):
        return HistGradientBoostingRegressor(
            categorical_features=[0], max_iter=self.max_iter,
            learning_rate=0.08, min_samples_leaf=5, random_state=0)

    def fit(self, market_df: pd.DataFrame, grade: str = "A") -> "ColdStartValueModel":
        df = market_df[market_df.grade_segment == grade].copy()
        df["model_ord"] = df.groupby("canonical_brand")["canonical_model"] \
                            .transform(lambda s: s.astype("category").cat.codes)
        for brand, g in df.groupby("canonical_brand"):
            cats = g["canonical_model"].astype("category").cat.categories
            m = self._new_gbr().fit(g[["model_ord", "storage_gb"]],
                                    np.log(g.price_median))
            self.models[brand] = (m, list(cats))
        self.global_model = HistGradientBoostingRegressor(
            max_iter=self.max_iter, learning_rate=0.08,
            min_samples_leaf=5, random_state=0).fit(
            df[["storage_gb"]], np.log(df.price_median))
        self.brand_medians = df.groupby("canonical_brand").price_median.median()
        self.global_median = float(df.price_median.median())
        return self

    def predict_one(self, brand: str, model: str,
                    storage_gb: float) -> tuple[float, str]:
        """Returns (price, detail) where detail marks the actual path taken."""
        pack = self.models.get(brand)
        if pack is not None:
            gbr, cats = pack
            if model in cats:
                code = cats.index(model)
                return (float(np.exp(gbr.predict([[code, storage_gb]])[0])),
                        "COLD_START_ML")
        if brand in self.models:
            return (float(self.brand_medians[brand]),
                    "COLD_START_ML_BRAND_MEDIAN_FALLBACK")
        if np.isfinite(storage_gb):
            return (float(np.exp(
                self.global_model.predict([[storage_gb]])[0])),
                "COLD_START_ML_GLOBAL")
        return (self.global_median, "COLD_START_ML_GLOBAL")

    def predict(self, df: pd.DataFrame) -> pd.Series:
        return df.apply(lambda r: self.predict_one(
            r["canonical_brand"], r["canonical_model"],
            r["storage_gb"])[0], axis=1)
