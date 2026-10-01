package com.tradeagent.backend.domain;

import java.util.List;

/**
 * Deterministic multi-brand repair-KB lookup result.
 * totalCost stays null when unknown (never fabricated).
 * quoteStatus: OK / INCOMPLETE_REPAIR_COST / NO_REPAIR_DATA.
 * alternates keeps every other candidate observation (quality tiers,
 * other sources) — nothing is silently collapsed.
 */
public record RepairQuote(
        String repairType,
        String lookupMethod,   // EXACT_REPAIR_LOOKUP / SERIES_LEVEL_LOOKUP / NO_REPAIR_DATA
        Double totalCost,
        String deviceId,
        String sourceId,
        String observedAt,
        String note,
        String priceType,          // FULL_REPAIR / PART_ONLY
        Boolean includesLabor,
        String sourceType,         // OFFICIAL_MANUFACTURER / AUTHORIZED_SERVICE /
                                 // INDEPENDENT_REPAIR_SERVICE / PART_SUPPLIER
        String repairQuality,
        String modelKey,
        String sourceReference,
        String quoteStatus,
        List<Alternate> alternates) {

    /** Another observation that matched the same lookup. */
    public record Alternate(
            String repairQuality,
            String sourceQualityLabel,
            Double totalCost,
            String priceType,
            String sourceId,
            String sourceType,
            String observedAt) {
    }

    public boolean isPartOnly() {
        return "PART_ONLY".equals(priceType);
    }
}
