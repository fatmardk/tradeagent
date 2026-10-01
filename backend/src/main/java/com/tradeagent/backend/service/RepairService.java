package com.tradeagent.backend.service;

import com.tradeagent.backend.domain.RepairObservation;
import com.tradeagent.backend.domain.RepairQuote;
import com.tradeagent.backend.exception.ApiException;
import com.tradeagent.backend.repository.RepairKbRepository;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

/**
 * Multi-brand REPAIR_KB lookup — Java replica of src/repair/lookup.py.
 *
 * Lookup: EXACT_REPAIR_LOOKUP -> SERIES_LEVEL_LOOKUP -> NO_REPAIR_DATA.
 * Selection within matching rows: source_type provenance
 * (OFFICIAL_MANUFACTURER -> AUTHORIZED_SERVICE
 *  -> INDEPENDENT_REPAIR_SERVICE -> PART_SUPPLIER),
 * then FULL_REPAIR -> PART_ONLY, then newest observed_at,
 * then quality tier (ORIGINAL first). Never fabricates a cost.
 * PART_ONLY is flagged INCOMPLETE_REPAIR_COST — labor is not included.
 */
@Service
public class RepairService {

    private static final Map<String, String> ALIASES = Map.of(
            "screen_replacement", "screen_module",
            "battery_replacement", "battery");

    private static final Map<String, Integer> SOURCE_TYPE_RANK = Map.of(
            "OFFICIAL_MANUFACTURER", 0,
            "AUTHORIZED_SERVICE", 1,
            "INDEPENDENT_REPAIR_SERVICE", 2,
            "PART_SUPPLIER", 3);
    private static final Map<String, Integer> PRICE_TYPE_RANK = Map.of(
            "FULL_REPAIR", 0,
            "PART_ONLY", 1);
    private static final Map<String, Integer> QUALITY_RANK = Map.of(
            "ORIGINAL", 0, "SERVICE", 1, "PREMIUM", 2, "HIGH_QUALITY", 3,
            "REFURBISHED", 4, "PULLED", 5, "COMPATIBLE", 6, "UNKNOWN", 7);

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
        return quote(repairType, modelCode, modelName, series, null);
    }

    public RepairQuote quote(String repairType, String modelCode,
                             String modelName, String series,
                             String modelKey) {
        List<RepairObservation> rows = repo.findAll().stream()
                .filter(r -> r.repairType().equals(repairType)).toList();

        List<RepairObservation> cand =
                candidates(rows, modelCode, modelName, modelKey);
        if (!cand.isEmpty()) {
            List<RepairObservation> ranked = rank(cand);
            RepairQuote q = toQuote(repairType, "EXACT_REPAIR_LOOKUP",
                    ranked.get(0), ranked.subList(1, ranked.size()));
            if (ranked.size() > 1) {
                Set<String> tiers = new TreeSet<>();
                tiers.add(ranked.get(0).repairQuality());
                ranked.subList(1, ranked.size())
                        .forEach(r -> tiers.add(r.repairQuality()));
                q = appendNote(q, ranked.size() + " observations across "
                        + tiers.size() + " quality tiers");
            }
            return q;
        }

        String code = (modelCode != null && !modelCode.isBlank())
                ? modelCode
                : codeForName(rows, modelName);
        if (series != null && !series.isBlank()) {
            var hit = rows.stream()
                    .filter(r -> r.deviceId() == null
                            && series.equalsIgnoreCase(r.series()))
                    .toList();
            if (!hit.isEmpty()) {
                List<RepairObservation> ranked = rank(hit);
                RepairQuote q = toQuote(repairType, "SERIES_LEVEL_LOOKUP",
                        ranked.get(0), ranked.subList(1, ranked.size()));
                q = appendNote(q, "series-level (" + series
                        + ") price, not model-specific");
                return q;
            }
        }
        return new RepairQuote(repairType, "NO_REPAIR_DATA", null, code,
                null, null,
                "no reliable repair record — cost unknown",
                null, null, null, null, null, null, "NO_REPAIR_DATA",
                List.of());
    }

    public List<RepairQuote> quoteAll(List<String> repairTypes,
                                      String modelCode, String modelName,
                                      String series) {
        return repairTypes.stream()
                .map(t -> quote(t, modelCode, modelName, series))
                .toList();
    }

    // ---------- candidate selection (deterministic, no fuzzy merges) ----------

    private List<RepairObservation> candidates(List<RepairObservation> rows,
                                               String modelCode,
                                               String modelName,
                                               String modelKey) {
        if (modelKey != null && !modelKey.isBlank()) {
            var hit = rows.stream()
                    .filter(r -> modelKey.equals(r.modelKey())).toList();
            if (!hit.isEmpty()) return hit;
        }
        String code = (modelCode != null && !modelCode.isBlank())
                ? modelCode : codeForName(rows, modelName);
        if (code != null) {
            final String c = code;
            var hit = rows.stream()
                    .filter(r -> c.equals(r.deviceId())
                            || c.equals(r.modelCode())).toList();
            if (!hit.isEmpty()) return hit;
        }
        if (modelName != null && !modelName.isBlank()) {
            String slug = slug(modelName);
            var hit = rows.stream()
                    .filter(r -> r.modelKey() != null
                            && r.modelKey().endsWith("::" + slug)).toList();
            if (!hit.isEmpty()) return hit;
            String name = modelName.trim();
            hit = rows.stream()
                    .filter(r -> r.modelName() != null
                            && r.modelName().trim().equalsIgnoreCase(name))
                    .toList();
            if (!hit.isEmpty()) return hit;
        }
        return List.of();
    }

    private String codeForName(List<RepairObservation> rows, String modelName) {
        if (modelName == null || modelName.isBlank()) return null;
        return rows.stream()
                .filter(r -> r.modelName() != null
                        && r.modelName().trim()
                                .equalsIgnoreCase(modelName.trim()))
                .map(r -> r.deviceId() != null ? r.deviceId() : r.modelCode())
                .filter(id -> id != null && !id.isBlank())
                .findFirst().orElse(null);
    }

    private static String slug(String s) {
        return s.strip().toLowerCase()
                .replaceAll("[^a-z0-9]+", "-")
                .replaceAll("^-+|-+$", "");
    }

    /** provenance -> price_type -> newest observed_at -> quality tier. */
    private List<RepairObservation> rank(List<RepairObservation> rows) {
        List<RepairObservation> out = new ArrayList<>(rows);
        out.sort(Comparator
                .comparingInt((RepairObservation r) ->
                        SOURCE_TYPE_RANK.getOrDefault(r.sourceType(), 9))
                .thenComparingInt(r ->
                        PRICE_TYPE_RANK.getOrDefault(r.repairPriceType(), 9))
                .thenComparing(this::obsDate,
                        Comparator.nullsLast(Comparator.reverseOrder()))
                .thenComparingInt(r ->
                        QUALITY_RANK.getOrDefault(r.repairQuality(), 9)));
        return out;
    }

    private LocalDate obsDate(RepairObservation r) {
        try {
            return r.observedAt() == null ? null
                    : LocalDate.parse(r.observedAt().substring(0, 10));
        } catch (Exception e) {
            return null;
        }
    }

    private RepairQuote toQuote(String repairType, String method,
                                RepairObservation r,
                                List<RepairObservation> rest) {
        String priceType = r.repairPriceType() == null
                ? "FULL_REPAIR" : r.repairPriceType();
        String status = "PART_ONLY".equals(priceType)
                ? "INCOMPLETE_REPAIR_COST" : "OK";
        String note = "PART_ONLY".equals(priceType)
                ? "part-only price — labor NOT included; "
                  + "do not use as a complete repair cost"
                : null;
        List<RepairQuote.Alternate> alternates = rest.stream()
                .map(a -> new RepairQuote.Alternate(
                        a.repairQuality(), a.sourceQualityLabel(),
                        a.totalRepairCost(), a.repairPriceType(),
                        a.sourceId(), a.sourceType(), a.observedAt()))
                .toList();
        return new RepairQuote(repairType, method, r.totalRepairCost(),
                r.deviceId(), r.sourceId(), r.observedAt(), note,
                priceType,
                r.includesLabor() != null ? r.includesLabor()
                        : "FULL_REPAIR".equals(priceType),
                r.sourceType(), r.repairQuality(), r.modelKey(),
                r.sourceReference(), status, alternates);
    }

    private RepairQuote appendNote(RepairQuote q, String extra) {
        String note = q.note() == null ? extra : q.note() + "; " + extra;
        return new RepairQuote(q.repairType(), q.lookupMethod(), q.totalCost(),
                q.deviceId(), q.sourceId(), q.observedAt(), note,
                q.priceType(), q.includesLabor(), q.sourceType(),
                q.repairQuality(), q.modelKey(), q.sourceReference(),
                q.quoteStatus(), q.alternates());
    }
}
