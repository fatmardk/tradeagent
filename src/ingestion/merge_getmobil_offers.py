"""Rebuild the raw observation CSV with seller-level Getmobil offers.

The product-page collector (collect_getmobil_products.py) yields one row
per (product, seller-offer) with seller identity, product URL and product
ID — a strict superset of the earlier category-card (gm-cat-*) rows, which
captured only the card/buybox price without seller attribution.

This script:
  * keeps every non-getmobil row (apple_tr_store, easycep) untouched
  * keeps gm-cat-* category-card rows whose grade is NOT Mükemmel (A):
    Getmobil's sitemap indexes only Mükemmel product pages, so B/C/S/D
    card observations are listings absent from gm-prod-* — keeping them
    preserves multi-grade coverage (seller/product-id unrecoverable on
    category cards; documented limitation)
  * drops gm-cat-* A-grade rows (same Mükemmel listings as gm-prod-*,
    but without seller attribution)
  * appends gm-prod-* rows, one per seller offer observed on a product page

Usage:
    python -m src.ingestion.merge_getmobil_offers \
        [--raw BASE_CSV] [--offers OFFERS_CSV] [--out OUT_CSV]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "tr_observations" / "price_observations_2026.csv"
OFFERS = ROOT / "data" / "raw" / "tr_observations" / "getmobil_product_offers_2026.csv"

GRADE_MAP = {"Premium Plus": "S", "Mükemmel": "A", "Çok İyi": "B",
             "İyi": "C", "Premium": "A"}

STORAGE_RE = re.compile(r"(\d+)\s*(GB|TB)\b", re.I)

# multi-word brands first, then single tokens
BRANDS = ["General Mobile", "Apple", "Samsung", "Xiaomi", "Redmi", "Poco",
          "Huawei", "Honor", "Oppo", "Realme", "Vivo", "Tecno", "Infinix",
          "OnePlus", "Nokia", "Reeder", "Casper", "Omix", "Vestel",
          "TCL", "Lenovo", "Alcatel", "ZTE", "Meizu", "Sony"]


def split_title(title: str, color_slug_tokens: int):
    """Handle BOTH Getmobil title layouts:
      'Yenilenmiş Apple iPhone 11 Beyaz 128 GB'      (color before storage)
      'Yenilenmiş Apple iPhone 16 128 GB Laciverttaş' (color after storage)
    -> (brand, model, color_title_fragment)."""
    t = re.sub(r"(?i)^yenilenmi[sş]\s+", "", str(title)).strip()
    brand = next((b for b in BRANDS if t.lower().startswith(b.lower())), None)
    rest = t[len(brand):].strip() if brand else t
    m = STORAGE_RE.search(rest)
    if not m:
        return brand, rest, ""
    before = rest[: m.start()].strip()
    after = rest[m.end():].strip()
    if after:
        # color sits after the storage spec
        return brand, before, after
    # color sits before storage: drop the last N tokens (N from URL slug)
    toks = before.split()
    if color_slug_tokens and len(toks) > color_slug_tokens:
        return brand, " ".join(toks[:-color_slug_tokens]), \
            " ".join(toks[-color_slug_tokens:])
    return brand, before, ""


def color_tokens_from_url(url: str) -> int:
    m = re.search(r"-\d+-(gb|tb)-(.+)-\d+/?$", str(url), re.I)
    if not m:
        return 0
    return len(m.group(2).split("-"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(RAW),
                    help="base CSV to keep non-getmobil rows from")
    ap.add_argument("--offers", default=str(OFFERS))
    ap.add_argument("--out", default=str(RAW),
                    help="defaults to --raw (in-place, Snapshot 1 behaviour)")
    args = ap.parse_args()
    df = pd.read_csv(args.raw, dtype=str, keep_default_na=False)
    offers = pd.read_csv(args.offers, dtype=str, keep_default_na=False)

    keep = df[(df["source_id"] != "getmobil")
              | (df["condition_raw"] != "Mükemmel")].copy()
    n = int(df["obs_id"].str.extract(r"-(\d+)$")[0].astype(float).max())
    snap = re.search(r"_s(\d+)", args.raw)
    prefix = f"tr-s{snap.group(1)}-" if snap else "tr-"

    rows = []
    for _, o in offers.iterrows():
        try:
            price = float(o["price"])
        except ValueError:
            continue
        if price <= 0:
            continue
        ct = color_tokens_from_url(o["product_url"])
        brand, model, color_title = split_title(o["title"], ct)
        color = o["color"] or color_title
        n += 1
        notes = []
        if o.get("offer_role"):
            notes.append(o["offer_role"])
        if o.get("stock"):
            notes.append(f"stock:{o['stock']}")
        if str(o.get("is_buybox")).lower() == "true":
            notes.append("buybox_winner")
        if str(o.get("is_fast_delivery")).lower() == "true":
            notes.append("fast_delivery")
        rows.append({
            "obs_id": f"{prefix}{n:04d}", "source_id": "getmobil",
            "source_url": o["product_url"],
            "raw_title": o["title"],
            "brand": brand or "", "model": model,
            "storage_gb": o["storage_gb"], "color": color,
            "condition_raw": o["condition_raw"],
            "condition_grade": GRADE_MAP.get(o["condition_raw"], ""),
            "battery_health_pct": "", "price": price,
            "currency": "TRY", "country": "TR",
            "price_kind": "REFURBISHED_LIST",
            "observed_at": o["retrieved_at"],
            "retrieved_at": o["retrieved_at"],
            "raw_reference": f"gm-prod-{o['source_product_id']}",
            "confidence_class": "AUTHORIZED_REFURBISHER",
            "seller_name": o["seller_name"],
            "source_seller_id": o["source_seller_id"],
            "product_url": o["product_url"],
            "source_product_id": o["source_product_id"],
            "is_from_price": "false",
            "notes": ";".join(notes),
        })

    out = pd.concat([keep, pd.DataFrame(rows)], ignore_index=True)
    out.to_csv(args.out, index=False)
    print(f"kept {len(keep)} non-getmobil rows; "
          f"replaced gm-cat rows with {len(rows)} gm-prod offer rows; "
          f"total {len(out)}")


if __name__ == "__main__":
    main()
