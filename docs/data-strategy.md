# Data Strategy — Final (Phase 1A)

Full source research: `docs/data-source-research.md` (Bölüm I–III).
This file is the operative summary.

## Layered architecture

```
DEVICE_MASTER / DEVICE_VARIANT / DEVICE_ALIAS        (entity layer)
        │  B-enrichment: release_date, ram, storage, specs
PRICE_OBSERVATION                                    (economic layer)
        │  price_kind: MSRP | NEW_LIST | USED_LIST | REFURBISHED_LIST
        │            | SOLD | BUYBACK_OFFER | WHOLESALE
REPAIR_COST_OBSERVATION (REPAIR_KB)                  (deterministic layer)
        │
DEFECT PRIORS (Open Repair Alliance — C: prior only, never row-joined)
        │
MODEL 1 market value  +  REPAIR_KB  +  business params
        ↓
ACQUISITION ENGINE (deterministic, interval output)
```

## Two-layer learning design

| Layer | Data | Learns |
|---|---|---|
| A — structure | ReCell (ratio), condition/battery effects where real data exists | `ratio = f(age, condition, battery, storage, segment)` |
| B — level | our 2026 TR observations | `refurb_price_TR(model, grade, t)`; calibrates A via shrunk κ per brand×segment |

No row-level join between populations. κ = shrinkage-adjusted
`median(observed_ratio / predicted_ratio)`.

## Missing-data rule

Model-level immutable attributes (release date, RAM, battery capacity, chipset,
5G) may be enriched onto a variant. Individual-device attributes
(battery_health, damage, repair history, parts replaced) stay NULL when
unobserved. Enforced by schema nullability + `is_synthetic` flag +
`synthetic_provenance` side table.

## Source status (Phase 1A verified against real files)

| Source | Status | Reason |
|---|---|---|
| ReCell/ahsan81 | APPROVED_FOR_EXPLORATION_ONLY | real lineage but prices normalized; R²(ratio~days_used)=0.90 is too clean for raw market data |
| mizan121 | **REJECTED (training)** | corr(battery,age)≈0, corr(storage,ratio)≈0.01, uniform brand×condition grid, exactly 5000 rows — synthetic-generation evidence. REFERENCE_ONLY for schema |
| TR observations | PENDING_COLLECTION | schema ready; Getmobil/EasyCep/Amazon Depo permitted observation only |
| Apple/Samsung TR repair lists | PENDING_COLLECTION | REPAIR_KB primary sources |
| Open Repair Alliance | PENDING (prior only) | defect frequencies at brand/year level |
| SHPhoneBench | REFERENCE_ONLY | defect/grade taxonomy; DP-perturbed CNY prices are not a target |
| SENATECH/AKILLICIHAZ | UNAVAILABLE | proprietary; partnership target |

## Decision timeline (leakage guard)

T0 offered → T1 inspected → T2 refurbished → T3 listed → T4 sold.
T0 model sees only: identity, declared condition, market snapshots, priors.
T1+ fields (battery_health, defect codes, repair cost, final grade,
list/sale price, days_to_sell) are labels/posteriors, never T0 features.

## Company-data upgrade path

| Proprietary field | Component improved |
|---|---|
| purchase_price (T0 outcome) | offer→acceptance calibration, risk buffer |
| inspection results, battery_health, defects (T1) | Model 1 features; P(defect|model,age) posterior replaces ORA prior |
| parts_replaced, part_cost, labor_cost (T2) | REPAIR_KB lookup → learned cost model |
| final_grade (T2) | true grade labels replace seller-grade mapping |
| list_price, sale_price, sale_date (T3–T4) | list→sale discount + days_to_sell models (currently impossible) |
| returns, warranty_claims | learned risk score replaces rule buffer |

No fabricated company data, no claimed accuracy deltas.
