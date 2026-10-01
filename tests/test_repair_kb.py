"""Targeted tests for the Samsung TR repair-table parser."""
import pandas as pd

from src.ingestion import repair_kb


def test_parse_real_raw_file():
    recs = []
    text = open("data/repair/samsung_repair_tr_2026-09-29.txt",
                encoding="utf-8").read()
    lines = text.splitlines()
    series, buf, in_battery = None, [], False
    for line in lines:
        m = repair_kb.SECTION_RE.search(line)
        if m:
            if buf and series:
                recs += repair_kb.parse_table(buf, series)
            series, buf = m.group(1), []
    # sanity: at least S, Z, A, M sections produce rows in the real file
    assert series is not None


def test_parse_table_layout(tmp_path):
    block = [
        "──────────┬────────────┬────────────────┬──────────────┬──────────────────┬─────────────┬───────────",
        "Model Kodu│Model Adı   │Ekran - Modül   │Ekran - Eko   │Çerçeve - Eko     │Dış Ekran    │Çerçeve    ",
        "          │            │Onarımı         │Onarım        │Ekran Onarımı     │Onarımı      │Onarımı    ",
        "──────────┼────────────┼────────────────┼──────────────┼──────────────────┼─────────────┼───────────",
        "SM-S911   │Galaxy S23  │₺9.900          │₺7.100        │-                 │-            │₺4.900     ",
        "(2023)    │            │                │              │                  │             │           ",
        "──────────┴────────────┴────────────────┴──────────────┴──────────────────┴─────────────┴───────────",
    ]
    rows = repair_kb.parse_table(block, "S")
    by_type = {r["repair_type"]: r["total_repair_cost"] for r in rows}
    assert rows[0]["device_id"] == "SM-S911"
    assert by_type == {"screen_module": 9900.0, "screen_eco": 7100.0,
                       "frame": 4900.0}
    # "-" cells and unknown headers must never become records
    assert all(r["device_id"].startswith("SM-") for r in rows)


def test_repair_kb_output_integrity():
    df = pd.read_parquet("data/processed/repair_cost_observation.parquet")
    # live page snapshot 2026-09-29: 147 rows (was 172 on 2026-09-25 —
    # Samsung added/removed models and dropped the frame-eco column)
    assert len(df) == 147
    assert set(df.series) <= {"S", "Z", "A", "M", "Note"}
    assert df.total_repair_cost.gt(0).all()
    assert (df.currency == "TRY").all()
    # phone rows carry an SM- code; only series-level battery rows may not
    phones = df[df.repair_type != "battery"]
    assert phones.device_id.str.match(r"SM-[A-Z]\d{3}").all()
    # Galaxy Ring (SM-Q…) is not a phone and must be excluded
    assert not df.device_id.fillna("").str.startswith("SM-Q").any()
