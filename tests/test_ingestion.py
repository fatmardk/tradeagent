import pandas as pd
import pytest

from src.ingestion import mizan121, recell


def test_recell_raw_schema():
    df = recell.load_raw()
    assert recell.EXPECTED_COLUMNS <= set(df.columns)
    assert len(df) > 3000


def test_recell_ratio_semantics():
    df = recell.transform(recell.load_raw())
    assert df["used_to_new_ratio"].between(0, 1.5).all()
    assert (df["price_kind"] == "ACADEMIC_NORMALIZED").all()
    # normalized prices must never be read as currency
    assert "price_kind" in df.columns


def test_mizan_raw_schema():
    df = mizan121.load_raw()
    assert mizan121.EXPECTED_COLUMNS <= set(df.columns)


def test_mizan_condition_mapping_complete():
    df = mizan121.transform(mizan121.load_raw())
    assert df["condition_grade"].notna().all()
    assert set(df["condition_grade"].unique()) <= {"A", "B", "C", "D"}
    assert (df["currency"] == "INR").all()


def test_missing_stays_missing():
    """No-fabrication rule: unobserved individual-device fields remain NULL."""
    df = recell.transform(recell.load_raw())
    assert "battery_health_pct" not in df.columns  # never invented
