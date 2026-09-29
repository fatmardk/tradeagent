package com.tradeagent.backend.dto;

public record DeviceDto(String brand, String model, Double storageGb,
                        String canonicalVariant) {
}
