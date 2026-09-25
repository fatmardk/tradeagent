"""Dataset manifest: record provenance + file hash so runs are reproducible.

Manifests live in data/manifests/ and ARE committed to git; the raw files they
describe are not.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_DIR = Path(__file__).resolve().parents[2] / "data" / "manifests"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_manifest(
    *,
    dataset_name: str,
    raw_path: Path,
    source_url: str,
    license: str,
    record_count: int,
    notes: str = "",
    dataset_version: str = "",
) -> Path:
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "dataset_name": dataset_name,
        "dataset_version": dataset_version,
        "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_url": source_url,
        "license": license,
        "record_count": record_count,
        "file_hash_sha256": sha256_file(raw_path),
        "original_filename": raw_path.name,
        "file_size_bytes": raw_path.stat().st_size,
        "notes": notes,
    }
    out = MANIFEST_DIR / f"{dataset_name}.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
