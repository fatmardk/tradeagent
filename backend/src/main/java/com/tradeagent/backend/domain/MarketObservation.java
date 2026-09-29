package com.tradeagent.backend.domain;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.LocalDate;

/** One row of the canonical market_snapshot analytical layer. */
public record MarketObservation(
        @JsonProperty("observed_date") String observedDate,
        @JsonProperty("canonical_variant") String canonicalVariant,
        @JsonProperty("grade_segment") String gradeSegment,
        @JsonProperty("canonical_brand") String canonicalBrand,
        @JsonProperty("canonical_model") String canonicalModel,
        @JsonProperty("storage_gb") Double storageGb,
        @JsonProperty("n_offers") Integer nOffers,
        @JsonProperty("n_sellers") Integer nSellers,
        @JsonProperty("n_sources") Integer nSources,
        @JsonProperty("price_median") Double priceMedian,
        @JsonProperty("price_q25") Double priceQ25,
        @JsonProperty("price_q75") Double priceQ75,
        @JsonProperty("price_min") Double priceMin,
        @JsonProperty("price_max") Double priceMax,
        @JsonProperty("snapshot_id") String snapshotId) {

    public LocalDate date() {
        return LocalDate.parse(observedDate);
    }
}
