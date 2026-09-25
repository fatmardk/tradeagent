"""Append non-Mükemmel category-card observations for a snapshot.

Replicates the Snapshot-2/3 category flow: parse each saved
webfetch-rendered category page, keep rows whose grade is not Mükemmel
(the sitemap/product-page path covers Mükemmel with seller attribution),
and append them to the merged raw CSV.

Usage:
    python -m src.ingestion.append_getmobil_cat \
        --pages-dir data/raw/tr_observations/gm_cat_pages_s3 \
        --raw data/raw/tr_observations/price_observations_2026_s3.csv \
        --snap s3 --observed-at 2026-09-25
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from src.ingestion.parse_getmobil_listings import parse
from src.ingestion.merge_getmobil_offers import split_title

GRADE_MAP = {"Premium Plus": "S", "Mükemmel": "A", "Çok İyi": "B",
             "İyi": "C", "Premium": "A"}
STORAGE_RE = re.compile(r"(\d+)\s*(GB|TB)\b", re.I)
BRAND_DIR = {"iphone": "iphone-ios-telefonlar/apple",
             "galaxy": "android-telefonlar/samsung",
             "xiaomi": "android-telefonlar/xiaomi",
             "redmi": "android-telefonlar/xiaomi"}


def storage_of(title: str) -> str:
    m = STORAGE_RE.search(title)
    if not m:
        return ""
    gb = int(m.group(1)) * (1024 if m.group(2).upper() == "TB" else 1)
    return str(gb)


def page_url(slug: str) -> str:
    family = slug.split("-")[0]
    sub = BRAND_DIR[family]
    name = slug[len("xiaomi-"):] if slug.startswith("xiaomi-") else slug
    return f"https://getmobil.com/satin-al/cep-telefonu/{sub}/{name}/"


def to_number(tr_price: str) -> float:
    return float(tr_price.replace(".", "").replace(",", "."))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages-dir", required=True)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--snap", required=True)
    ap.add_argument("--observed-at", required=True)
    args = ap.parse_args()

    df = pd.read_csv(args.raw, dtype=str, keep_default_na=False)
    n = int(df["obs_id"].str.extract(r"-(\d+)$")[0].astype(float).max())
    rows = []
    for f in sorted(Path(args.pages_dir).glob("*.txt")):
        slug = f.stem
        url = page_url(slug)
        for grade, title, price in parse(f.read_text(encoding="utf-8")):
            if not price or not grade or grade == "Mükemmel":
                continue
            brand, model, color_title = split_title(title, 0)
            n += 1
            rows.append({
                "obs_id": f"tr-{args.snap}-{n:04d}",
                "source_id": "getmobil", "source_url": url,
                "raw_title": title, "brand": brand or "",
                "model": model, "storage_gb": storage_of(title),
                "color": color_title, "condition_raw": grade,
                "condition_grade": GRADE_MAP.get(grade, ""),
                "battery_health_pct": "", "price": to_number(price),
                "currency": "TRY", "country": "TR",
                "price_kind": "REFURBISHED_LIST",
                "observed_at": args.observed_at,
                "retrieved_at": args.observed_at,
                "raw_reference": f"gm-cat-{args.snap}-{slug}",
                "confidence_class": "AUTHORIZED_REFURBISHER",
                "seller_name": "", "source_seller_id": "",
                "product_url": "", "source_product_id": "",
                "is_from_price": "false",
                "notes": "category_card;no_seller_attribution",
            })
    out = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
    out.to_csv(args.raw, index=False)
    print(f"appended {len(rows)} non-A category rows; total {len(out)}")


if __name__ == "__main__":
    main()
