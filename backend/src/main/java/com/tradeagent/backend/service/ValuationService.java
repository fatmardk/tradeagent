package com.tradeagent.backend.service;

import com.tradeagent.backend.config.BackendProperties;
import com.tradeagent.backend.domain.MarketObservation;
import com.tradeagent.backend.domain.SourceType;
import com.tradeagent.backend.domain.ValuationMethod;
import com.tradeagent.backend.domain.ValuationResult;
import com.tradeagent.backend.repository.MarketSnapshotRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Hybrid Engine v1 routing — Java replica of src/market/{engine,valuation,
 * cold_start}.py. Methodology unchanged:
 *
 *   fresh obs + >=2 offers + >=2 sellers -> RECENT_MARKET_MEDIAN
 *   fresh obs, weak coverage             -> MARKET_MEDIAN_LOW_COVERAGE
 *   stale / missing                      -> deterministic median hierarchy
 *      COLD_START_MODEL_MEDIAN -> BRAND_STORAGE -> BRAND -> GLOBAL
 *
 * No ML in the default path — same as the validated Python engine.
 */
@Service
public class ValuationService {

    private final MarketSnapshotRepository repo;
    private final int maxObsAgeDays;
    private final String gradeSegment;

    // latest row per "variant|grade" (mirrors MarketEstimator.latest)
    private final Map<String, MarketObservation> latest = new HashMap<>();
    private final LocalDate asOf;

    public ValuationService(MarketSnapshotRepository repo,
                            BackendProperties props) {
        this.repo = repo;
        var v = props.getValuation();
        this.maxObsAgeDays = v.getMaxObsAgeDays();
        this.gradeSegment = v.getGradeSegment();
        List<MarketObservation> sorted = repo.findAll().stream()
                .sorted(Comparator.comparing(MarketObservation::date))
                .toList();
        for (MarketObservation r : sorted) {
            latest.put(r.canonicalVariant() + "|" + r.gradeSegment(), r);
        }
        this.asOf = v.getAsOf() == null || v.getAsOf().isBlank()
                ? sorted.stream().map(MarketObservation::date)
                        .max(Comparator.naturalOrder())
                        .orElse(LocalDate.now())
                : LocalDate.parse(v.getAsOf());
    }

    /** brand|model-slug|gb — same slug rule as src/market/engine.py. */
    public static String canonicalVariant(String brand, String model,
                                          double storageGb) {
        String slug = model.toLowerCase()
                .replaceAll("[^a-z0-9]", "-")
                .replaceAll("-+", "-")
                .replaceAll("^-|-$", "");
        return brand.toLowerCase() + "|" + slug + "|" + (int) storageGb;
    }

    public LocalDate asOf() {
        return asOf;
    }

    /** Latest observation per variant+grade (for /api/devices). */
    public List<MarketObservation> latestAll() {
        return new ArrayList<>(latest.values());
    }

    public ValuationResult valuate(String brand, String model,
                                   Double storageGb) {
        String variant = storageGb != null
                ? canonicalVariant(brand, model, storageGb) : null;
        MarketObservation row = variant == null
                ? null : latest.get(variant + "|" + gradeSegment);

        List<String> notes = new ArrayList<>();
        if (row != null && row.priceMedian() != null) {
            int age = (int) ChronoUnit.DAYS.between(row.date(), asOf);
            if (age <= maxObsAgeDays) {
                ValuationMethod method = ValuationMethod.RECENT_MARKET_MEDIAN;
                if (row.nOffers() == 1 || row.nSellers() < 2) {
                    method = ValuationMethod.MARKET_MEDIAN_LOW_COVERAGE;
                    notes.add("single offer/seller — point estimate is real"
                            + " but spread is not market-derived");
                }
                Double p25 = row.priceQ25(), p75 = row.priceQ75(), riqr = null;
                if (row.nOffers() < 2) {
                    p25 = p75 = null;  // quartiles undefined with one offer
                } else if (row.priceMedian() != 0) {
                    riqr = (p75 - p25) / row.priceMedian();
                }
                return new ValuationResult(method, row.priceMedian(),
                        SourceType.REAL_MARKET_OBSERVATION,
                        row.observedDate(), age, row.nOffers(),
                        row.nSellers(), p25, p75, riqr, gradeSegment,
                        null, notes);
            }
            notes.add("observation is " + age + "d old, beyond provisional "
                    + maxObsAgeDays + "d freshness window");
        }

        // ---- deterministic cold-start hierarchy (src/market/cold_start.py)
        return coldStart(brand, model, storageGb, notes);
    }

    private ValuationResult coldStart(String brand, String model,
                                      Double storageGb, List<String> notes) {
        List<MarketObservation> gradeRows = repo.findAll().stream()
                .filter(r -> gradeSegment.equals(r.gradeSegment()))
                .toList();

        if (model != null) {
            List<Double> vals = gradeRows.stream()
                    .filter(r -> model.equalsIgnoreCase(r.canonicalModel()))
                    .map(MarketObservation::priceMedian)
                    .toList();
            if (!vals.isEmpty()) {
                notes.add("same-model median across its observed storages");
                return fallbackResult(ValuationMethod.COLD_START_MODEL_MEDIAN,
                        median(vals), vals.size(), notes);
            }
        }
        if (storageGb != null) {
            List<Double> vals = gradeRows.stream()
                    .filter(r -> brand.equalsIgnoreCase(r.canonicalBrand())
                            && r.storageGb() != null
                            && r.storageGb().equals(storageGb))
                    .map(MarketObservation::priceMedian)
                    .toList();
            if (!vals.isEmpty()) {
                return fallbackResult(ValuationMethod.COLD_START_BRAND_STORAGE,
                        median(vals), vals.size(), notes);
            }
        }
        List<Double> brandVals = gradeRows.stream()
                .filter(r -> brand.equalsIgnoreCase(r.canonicalBrand()))
                .map(MarketObservation::priceMedian)
                .toList();
        if (!brandVals.isEmpty()) {
            return fallbackResult(ValuationMethod.COLD_START_BRAND,
                    median(brandVals), brandVals.size(), notes);
        }
        List<Double> all = gradeRows.stream()
                .map(MarketObservation::priceMedian).toList();
        notes.add("no brand/model coverage — global median");
        return fallbackResult(ValuationMethod.COLD_START_GLOBAL,
                median(all), all.size(), notes);
    }

    private ValuationResult fallbackResult(ValuationMethod m, double value,
                                           int support, List<String> notes) {
        return new ValuationResult(m, value, SourceType.FALLBACK_ESTIMATE,
                null, null, null, null, null, null, null, gradeSegment,
                support, notes);
    }

    private static double median(List<Double> vals) {
        List<Double> s = vals.stream().sorted().collect(Collectors.toList());
        int n = s.size();
        return n % 2 == 1 ? s.get(n / 2)
                          : (s.get(n / 2 - 1) + s.get(n / 2)) / 2.0;
    }
}
