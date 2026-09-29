package com.tradeagent.backend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

public record ValuationRequest(
        @NotBlank String brand,
        @NotBlank String model,
        @NotNull @Positive Double storageGb) {
}
