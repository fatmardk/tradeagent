"""Acquisition pricing — deterministic formula over explicit inputs.

    max_acquisition_price = expected_market_value
                          - repair_cost
                          - operational_cost      (BUSINESS_INPUT)
                          - risk_buffer           (BUSINESS_INPUT)
                          - required_profit       (BUSINESS_INPUT)

required_profit may be given as an absolute amount or as a margin
fraction of market value. Nothing here is learned — every component is
labelled OBSERVED / OFFICIAL_REPAIR_DATA / BUSINESS_INPUT / MODEL_OUTPUT.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from src.repair.lookup import RepairKB

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class BusinessRules:
    operational_cost: float = 0.0
    risk_buffer: float = 0.0
    required_profit: float = 0.0        # absolute TRY
    required_margin: float | None = None  # fraction of market value, alt.


@dataclass
class AcquisitionResult:
    recommended_max_price: float | None
    components: dict
    explanation: dict
    warnings: list[str] = field(default_factory=list)


def compute_acquisition(market_value_block: dict,
                        repair_quotes: list,
                        rules: BusinessRules) -> AcquisitionResult:
    mv = market_value_block.get("value")
    warnings = []
    if mv is None:
        return AcquisitionResult(None, {}, {},
                                 ["no market value — cannot price"])

    known = [q for q in repair_quotes if q.total_cost is not None]
    unknown = [q for q in repair_quotes if q.total_cost is None]
    repair_cost = float(sum(q.total_cost for q in known))
    for q in unknown:
        warnings.append(f"{q.repair_type}: NO_REPAIR_DATA — cost excluded, "
                        "acquisition price is optimistic")
    profit = rules.required_profit
    if rules.required_margin is not None:
        profit = mv * rules.required_margin

    price = mv - repair_cost - rules.operational_cost \
        - rules.risk_buffer - profit
    components = {
        "expected_market_value": mv,
        "repair_cost": repair_cost,
        "operational_cost": rules.operational_cost,
        "risk_buffer": rules.risk_buffer,
        "required_profit": profit,
    }
    explanation = {
        "valuation_source": market_value_block.get("method"),
        "valuation_evidence": market_value_block.get("source"),
        "market_reference_count": market_value_block.get("offer_count"),
        "repair_cost_source": sorted({q.source_id for q in known
                                      if q.source_id}) or None,
        "repair_lookup_methods": [q.lookup_method for q in repair_quotes],
        "repairs_without_data": [q.repair_type for q in unknown] or None,
        "profit_target": "BUSINESS_INPUT",
        "operational_cost_source": "BUSINESS_INPUT",
        "risk_buffer_source": "BUSINESS_INPUT",
        "market_value_origin": ("REAL_MARKET_OBSERVATION"
                                if market_value_block.get("source")
                                == "REAL_MARKET_OBSERVATION"
                                else "MODEL_ESTIMATE"),
    }
    if price < 0:
        warnings.append("computed max acquisition price is negative — "
                        "device should likely not be acquired")
    return AcquisitionResult(round(price, 2), components, explanation,
                             warnings)


def full_valuation(valuer, repair_kb: RepairKB, brand: str, model: str,
                   storage_gb, repairs: list[str] | None = None,
                   rules: BusinessRules | None = None,
                   model_code: str | None = None,
                   series: str | None = None,
                   canonical_variant: str | None = None,
                   as_of=None) -> dict:
    """End-to-end: market value -> repair lookup -> acquisition price."""
    mv_block = valuer.valuate(brand, model, storage_gb,
                              canonical_variant=canonical_variant,
                              as_of=as_of)
    quotes = repair_kb.quote_all(repairs or [], model_code=model_code,
                                 model_name=model, series=series) \
        if repair_kb is not None else []
    acq = compute_acquisition(mv_block, quotes, rules or BusinessRules())
    return {
        "device": {"brand": brand, "model": model,
                   "storage_gb": storage_gb,
                   "canonical_variant": canonical_variant},
        "market_value": mv_block,
        "repair": {"required_repairs": repairs or [],
                   "quotes": [vars(q) for q in quotes],
                   "expected_cost": acq.components.get("repair_cost")},
        "business": {"operational_cost": rules.operational_cost if rules else 0,
                     "risk_buffer": rules.risk_buffer if rules else 0,
                     "required_profit": acq.components.get("required_profit")},
        "acquisition": {"recommended_max_price": acq.recommended_max_price,
                        "components": acq.components},
        "explanation": acq.explanation,
        "warnings": acq.warnings + mv_block.get("notes", []),
    }
