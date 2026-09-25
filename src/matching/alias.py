"""Rule-based alias resolution.

Phase 1A policy: FUZZY_CANDIDATE results are written with
review_status=NEEDS_REVIEW and never auto-join. Only EXACT_MODEL_CODE /
EXACT_CANONICAL_NAME / RULE_BASED / MANUAL may produce APPROVED links.
"""
from __future__ import annotations

from src.normalization.device_names import normalize_name, split_model_storage


def classify_match(raw: str, canonical_index: dict[str, str]) -> dict:
    """Match `raw` against {normalized_canonical_name: device_id}.

    Returns a device_alias-shaped dict. Never fabricates a match:
    unmatched rows come back with device_id=None and NEEDS_REVIEW.
    """
    norm = normalize_name(raw)
    result = {
        "raw_variant": raw,
        "normalized_name": norm,
        "device_id": None,
        "variant_id": None,
        "match_method": None,
        "match_confidence_class": None,
        "review_status": "NEEDS_REVIEW",
    }
    if norm is None:
        return result
    if norm in canonical_index:
        result.update(
            device_id=canonical_index[norm],
            match_method="EXACT_CANONICAL_NAME",
            match_confidence_class="HIGH",
            review_status="APPROVED",
        )
        return result
    # deterministic rule: try stripping storage token then re-match
    model_part, _storage = split_model_storage(raw)
    if model_part and model_part in canonical_index:
        result.update(
            device_id=canonical_index[model_part],
            match_method="RULE_BASED",
            match_confidence_class="MEDIUM",
            review_status="APPROVED",
        )
    return result
