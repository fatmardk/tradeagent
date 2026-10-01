# Multi-Brand Repair KB — Entegrasyon Raporu

Tarih: 2026-09-29 · Repo: fatmardk/tradeagent · Commit/push yapılmadı.

**DURUM:** `feature/backend-api` üzerine `devin/multibrand-repair` branch'inde üç katman da entegre ve yeşil. Market baseline'e dokunulmadı (`market_snapshot.json` aynen, `merge_getmobil_offers` revert, `price_observations` git-ignored). Commit/push/merge yapılmadı.

**UYARI — `backend/pom.xml` repoda yoktu:** branch push'lanırken pom düşmüş (git geçmişinde hiç pom/gradle yok). Orijinal stack'e göre **Spring Boot 3.3.5 + Java 17** + web/validation/test starter olarak yeniden yazdım — framework upgrade yok; kendi pom'un varsa geri koy. `backend/target/`, `frontend/dist/`, `frontend/node_modules/` artık tracked değil + `.gitignore`'da.

## 1. Entegre edilen dosyalar

`data/repair/` (repoya yeni, git'e eklenecek):
- `repair_sources.csv` — kaynak registry (provenance sınıfı + ToS notu)
- `real_repair_observations.csv` — 1.705 gerçek gözlem (TP 1.578 + ErCorp 127)
- `kb.json` — current/history/stats (current=1.699)
- `coverage_report.csv` — toolkit kapsama raporu
- `repair_catalogue_match_report.csv` — canonical katalog eşleşme raporu (yeni)
- `catalogue_repair_coverage.csv` — katalog-bazlı kapsama (yeni)

Yeni/üretilen (git-ignored `data/processed/`): `repair_cost_observation_multibrand.parquet` (1.852 satır = 147 Samsung + 1.705 çok markalı), `price_observation.parquet`, `offer_level{_combined}`, `market_snapshot{_combined}`.

Yeni kod: `src/ingestion/repair_kb_multibrand.py`, `src/matching/repair_match.py`, `tests/test_multibrand_repair.py`.
Değişen: `src/repair/lookup.py` (yeniden yazıldı), `src/acquisition/engine.py` (PART_ONLY), `src/ingestion/merge_getmobil_offers.py` (boş base CSV fix), `src/ingestion/repair_kb.py` (yeni raw dosya yolu), `tests/test_hybrid.py` + `tests/test_repair_kb.py` (data-refresh sabitleri).

## 2. Domain / schema değişiklikleri

Multibrand parquet kolon süperseti mevcut `repair_cost_observation` şemasını genişletiyor: `brand, model_code, model_key (BRAND::slug), variant, repair_price_type (FULL_REPAIR|PART_ONLY), includes_labor, repair_quality (ORIGINAL/SERVICE/PREMIUM/HIGH_QUALITY/COMPATIBLE/REFURBISHED/PULLED/UNKNOWN), source_quality_label (ham etiket korunur), source_type (4 provenance), source_name, source_reference, observed_at`. Samsung satırları `FULL_REPAIR + includes_labor=True + SERVICE + AUTHORIZED_SERVICE` olarak tasnif edildi — tek "repair price"e indirgenmedi.

## 3. Matching stratejisi

`src/matching/repair_match.py` — tamamen deterministik, fuzzy merge yok:
1. `CANONICAL_MODEL_SLUG` — model_key slug == canonical_model slug
2. `..._VIA_ALIAS` — MODEL_ALIASES sonrası
3. `..._SLUG_FUSED` — sadece boşluk farkı ("C 25S" ≡ "C25S")
4. `CANONICAL_MODEL_PREFIX` — repair modeli katalog adının prefix'i ("Galaxy A34" → "Galaxy A34 5G")
5. `UNMATCHED` — asla tahminle eşleştirilmez; raporlanır.

Sonuç: 493 repair model → 133 EXACT + 13 ALIAS + 13 FUSED + 27 PREFIX = **186 eşleşme, 307 unmatched**.

## 4. RepairService / lookup değişiklikleri

**Python** `src/repair/lookup.py` sıfırdan: `RepairKB.load()` multibrand parquet okuyor (eski parquet hâlâ okunur). Seçim: `source_type (OFFICIAL→AUTHORIZED→INDEPENDENT→PART_SUPPLIER)` → `FULL_REPAIR→PART_ONLY` → `observed_at desc` → `repair_quality (ORIGINAL→…→UNKNOWN)`. Lookup: EXACT (model_key → device_id → model_name) → SERIES → NO_REPAIR_DATA. `RepairQuote` yeni alanlar: `price_type, includes_labor, source_type, repair_quality, model_key, source_reference, quote_status, alternates`.

**Java** `RepairService` aynı kuralların birebir replikası (aynı rank haritaları + comparator) — iki dilde farklı kural yok. `RepairObservation`/`RepairQuote` record'ları yeni alanlarla genişledi, `RepairController` `modelKey` paramı + coverage meta. `data/export/repair_kb.json` artık multibrand parquet'ten export (1.852 satır). `AcquisitionService` PART_ONLY'yi düşmez → `INCOMPLETE_REPAIR_COST` + `repair_quote_status` + `repairs_part_only`; `repair.source_type` artık gerçek provenance (OFFICIAL_REPAIR_DATA yerine).

## 5. Frontend değişiklikleri (React)

`RepairSelector.jsx`: chip artık fiyat + kalite etiketi (Original/High Quality/Compatible…) + kaynak tipi (Independent Repair Service vb.) + `FULL_REPAIR`/`PART ONLY` rozet gösteriyor; PART ONLY'de "Labor not included", veri yoksa "Repair cost unavailable" (seçilemez). "Samsung TR only" metni kalktı. `ResultPanel.jsx`: quote başına rozet + kalite + provenance, PART ONLY uyarı satırı, `source_types` listesi. `styles.css`: `price-badge`, `repair-chip-meta` sınıfları. Frontend hesap yapmıyor — her şey API'den.

## 6. FULL_REPAIR / PART_ONLY davranışı

`compute_acquisition`: FULL_REPAIR normal düşülür. PART_ONLY düşülmez — `quoteStatus=INCOMPLETE_REPAIR_COST` + warning + `explanation.repairs_part_only` listesi (part_price + source_id). NO_REPAIR_DATA → mevcut MISSING_REPAIR_COST davranışı aynen. Eksik işçilik asla sıfır sayılmaz.

## 7. Katalog kapsaması (getmobil canonical katalog, 265 model)

| Brand | Model | FULL_REPAIR | Sadece PART_ONLY | Veri yok | FULL % | ANY % |
|---|---|---|---|---|---|---|
| Apple | 37 | 34 | 0 | 3 | 92% | 92% |
| Samsung | 86 | 75 | 0 | 11 | 87% | 87% |
| Xiaomi | 40 | 33 | 0 | 7 | 82% | 82% |
| Realme | 15 | 12 | 0 | 3 | 80% | 80% |
| Oppo | 15 | 10 | 0 | 5 | 67% | 67% |
| Diğer (Huawei/Honor/Tecno/Vivo/Poco/GM/…) | 72 | 0 | 0 | 72 | 0% | 0% |
| **Toplam** | **265** | **164** | **0** | **101** | **62%** | **62%** |

## 8. Samsung regresyon sonucu

SM-S911 (Galaxy S23 256GB) SCREEN_MODULE — eski: `samsung_tr_support` 9.900 TRY; yeni: **aynı** (AUTHORIZED_SERVICE, TP'nin INDEPENDENT katmanlarına alternates olarak üstün geliyor). Seçim değişmedi → formül sonucu korunuyor: 34.124,50 − 9.900 − 1.500 − 1.000 − 15% ⇒ **16.605,83 TRY** (testte `pytest.approx` ile kilitli).

## 9. Apple/Xiaomi canlı örnekler

- iPhone 13 battery → 6.250 TRY ORIGINAL (TP FULL_REPAIR; alternates: Premium 4.550, Yüksek Kalite 2.500, ErCorp parça 591,48)
- iPhone 13 Pro Max screen → 18.400 ORIGINAL (alt: HK 7.000, REFURB 9.900, PULLED 11.100, parça 2.918,97)
- Galaxy S23 battery → 3.500 ORIGINAL (alt: Premium 2.500, Standart 1.850, parça 464,73)
- Realme C55 battery → 1.650 COMPATIBLE; iPhone XS earpiece → 50,95 PART_ONLY → INCOMPLETE_REPAIR_COST
- Redmi Note 13 Pro screen → NO_REPAIR_DATA (KB'de yok — uydurulmadı)

## 10. Testler — üç katman

- **Python: 50/50 PASS** (14 hybrid + 17 ingestion/lookup/matching + 19 yeni multibrand)
- **Java: 27/27 PASS** (19 ApiIntegrationTest — 3 yeni multibrand endpoint testi dahil — + 8 yeni RepairServiceSelectionTest birim testi)
- **Frontend build: PASS** (`vite build` — 37 modül, test script'i yok)

Java test notları: `repairSeriesLookup` 3.100→3.150 (Samsung canlı sayfa değeri değişmişti — repair-data refresh); `acquisitionUnknownRepairWarnsNotInvents` battery→frame'e taşındı çünkü iPhone 16e battery artık gerçek PART_ONLY verisi — aynı test artık PART_ONLY'nin düşülmediğini de doğruluyor.

## 10b. Diff review — değişiklik grupları

**A. Repair dataset/toolkit:** `data/repair/` (6 dosya + Samsung raw audit kopyası), `src/ingestion/repair_kb_multibrand.py`, `data/export/repair_kb.json` (yeniden export).
**B. Python entegrasyonu:** `src/repair/lookup.py`, `src/acquisition/engine.py`, `src/ingestion/repair_kb.py` (raw path), `src/ingestion/export_backend.py` (kolonlar+kaynak), `src/matching/repair_match.py`, `tests/test_multibrand_repair.py`, `tests/test_hybrid.py` + `tests/test_repair_kb.py` (repair-data sabitleri).
**C. Spring Boot:** `domain/RepairObservation.java`, `domain/RepairQuote.java`, `service/RepairService.java`, `service/AcquisitionService.java`, `controller/RepairController.java`, `test/ApiIntegrationTest.java`, `test/RepairServiceSelectionTest.java` (yeni), **`backend/pom.xml` (YENİ — repoda yoktu; 3.3.5 olarak yeniden yazıldı)**.
**D. React:** `frontend/src/components/{RepairSelector,ResultPanel}.jsx`, `frontend/src/styles.css`.
**E. Gitignore/build temizliği:** `.gitignore` + `git rm --cached` ile `backend/target/`, `frontend/dist/`, `frontend/node_modules/` untracked (46 yol); `package.json`/`package-lock.json` korundu.

**Repair ile ilgisiz değişen dosya: YOK.** `data/export/market_snapshot.json`, `src/market`, `src/normalization`, `data/raw|processed` — hepsi dokunulmadı.

## 11. Kalan eşleşmeyen modeller (top 20)

iPhone 6–8 ailesi (katalogda yok), iPhone 16E/18 serisi (katalogda yok), Realme C-serisi eski (C3/C11/C15/C21/C25… katalogda yok), Oppo A15/A54 4G/A58, Xiaomi Mi 9 SE, Redmi Note 10S 4G / Note 12 Pro varyantları. Tam liste: `data/repair/repair_catalogue_match_report.csv` (UNMATCHED=307).

## 12. Önerilen sonraki adım

Katalogdaki 72 "diğer marka" (Huawei/Honor/Tecno/Vivo/Poco/General Mobile) tamir verisi sıfır — sonraki toplama batch'i bu markalar + TP'nin kalan işlem sayfaları (ön kamera/hoparlör/kasa) olmalı. Sonra frontend katmanı gelince `display_repair` + `alternates` doğrudan kullanılır.

## Bilinen sınırlar

- `price_observations_2026.csv` bu makinede **sadece Getmobil** satırlarıyla üretildi (el-girisi base CSV bende yok). Kendi tam base'iniz varsa `merge_getmobil_offers` → `tr_observations` → `build_analytical` → `combine_snapshots` zincirini aynen çalıştırın; kapsama raporu zenginleşir.
- Samsung canlı sayfa değerleri eski snapshot'tan farklılaşmıştı (pil serisi 3.150, 147 satır) — test sabitleri data-refresh olarak güncellendi.
