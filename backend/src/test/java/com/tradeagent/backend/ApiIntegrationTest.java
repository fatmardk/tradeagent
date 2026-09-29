package com.tradeagent.backend;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.hamcrest.Matchers.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class ApiIntegrationTest {

    @Autowired
    MockMvc mvc;

    // ---------- /api/devices ----------

    @Test
    void devicesSearchByBrandAndModel() throws Exception {
        mvc.perform(get("/api/devices")
                        .param("brand", "Samsung")
                        .param("model", "S23"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.count", greaterThan(0)))
                .andExpect(jsonPath("$.devices[*].canonicalVariant",
                        hasItem("samsung|galaxy-s23|256")));
    }

    @Test
    void devicesNoMatchReturnsEmpty() throws Exception {
        mvc.perform(get("/api/devices").param("brand", "Nokia"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.count", is(0)));
    }

    // ---------- /api/valuation routing ----------

    @Test
    void recentMarketMedian() throws Exception {
        mvc.perform(post("/api/valuation")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"brand\":\"Samsung\",\"model\":"
                                + "\"Galaxy S23\",\"storageGb\":256}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.valuation.valuationMethod",
                        is("RECENT_MARKET_MEDIAN")))
                .andExpect(jsonPath("$.valuation.sourceType",
                        is("REAL_MARKET_OBSERVATION")))
                .andExpect(jsonPath("$.valuation.marketValue",
                        closeTo(34124.5, 0.5)))
                .andExpect(jsonPath("$.valuation.offerCount", is(12)))
                .andExpect(jsonPath("$.valuation.sellerCount", is(9)))
                .andExpect(jsonPath("$.valuation.marketP25", notNullValue()))
                .andExpect(jsonPath("$.valuation.daysSinceObservation",
                        notNullValue()));
    }

    @Test
    void lowCoverageMarketMedian() throws Exception {
        mvc.perform(post("/api/valuation")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"brand\":\"Apple\",\"model\":"
                                + "\"iPhone 16e\",\"storageGb\":128}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.valuation.valuationMethod",
                        is("MARKET_MEDIAN_LOW_COVERAGE")))
                .andExpect(jsonPath("$.valuation.sourceType",
                        is("REAL_MARKET_OBSERVATION")))
                .andExpect(jsonPath("$.valuation.offerCount", is(1)))
                .andExpect(jsonPath("$.valuation.marketP25", nullValue()));
    }

    @Test
    void coldStartModelMedian() throws Exception {
        // known model, unseen storage -> same-model median hierarchy
        mvc.perform(post("/api/valuation")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"brand\":\"Samsung\",\"model\":"
                                + "\"Galaxy S23\",\"storageGb\":1024}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.valuation.valuationMethod",
                        is("COLD_START_MODEL_MEDIAN")))
                .andExpect(jsonPath("$.valuation.sourceType",
                        is("FALLBACK_ESTIMATE")))
                .andExpect(jsonPath("$.valuation.supportRows",
                        greaterThan(0)));
    }

    @Test
    void coldStartGlobalForUnknownBrand() throws Exception {
        mvc.perform(post("/api/valuation")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"brand\":\"FooBrand\",\"model\":"
                                + "\"X1\",\"storageGb\":128}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.valuation.valuationMethod",
                        is("COLD_START_GLOBAL")));
    }

    // ---------- /api/repair-costs ----------

    @Test
    void repairExactLookup() throws Exception {
        mvc.perform(get("/api/repair-costs")
                        .param("repairType", "screen_module")
                        .param("modelName", "Galaxy S23"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.quotes[0].lookupMethod",
                        is("EXACT_REPAIR_LOOKUP")))
                .andExpect(jsonPath("$.quotes[0].totalCost",
                        closeTo(9900.0, 0.01)))
                .andExpect(jsonPath("$.quotes[0].deviceId", is("SM-S911")));
    }

    @Test
    void repairSeriesLookup() throws Exception {
        mvc.perform(get("/api/repair-costs")
                        .param("repairType", "battery")
                        .param("series", "S"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.quotes[0].lookupMethod",
                        is("SERIES_LEVEL_LOOKUP")))
                .andExpect(jsonPath("$.quotes[0].totalCost",
                        closeTo(3100.0, 0.01)));
    }

    @Test
    void repairNoDataReturnsNullCost() throws Exception {
        mvc.perform(get("/api/repair-costs")
                        .param("repairType", "screen_module")
                        .param("modelName", "Nothing Phone 2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.quotes[0].lookupMethod",
                        is("NO_REPAIR_DATA")))
                .andExpect(jsonPath("$.quotes[0].totalCost", nullValue()));
    }

    @Test
    void repairAliasAndInvalidType() throws Exception {
        mvc.perform(get("/api/repair-costs")
                        .param("repairType", "SCREEN_REPLACEMENT")
                        .param("modelName", "Galaxy S23"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.quotes[0].repairType",
                        is("screen_module")));
        mvc.perform(get("/api/repair-costs")
                        .param("repairType", "flux_capacitor")
                        .param("modelName", "Galaxy S23"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code",
                        is("INVALID_REPAIR_TYPE")));
    }

    // ---------- /api/acquisition/quote ----------

    @Test
    void acquisitionQuoteFull() throws Exception {
        String body = """
                {"brand":"Samsung","model":"Galaxy S23","storageGb":256,
                 "requiredRepairs":["screen_module"],
                 "operationalCost":1500,"riskBuffer":1000,
                 "requiredMargin":0.15}""";
        // 34124.5 - 9900 - 1500 - 1000 - 5118.675 = 16605.825 -> 16605.83
        mvc.perform(post("/api/acquisition/quote")
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.acquisition.recommended_max_price",
                        closeTo(16605.83, 0.01)))
                .andExpect(jsonPath("$.repair.expected_cost",
                        closeTo(9900.0, 0.01)))
                .andExpect(jsonPath("$.repair.source_type",
                        is("OFFICIAL_REPAIR_DATA")))
                .andExpect(jsonPath("$.business.source_type",
                        is("BUSINESS_INPUT")))
                .andExpect(jsonPath("$.explanation.market_value_origin",
                        is("REAL_MARKET_OBSERVATION")))
                .andExpect(jsonPath("$.explanation.valuation_method",
                        is("RECENT_MARKET_MEDIAN")));
    }

    @Test
    void acquisitionProfitAmountVsMargin() throws Exception {
        String amount = """
                {"brand":"Samsung","model":"Galaxy S23","storageGb":256,
                 "requiredRepairs":[],"requiredProfit":5000}""";
        // 34124.5 - 5000 = 29124.5
        mvc.perform(post("/api/acquisition/quote")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(amount))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.acquisition.recommended_max_price",
                        closeTo(29124.5, 0.01)));

        String margin = """
                {"brand":"Samsung","model":"Galaxy S23","storageGb":256,
                 "requiredRepairs":[],"requiredProfit":5000,
                 "requiredMargin":0.10}""";
        // margin overrides: 34124.5 - 3412.45 = 30712.05
        mvc.perform(post("/api/acquisition/quote")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(margin))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.acquisition.recommended_max_price",
                        closeTo(30712.05, 0.01)));
    }

    @Test
    void acquisitionUnknownRepairWarnsNotInvents() throws Exception {
        String body = """
                {"brand":"Samsung","model":"Galaxy S23","storageGb":256,
                 "requiredRepairs":["screen_module"],
                 "modelName":"unknown","series":"Q"}""";
        // series Q has no KB rows -> NO_REPAIR_DATA warning path:
        // use a repair type that exists but model series missing
        String body2 = """
                {"brand":"Apple","model":"iPhone 16e","storageGb":128,
                 "requiredRepairs":["battery"],"operationalCost":500}""";
        mvc.perform(post("/api/acquisition/quote")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body2))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.explanation.repairs_without_data",
                        hasItem("battery")));
    }

    // ---------- invalid input ----------

    @Test
    void missingStorageGbIs400() throws Exception {
        mvc.perform(post("/api/valuation")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"brand\":\"Samsung\",\"model\":\"Galaxy S23\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code", is("VALIDATION_FAILED")));
    }

    @Test
    void negativeMoneyIs400() throws Exception {
        String body = """
                {"brand":"Samsung","model":"Galaxy S23","storageGb":256,
                 "operationalCost":-10}""";
        mvc.perform(post("/api/acquisition/quote")
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isBadRequest());
    }

    @Test
    void invalidRepairTypeInAcquisitionIs400() throws Exception {
        String body = """
                {"brand":"Samsung","model":"Galaxy S23","storageGb":256,
                 "requiredRepairs":["warp_drive"]}""";
        mvc.perform(post("/api/acquisition/quote")
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code",
                        is("INVALID_REPAIR_TYPE")));
    }
}
