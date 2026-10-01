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
        // FULL_REPAIR is the only type treated as a complete repair cost.
        List<RepairQuote> known = quotes.stream()
                .filter(q -> q.totalCost() != null && !q.isPartOnly())
                .toList();
        List<RepairQuote> partOnly = quotes.stream()
                .filter(q -> q.totalCost() != null && q.isPartOnly())
                .toList();
        List<RepairQuote> unknown = quotes.stream()
                .filter(q -> q.totalCost() == null).toList();
        double repairCost = known.stream()
                .mapToDouble(RepairQuote::totalCost).sum();
        partOnly.forEach(q -> warnings.add(q.repairType()
                + ": INCOMPLETE_REPAIR_COST — part-only price "
                + q.totalCost()
                + " TRY exists but labor is not included; "
                + "not subtracted as a complete repair cost"));
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
        Map<String, String> quoteStatus = new LinkedHashMap<>();
        quotes.forEach(q -> quoteStatus.put(q.repairType(),
                q.quoteStatus()));
        explanation.put("repair_quote_status", quoteStatus);
        explanation.put("repairs_part_only",
                partOnly.stream().map(q -> Map.of(
                        "repair_type", q.repairType(),
                        "part_price", q.totalCost(),
                        "source_id",
                        q.sourceId() == null ? "" : q.sourceId())).toList());
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
                        "source_type", repairSourceType(known, partOnly),
                        "source_types", quotes.stream()
                                .map(RepairQuote::sourceType)
                                .filter(Objects::nonNull).distinct().sorted()
                                .toList()),
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

    /** Distinct repair source provenance label for the repair block. */
    private static String repairSourceType(List<RepairQuote> known,
                                           List<RepairQuote> partOnly) {
        var types = java.util.stream.Stream
                .concat(known.stream(), partOnly.stream())
                .map(RepairQuote::sourceType).filter(Objects::nonNull)
                .distinct().sorted().toList();
        if (types.isEmpty()) {
            return "REPAIR_DATA_UNAVAILABLE";
        }
        return types.size() == 1 ? types.get(0) : "MIXED_REPAIR_SOURCES";
    }

    private static double round2(double x) {
        return Math.round(x * 100.0) / 100.0;
    }
}
