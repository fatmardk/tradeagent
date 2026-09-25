"""REPAIR_KB lookup service — deterministic, never fabricates.

Lookup order for (repair_type, device):
  1. EXACT_REPAIR_LOOKUP   — SM- model code or exact model-name match
  2. SERIES_LEVEL_LOOKUP   — series-level rows (battery prices)
  3. NO_REPAIR_DATA        — nothing reliable exists; returns None cost

Samsung TR prices are totals (part+labor included); part_price/labor_cost
stay NULL rather than being reverse-engineered.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
KB = ROOT / "data/processed/repair_cost_observation.parquet"


@dataclass
class RepairQuote:
    repair_type: str
    lookup_method: str          # EXACT_REPAIR_LOOKUP / SERIES_LEVEL_LOOKUP / NO_REPAIR_DATA
    total_cost: float | None
    device_id: str | None
    source_id: str | None
    observed_at: str | None
    note: str | None = None


# canonical model name -> Samsung SM- code, built from KB itself
def _code_for(df: pd.DataFrame, model_name: str) -> str | None:
    name = str(model_name).strip().lower()
    hit = df[df.model_name.fillna("").str.strip().str.lower() == name]
    if len(hit):
        return hit.device_id.iloc[0]
    return None


class RepairKB:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    @classmethod
    def load(cls, path: str | Path = KB) -> "RepairKB":
        return cls(pd.read_parquet(path))

    def quote(self, repair_type: str, model_code: str | None = None,
              model_name: str | None = None,
              series: str | None = None) -> RepairQuote:
        d = self.df[self.df.repair_type == repair_type]
        code = model_code or (model_name and _code_for(d, model_name))
        if code:
            hit = d[d.device_id == code]
            if len(hit):
                r = hit.iloc[0]
                return RepairQuote(repair_type, "EXACT_REPAIR_LOOKUP",
                                   float(r.total_repair_cost), r.device_id,
                                   r.source_id, str(r.observed_at))
        if series:
            hit = d[(d.device_id.isna())
                    & (d.series == series)]
            if len(hit):
                r = hit.iloc[0]
                return RepairQuote(repair_type, "SERIES_LEVEL_LOOKUP",
                                   float(r.total_repair_cost), None,
                                   r.source_id, str(r.observed_at),
                                   note=f"series-level ({series}) price, "
                                        "not model-specific")
        return RepairQuote(repair_type, "NO_REPAIR_DATA", None,
                           code, None, None,
                           note="no reliable repair record — cost unknown")

    def quote_all(self, repairs: list[str], **kw) -> list[RepairQuote]:
        return [self.quote(rt, **kw) for rt in repairs]
