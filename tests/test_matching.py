from src.matching.alias import classify_match

CANONICAL = {"apple iphone13": "dev_iphone13", "samsung galaxys23": "dev_s23"}


def test_exact_match_approved():
    r = classify_match("Apple iPhone 13", CANONICAL)
    assert r["device_id"] == "dev_iphone13"
    assert r["review_status"] == "APPROVED"
    assert r["match_method"] == "EXACT_CANONICAL_NAME"


def test_rule_based_with_storage():
    r = classify_match("apple iphone 13 128gb", CANONICAL)
    assert r["device_id"] == "dev_iphone13"
    assert r["match_method"] == "RULE_BASED"


def test_unmatched_never_fabricated():
    r = classify_match("Xperia ZZ 9000", CANONICAL)
    assert r["device_id"] is None
    assert r["review_status"] == "NEEDS_REVIEW"


def test_empty_input():
    r = classify_match("", CANONICAL)
    assert r["device_id"] is None
    assert r["review_status"] == "NEEDS_REVIEW"
