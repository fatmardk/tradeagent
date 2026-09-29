package com.tradeagent.backend.domain;

/** How a market value was produced — mirrors Hybrid Engine v1 routing. */
public enum ValuationMethod {
    RECENT_MARKET_MEDIAN,
    MARKET_MEDIAN_LOW_COVERAGE,
    COLD_START_MODEL_MEDIAN,
    COLD_START_BRAND_STORAGE,
    COLD_START_BRAND,
    COLD_START_GLOBAL,
    NONE
}
