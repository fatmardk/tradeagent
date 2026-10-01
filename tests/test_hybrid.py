"""Tests for the hybrid valuation engine, repair lookup and acquisition."""
import datetime as dt

import pandas as pd
import pytest

from src.acquisition.engine import BusinessRules, compute_acquisition, \
    full_valuation
from src.market.cold_start import FallbackEstimator
from src.market.engine import HybridValuer, ValuationConfig
from src.market.valuation import MarketEstimator
from src.repair.lookup import RepairKB

MARKET = "data/processed/market_snapshot_combined.parquet"
KB = "data/processed/repair_cost_observation.parquet"


@pytest.fixture(scope="module")
def market_df():
    return pd.read_parquet(MARKET)


@pytest.fixture(scope="module")
def valuer(market_df):
    return HybridValuer(market_df, ValuationConfig(max_obs_age_days=45))


@pytest.fixture(scope="module")
def kb():
    return RepairKB.load(KB)


# ---------- market estimator routing ----------

def test_market_median_routing(valuer):
    r = valuer.valuate("Samsung", "Galaxy S23", 256,
                       canonical_variant="samsung|galaxy-s23|256")
    assert r["method"] == "RECENT_MARKET_MEDIAN"
    assert r["source"] == "REAL_MARKET_OBSERVATION"
    assert r["value"] > 0 and r["offer_count"] >= 2
    assert r["market_p25"] <= r["value"] <= r["market_p75"]


def test_low_coverage_flag(valuer, market_df):
    # a variant whose LATEST observation is single-offer/single-seller
    latest = (market_df.sort_values("observed_date")
              .groupby(["canonical_variant", "grade_segment"]).last())
    latest = latest[latest.index.get_level_values(1) == "A"]
    single = latest[(latest.n_offers == 1) | (latest.n_sellers < 2)]
    if len(single):
        v = single.index[0][0]
        r = valuer.valuate("x", "y", 0, canonical_variant=v)
        assert r["method"] == "MARKET_MEDIAN_LOW_COVERAGE"


def test_cold_start_routing(valuer):
    r = valuer.valuate("NonexistentBrand", "No Such Model", 512)
    assert r["method"].startswith("COLD_START")
    assert r["source"] == "FALLBACK_ESTIMATE"
    assert r["value"] is not None


def test_stale_observation_routing(market_df):
    v = HybridValuer(market_df, ValuationConfig(max_obs_age_days=5))
    # as_of far beyond snapshot dates -> stale -> cold start
    r = v.valuate("Samsung", "Galaxy S23", 256,
                  canonical_variant="samsung|galaxy-s23|256",
                  as_of=dt.date(2026, 12, 31))
    assert r["method"].startswith("COLD_START")


def test_fallback_hierarchy(market_df):
    fb = FallbackEstimator(market_df)
    # seen model, any storage -> model median
    e = fb.estimate("Samsung", "Galaxy S23", 128)
    assert e.valuation_method == "COLD_START_MODEL_MEDIAN"
    # unseen model, seen brand+storage
    e = fb.estimate("Samsung", "Galaxy ZZZ Fictional", 256)
    assert e.valuation_method in ("COLD_START_BRAND_STORAGE",
                                  "COLD_START_BRAND")
    # unseen brand entirely
    e = fb.estimate("FictionalBrand", "Model X", 64)
    assert e.valuation_method == "COLD_START_GLOBAL"


# ---------- repair lookup ----------

def test_repair_exact_lookup(kb):
    q = kb.quote("screen_module", model_code="SM-S911")
    assert q.lookup_method == "EXACT_REPAIR_LOOKUP"
    assert q.total_cost == 9900.0
    assert q.source_id == "samsung_tr_support"


def test_repair_series_lookup(kb):
    q = kb.quote("battery", series="S")
    assert q.lookup_method == "SERIES_LEVEL_LOOKUP"
    # battery series price moved 3.100 -> 3.150 on the 2026-09-29 page
    assert q.total_cost == 3150.0


def test_repair_no_data_never_fabricates(kb):
    q = kb.quote("screen_module", model_name="iPhone 13")
    assert q.lookup_method == "NO_REPAIR_DATA"
    assert q.total_cost is None


def test_repair_model_name_resolves(kb):
    q = kb.quote("screen_module", model_name="Galaxy S23")
    assert q.lookup_method == "EXACT_REPAIR_LOOKUP"
    assert q.device_id == "SM-S911"


# ---------- acquisition formula ----------

def test_acquisition_formula(valuer, kb):
    mv = {"value": 30000.0, "method": "RECENT_MARKET_MEDIAN",
          "source": "REAL_MARKET_OBSERVATION", "offer_count": 5}
    q = kb.quote("screen_module", model_code="SM-S911")
    rules = BusinessRules(operational_cost=1000, risk_buffer=500,
                          required_profit=2000)
    r = compute_acquisition(mv, [q], rules)
    # 30000 - 9900 - 1000 - 500 - 2000
    assert r.recommended_max_price == 16600.0
    assert r.explanation["profit_target"] == "BUSINESS_INPUT"
    assert r.explanation["market_value_origin"] == "REAL_MARKET_OBSERVATION"


def test_acquisition_margin_mode():
    mv = {"value": 20000.0, "method": "COLD_START_BRAND",
          "source": "FALLBACK_ESTIMATE"}
    rules = BusinessRules(required_margin=0.10)
    r = compute_acquisition(mv, [], rules)
    assert r.recommended_max_price == 18000.0
    assert r.explanation["market_value_origin"] == "MODEL_ESTIMATE"


def test_acquisition_missing_repair_warns(valuer, kb):
    mv = {"value": 30000.0, "method": "RECENT_MARKET_MEDIAN",
          "source": "REAL_MARKET_OBSERVATION", "offer_count": 5}
    q = kb.quote("screen_module", model_name="iPhone 13")  # no data
    r = compute_acquisition(mv, [q], BusinessRules())
    assert any("NO_REPAIR_DATA" in w for w in r.warnings)
    assert r.explanation["repairs_without_data"] == ["screen_module"]


def test_no_market_value_no_price():
    r = compute_acquisition({"value": None}, [], BusinessRules())
    assert r.recommended_max_price is None


# ---------- provenance / no cross-path leakage ----------

def test_every_prediction_states_its_method(valuer):
    for variant, method_prefix in [
            ("samsung|galaxy-s23|256", "RECENT_MARKET"),
            ("nonexistent|thing|64", "COLD_START")]:
        r = valuer.valuate("b", "m", 0, canonical_variant=variant)
        assert r["method"].startswith(method_prefix)
        assert r["source"] in ("REAL_MARKET_OBSERVATION",
                               "FALLBACK_ESTIMATE")
