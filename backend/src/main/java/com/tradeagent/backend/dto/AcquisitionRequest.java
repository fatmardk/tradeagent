package com.tradeagent.backend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.PositiveOrZero;

import java.util.List;

public record AcquisitionRequest(
        @NotBlank String brand,
        @NotBlank String model,
        @NotNull @Positive Double storageGb,
        List<String> requiredRepairs,
        @PositiveOrZero Double operationalCost,
        @PositiveOrZero Double riskBuffer,
        @PositiveOrZero Double requiredProfit,
        @PositiveOrZero Double requiredMargin,
        String modelCode,
        String series) {
}
