package com.tradeagent.backend.controller;

import com.tradeagent.backend.domain.MarketObservation;
import com.tradeagent.backend.service.ValuationService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Comparator;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/devices")
public class DeviceController {

    private final ValuationService valuation;

    public DeviceController(ValuationService valuation) {
        this.valuation = valuation;
    }

    public record DeviceRow(String canonicalVariant, String brand,
                            String model, Double storageGb,
                            String gradeSegment, Double priceMedian,
                            String observedAt, Integer offerCount,
                            Integer sellerCount) {
    }

    @GetMapping
    public Map<String, Object> list(
            @RequestParam(required = false) String brand,
            @RequestParam(required = false) String model,
            @RequestParam(required = false) String grade,
            @RequestParam(required = false) Double storageGb) {
        List<DeviceRow> rows = valuation.latestAll().stream()
                .filter(r -> brand == null
                        || r.canonicalBrand().equalsIgnoreCase(brand))
                .filter(r -> model == null
                        || r.canonicalModel().toLowerCase()
                                .contains(model.toLowerCase()))
                .filter(r -> grade == null
                        || r.gradeSegment().equalsIgnoreCase(grade))
                .filter(r -> storageGb == null
                        || (r.storageGb() != null
                            && r.storageGb().equals(storageGb)))
                .sorted(Comparator.comparing(
                        MarketObservation::canonicalVariant))
                .map(r -> new DeviceRow(r.canonicalVariant(),
                        r.canonicalBrand(), r.canonicalModel(),
                        r.storageGb(), r.gradeSegment(), r.priceMedian(),
                        r.observedDate(), r.nOffers(), r.nSellers()))
                .toList();
        return Map.of("count", rows.size(), "devices", rows,
                "asOf", valuation.asOf().toString());
    }
}
