"""Append parsed Getmobil category-page listings to the raw observation CSV.

Reads a webfetch-rendered page text, extracts (grade, title, price) triples
via parse_getmobil_listings.parse, normalizes brand/model/storage/color,
and appends rows to price_observations_2026.csv with full provenance.

Usage:
    python -m src.ingestion.append_getmobil <page.txt> <category_url> <raw_ref>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

from src.ingestion.parse_getmobil_listings import parse

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "tr_observations" / "price_observations_2026.csv"

GRADE_MAP = {"Premium Plus": "S", "Mükemmel": "A", "Çok İyi": "B",
             "İyi": "C", "Premium": "A"}  # Premium tier mapping provisional; raw kept
BRAND_OF = {"Apple": "Apple", "Samsung": "Samsung", "Xiaomi": "Xiaomi",
            "Poco": "Poco", "Huawei": "Huawei", "Oppo": "Oppo",
            "Realme": "Realme", "Honor": "Honor"}
STORAGE_RE = re.compile(r"(\d+)\s*(GB|TB)\b", re.I)


def parse_title(title: str):
    """'Yenilenmiş Apple iPhone 14 Pro Max 256 GB Derin Mor' ->
    (brand, model, storage_gb, color)."""
    t = re.sub(r"^Yenilenmiş\s+", "", title).strip()
    brand = next((b for b in BRAND_OF if t.startswith(b)), None)
    rest = t[len(brand):].strip() if brand else t
    m = STORAGE_RE.search(rest)
    storage, color = None, None
    if m:
        storage = int(m.group(1)) * (1024 if m.group(2).upper() == "TB" else 1)
        model = rest[: m.start()].strip()
        color = rest[m.end():].strip() or None
    else:
        model = rest
    return brand, model, storage, color


def to_number(tr_price: str) -> float:
    return float(tr_price.replace(".", "").replace(",", "."))


def main(page_file: str, category_url: str, raw_ref: str) -> None:
    df = pd.read_csv(RAW, dtype=str, keep_default_na=False)
    n = int(df["obs_id"].str.extract(r"tr-(\d+)")[0].astype(int).max())
    rows = []
    for grade, title, price in parse(Path(page_file).read_text(encoding="utf-8")):
        if not price:
            continue  # FAQ headings etc.
        brand, model, storage, color = parse_title(title)
        n += 1
        rows.append({
            "obs_id": f"tr-{n:04d}", "source_id": "getmobil",
            "source_url": category_url, "raw_title": title,
            "brand": brand or "", "model": model,
            "storage_gb": storage or "", "color": color or "",
            "condition_raw": grade or "",
            "condition_grade": GRADE_MAP.get(grade or "", ""),
            "battery_health_pct": "", "price": to_number(price),
            "currency": "TRY", "country": "TR",
            "price_kind": "REFURBISHED_LIST",
            "observed_at": "2026-09-16", "retrieved_at": "2026-09-16",
            "raw_reference": raw_ref,
            "confidence_class": "AUTHORIZED_REFURBISHER",
            "seller_name": "", "source_seller_id": "",
            "product_url": "", "source_product_id": "",
            "is_from_price": "false", "notes": "",
        })
    out = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
    out.to_csv(RAW, index=False)
    print(f"appended {len(rows)} rows from {raw_ref} (total {len(out)})")


if __name__ == "__main__":
    main(*sys.argv[1:4])
