"""Deterministic device-name normalization.

Transparent rules only — no ML entity resolution in Phase 1A.
Anything we cannot resolve deterministically is returned with
review_status=NEEDS_REVIEW rather than guessed.
"""
from __future__ import annotations

import re

BRAND_ALIASES = {
    "apple": "Apple", "iphone": "Apple",
    "samsung": "Samsung", "galaxy": "Samsung",
    "xiaomi": "Xiaomi", "redmi": "Xiaomi", "poco": "Xiaomi",
    "oppo": "Oppo", "vivo": "Vivo", "realme": "Realme",
    "oneplus": "OnePlus", "huawei": "Huawei", "honor": "Honor",
    "google": "Google", "pixel": "Google", "motorola": "Motorola",
    "infinix": "Infinix", "tecno": "Tecno", "iqoo": "iQOO", "nokia": "Nokia",
}

_STORAGE_RE = re.compile(r"(\d{1,4})\s*(gb|g|tb)\b", re.IGNORECASE)
_WS_RE = re.compile(r"\s+")


def normalize_brand(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    key = str(raw).strip().lower()
    return BRAND_ALIASES.get(key, str(raw).strip().title())


def parse_storage_gb(text: str | None) -> int | None:
    """Extract canonical numeric storage. '128GB'/'128 gb'/'1TB' -> 128/128/1024."""
    if not text:
        return None
    m = _STORAGE_RE.search(str(text))
    if not m:
        return None
    val = int(m.group(1))
    unit = m.group(2).lower()
    if unit == "tb":
        return val * 1024
    if val < 8 and unit in ("gb", "g"):  # "4 GB" is RAM-ish, not storage — caller decides
        return val
    return val


def normalize_name(raw: str | None) -> str | None:
    """'  APPLE   iPhone-13  128GB ' -> 'apple iphone 13 128gb' (canonical key form)."""
    if not raw or not str(raw).strip():
        return None
    s = str(raw).lower().strip()
    s = s.replace("-", " ").replace("_", " ")
    s = _WS_RE.sub(" ", s)
    # fuse 'iphone 13'/'iphone13' style splits
    s = re.sub(r"\b(iphone|galaxy|redmi|poco|pixel|nord|reno)\s+([a-z]?\d)", r"\1\2", s)
    return s


def split_model_storage(raw: str | None) -> tuple[str | None, int | None]:
    """'iPhone 13 128GB' -> ('iphone 13', 128)."""
    if not raw:
        return None, None
    storage = parse_storage_gb(raw)
    model = _STORAGE_RE.sub("", str(raw))
    model = _WS_RE.sub(" ", model).strip(" -/")
    return (normalize_name(model) or None), storage
