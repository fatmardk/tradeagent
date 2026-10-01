package com.tradeagent.backend.controller;

import com.tradeagent.backend.domain.RepairQuote;
import com.tradeagent.backend.service.RepairService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/repair-costs")
public class RepairController {

    private final RepairService repair;

    public RepairController(RepairService repair) {
        this.repair = repair;
    }

    @GetMapping
    public Map<String, Object> lookup(
            @RequestParam(required = false) String repairType,
            @RequestParam(required = false) String modelCode,
            @RequestParam(required = false) String modelName,
            @RequestParam(required = false) String series,
            @RequestParam(required = false) String modelKey) {
        if (repairType != null && !repairType.isBlank()) {
            String t = repair.normalizeRepairType(repairType);
            RepairQuote q = repair.quote(t, modelCode, modelName, series,
                    modelKey);
            return Map.of("device", deviceMeta(modelCode, modelName, series),
                    "quotes", List.of(q));
        }
        // all repair types for the device
        List<RepairQuote> quotes = repair.knownRepairTypes().stream()
                .map(t -> repair.quote(t, modelCode, modelName, series,
                        modelKey))
                .toList();
        return Map.of("device", deviceMeta(modelCode, modelName, series),
                "quotes", quotes);
    }

    private Map<String, Object> deviceMeta(String code, String name,
                                           String series) {
        return Map.of("modelCode", code == null ? "" : code,
                "modelName", name == null ? "" : name,
                "series", series == null ? "" : series,
                "repair_kb_coverage",
                "multi-brand (Apple/Samsung/Xiaomi/Oppo/Realme"
                        + " + part suppliers)");
    }
}
