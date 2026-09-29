package com.tradeagent.backend.domain;

import com.fasterxml.jackson.annotation.JsonProperty;

/** One row of the canonical repair_cost_observation KB (Samsung TR official). */
public record RepairObservation(
        @JsonProperty("repair_type") String repairType,
        @JsonProperty("device_id") String deviceId,
        @JsonProperty("model_name") String modelName,
        @JsonProperty("series") String series,
        @JsonProperty("total_repair_cost") Double totalRepairCost,
        @JsonProperty("part_type") String partType,
        @JsonProperty("part_quality") String partQuality,
        @JsonProperty("currency") String currency,
        @JsonProperty("source_id") String sourceId,
        @JsonProperty("source_url") String sourceUrl,
        @JsonProperty("observed_at") String observedAt,
        @JsonProperty("notes") String notes) {
}
