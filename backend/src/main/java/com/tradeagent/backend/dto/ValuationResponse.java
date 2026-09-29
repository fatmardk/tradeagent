package com.tradeagent.backend.dto;

import com.tradeagent.backend.domain.ValuationResult;

import java.util.List;

public record ValuationResponse(
        String valuationMethod,
        Double marketValue,
        String currency,
        String sourceType,
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

    public static ValuationResponse from(ValuationResult v) {
        return new ValuationResponse(v.method().name(), v.marketValue(),
                "TRY", v.sourceType().name(), v.observedAt(),
                v.daysSinceObservation(), v.offerCount(), v.sellerCount(),
                v.marketP25(), v.marketP75(), v.relativeIqr(),
                v.gradeSegment(), v.supportRows(), v.notes());
    }
}
