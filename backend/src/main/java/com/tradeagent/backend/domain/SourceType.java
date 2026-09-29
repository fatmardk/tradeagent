package com.tradeagent.backend.domain;

/** Provenance of a number — never blur observed, estimated and input values. */
public enum SourceType {
    REAL_MARKET_OBSERVATION,
    FALLBACK_ESTIMATE,
    OFFICIAL_REPAIR_DATA,
    BUSINESS_INPUT,
    MODEL_ESTIMATE
}
