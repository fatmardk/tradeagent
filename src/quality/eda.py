"""Focused economic EDA — every table answers a real question.

Appends an EDA section to docs/phase1a-data-quality-report.md.
Questions:
  Q1 ratio vs days_used (ReCell)          — depreciation shape
  Q2 ratio vs release_year (ReCell)       — vintage effect
  Q3 does storage matter? (ReCell)
  Q4 brand effects (ReCell)
  Q5 resale ratio by condition (mizan)    — condition effect
  Q6 battery vs ratio (mizan)             — battery effect
  Q7 confounding check (mizan)            — is condition independent of age?
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs" / "phase1a-data-quality-report.md"


def _decile_ratio(df: pd.DataFrame, col: str, ratio: str, q: int = 8) -> pd.DataFrame:
    d = df.copy()
    d["bin"] = pd.qcut(d[col], q, duplicates="drop")
    return d.groupby("bin", observed=True)[ratio].agg(["count", "mean", "std"]).round(4)


def run() -> None:
    recell = pd.read_parquet(ROOT / "data" / "interim" / "recell.parquet")
    mizan = pd.read_parquet(ROOT / "data" / "interim" / "mizan121.parquet")

    lines = [
        "",
        "## Focused EDA (economic questions)",
        "",
        "**Q1 — used/new ratio by days_used (ReCell, octiles):**",
        "",
        _decile_ratio(recell, "days_used", "used_to_new_ratio").to_markdown(),
        "",
        "**Q2 — used/new ratio by release_year (ReCell):**",
        "",
        recell.groupby("release_year")["used_to_new_ratio"].agg(["count", "mean"]).round(4).to_markdown(),
        "",
        "**Q3 — does storage matter? ratio by storage tier (ReCell):**",
        "",
        recell.assign(storage_tier=pd.cut(recell["storage_gb"], [0, 16, 64, 128, 256, 2048]))
              .groupby("storage_tier", observed=True)["used_to_new_ratio"].agg(["count", "mean"]).round(4).to_markdown(),
        "",
        "**Q4 — brand effect: top-10 brands by mean ratio (ReCell, n≥30):**",
        "",
        recell.groupby("brand")["used_to_new_ratio"].agg(["count", "mean"])
              .query("count >= 30").sort_values("mean", ascending=False).head(10).round(4).to_markdown(),
        "",
        "**Q5 — resale/original ratio by condition (mizan121):**",
        "",
        mizan.groupby("condition_grade")["resale_to_original_ratio"].agg(["count", "mean", "std"]).round(4).to_markdown(),
        "",
        "**Q6 — ratio by battery-health decile (mizan121):**",
        "",
        _decile_ratio(mizan, "battery_health", "resale_to_original_ratio").to_markdown(),
        "",
        "**Q7 — confounding: condition×age crosstab of mean ratio (mizan121).**",
        "If condition effects were real, the gradient should survive within age bands:",
        "",
        mizan.pivot_table(index="condition_grade", columns="age_years",
                          values="resale_to_original_ratio", aggfunc="mean").round(4).to_markdown(),
        "",
        "> Reading note: in mizan121 battery_health ⊥ age_years (corr≈0) and",
        "> condition means are flat across age — the condition gradient above is a",
        "> generation formula's direct effect, not evidence about real markets.",
        "",
    ]
    with open(REPORT, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    run()
