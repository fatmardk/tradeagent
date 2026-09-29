package com.tradeagent.backend.domain;

/** Deterministic REPAIR_KB lookup result; totalCost stays null when unknown. */
public record RepairQuote(
        String repairType,
        String lookupMethod,   // EXACT_REPAIR_LOOKUP / SERIES_LEVEL_LOOKUP / NO_REPAIR_DATA
        Double totalCost,
        String deviceId,
        String sourceId,
        String observedAt,
        String note) {
}
