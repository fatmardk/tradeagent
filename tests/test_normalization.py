from src.normalization.device_names import (
    normalize_brand, normalize_name, parse_storage_gb, split_model_storage,
)


def test_normalize_brand_known():
    assert normalize_brand("apple") == "Apple"
    assert normalize_brand("  SAMSUNG ") == "Samsung"
    assert normalize_brand("redmi") == "Xiaomi"


def test_normalize_brand_unknown_titlecases():
    assert normalize_brand("somebrand") == "Somebrand"
    assert normalize_brand("") is None
    assert normalize_brand(None) is None


def test_parse_storage():
    assert parse_storage_gb("iPhone 13 128GB") == 128
    assert parse_storage_gb("Galaxy S23 256 gb") == 256
    assert parse_storage_gb("Device 1TB") == 1024
    assert parse_storage_gb("iPhone 13") is None


def test_normalize_name_canonical_key():
    assert normalize_name("  APPLE   iPhone-13  128GB ") == "apple iphone13 128gb"
    assert normalize_name("iPhone 13") == "iphone13"


def test_split_model_storage():
    model, storage = split_model_storage("Samsung Galaxy S23 Ultra 256GB")
    assert storage == 256
    assert "galaxy" in model
    assert split_model_storage(None) == (None, None)
