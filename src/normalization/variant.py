"""Canonical variant identity for the analytical layer.

A canonical variant = (canonical_brand, canonical_model, storage_gb).
Rules are deterministic and transparent; anything we cannot resolve is
left as-is (never merged by guessing).
"""
from __future__ import annotations

import re

_WS = re.compile(r"\s+")

# observed spelling variants -> canonical model name (per brand, lower key)
MODEL_ALIASES: dict[tuple[str, str], str] = {
    ("samsung", "galaxy s22 ultra 5g"): "Galaxy S22 Ultra 5G",
    ("samsung", "galaxy a34 5g"): "Galaxy A34",          # A34 exists only as 5G
    ("apple", "iphone 13 mini"): "iPhone 13 Mini",
    ("apple", "iphone 12 mini"): "iPhone 12 Mini",
    ("poco", "x3 pro"): "Poco X3 Pro",
    ("omix", "x700"): "Omix X700",
    ("samsung", "galaxy s20 fe"): "Galaxy S20 FE",
}


def canonical_model(brand: str | None, model: str | None) -> str | None:
    if not model or not str(model).strip():
        return None
    b = (brand or "").strip().lower()
    m = _WS.sub(" ", str(model).strip())
    key = m.lower()
    hit = MODEL_ALIASES.get((b, key)) or MODEL_ALIASES.get(("", key))
    if hit:
        return hit
    # generic case fixes: ALL-CAPS/lower tokens -> title-ish canonical
    m = re.sub(r"\bULTRA\b", "Ultra", m, flags=re.I)
    m = re.sub(r"\bpro\b", "Pro", m, flags=re.I)
    m = re.sub(r"\bplus\b", "Plus", m, flags=re.I)
    m = re.sub(r"\bfe\b", "FE", m, flags=re.I)
    m = re.sub(r"\bmini\b", "Mini", m, flags=re.I)
    m = re.sub(r"\b5g\b", "5G", m, flags=re.I)
    return m


def canonical_brand(brand: str | None) -> str | None:
    if not brand or not str(brand).strip():
        return None
    return _WS.sub(" ", str(brand).strip()).title()


def canonical_variant_key(brand: str | None, model: str | None,
                          storage_gb) -> str | None:
    """e.g. 'apple|iphone-13|128'. Returns None if storage unknown —
    from-price/model-level rows cannot form a variant key."""
    cb, cm = canonical_brand(brand), canonical_model(brand, model)
    if not cb or not cm or storage_gb is None:
        return None
    try:
        gb = int(float(storage_gb))
    except (TypeError, ValueError):
        return None
    slug = re.sub(r"[^a-z0-9]+", "-", cm.lower()).strip("-")
    return f"{cb.lower()}|{slug}|{gb}"
