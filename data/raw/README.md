# data/raw — immutable source files

Files here are the **original, unmodified** downloads. Nothing in `src/` may
write to this directory. Cleaning output goes to `data/interim/`; canonical
tables to `data/processed/`.

This directory is git-ignored (see `.gitignore`). Provenance is tracked in
`data/manifests/*.json` (committed) — each manifest records source URL,
license, record count and SHA-256 of the file used.

| Directory | File | Source | Status |
|---|---|---|---|
| `recell/` | `used_phone_data.csv` | Kaggle `ahsan81/used-handheld-device-data` (CC0), fetched via GitHub mirror `JesusTorres98/ReCell` | downloaded |
| `mizan121/` | `used_phone.csv` | Kaggle `mizan121/used-phone-dataset` (anonymous Kaggle API endpoint) | downloaded — provenance unverified, see quality report |
