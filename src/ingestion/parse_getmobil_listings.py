"""Parse a webfetch-rendered Getmobil category page into observation rows.

The fetched page text repeats each listing as:

    <Grade>                       <- own line: Premium Plus|Premium|Mükemmel|Çok İyi|İyi
    [<title>]                     <- link text
    [Hızlı teslimat]              <- optional badge
    Getmobil Güvencesi
    ### <title>
    12 x 2.558,25 TL              <- installment line
    30.699 TL                     <- cash price

Usage: python -m src.ingestion.parse_getmobil_listings <fetched_page.txt>
Emits TSV rows: grade, title, price  (for manual review before CSV append).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

GRADES = {"Premium Plus", "Premium", "Mükemmel", "Çok İyi", "İyi"}
PRICE_RE = re.compile(r"^([\d.]+(?:,\d+)?) TL$")
TITLE_RE = re.compile(r"^###\s+(Yenilenmiş .+)$")


def parse(text: str):
    lines = [ln.strip() for ln in text.splitlines()]
    rows = []
    for i, ln in enumerate(lines):
        m = TITLE_RE.match(ln)
        if not m:
            continue
        title = m.group(1).strip()
        # grade: nearest preceding standalone grade line within 6 lines
        grade = next(
            (lines[j] for j in range(i - 1, max(i - 8, -1), -1)
             if lines[j] in GRADES), None)
        # price: first standalone "X TL" line within next 8 lines
        price = next(
            (PRICE_RE.match(lines[j]).group(1)
             for j in range(i + 1, min(i + 9, len(lines)))
             if PRICE_RE.match(lines[j])), None)
        rows.append((grade, title, price))
    return rows


if __name__ == "__main__":
    text = Path(sys.argv[1]).read_text(encoding="utf-8")
    for grade, title, price in parse(text):
        print(f"{grade or ''}\t{title}\t{price or ''}")
