package com.tradeagent.backend.domain;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * One row of the multi-brand repair KB (data/export/repair_kb.json,
 * exported from repair_cost_observation_multibrand.parquet).
 * Fields added for the multi-brand KB are nullable for legacy rows.
 */
public record RepairObservation(
        @JsonProperty("repair_type") String repairType,
        @JsonProperty("device_id") String deviceId,
        @JsonProperty("model_name") String modelName,
        @JsonProperty("model_code") String modelCode,
        @JsonProperty("model_key") String modelKey,
        @JsonProperty("series") String series,
        @JsonProperty("brand") String brand,
        @JsonProperty("variant") String variant,
        @JsonProperty("total_repair_cost") Double totalRepairCost,
        @JsonProperty("part_type") String partType,
        @JsonProperty("part_quality") String partQuality,
        @JsonProperty("repair_price_type") String repairPriceType,
        @JsonProperty("includes_labor") Boolean includesLabor,
        @JsonProperty("repair_quality") String repairQuality,
        @JsonProperty("source_quality_label") String sourceQualityLabel,
        @JsonProperty("currency") String currency,
        @JsonProperty("source_id") String sourceId,
        @JsonProperty("source_name") String sourceName,
        @JsonProperty("source_type") String sourceType,
        @JsonProperty("source_url") String sourceUrl,
        @JsonProperty("source_reference") String sourceReference,
        @JsonProperty("observed_at") String observedAt,
        @JsonProperty("notes") String notes) {

    public boolean isPartOnly() {
        return "PART_ONLY".equals(repairPriceType);
    }

    public boolean isFullRepair() {
        return !isPartOnly();
    }
}
