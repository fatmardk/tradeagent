"""Getmobil product-page collector.

Reads the PUBLIC sitemap_products.xml, fetches each phone product page
(robots.txt allows clean /satin-al/... paths; no /api/, no query filters),
and extracts the seller-level offers embedded in the page's React
Server Component payload (``self.__next_f.push``).

Each product page = one (model, storage, color, condition) product; its
``sellers`` array = one offer per merchant (vendorId, displayName, price,
stock, isBuyboxWinner). Every offer becomes one PRICE_OBSERVATION row.

Usage:
    python -m src.ingestion.collect_getmobil_products \
        --sitemap data/raw/tr_observations/gm_products.xml \
        --out data/raw/tr_observations/getmobil_product_offers_2026.csv \
        [--limit N] [--delay 0.3]
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

UA = ("Mozilla/5.0 (compatible; TradeAgentResearch/1.0; "
      "+price-observation-study)")

GRADE_MAP = {
    "Premium Plus": "S",
    "Mükemmel": "A",
    "Çok İyi": "B",
    "İyi": "C",
}

STORAGE_RE = re.compile(r"(\d+)\s*(GB|TB)", re.I)


def fetch(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def _decode_nextf(html: str) -> str:
    chunks = re.findall(
        r'self\.__next_f\.push\(\[1,\s*"(.*?)"\]\)', html, re.S)
    return "".join(chunks).encode().decode("unicode_escape", errors="ignore")


def _json_value_at(data: str, start: int):
    """Parse the JSON array/object starting at index `start` in data."""
    dec = json.JSONDecoder()
    # the payload is inside an escaped string already decoded; find the
    # first balanced bracket JSON from start
    return dec.raw_decode(data[start:])


def parse_product_page(html: str, url: str) -> dict:
    out = {"url": url, "title": None, "product_id": None, "sku": None,
           "condition_raw": None, "vendor": None, "page_price": None,
           "sellers": []}

    m = re.search(r"-(\d+)/?$", url)
    if m:
        out["product_id"] = int(m.group(1))

    ld = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    for b in ld:
        try:
            j = json.loads(b)
        except Exception:
            continue
        if isinstance(j, dict) and j.get("@type") == "ProductGroup":
            out["title"] = j.get("name")
            out["sku"] = j.get("sku")

    data = _decode_nextf(html)

    # page-level condition for this product ("condition":"Mükemmel")
    m = re.search(r'"condition"\s*:\s*"([^"]+)"', data)
    if m:
        out["condition_raw"] = m.group(1)
    # fix mojibake from double decoding
    if out["condition_raw"]:
        out["condition_raw"] = _fix_tr(out["condition_raw"])
    if out["title"]:
        out["title"] = _fix_tr(out["title"])

    # vendorInfo = the vendor whose listing this product page represents.
    # Its price is the isSelected option inside conditionGroup (the LD-JSON
    # offer is the buybox/cheapest offer, NOT this vendor's price).
    m = re.search(r'"vendorInfo"\s*:\s*(\{.*?\})', data)
    if m:
        seg = m.group(1)
        vid = re.search(r'"id"\s*:\s*(\d+)', seg)
        nm = re.search(r'"displayName"\s*:\s*"([^"]*)"', seg)
        sl = re.search(r'"slug"\s*:\s*"([^"]*)"', seg)
        if vid:
            out["vendor"] = {
                "vendorId": int(vid.group(1)),
                "displayName": _fix_tr(nm.group(1)) if nm else None,
                "vendorSlug": _fix_tr(sl.group(1)) if sl else None}
    # selected condition option -> page offer price
    i = data.find('"conditionGroup"')
    if i >= 0:
        seg = data[i:i + 6000]
        m = re.search(
            r'\{[^{}]*"isSelected"\s*:\s*true[^{}]*\}', seg)
        if m:
            sel = m.group(0)
            pm = re.search(r'"price"\s*:\s*([0-9.]+)', sel)
            if pm:
                out["page_price"] = float(pm.group(1))

    # sellers array = alternative marketplace offers for the same spec
    i = data.find('"sellers"')
    if i >= 0:
        j = data.find("[", i)
        if j >= 0:
            try:
                sellers, _ = _json_value_at(data, j)
                out["sellers"] = sellers
            except Exception:
                pass
    for s in out["sellers"]:
        for k in ("vendorTitle", "displayName", "vendorSlug"):
            if k in s and isinstance(s[k], str):
                s[k] = _fix_tr(s[k])
    return out


def _fix_tr(s: str) -> str:
    """Repair UTF-8-as-latin1 mojibake produced by unicode_escape decode."""
    try:
        return s.encode("latin-1").decode("utf-8")
    except Exception:
        return s


COLOR_SLUG_RE = re.compile(r"-\d+-(gb|tb)-(.+)-\d+/?$", re.I)


def parse_title(title: str, url: str = ""):
    """'Yenilenmiş Apple iPhone 11 Siyah 128 GB' -> (storage_gb, color).

    Color comes from the URL slug (last token before the product id) since
    the display title embeds the color inside the device name.
    """
    storage_gb = None
    color = None
    if title:
        m = STORAGE_RE.search(title)
        if m:
            storage_gb = int(m.group(1)) * (1024 if m.group(2).upper() == "TB"
                                            else 1)
    m = COLOR_SLUG_RE.search(url)
    if m:
        color = _fix_tr(m.group(2).replace("-", " ")).title()
    return storage_gb, color


def iter_product_urls(sitemap_path: Path):
    xml = Path(sitemap_path).read_text(encoding="utf-8")
    for u in re.findall(r"<loc>([^<]+)</loc>", xml):
        if "/cep-telefonu/" in u:
            yield u


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sitemap", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.3)
    ap.add_argument("--retrieved-at", default=None)
    args = ap.parse_args()

    urls = list(iter_product_urls(args.sitemap))
    if args.limit:
        urls = urls[: args.limit]
    print(f"{len(urls)} product pages to fetch", flush=True)

    retrieved_at = args.retrieved_at or time.strftime("%Y-%m-%d")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fields = ["product_url", "source_product_id", "sku", "title",
              "condition_raw", "storage_gb", "color", "offer_role",
              "seller_name", "source_seller_id", "seller_slug",
              "price", "stock", "is_buybox", "is_fast_delivery",
              "retrieved_at"]

    n_pages = n_rows = n_fail = 0
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        def emit(p, url, storage_gb, color, role, name, vid, slug,
                 price, stock="", buybox="", fast=""):
            nonlocal n_rows
            w.writerow({
                "product_url": url,
                "source_product_id": p["product_id"],
                "sku": p["sku"],
                "title": p["title"],
                "condition_raw": p["condition_raw"],
                "storage_gb": storage_gb,
                "color": color,
                "offer_role": role,
                "seller_name": name,
                "source_seller_id": vid,
                "seller_slug": slug,
                "price": price,
                "stock": stock,
                "is_buybox": buybox,
                "is_fast_delivery": fast,
                "retrieved_at": retrieved_at,
            })
            n_rows += 1

        for url in urls:
            n_pages += 1
            try:
                html = fetch(url)
                p = parse_product_page(html, url)
            except Exception as e:
                n_fail += 1
                print(f"FAIL {url} :: {e}", flush=True)
                continue
            storage_gb, color = parse_title(p["title"], url)
            seen = set()
            if p["vendor"] and p["page_price"]:
                emit(p, url, storage_gb, color, "listing_vendor",
                     p["vendor"]["displayName"], p["vendor"]["vendorId"],
                     p["vendor"]["vendorSlug"], p["page_price"])
                seen.add((p["vendor"]["vendorId"], p["page_price"]))
            for s in p["sellers"]:
                if not isinstance(s, dict) or s.get("price") in (None, ""):
                    continue
                key = (s.get("vendorId"), s.get("price"))
                if key in seen:
                    continue
                seen.add(key)
                emit(p, url, storage_gb, color, "marketplace_offer",
                     s.get("displayName") or s.get("vendorTitle"),
                     s.get("vendorId"), s.get("vendorSlug"), s.get("price"),
                     s.get("stock", ""), s.get("isBuyboxWinner", ""),
                     s.get("isFastDelivery", ""))
            if n_pages % 25 == 0:
                print(f"{n_pages}/{len(urls)} pages, {n_rows} offers, "
                      f"{n_fail} failures", flush=True)
            time.sleep(args.delay)

    print(f"DONE: {n_pages} pages, {n_rows} offer rows, {n_fail} failures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
