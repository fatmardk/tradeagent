package com.tradeagent.backend.domain;

import java.util.List;

/** Result of Hybrid Engine v1 routing for one canonical variant. */
public record ValuationResult(
        ValuationMethod method,
        Double marketValue,
        SourceType sourceType,
        String observedAt,
        Integer daysSinceObservation,
        Integer offerCount,
        Integer sellerCount,
        Double marketP25,
        Double marketP75,
        Double relativeIqr,
        String gradeSegment,
        Integer supportRows,
        List<String> notes) {
}
