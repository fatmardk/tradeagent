package com.tradeagent.backend.service;

import com.tradeagent.backend.domain.RepairObservation;
import com.tradeagent.backend.domain.RepairQuote;
import com.tradeagent.backend.exception.ApiException;
import com.tradeagent.backend.repository.RepairKbRepository;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

/**
 * REPAIR_KB lookup — Java replica of src/repair/lookup.py.
 * EXACT_REPAIR_LOOKUP -> SERIES_LEVEL_LOOKUP -> NO_REPAIR_DATA.
 * Never fabricates a cost.
 */
@Service
public class RepairService {

    /** Friendly aliases -> canonical KB repair_type. */
    private static final Map<String, String> ALIASES = Map.of(
            "screen_replacement", "screen_module",
            "battery_replacement", "battery");

    private final RepairKbRepository repo;

    public RepairService(RepairKbRepository repo) {
        this.repo = repo;
    }

    public Set<String> knownRepairTypes() {
        Set<String> t = new TreeSet<>();
        repo.findAll().forEach(r -> t.add(r.repairType()));
        return t;
    }

    /** Normalizes and validates a repair type; 400 on unknown input. */
    public String normalizeRepairType(String raw) {
        String key = raw.trim().toLowerCase().replace('-', '_')
                .replace(' ', '_');
        String canonical = ALIASES.getOrDefault(key, key);
        if (!knownRepairTypes().contains(canonical)) {
            throw new ApiException(HttpStatus.BAD_REQUEST,
                    "INVALID_REPAIR_TYPE",
                    "Unknown repair type '" + raw + "'. Valid: "
                            + knownRepairTypes()
                            + " (aliases: " + ALIASES.keySet() + ")");
        }
        return canonical;
    }

    public RepairQuote quote(String repairType, String modelCode,
                             String modelName, String series) {
        List<RepairObservation> rows = repo.findAll().stream()
                .filter(r -> r.repairType().equals(repairType)).toList();

        String code = modelCode;
        if ((code == null || code.isBlank()) && modelName != null) {
            code = rows.stream()
                    .filter(r -> r.modelName() != null
                            && r.modelName().trim()
                                    .equalsIgnoreCase(modelName.trim()))
                    .map(RepairObservation::deviceId)
                    .filter(id -> id != null && !id.isBlank())
                    .findFirst().orElse(null);
        }
        if (code != null && !code.isBlank()) {
            final String lookupCode = code;
            var hit = rows.stream()
                    .filter(r -> lookupCode.equals(r.deviceId())).findFirst();
            if (hit.isPresent()) {
                var r = hit.get();
                return new RepairQuote(repairType, "EXACT_REPAIR_LOOKUP",
                        r.totalRepairCost(), r.deviceId(), r.sourceId(),
                        r.observedAt(), null);
            }
        }
        if (series != null && !series.isBlank()) {
            var hit = rows.stream()
                    .filter(r -> r.deviceId() == null
                            && series.equalsIgnoreCase(r.series()))
                    .findFirst();
            if (hit.isPresent()) {
                var r = hit.get();
                return new RepairQuote(repairType, "SERIES_LEVEL_LOOKUP",
                        r.totalRepairCost(), null, r.sourceId(),
                        r.observedAt(),
                        "series-level (" + series + ") price,"
                                + " not model-specific");
            }
        }
        return new RepairQuote(repairType, "NO_REPAIR_DATA", null, code,
                null, null,
                "no reliable repair record — cost unknown");
    }

    public List<RepairQuote> quoteAll(List<String> repairTypes,
                                      String modelCode, String modelName,
                                      String series) {
        return repairTypes.stream()
                .map(t -> quote(t, modelCode, modelName, series))
                .toList();
    }
}
