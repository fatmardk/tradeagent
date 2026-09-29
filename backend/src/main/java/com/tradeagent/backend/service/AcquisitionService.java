package com.tradeagent.backend.service;

import com.tradeagent.backend.domain.BusinessRules;
import com.tradeagent.backend.domain.RepairQuote;
import com.tradeagent.backend.domain.SourceType;
import com.tradeagent.backend.domain.ValuationResult;
import com.tradeagent.backend.dto.AcquisitionResponse;
import com.tradeagent.backend.dto.DeviceDto;
import com.tradeagent.backend.dto.ValuationResponse;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * Acquisition formula — replica of src/acquisition/engine.py:
 *   max_price = market_value - repair_cost - operational_cost
 *               - risk_buffer - required_profit
 * All business parameters stay explicit BUSINESS_INPUT.
 */
@Service
public class AcquisitionService {

    private final ValuationService valuationService;
    private final RepairService repairService;

    public AcquisitionService(ValuationService valuationService,
                              RepairService repairService) {
        this.valuationService = valuationService;
        this.repairService = repairService;
    }

    public AcquisitionResponse quote(String brand, String model,
                                     Double storageGb,
                                     List<String> requiredRepairs,
                                     BusinessRules rules,
                                     String modelCode, String series) {
        ValuationResult v = valuationService.valuate(brand, model, storageGb);
        List<String> repairTypes = requiredRepairs == null ? List.of()
                : requiredRepairs.stream()
                        .map(repairService::normalizeRepairType).toList();
        List<RepairQuote> quotes = repairService.quoteAll(
                repairTypes, modelCode, model, series);

        List<String> warnings = new ArrayList<>();
        List<RepairQuote> known = quotes.stream()
                .filter(q -> q.totalCost() != null).toList();
        List<RepairQuote> unknown = quotes.stream()
                .filter(q -> q.totalCost() == null).toList();
        double repairCost = known.stream()
                .mapToDouble(RepairQuote::totalCost).sum();
        unknown.forEach(q -> warnings.add(q.repairType()
                + ": NO_REPAIR_DATA — cost excluded, acquisition price"
                + " is optimistic"));

        Double mv = v.marketValue();
        Double maxPrice = null;
        double profit = 0.0;
        Map<String, Object> components = new LinkedHashMap<>();
        if (mv != null) {
            profit = rules.profitFor(mv);
            maxPrice = round2(mv - repairCost - rules.operationalCost()
                    - rules.riskBuffer() - profit);
            if (maxPrice < 0) {
                warnings.add("computed max acquisition price is negative —"
                        + " device should likely not be acquired");
            }
            components.put("expected_market_value", mv);
            components.put("repair_cost", repairCost);
            components.put("operational_cost", rules.operationalCost());
            components.put("risk_buffer", rules.riskBuffer());
            components.put("required_profit", profit);
        } else {
            warnings.add("no market value — cannot price");
        }

        Map<String, Object> explanation = new LinkedHashMap<>();
        explanation.put("valuation_method", v.method().name());
        explanation.put("valuation_source", v.sourceType().name());
        explanation.put("market_reference_count", v.offerCount());
        explanation.put("repair_cost_source",
                known.stream().map(RepairQuote::sourceId)
                        .filter(Objects::nonNull).distinct().sorted().toList());
        explanation.put("repair_lookup_methods",
                quotes.stream().map(RepairQuote::lookupMethod).toList());
        explanation.put("repairs_without_data",
                unknown.stream().map(RepairQuote::repairType).toList());
        explanation.put("profit_target", SourceType.BUSINESS_INPUT.name());
        explanation.put("operational_cost_source",
                SourceType.BUSINESS_INPUT.name());
        explanation.put("risk_buffer_source",
                SourceType.BUSINESS_INPUT.name());
        explanation.put("market_value_origin",
                v.sourceType() == SourceType.REAL_MARKET_OBSERVATION
                        ? SourceType.REAL_MARKET_OBSERVATION.name()
                        : SourceType.MODEL_ESTIMATE.name());

        warnings.addAll(v.notes());

        return new AcquisitionResponse(
                new DeviceDto(brand, model, storageGb,
                        storageGb == null ? null
                                : ValuationService.canonicalVariant(
                                        brand, model, storageGb)),
                ValuationResponse.from(v),
                Map.of("required_repairs", repairTypes,
                        "quotes", quotes,
                        "expected_cost", repairCost,
                        "source_type", SourceType.OFFICIAL_REPAIR_DATA.name()),
                Map.of("operational_cost", rules.operationalCost(),
                        "risk_buffer", rules.riskBuffer(),
                        "required_profit", profit,
                        "required_margin", rules.requiredMargin() != null
                                ? rules.requiredMargin() : "n/a",
                        "source_type", SourceType.BUSINESS_INPUT.name()),
                Map.of("recommended_max_price",
                        maxPrice == null ? "unavailable" : maxPrice,
                        "components", components,
                        "currency", "TRY"),
                explanation, warnings);
    }

    private static double round2(double x) {
        return Math.round(x * 100.0) / 100.0;
    }
}
