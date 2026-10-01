package com.tradeagent.backend;

import com.tradeagent.backend.domain.RepairObservation;
import com.tradeagent.backend.domain.RepairQuote;
import com.tradeagent.backend.repository.RepairKbRepository;
import com.tradeagent.backend.service.RepairService;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for the multi-brand selection rules — the Java replica of
 * the ranking exercised by tests/test_multibrand_repair.py.
 */
class RepairServiceSelectionTest {

    private RepairObservation obs(String quality, String ptype,
                                  String stype, double cost, String date) {
        return new RepairObservation(
                "battery", null, "m", null, "X::m", null, "X", null,
                cost, "b", null, ptype, "FULL_REPAIR".equals(ptype),
                quality, null, "TRY", "s", "s", stype, "u", "r",
                date, null);
    }

    private RepairService svc(RepairObservation... rows) {
        RepairKbRepository repo = () -> List.of(rows);
        return new RepairService(repo);
    }

    @Test
    void provenancePriority() {
        RepairService s = svc(
                obs("UNKNOWN", "PART_ONLY", "PART_SUPPLIER", 50, "2026-01-01"),
                obs("UNKNOWN", "FULL_REPAIR", "AUTHORIZED_SERVICE", 900, "2026-01-01"),
                obs("UNKNOWN", "FULL_REPAIR", "INDEPENDENT_REPAIR_SERVICE", 400, "2026-01-01"),
                obs("UNKNOWN", "FULL_REPAIR", "OFFICIAL_MANUFACTURER", 1200, "2026-01-01"));
        RepairQuote q = s.quote("battery", null, "m", null);
        assertEquals(1200.0, q.totalCost());
        assertEquals("OFFICIAL_MANUFACTURER", q.sourceType());
        assertEquals(3, q.alternates().size());
    }

    @Test
    void fullRepairBeatsPartOnlySameSource() {
        RepairService s = svc(
                obs("UNKNOWN", "PART_ONLY", "PART_SUPPLIER", 50, "2026-01-01"),
                obs("UNKNOWN", "FULL_REPAIR", "PART_SUPPLIER", 400, "2026-01-01"));
        RepairQuote q = s.quote("battery", null, "m", null);
        assertEquals("FULL_REPAIR", q.priceType());
        assertEquals(400.0, q.totalCost());
    }

    @Test
    void newestObservationTiebreak() {
        RepairService s = svc(
                obs("UNKNOWN", "FULL_REPAIR", "PART_SUPPLIER", 300, "2026-01-01"),
                obs("UNKNOWN", "FULL_REPAIR", "PART_SUPPLIER", 450, "2026-09-01"));
        RepairQuote q = s.quote("battery", null, "m", null);
        assertEquals(450.0, q.totalCost());
    }

    @Test
    void qualityTierOrderAndAlternates() {
        RepairService s = svc(
                obs("COMPATIBLE", "FULL_REPAIR", "INDEPENDENT_REPAIR_SERVICE", 300, "2026-01-01"),
                obs("ORIGINAL", "FULL_REPAIR", "INDEPENDENT_REPAIR_SERVICE", 900, "2026-01-01"),
                obs("HIGH_QUALITY", "FULL_REPAIR", "INDEPENDENT_REPAIR_SERVICE", 500, "2026-01-01"));
        RepairQuote q = s.quote("battery", null, "m", null);
        assertEquals(900.0, q.totalCost());
        assertEquals("ORIGINAL", q.repairQuality());
        assertEquals(List.of(500.0, 300.0),
                q.alternates().stream().map(RepairQuote.Alternate::totalCost)
                        .toList());
    }

    @Test
    void partOnlyFlaggedIncomplete() {
        RepairService s = svc(
                obs("COMPATIBLE", "PART_ONLY", "PART_SUPPLIER", 50, "2026-01-01"));
        RepairQuote q = s.quote("battery", null, "m", null);
        assertTrue(q.isPartOnly());
        assertEquals("INCOMPLETE_REPAIR_COST", q.quoteStatus());
        assertFalse(q.includesLabor());
        assertTrue(q.note().toLowerCase().contains("labor"));
    }

    @Test
    void noRepairDataNeverFabricates() {
        RepairService s = svc(
                obs("UNKNOWN", "FULL_REPAIR", "PART_SUPPLIER", 100, "2026-01-01"));
        RepairQuote q = s.quote("mainboard", null, "m", null);
        assertNull(q.totalCost());
        assertEquals("NO_REPAIR_DATA", q.quoteStatus());
    }

    @Test
    void modelKeyResolvesExact() {
        RepairObservation r = obs("UNKNOWN", "FULL_REPAIR",
                "AUTHORIZED_SERVICE", 900, "2026-01-01");
        RepairService s = svc(r);
        RepairQuote q = s.quote("battery", null, "unrelated name", null,
                "X::m");
        assertEquals(900.0, q.totalCost());
        assertEquals("EXACT_REPAIR_LOOKUP", q.lookupMethod());
    }

    @Test
    void modelKeySlugSuffixMatchesModelName() {
        // "iPhone 13" -> slug suffix ::iphone-13 matches APPLE::iphone-13
        RepairObservation r = new RepairObservation(
                "battery", null, "iPhone 13", null, "APPLE::iphone-13",
                null, "APPLE", null, 6250.0, "b", null, "FULL_REPAIR",
                true, "ORIGINAL", null, "TRY", "tp", "tp",
                "INDEPENDENT_REPAIR_SERVICE", "u", "r", "2026-09-27", null);
        RepairService s = svc(r);
        RepairQuote q = s.quote("battery", null, "iPhone 13", null);
        assertEquals(6250.0, q.totalCost());
        assertEquals("APPLE::iphone-13", q.modelKey());
    }
}
