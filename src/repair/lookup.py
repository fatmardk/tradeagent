"""Multi-brand repair-cost lookup — deterministic, never fabricates.

Lookup order for (repair_type, device):
  1. EXACT_REPAIR_LOOKUP   — model_code (SM-…) / model_key / model-name match
  2. SERIES_LEVEL_LOOKUP   — series-level rows (Samsung battery table)
  3. NO_REPAIR_DATA        — nothing reliable exists; returns None cost

Within the matching candidate rows the selected observation is chosen by:

  source_type  : OFFICIAL_MANUFACTURER < AUTHORIZED_SERVICE
                 < INDEPENDENT_REPAIR_SERVICE < PART_SUPPLIER
  price_type   : FULL_REPAIR < PART_ONLY
  observed_at  : newest first

PART_ONLY is never treated as a complete repair cost: the quote carries
price_type=PART_ONLY and includes_labor=False; downstream consumers must
flag it (see acquisition.engine — INCOMPLETE_REPAIR_COST).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
KB = ROOT / "data/processed/repair_cost_observation_multibrand.parquet"

SOURCE_TYPE_RANK = {
    "OFFICIAL_MANUFACTURER": 0,
    "AUTHORIZED_SERVICE": 1,
    "INDEPENDENT_REPAIR_SERVICE": 2,
    "PART_SUPPLIER": 3,
}
PRICE_TYPE_RANK = {"FULL_REPAIR": 0, "PART_ONLY": 1}

# Within equal provenance/price_type/date, prefer the genuine-part tier so
# the headline quote is a "proper repair" estimate; every other tier stays
# available via RepairQuote.alternates (never collapsed silently).
QUALITY_RANK = {
    "ORIGINAL": 0, "SERVICE": 1, "PREMIUM": 2, "HIGH_QUALITY": 3,
    "REFURBISHED": 4, "PULLED": 5, "COMPATIBLE": 6, "UNKNOWN": 7,
}

_SOURCE_TYPE_LABEL = {
    "OFFICIAL_MANUFACTURER": "Official Manufacturer",
    "AUTHORIZED_SERVICE": "Authorized Service",
    "INDEPENDENT_REPAIR_SERVICE": "Independent Repair Service",
    "PART_SUPPLIER": "Part Supplier",
}


@dataclass
class RepairQuote:
    repair_type: str
    lookup_method: str          # EXACT_REPAIR_LOOKUP / SERIES_LEVEL_LOOKUP / NO_REPAIR_DATA
    total_cost: float | None
    device_id: str | None
    source_id: str | None
    observed_at: str | None
    note: str | None = None
    # multi-brand fields (None on legacy-shaped quotes)
    price_type: str | None = None        # FULL_REPAIR / PART_ONLY
    includes_labor: bool | None = None
    source_type: str | None = None       # provenance class
    repair_quality: str | None = None
    model_key: str | None = None
    source_reference: str | None = None
    quote_status: str | None = None      # OK / INCOMPLETE_REPAIR_COST / NO_REPAIR_DATA
    alternates: list = field(default_factory=list)  # other tiers/sources kept

    @property
    def is_part_only(self) -> bool:
        return self.price_type == "PART_ONLY"


def _slug(s: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", str(s).strip().lower()).strip("-")


def _code_for(df: pd.DataFrame, model_name: str) -> str | None:
    """Legacy name->SM-code resolution used when only model_name is given."""
    name = str(model_name).strip().lower()
    hit = df[df.model_name.fillna("").str.strip().str.lower() == name]
    codes = hit.device_id.dropna()
    if len(codes):
        return codes.iloc[0]
    return None


def _rank(df: pd.DataFrame) -> pd.DataFrame:
    """provenance -> price_type -> newest -> quality tier (genuine first).

    Tolerates the legacy Samsung-only parquet which lacks the new columns —
    missing fields rank last instead of crashing.
    """
    d = df.copy()
    def col(name):
        return d[name] if name in d.columns else pd.Series([None] * len(d))
    d["_prov"] = col("source_type").map(SOURCE_TYPE_RANK).fillna(9)
    d["_ptype"] = col("repair_price_type").map(PRICE_TYPE_RANK).fillna(9)
    d["_obs"] = pd.to_datetime(col("observed_at"), errors="coerce")
    d["_qual"] = col("repair_quality").map(QUALITY_RANK).fillna(9)
    return d.sort_values(["_prov", "_ptype", "_obs", "_qual"],
                         ascending=[True, True, False, True])


def _alternates(df: pd.DataFrame, skip_idx) -> list:
    out = []
    for _, a in df.iterrows():
        if a.name == skip_idx:
            continue
        out.append({
            "repair_quality": getattr(a, "repair_quality", None),
            "source_quality_label": getattr(a, "source_quality_label", None),
            "total_cost": float(a.total_repair_cost),
            "price_type": getattr(a, "repair_price_type", "FULL_REPAIR"),
            "source_id": getattr(a, "source_id", None),
            "source_type": getattr(a, "source_type", None),
            "observed_at": str(a.observed_at),
        })
    return out


def _quote_from_row(rt: str, method: str, r, alternates: list | None = None) -> RepairQuote:
    price_type = getattr(r, "repair_price_type", None) or "FULL_REPAIR"
    status = ("INCOMPLETE_REPAIR_COST" if price_type == "PART_ONLY"
              else "OK")
    note = None
    if price_type == "PART_ONLY":
        note = ("part-only price — labor NOT included; "
                "do not use as a complete repair cost")
    return RepairQuote(
        repair_type=rt, lookup_method=method,
        total_cost=float(r.total_repair_cost),
        device_id=getattr(r, "device_id", None),
        source_id=getattr(r, "source_id", None),
        observed_at=str(getattr(r, "observed_at", "")),
        note=note,
        price_type=price_type,
        includes_labor=bool(getattr(r, "includes_labor", price_type == "FULL_REPAIR")),
        source_type=getattr(r, "source_type", None),
        repair_quality=getattr(r, "repair_quality", None),
        model_key=getattr(r, "model_key", None),
        source_reference=getattr(r, "source_reference", None),
        quote_status=status,
        alternates=alternates or [],
    )


class RepairKB:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    @classmethod
    def load(cls, path: str | Path = KB) -> "RepairKB":
        return cls(pd.read_parquet(path))

    # ---------- candidate selection ----------

    def _candidates(self, d: pd.DataFrame, model_code: str | None,
                    model_name: str | None, model_key: str | None
                    ) -> pd.DataFrame:
        """Deterministic exact-model candidates; empty when nothing matches."""
        if model_key and "model_key" in d:
            hit = d[d.model_key == model_key]
            if len(hit):
                return hit
        code = model_code or (model_name and _code_for(d, model_name))
        if code:
            hit = d[d.device_id == code]
            if len(hit):
                return hit
        if model_name:
            slug = _slug(model_name)
            if "model_key" in d:
                hit = d[d.model_key.str.split("::").str[-1] == slug]
                if len(hit):
                    return hit
            name = str(model_name).strip().lower()
            hit = d[d.model_name.fillna("").str.strip().str.lower() == name]
            if len(hit):
                return hit
        return d.iloc[0:0]

    # ---------- public API ----------

    def quote(self, repair_type: str, model_code: str | None = None,
              model_name: str | None = None,
              series: str | None = None,
              model_key: str | None = None) -> RepairQuote:
        d = self.df[self.df.repair_type == repair_type]
        cand = self._candidates(d, model_code, model_name, model_key)
        if len(cand):
            ranked = _rank(cand)
            r = ranked.iloc[0]
            q = _quote_from_row(repair_type, "EXACT_REPAIR_LOOKUP", r,
                                _alternates(ranked, r.name))
            if len(ranked) > 1:
                tiers = {a["repair_quality"] for a in q.alternates}
                tiers.add(q.repair_quality)
                q.note = (q.note + "; " if q.note else "") + \
                    f"{len(ranked)} observations across {len(tiers)} quality tiers"
            return q
        code = model_code or (model_name and _code_for(d, model_name))
        if series:
            hit = d[(d.device_id.isna()) & (d.series == series)]
            if len(hit):
                ranked = _rank(hit)
                r = ranked.iloc[0]
                q = _quote_from_row(repair_type, "SERIES_LEVEL_LOOKUP", r,
                                    _alternates(ranked, r.name))
                q.note = (q.note + "; " if q.note else "") + \
                    f"series-level ({series}) price, not model-specific"
                return q
        return RepairQuote(repair_type, "NO_REPAIR_DATA", None,
                           code, None, None,
                           note="no reliable repair record — cost unknown",
                           quote_status="NO_REPAIR_DATA")

    def quote_all(self, repairs: list[str], **kw) -> list[RepairQuote]:
        return [self.quote(rt, **kw) for rt in repairs]

    def available_repairs(self, **kw) -> list[str]:
        """Repair types with at least one real observation for this device."""
        cand = self._candidates(self.df, kw.get("model_code"),
                                kw.get("model_name"), kw.get("model_key"))
        return sorted(cand.repair_type.dropna().unique().tolist())


def display_repair(quote: RepairQuote) -> dict:
    """Presentation strings for the UI layer.

    A PART_ONLY price is always labelled as such — never shown as a
    complete repair quote. Missing data renders as 'unavailable'.
    """
    label = quote.repair_type.replace("_", " ").title()
    if quote.lookup_method == "NO_REPAIR_DATA" or quote.total_cost is None:
        return {"title": f"{label}", "price": None,
                "status": "Repair cost unavailable"}
    src = _SOURCE_TYPE_LABEL.get(quote.source_type or "", "")
    price = f"{quote.total_cost:,.0f} TRY"
    if quote.is_part_only:
        return {"title": label, "price": price, "badge": "PART ONLY",
                "status": "Labor not included", "source": src}
    return {"title": label, "price": price, "badge": "FULL_REPAIR",
            "status": src, "source": src,
            "quality": quote.repair_quality}
