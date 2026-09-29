package com.tradeagent.backend.dto;

import java.util.List;
import java.util.Map;

public record AcquisitionResponse(
        DeviceDto device,
        ValuationResponse marketValuation,
        Map<String, Object> repair,
        Map<String, Object> business,
        Map<String, Object> acquisition,
        Map<String, Object> explanation,
        List<String> warnings) {
}
