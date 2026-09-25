# Türkiye 2026 PRICE_OBSERVATION — Toplama Planı

Amaç: `price_observation` tablosunu **gerçek, yasal, provenance'lı** Türkiye
gözlemleriyle doldurmak. Yöntem: public sayfaların düşük hacimli manuel/yardımlı
okunması — scraping altyapısı YOK, otomasyon ancak yazılı izin sonrası.

## Yasal çerçeve

| İlke | Uygulama |
|---|---|
| Sadece public, auth'suz sayfalar | Ürün/kategori sayfaları, resmi fiyat listeleri |
| Toplu otomatik scraping yok | Kayıtlar insan-incelemeli, gözlem başına `raw_reference` tutulur |
| ToS gri alan yok | Sahibinden/Letgo/3. taraf scraper API'leri hariç |
| Her satır provenance taşır | source_id + observed_at + retrieved_at + confidence_class |

## Kaynak → alan haritası

| Kaynak | price_kind | Alınabilir alanlar | confidence_class | Not |
|---|---|---|---|---|
| **getmobil.com** ürün/kategori sayfaları | REFURBISHED_LIST | model, storage, renk, **derece** (Mükemmel/Çok İyi/İyi), ₺ fiyat, garanti(12ay) | AUTHORIZED_REFURBISHER | Anasayfa+kategori sayfaları gerçek fiyat veriyor; ürün detayında IMEI/sertifika bilgisi de var |
| **easycep.com** kategori sayfaları | REFURBISHED_LIST | model, "başlayan fiyat", derece (ürün sayfasında) | AUTHORIZED_REFURBISHER | Kategori sayfası model-bazlı taban fiyat verir |
| **cihazsat.senatech.com** | BUYBACK_OFFER | model×durum cevapları → teklif | BUYBACK_OFFER | Form akışı; tek tek sorgu |
| **Getmobil "Cihaz Sat"** akışı | BUYBACK_OFFER | model, storage, pil/durum cevapları → ön teklif | BUYBACK_OFFER | Grid örnekleme: aynı modelde tek değişken değiştir |
| **apple.com/tr** mağaza | MSRP/NEW_LIST | model başlangıç fiyatı (KDV dahil) | OFFICIAL_MANUFACTURER | Sadece güncel seri (16/17/17e/Air/18) satıyor |
| **samsung.com/tr** mağaza | NEW_LIST | model fiyatı | OFFICIAL_MANUFACTURER | JS-ağır; sayfa okunabilirse kaydet |
| **Amazon Depo (amazon.com.tr)** | USED_LIST | model, 4 derece (Yeni Gibi/Çok İyi/İyi/Kabul Edilebilir), ₺ | MARKETPLACE_LISTING | Ürün bazlı; arama sayfasından gözlem |
| Turkcell Pasaj / Vatan / MediaMarkt public sayfalar | NEW_LIST | eski modellerin güncel sıfır fiyatı | MARKETPLACE_LISTING | Apple'dan çıkmış modellerin new-price anchor'ı |

## İlk 30 hedef varyant (TR refurbished pazarında likit modeller)

| # | Varyant | Neden |
|---|---|---|
| 1–6 | iPhone 11 64/128, 12 64/128, 13 128/256 | En yüksek ikinci-el hacim; her iki satıcıda da var |
| 7–12 | iPhone 14 128/256, 14 Pro 256, 14 Pro Max 128/256, 15 128 | Getmobil/EasyCep'te aktif liste |
| 13–16 | iPhone 15 Pro 256, 15 Pro Max 256, 16 128/256 | Üst segment kapsama |
| 17–22 | Galaxy S21 128, S22 128/256, S23 128/256, S23 Ultra 256 | Samsung refurbished ana hacim |
| 23–26 | Galaxy A54/A55 128/256 | TR'nin en çok satan orta segmenti |
| 27–30 | Redmi Note 12/13 128/256, Poco X6 256 | Xiaomi hacmi |

Kayıt formatı: `data/raw/tr_observations/price_observations_2026.csv`
(manuel tutulan kaynak-of-truth; immutable mantık — her gözlem yeni satır).

## Gözlem disiplini

- `observed_at` = fiyatın kaynakta geçerli olduğu tarih; `retrieved_at` = bizim okuduğumuz an.
- "X'den başlayan fiyatlar" → grade=NULL + `notes=from_price` (koşul bilinmiyorsa derece uydurulmaz).
- Pil sağlığı/defekt gibi cihaz-bazlı alanlar satıcı vermedikçe NULL kalır.
- Aynı cihazın farklı derece/renk listeleri ayrı gözlemdir (real market varyansı).

## İlk Seed Durumu (2026-09-16)

- **39 gerçek gözlem** toplandı → `data/processed/price_observation.parquet` (loader: `src/ingestion/tr_observations.py`, tüm validasyonlar geçti).
- Dağılım: getmobil `REFURBISHED_LIST` ×28, easycep `REFURBISHED_LIST` ×6, apple_tr_store `MSRP` ×5.
- Kapsanan varyantlar (model+depolama): iPhone 11/64, iPhone 12/128, iPhone 13/128, iPhone 14 Pro/256, iPhone 14 Pro Max/128+256, iPhone 15/128, Galaxy S23/256; aile düzeyi EasyCep gözlemleri iPhone 11–14 Pro Max.
- Gerçek sinyal örneği: Galaxy S23/256 aynı sayfada derece varyansı gözlendi — İyi ₺35.000, Çok İyi ₺28.499–28.500, Mükemmel ₺29.949–33.649, Premium Plus ₺35.199–35.999. Fiyatların dereceyle tek düze sıralı OLMAMASI (satıcı varyansı) verinin gerçek olduğunun işareti.
- Yeni derece keşfi: Getmobil'in "Premium Plus" katmanı → kanonik `condition_grade='S'` olarak eklendi.
- Sınırlar: batarya sağlığı hiçbir kaynakta yok (beklendiği gibi NULL); EasyCep gözlemleri varyant-düzeyi değil aile/starting-price düzeyi; A54/A55, Redmi, Poco varyantları henüz toplanmadı — bir sonraki tur.
- Tekrar gözlem takvimi önerisi: aynı URL seti haftada bir yeniden çekilip yeni `observed_at` ile eklenmeli → zaman serisi ve fiyat-değişimi ölçümü.

## Geniş Kesit Genişletmesi (2026-09-17)

Seed'in yetersizliği üzerine haftalık seriye geçmeden önce güncel-tarihli
kesitsel kapsam genişletildi.

### Toplama yöntemi — Getmobil ürün sayfaları (satıcı-bazlı)

Kategori-kart yaklaşımı (gm-cat-*) yerine **ürün sayfası** yaklaşımına geçildi:

- `sitemap.xml` → `sitemap_products.xml` içindeki tüm telefon ürün URL'leri
  (853 sayfa) tek tek, sıralı ve ~0.3 sn arayla okundu.
- Yasal dayanak: robots.txt temiz `/satin-al/...` yollarını disallow etmiyor
  (yasaklı: `/api/`, `/satin-al-v1`, `/satin-al/aksesuar`, filtreli query
  parametreleri); URL listesi sitenin kendi yayınladığı sitemap'ten alındı;
  `/api/` ve filtre URL'lerine dokunulmadı.
- Her ürün sayfası = (model, depolama, renk, **derece**) kombinasyonu;
  React Server Component payload'ındaki `vendorInfo` (ilan sahibi satıcı)
  + `sellers[]` (alternatif pazar teklifleri) + `conditionGroup`
  (isSelected → derece + sayfa fiyatı) çıkarıldı.
- Çıktı: `data/raw/tr_observations/getmobil_product_offers_2026.csv` —
  teklif başına satır: seller_name, source_seller_id (vendorId), seller_slug,
  product_url, source_product_id, condition_raw, price, stock, is_buybox.
- `merge_getmobil_offers.py` ile ana CSV yeniden kuruldu: gm-cat-* satırları
  aynı ilanların daha fakir görünümü olduğundan gm-prod-* satırlarıyla
  değiştirildi (aynı gözlem, satıcı kimliği ve ürün kimliği korunarak).
- Kollektör: `src/ingestion/collect_getmobil_products.py`.

### Şema genişletmesi

`price_observation` ham CSV'sine eklendi: `seller_name`,
`source_seller_id`, `product_url`, `source_product_id`, `is_from_price`.
Offers ara dosyasında ayrıca `seller_slug`, `stock`, `is_buybox`,
`is_fast_delivery`, `offer_role` (listing_vendor / marketplace_offer)
tutulur; ana CSV'de bunlar `notes`'a yazılır.

Kurallar:

- `is_from_price=true` → model/aile başlangıç fiyatı; depolama VE derece
  aynı anda dolu olamaz (loader bunu reddeder).
- Aynı (model, depolama, renk, derece) için farklı satıcı teklifleri ayrı
  gözlemdir — derece-fiyat ilişkisi ancak satıcı kontrolüyle yorumlanır.

### Apple TR varyant MSRP

`apple.com/tr/shop/buy-iphone/<model>` sayfaları depolama-bazlı fiyat
veriyor → her (model, depolama) ayrı `MSRP` + `is_from_price=false` satırı.
Model başlangıç satırları (is_from_price=true) korundu.

### Geniş kesit sonucu (2026-09-17, işlenmiş parquet'ten ölçüldü)

- **2.252 gözlem** | 16 marka | 270 model | **392 model+depolama varyantı**
  (hedef ~50–100 → aşıldı)
- Kaynak: getmobil REFURBISHED_LIST ×2.221, apple_tr_store MSRP ×25
  (5 model-başlangıç + 20 varyant), easycep REFURBISHED_LIST ×6
- Derece: A 2.138, B 40, C 31, S 11, yok 32 — ağırlık Mükemmel'de
  (sitemap yalnız Mükemmel ürün sayfalarını indeksliyor; diğer dereceler
  kategori-kart gözlemlerinden, satıcı kimliği olmadan)
- **290 tekil satıcı** (vendorId), 2.135 satır satıcı-etiketli;
  2.135 satır product_url + source_product_id'li
- Tam duplike 0; near-dup (model+dep+derece+fiyat) 713 — çoğu aynı speçin
  farklı satıcı teklifleri (ayrıştırıcı gözlem), az kısmı aynı satıcının
  farklı ürün-id'li paralel ilanları
- 160 modelde çoklu satıcı, 24 modelde çoklu derece gözlendi
- Kalan boşluklar: batarya sağlığı/defekt hiçbir yerde yok; EasyCep hâlâ
  aile-bazlı başlangıç fiyatı; ikinci bir satıcı-etiketli kaynak yok
  (tek-kaynak bağımlılığı); non-A derecelerde satıcı atıfı yok;
  'Galaxy S22 ULTRA 5G' gibi yazım varyantları device_alias katmanına
  bırakıldı (ham veri korundu)

## 2026-03 güncelleme — V0/V1 kararı ve analitik katman

**Karar: V0_BASELINE = GO, V1_MARKET_VALUE = GO** (sınırlı kapsam: grade-A segmenti, kesitsel).

### Kanonikleştirme denetimi sonucu
- Aile-bazlı kayıt kalmadı: `iPhone`, `Galaxy Z`, `Redmi`, `Reno` gibi jenerik adlar sıfır satır (parser düzeltmesi sonrası).
- Tek yazım varyantı: `Galaxy S22 ULTRA 5G` → alias tablosuyla birleştirildi (`Galaxy S22 Ultra 5G`).
- Sayım mutabakatı: 268→270 model / 391→392 varyant farkı parser düzeltmesinden; kanonikleştirme sonrası 392→388 canonical varyant (case/alias birleşmeleri).
- Bare-numeric modeller (`Xiaomi 13`, `Realme 10`) gerçek — family-level değil.

### Analitik katman
- `offer_level.parquet`: 2.252 satır, teklif bazlı, provenance korunuyor.
- `market_snapshot.parquet`: 439 satır, grain = (date, canonical_variant, grade_segment). V1 target = `price_median`.
- Grade A segmenti: 371 varyant, 262 model, 16 marka. 146 varyant tek teklifli (gürültülü median) — ileride min-offer eşiği değerlendirilebilir.

### Baseline sonuçları (docs/v1-baseline-report.md)
Leakage-safe: GroupKFold by canonical_model (görülmemiş model, strict) + random KFold (interpolasyon). Naive fallback train-fit-only.
- HistGBR MAE ₺9.7–10.2k / MAPE ~32–34% vs global-median ₺18.3k / 65%.
- `model_median` baseline `brand_median`'a eşit → GroupKFold'da test modelleri hiç görülmemiş; doğru davranış.

### Sınırlar (dürüstlük)
- Kesitsel model — zaman genellemesi iddiası yok. Snapshot 2 gelince out-of-time test.
- Koşul etkisi öğrenilmedi (A:%96); B/C/S ayrı segment olarak saklı, V3'e kadar.
- `battery_health_pct` %100 eksik — uydurma değer yok.
- `n_offers`/`n_sellers` V1 feature'ı değil (piyasa derinliği kovaryatı; cihaz özelliği değil).
- Periyodik snapshot toplama paralelde başlayabilir; Snapshot 1 immutable.

## 2026-09-25 güncelleme — Snapshot 2 ve out-of-time doğrulama

### Snapshot 2 (immutable, S1 ile aynı metodoloji)
- Aynı pipeline: sitemap → ürün sayfası → satıcı teklifleri (vendorInfo + sellers[] + conditionGroup); 839 sitemap URL'si (S1'de 853 — 14 ürün delist), 0 hata, 2.095 teklif.
- Non-A kategori gözlemleri de aynı 24 sayfadan aynı parser'la tekrar toplandı: 101 non-A satır (S1: 86).
- Çıktılar ayrı dosyalarda: `price_observations_2026_s2.csv`, `getmobil_product_offers_2026_s2.csv`, `gm_products_s2.xml`, `*_s2.parquet`. S1 dosyaları değişmedi (2.252 obs / 2.135 teklif, tarihler 09-16/17 korunuyor).
- S2: 2.227 obs | 443 market satırı | 383 canonical varyant | grade A 366, B 30, C 13, S 14, UNKNOWN 20.

### Out-of-time sonuç (docs/v1-oot-report-s1-s2.md)
- Shared 325 / new 41 / disappeared 44 varyant (grade A).
- Drift: median %0, %78 varyant ±%5 içinde; geniş yeniden-fiyatlama yok.
- **Persistence kazandı**: S1 variant-median MAPE %4.3, last-price %6.5 — V1 %31.6. V1'in rolü kapsama boşlukları (yeni/görülmemiş varyantlar: MAPE %57 vs brand-median %96).
- Teknik not: tam-S1 fit'i marka-başına HistGBR (262 model > 255 kategori limiti); feature/target değişmedi.

### REPAIR_KB (Samsung TR resmi onarım listesi)
- Kaynak: samsung.com/tr/support/ekran-degisimi-fiyat-bilgisi — ham sayfa `data/raw/tr_observations/samsung_repair_tr_2026-09-25.txt` olarak korunuyor.
- Parser: `src/ingestion/repair_kb.py` (section-aware: S/Z/A/M farklı sütun düzenleri; Galaxy Ring telefon olmadığı için dışarıda).
- Çıktı: `repair_cost_observation.parquet` — **172 satır**, 89 model (S 61, A 55, Z 43, M 12) + 5 seri-bazlı batarya ücreti (S/Note ₺3.100, Z ₺3.750, A/M ₺2.950).
- repair_type'lar: screen_module 72, screen_eco 42, frame 22, frame_eco_screen 17, outer_screen 14, battery 5. Not: S/Z serisinde screen_module/frame onarımlarına batarya dahil (kaynak dipnotu).
- Apple TR tamir ücreti public tablo olarak yok → REPAIR_KB şimdilik Samsung-only; bu kısıt bilinerek kullanılmalı.

## 2026-09-26 güncelleme — Hybrid Market Valuation Engine v1

- Mimari: market-first routing (`src/market/engine.py`) — RECENT_MARKET_MEDIAN / MARKET_MEDIAN_LOW_COVERAGE / COLD_START_*. Her tahmin `method` + `source` (REAL_MARKET_OBSERVATION / FALLBACK_ESTIMATE) taşıyor.
- Cold-start: leakage-safe eval medyan hiyerarşisini seçti (model ₺5.1k/%21 → brand+storage → brand → global); HistGBR aday olarak `src/model/cold_start.py`'de tutuluyor, default değil. Rapor: `docs/hybrid-valuation-report.md`.
- REPAIR_KB lookup: `src/repair/lookup.py` — EXACT / SERIES_LEVEL / NO_REPAIR_DATA katmanları, fabrikasyon yok.
- Acquisition: `src/acquisition/engine.py` — deterministik formül, iş kuralları BUSINESS_INPUT olarak etiketli.
- Freshness (`max_obs_age_days=45`) placeholder; S3 ile yaşa göre hata ölçülecek.
- New-price kapsamı: 5/410 exact anchor (Apple only); Samsung TR fiyatları JS-gated → sıfır anchor olarak dokümante, fabrikasyon yok.
- 31/31 test geçiyor.

## 2026-09-26 güncelleme — Snapshot 3 doğrulama ve freeze kararı

### Snapshot 3 (immutable, S1/S2 ile aynı metodoloji)
- Aynı pipeline: sitemap → ürün sayfası → satıcı teklifleri; 839 sitemap URL'si (S2 ile birebir aynı liste), 0 hata, 2.167 teklif.
- Non-A kategori sayfaları aynı parser ile tekrar toplandı: 68 satır (İyi 34 + Premium Plus 34; **Çok İyi/B envanteri bugün sitenin tamamında yok** — S2'de 46 idi). Kategori URL seti S2 ile aynı.
- Taban: 25 Apple MSRP + 6 EasyCep (fiyatlar yeniden doğrulandı, değişmemiş).
- Çıktılar ayrı dosyalarda: `price_observations_2026_s3.csv`, `getmobil_product_offers_2026_s3.csv`, `gm_products_s3.xml`, `*_s3.parquet`. S1/S2 dosyaları değişmedi.
- S3: 2.266 obs | 415 market satırı | 378 canonical varyant | grade A 362, S 15, C 18, UNKNOWN 20.
- `market_snapshot_combined.parquet` artık S1+S2+S3 (1.297 satır, 427 varyant); `offer_level_combined.parquet` 6.745 satır.

### OOT sonuç (docs/s3-validation-report.md)
- Shared 361 / new 1 / disappeared 49 (grade A).
- **Persistence yine kazandı**: variant-median MAPE %0.4 (MAE ₺143), last-price %3.8, V1 %30.3, brand %59.7.
- Intra-day drift: median %0, mean -%0.13, %86 değişmemiş, %98 ±%5 içinde.
- Kritik uyarı: S3, S2 ile **aynı takvim günü** (~1.5 saat sonra) toplandı → pipeline tekrarlanabilirliğini doğrular, çok-günlük temporal genellemeyi ölçmez.
- Unseen varyant sadece 1 (`xiaomi|14t|512`): cold-start fallback %37.7 APE < brand %55.0 < V1 %97.1 → yön doğru ama n=1, istatistiksel iddia yok.
- **Yaş↔hata analizi ölçülemedi**: tüm S3 varyantları aynı gün S2'de de vardı → `days_since_obs` tamamen 0. `max_obs_age_days=45` kalibre edilememiş placeholder olarak kalıyor; yeni eşik seçilmedi.
- **Hybrid Market Valuation Engine v1: FREEZE-READY.** Backend/API aşaması önerilir (Spring Boot API + basit demo entegrasyonu).
