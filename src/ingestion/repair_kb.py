"""Parse Samsung TR official repair-fee page into repair_cost_observation rows.

Source: https://www.samsung.com/tr/support/ekran-degisimi-fiyat-bilgisi/
Saved raw page text: data/raw/tr_observations/samsung_repair_tr_YYYY-MM-DD.txt

The page publishes box-drawing tables per device family (S, Z, A, M) with
section-specific column layouts, plus a series-level battery table and a
Galaxy Ring table (excluded — not a phone). Cells wrap across two lines;
fragments are merged per column position, never inferred.

Usage: python -m src.ingestion.repair_kb [--raw PATH] [--out PATH]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/tr_observations/samsung_repair_tr_2026-09-25.txt"
OUT = ROOT / "data/processed/repair_cost_observation.parquet"
CSV = ROOT / "data/raw/tr_observations/repair_cost_observation_2026.csv"
SOURCE_URL = "https://www.samsung.com/tr/support/ekran-degisimi-fiyat-bilgisi/"

SECTION_RE = re.compile(r"\[\s*Galaxy (\w+) Serisi\s*\]")
SEP_RE = re.compile(r"^─+[┬┼┴]")
PRICE_RE = re.compile(r"^₺?([\d.]+)$")
CODE_RE = re.compile(r"(SM-[A-Z]\d{3})")
YEAR_RE = re.compile(r"\((\d{4})\)")

REPAIR_TYPE = {
    "Ekran - Modül Onarımı": "screen_module",
    "Ekran - Eko Onarım": "screen_eco",
    "Ekran - Eko-Onarım": "screen_eco",
    "Çerçeve - Eko Ekran Onarımı": "frame_eco_screen",
    "Dış Ekran Onarımı": "outer_screen",
    "Çerçeve Onarımı": "frame",
}


def parse_price(cell: str):
    m = PRICE_RE.match(cell.strip())
    return float(m.group(1).replace(".", "")) if m else None


def parse_table(block: list[str], series: str) -> list[dict]:
    """Parse one box-drawing table block (list of lines)."""
    rows, cur = [], []
    for line in block:
        if SEP_RE.match(line.strip()):
            if cur:
                rows.append(cur)
                cur = []
        elif "│" in line:
            cur.append([c.strip() for c in line.split("│")])
    if cur:
        rows.append(cur)
    if not rows:
        return []

    ncols = max(len(c) for r in rows for c in r)
    # merge multi-line cells per column
    merged = []
    for r in rows:
        cells = [""] * ncols
        for line_cells in r:
            for i, frag in enumerate(line_cells):
                if frag:
                    cells[i] = (cells[i] + " " + frag).strip()
        merged.append(cells)

    header = merged[0]
    out = []
    for cells in merged[1:]:
        code = CODE_RE.search(cells[0])
        if not code:
            continue
        year = YEAR_RE.search(cells[0])
        for i in range(2, ncols):
            price = parse_price(cells[i])
            if price is None:
                continue
            rtype = REPAIR_TYPE.get(header[i])
            if rtype is None:
                continue
            out.append({
                "variant_id": None,
                "device_id": code.group(1),
                "model_name": cells[1],
                "model_year": int(year.group(1)) if year else None,
                "series": series,
                "repair_type": rtype,
                "part_type": None,
                "part_quality": "ORIGINAL_SERVICE",
                "part_price": None,
                "labor_cost": None,
                "total_repair_cost": price,
                "currency": "TRY",
                "country": "TR",
            })
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(RAW))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    text = Path(args.raw).read_text(encoding="utf-8")
    lines = text.splitlines()

    # split into sections by family heading; a table runs until the next
    # heading or a non-table block
    records = []
    series, buf = None, []
    in_battery = False
    for line in lines:
        m = SECTION_RE.search(line)
        if m:
            if buf and series:
                records += parse_table(buf, series)
            series, buf = m.group(1), []
            in_battery = False
            continue
        if "Tüm Galaxy Serileri" in line:
            if buf and series:
                records += parse_table(buf, series)
            in_battery, series, buf = True, None, []
            continue
        if "Galaxy Ring" in line:
            if buf and series:
                records += parse_table(buf, series)
            series, buf = None, []  # not a phone — exclude
            continue
        if in_battery and "│" in line:
            cells = [c.strip() for c in line.split("│") if c.strip()]
            if len(cells) == 2:
                price = parse_price(cells[1])
                sm = re.search(r"Galaxy (\w+) Serisi", cells[0])
                if price is not None and sm:
                    records.append({
                        "variant_id": None, "device_id": None,
                        "model_name": cells[0], "model_year": None,
                        "series": sm.group(1), "repair_type": "battery",
                        "part_type": None, "part_quality": "ORIGINAL_SERVICE",
                        "part_price": None, "labor_cost": None,
                        "total_repair_cost": price,
                        "currency": "TRY", "country": "TR"})
            continue
        if series and ("│" in line or SEP_RE.match(line.strip())):
            buf.append(line)
    if buf and series:
        records += parse_table(buf, series)

    df = pd.DataFrame(records)
    df.insert(0, "repair_cost_observation_id",
              [f"rep-samsungtr-{i:04d}" for i in range(1, len(df) + 1)])
    df["source_id"] = "samsung_tr_support"
    df["source_url"] = SOURCE_URL
    df["observed_at"] = "2026-09-25"
    df["retrieved_at"] = "2026-09-25"
    df["is_synthetic"] = 0
    df["notes"] = "part+labor included; battery included in S/Z screen_module,frame_eco_screen,frame"

    df.to_csv(CSV, index=False)
    df.to_parquet(args.out, index=False)
    print(f"{len(df)} repair rows -> {args.out}")
    print(df.groupby("series").size())
    print(df.repair_type.value_counts())


if __name__ == "__main__":
    main()
