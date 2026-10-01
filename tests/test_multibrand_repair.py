"""Multi-brand Repair KB tests — real data + synthetic priority scenarios."""
import pandas as pd
import pytest

from src.repair.lookup import RepairKB, RepairQuote, display_repair
from src.acquisition.engine import BusinessRules, compute_acquisition

MB = "data/processed/repair_cost_observation_multibrand.parquet"


@pytest.fixture(scope="module")
def kb():
    return RepairKB.load(MB)


# ---------- exact lookup per brand ----------

def test_apple_exact_lookup(kb):
    q = kb.quote("screen_module", model_name="iPhone 13")
    assert q.lookup_method == "EXACT_REPAIR_LOOKUP"
    assert q.total_cost is not None and q.total_cost > 0
    assert q.price_type == "FULL_REPAIR"


def test_samsung_exact_lookup(kb):
    q = kb.quote("screen_module", model_code="SM-S911")
    assert q.lookup_method == "EXACT_REPAIR_LOOKUP"
    assert q.total_cost == 9900.0  # regression value preserved


def test_xiaomi_exact_lookup(kb):
    q = kb.quote("screen_module", model_name="Redmi Note 13")
    assert q.lookup_method == "EXACT_REPAIR_LOOKUP"
    assert q.total_cost is not None and q.total_cost > 0


def test_oppo_realme_lookup(kb):
    for m in ("Realme 11",):
        q = kb.quote("battery", model_name=m)
        assert q.lookup_method == "EXACT_REPAIR_LOOKUP"
        assert q.price_type == "FULL_REPAIR"


# ---------- PART_ONLY behavior ----------

def test_part_only_flagged_not_full(kb):
    # pick a (model, repair_type) that has ONLY part-only rows in the real KB
    df = kb.df
    po = df[df.repair_price_type == "PART_ONLY"]
    full_models = df[(df.repair_price_type == "FULL_REPAIR")
                     ].groupby(["model_name", "repair_type"]).size()
    target = None
    for _, r in po.iterrows():
        if (r.model_name, r.repair_type) not in full_models.index:
            target = r
            break
    assert target is not None, "no part-only-only case found in KB"
    q = kb.quote(target.repair_type, model_name=target.model_name)
    assert q.lookup_method == "EXACT_REPAIR_LOOKUP"
    assert q.price_type == "PART_ONLY"
    assert q.includes_labor is False
    assert q.quote_status == "INCOMPLETE_REPAIR_COST"
    assert "labor" in (q.note or "").lower()


def test_part_only_not_subtracted_in_acquisition():
    mv_block = {"value": 30000.0, "method": "TEST", "source": "x"}
    q = RepairQuote("charging_port", "EXACT_REPAIR_LOOKUP", 500.0,
                    "dev", "ercorp", "2026-09-27",
                    price_type="PART_ONLY", includes_labor=False,
                    source_type="PART_SUPPLIER",
                    quote_status="INCOMPLETE_REPAIR_COST")
    rules = BusinessRules(operational_cost=1000, risk_buffer=500,
                          required_profit=2000, required_margin=None)
    res = compute_acquisition(mv_block, [q], rules)
    # part-only must NOT be subtracted: 30000-1000-500-2000 = 26500
    assert res.recommended_max_price == 26500.0
    assert any("INCOMPLETE_REPAIR_COST" in w for w in res.warnings)
    assert res.explanation["repairs_part_only"][0]["part_price"] == 500.0


def test_full_repair_subtracted_normally():
    mv_block = {"value": 30000.0, "method": "TEST", "source": "x"}
    q = RepairQuote("screen_module", "EXACT_REPAIR_LOOKUP", 9900.0,
                    "dev", "samsung_tr_support", "2026-09-29",
                    price_type="FULL_REPAIR", includes_labor=True,
                    source_type="AUTHORIZED_SERVICE", quote_status="OK")
    rules = BusinessRules(operational_cost=1000, risk_buffer=500,
                          required_profit=2000, required_margin=None)
    res = compute_acquisition(mv_block, [q], rules)
    assert res.recommended_max_price == 16600.0  # regression math


# ---------- ranking: provenance -> price_type -> newest -> quality ----------

def _mk(quality="UNKNOWN", ptype="FULL_REPAIR", stype="PART_SUPPLIER",
        cost=100.0, obs="2026-01-01", model_key="X::m", name="m",
        device_id=None):
    return {"variant_id": None, "device_id": device_id, "model_name": name,
            "model_year": None, "series": None, "repair_type": "battery",
            "part_type": "b", "part_quality": None, "part_price": cost,
            "labor_cost": None, "total_repair_cost": cost,
            "repair_price_type": ptype, "includes_labor": ptype == "FULL_REPAIR",
            "repair_quality": quality, "source_quality_label": None,
            "brand": "X", "model_code": device_id, "model_key": model_key,
            "variant": None, "currency": "TRY", "country": "TR",
            "source_id": "s", "source_name": "s", "source_type": stype,
            "source_url": "u", "source_reference": "r",
            "observed_at": obs, "retrieved_at": obs, "is_synthetic": False,
            "notes": None}


def test_provenance_priority():
    df = pd.DataFrame([
        _mk(stype="PART_SUPPLIER", cost=50, ptype="PART_ONLY"),
        _mk(stype="AUTHORIZED_SERVICE", cost=900),
        _mk(stype="INDEPENDENT_REPAIR_SERVICE", cost=400),
        _mk(stype="OFFICIAL_MANUFACTURER", cost=1200)])
    kb = RepairKB(df)
    q = kb.quote("battery", model_name="m")
    assert q.total_cost == 1200 and q.source_type == "OFFICIAL_MANUFACTURER"


def test_full_repair_preferred_over_part_only_same_source():
    df = pd.DataFrame([
        _mk(ptype="PART_ONLY", cost=50),
        _mk(ptype="FULL_REPAIR", cost=400)])
    kb = RepairKB(df)
    q = kb.quote("battery", model_name="m")
    assert q.price_type == "FULL_REPAIR" and q.total_cost == 400


def test_newest_observation_tiebreak():
    df = pd.DataFrame([
        _mk(cost=300, obs="2026-01-01"),
        _mk(cost=450, obs="2026-09-01")])
    kb = RepairKB(df)
    q = kb.quote("battery", model_name="m")
    assert q.total_cost == 450


def test_unknown_quality_preserved_not_dropped():
    df = pd.DataFrame([_mk(quality="UNKNOWN", cost=700)])
    kb = RepairKB(df)
    q = kb.quote("battery", model_name="m")
    assert q.total_cost == 700 and q.repair_quality == "UNKNOWN"


def test_alternates_expose_quality_tiers():
    df = pd.DataFrame([
        _mk(quality="ORIGINAL", cost=900),
        _mk(quality="HIGH_QUALITY", cost=500),
        _mk(quality="COMPATIBLE", cost=300)])
    kb = RepairKB(df)
    q = kb.quote("battery", model_name="m")
    assert q.total_cost == 900  # genuine tier leads
    costs = sorted(a["total_cost"] for a in q.alternates)
    assert costs == [300.0, 500.0]


# ---------- no data ----------

def test_missing_cost_never_fabricated(kb):
    q = kb.quote("mainboard", model_name="iPhone 13")
    assert q.total_cost is None
    assert q.quote_status == "NO_REPAIR_DATA"


def test_series_level_fallback(kb):
    q = kb.quote("battery", series="S")
    assert q.lookup_method == "SERIES_LEVEL_LOOKUP"
    assert q.total_cost == 3150.0


# ---------- display / "frontend" contract ----------

def test_display_full_repair():
    q = RepairQuote("battery", "EXACT_REPAIR_LOOKUP", 4250.0, "d",
                    "telefon_profesoru", "2026-09-27", price_type="FULL_REPAIR",
                    includes_labor=True,
                    source_type="INDEPENDENT_REPAIR_SERVICE",
                    repair_quality="HIGH_QUALITY")
    d = display_repair(q)
    assert d["price"] == "4,250 TRY" and d["badge"] == "FULL_REPAIR"
    assert "Independent Repair Service" in d["status"]


def test_display_part_only_not_a_quote():
    q = RepairQuote("screen_module", "EXACT_REPAIR_LOOKUP", 3200.0, "d",
                    "ercorp", "2026-09-27", price_type="PART_ONLY",
                    includes_labor=False, source_type="PART_SUPPLIER")
    d = display_repair(q)
    assert d["badge"] == "PART ONLY"
    assert "Labor not included" in d["status"]
    assert d["price"] == "3,200 TRY"  # shown, but clearly part-only


def test_display_unavailable():
    q = RepairQuote("mainboard", "NO_REPAIR_DATA", None, None, None, None)
    d = display_repair(q)
    assert d["price"] is None and d["status"] == "Repair cost unavailable"


# ---------- canonical matching ----------

def test_match_report_exists_and_deterministic():
    df = pd.read_csv("data/repair/repair_catalogue_match_report.csv")
    assert {"repair_model", "canonical_device", "match_status",
            "match_method"} <= set(df.columns)
    matched = df[df.match_status.isin(["MATCHED_EXACT", "MATCHED_VIA_ALIAS",
                                       "MATCHED_PREFIX"])]
    assert len(matched) > 0
    # every matched row has a real canonical_device, no fabricated maps
    assert matched.canonical_device.notna().all()


# ---------- Samsung regression summary ----------

def test_samsung_regression_end_to_end(kb):
    """The known S23 case: selection must still land on samsung_tr 9900
    (AUTHORIZED beats INDEPENDENT/TP for the same device+repair)."""
    q = kb.quote("screen_module", model_code="SM-S911")
    assert q.source_type == "AUTHORIZED_SERVICE"
    assert q.total_cost == 9900.0
    assert q.price_type == "FULL_REPAIR"
    mv_block = {"value": 34124.50, "method": "TEST", "source": "x"}
    rules = BusinessRules(operational_cost=1500, risk_buffer=1000,
                          required_profit=None, required_margin=0.15)
    res = compute_acquisition(mv_block, [q], rules)
    assert res.recommended_max_price == pytest.approx(16605.83, abs=0.01)
