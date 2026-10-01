"""Match multi-brand repair observations to the canonical device catalogue.

Deterministic only — no fuzzy merges. A repair model row attaches to a
canonical device when its slugified (brand, model) equals the slug of a
canonical_model in the market snapshot (after MODEL_ALIASES normalization).

Outputs:
    repair_catalogue_match_report.csv
        repair_model, brand, canonical_device, match_status, match_method

match_status:
    MATCHED_EXACT          — model_key slug == canonical model slug
    MATCHED_VIA_ALIAS      — matched after MODEL_ALIASES canonicalization
    MATCHED_VIA_PREFIX     — repair model is a prefix of the canonical name
                             (e.g. repair "Galaxy A34" -> "Galaxy A34 5G")
    UNMATCHED              — kept as repair-only record; reported, never
                             silently merged into a wrong device
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.normalization.variant import canonical_model as canon_alias
from src.normalization.device_names import normalize_name

ROOT = Path(__file__).resolve().parents[2]
REPAIR = ROOT / "data/processed/repair_cost_observation_multibrand.parquet"
CATALOGUE = ROOT / "data/processed/market_snapshot_combined.parquet"
REPORT = ROOT / "data/repair/repair_catalogue_match_report.csv"


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s).strip().lower()).strip("-")


def canonical_devices(catalogue_path: Path = CATALOGUE) -> pd.DataFrame:
    """Distinct canonical (brand, model) pairs from the market catalogue."""
    df = pd.read_parquet(catalogue_path)
    dev = (df[["canonical_brand", "canonical_model"]]
           .dropna().drop_duplicates().reset_index(drop=True))
    dev["slug"] = dev.canonical_model.map(slug)
    dev["brand_key"] = dev.canonical_brand.str.strip().str.lower()
    return dev


def match_repair_models(repair_path: Path = REPAIR,
                        catalogue_path: Path = CATALOGUE) -> pd.DataFrame:
    rep = pd.read_parquet(repair_path)
    dev = canonical_devices(catalogue_path)

    rows = (rep[["brand", "model_name", "model_key"]]
            .dropna(subset=["model_name"]).drop_duplicates())

    dev_by_key = {}
    for _, d in dev.iterrows():
        dev_by_key.setdefault((d.brand_key, d.slug), []).append(d.canonical_model)

    out = []
    for _, r in rows.iterrows():
        brand = str(r.brand).strip().lower()
        raw_model = str(r.model_name).strip()
        canon = canon_alias(brand, raw_model) or raw_model
        mk_slug = (str(r.model_key).split("::")[-1]
                   if r.model_key and str(r.model_key) != "nan"
                   else slug(raw_model))
        variants = {mk_slug, slug(canon)}

        # brand-prefixed repair names ("Realme C55" vs catalogue "C 55")
        # drop a leading brand token — deterministic, documented
        toks = raw_model.split()
        if toks and toks[0].strip().lower() == brand and len(toks) > 1:
            variants.add(slug(" ".join(toks[1:])))

        hit, method = None, None
        for v in variants:
            if (brand, v) in dev_by_key:
                hit, method = dev_by_key[(brand, v)][0], "CANONICAL_MODEL_SLUG"
                if v != slug(raw_model):
                    method = "CANONICAL_MODEL_SLUG_VIA_ALIAS"
                break
        if hit is None:
            # fused slug: "C25S" == "C 25S" (spacing differences only)
            fused_dev = {d.slug.replace("-", ""): d.canonical_model
                         for _, d in dev[dev.brand_key == brand].iterrows()}
            for v in variants:
                f = v.replace("-", "")
                if f in fused_dev:
                    hit, method = fused_dev[f], "CANONICAL_MODEL_SLUG_FUSED"
                    break
        if hit is None:
            # prefix: repair model shorter than catalogue model on same brand
            brand_devs = dev[dev.brand_key == brand]
            for _, d in brand_devs.iterrows():
                if d.slug.startswith(mk_slug + "-") or \
                        any(d.slug.startswith(v + "-") for v in variants):
                    hit = d.canonical_model
                    method = "CANONICAL_MODEL_PREFIX"
                    break
        status = {
            None: "UNMATCHED",
            "CANONICAL_MODEL_SLUG": "MATCHED_EXACT",
            "CANONICAL_MODEL_SLUG_VIA_ALIAS": "MATCHED_VIA_ALIAS",
            "CANONICAL_MODEL_SLUG_FUSED": "MATCHED_VIA_FUSED",
            "CANONICAL_MODEL_PREFIX": "MATCHED_PREFIX",
        }[method]
        out.append({
            "repair_model": raw_model,
            "brand": r.brand,
            "model_key": r.model_key,
            "canonical_device": hit,
            "match_status": status,
            "match_method": method or "NONE",
        })
    rep_df = pd.DataFrame(out)
    return rep_df


COVERAGE = ROOT / "data/repair/catalogue_repair_coverage.csv"


def coverage_report(repair_path: Path = REPAIR,
                    catalogue_path: Path = CATALOGUE,
                    match_report_path: Path = REPORT) -> pd.DataFrame:
    """Repair coverage of every canonical device in the market catalogue."""
    rep = pd.read_parquet(repair_path)
    snap = pd.read_parquet(catalogue_path)
    mr = pd.read_csv(match_report_path)
    matched = mr[mr.match_status.str.startswith("MATCHED")]
    key2dev = dict(zip(matched.model_key, matched.canonical_device))
    slug2dev = {(r.brand.strip().lower(),
                 str(r.model_key).split("::")[-1]): r.canonical_device
                for _, r in matched.iterrows()}
    fused = {(k[0], k[1].replace("-", "")): v for k, v in slug2dev.items()}

    def canon_of(r):
        b, mk = str(r.brand).strip().lower(), str(r.model_key)
        s = mk.split("::")[-1]
        return (key2dev.get(mk) or slug2dev.get((b, s))
                or fused.get((b, s.replace("-", ""))))

    rep = rep.copy()
    rep["canon"] = rep.apply(canon_of, axis=1)
    devs = (snap[["canonical_brand", "canonical_model", "canonical_variant"]]
            .drop_duplicates())
    rows = []
    for (b, m), g in devs.groupby(["canonical_brand", "canonical_model"]):
        obs = rep[rep.canon == m]
        fr = obs[obs.repair_price_type == "FULL_REPAIR"].repair_type.nunique()
        po = obs[obs.repair_price_type == "PART_ONLY"].repair_type.nunique()
        rows.append({
            "canonical_brand": b, "canonical_model": m,
            "canonical_variants": len(g),
            "has_full_repair": fr > 0, "full_repair_types": fr,
            "part_only_only": fr == 0 and po > 0,
            "no_repair_data": len(obs) == 0})
    cov = pd.DataFrame(rows)
    cov.to_csv(COVERAGE, index=False)
    return cov


def main() -> None:
    rep_df = match_repair_models()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    rep_df.to_csv(REPORT, index=False)
    print(rep_df.match_status.value_counts().to_string())
    unmatched = rep_df[rep_df.match_status == "UNMATCHED"]
    print(f"\nunmatched ({len(unmatched)}), top 20:")
    print(unmatched.groupby(["brand", "repair_model"]).size()
          .sort_values(ascending=False).head(20).to_string())
    print(f"-> {REPORT}")
    cov = coverage_report()
    for b, g in cov.groupby("canonical_brand"):
        print(f"{b:15s} models={len(g):3d} full={g.has_full_repair.sum():3d} "
              f"part={g.part_only_only.sum():2d} none={g.no_repair_data.sum():3d} "
              f"FULL%={100 * g.has_full_repair.mean():.0f}% "
              f"ANY%={100 * (~g.no_repair_data).mean():.0f}%")
    print(f"-> {COVERAGE}")


if __name__ == "__main__":
    main()
