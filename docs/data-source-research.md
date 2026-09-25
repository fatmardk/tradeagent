---
agent: devin-local
session: jungle-piano
created: 2026-09-16T19:02:55Z
---
# TradeAgent — İkinci El / Yenilenmiş Telefon Fiyat Tahmini: Veri Kaynakları Araştırma Raporu

Türkiye pazarına uyarlanabilir ikinci el/yenilenmiş telefon fiyat tahmin sistemi için mevcut açık datasetler, resmi API'ler, ticari veri sağlayıcıları ve hukuki erişim durumlarının kapsamlı fizibilite analizi; sonuç olarak katmanlı bir veri mimarisi ve master dataset şeması önerilmektedir.

# TradeAgent — Veri Kaynakları Araştırma Raporu

## 0. Yönetici Özeti (TL;DR)

- **Gerçek, etiketli, modele hazır "ikinci el telefon fiyatı" dataseti neredeyse yok.** Açık kaynaklarda bulunan en bilinen dataset (ReCell/Kaggle `ahsan81`) normalize edilmiş fiyatlar içeriyor, model adı yok, 2021 tarihli ve ~3.5K satır. Türkiye'ye özgü açık dataset hiç yok.
- **Türkiye için en değerli tek kaynak Samsung Türkiye'nin resmi tamir ücret listesi** (model bazında TL tamir fiyatları) ve **Getmobil'in herkese açık Marketplace API dokümantasyonu + web'deki yenilenmiş satış fiyatları + form tabanlı "Fiyatlandırma Motoru" geri alım teklifleri**.
- **Sahibinden / Letgo / Facebook Marketplace için yasal veri erişim kanalı yok.** Resmi API yok; scraping kullanım şartlarına aykırı. Teknik olarak mümkün (Bright Data, Apify aktörleri mevcut) ama hukuki/ToS riski taşır — karar sizin.
- **Global ikinci el fiyat gerçeği için en iyi kaynak Swappa** (ücretsiz public `/prices` sayfası + ücretli resmi veri servisi) ve **eBay Marketplace Insights API** (satılmış ilanlar, son 90 gün — limited release, onay gerekli).
- **Türkiye sıfır fiyatı için en pratik yol ticari API'ler**: Roketfy Data Engine (Akakçe fiyat geçmişi dahil, Trendyol/Hepsiburada/Amazon TR), SerpApi Google Shopping (`gl=tr`), SerpApi Amazon (`amazon.com.tr`). Keepa amazon.com.tr'yi desteklemiyor.
- **Parça fiyatı**: iFixit (ücretsiz resmi API — tamir rehberleri + parça listeleri), Apple Self Service Repair Store (resmi parça fiyatları, USD/EUR), Fransız Indice de Réparabilité açık verisi (parça fiyat/cihaz fiyat oranı alt skorları), Türkiye toptan parça siteleri (Gemtech, MobilYedek, ekranborsasi, telefonprofesoru — public fiyat listeleri, API yok).
- **Kritik veri boşluğu**: Türkiye'de koşul (condition/batarya/kozmetik) detaylı gerçek ikinci el satış verisi ve geri alım (buyback) fiyat verisi sadece Getmobil/EasyCep gibi şirketlerin elinde — en güçlü hamle **şirket ortaklığıyla bu veriyi almak** (projenin G maddesi zaten bunu öngörüyor).

---

## 1. ANA DATASETLER (İkinci El / Yenilenmiş Telefon)

### 1.1 Kullanılabilir açık datasetler

| Dataset | Link | Satır | Lisans | Yıl | Pazar | İçerik özeti |
|---|---|---|---|---|---|---|
| **Used Phones & Tablets Pricing Dataset (ReCell)** | [Kaggle](https://www.kaggle.com/datasets/ahsan81/used-handheld-device-data) | ~3.454 | **CC0 Public Domain** | 2021 | Global (normalize) | brand, os, screen_size, 4g, 5g, kameralar, int_memory, ram, battery, weight, release_year, **days_used**, normalized_new_price, **normalized_used_price (target)** |
| **Used Phone Dataset** | [Kaggle](https://www.kaggle.com/datasets/mizan121/used-phone-dataset) | ~2.000 (251 KB) | Kaggle (belirsiz) | ~2024 | Hindistan (INR) | brand, **model adı**, ram, storage, **condition (Like New/Good/Fair/Poor)**, battery_health %, launch price, resale price |
| **Used Phone Price Prediction Dataset** | [Kaggle](https://www.kaggle.com/datasets/sharmajicoder/used-phone-price-prediction-dataset) | 1.000.000 | Kaggle | 2025 | Sentetik (Hindistan simülasyonu) | 28 kolon: condition, battery_health, screen_cracked, water_damage, repair_history, warranty, market_demand_score → resale_price. **AÇIKÇA SENTETİK** |
| **Used Smartphone Price 3000** | [HF](https://huggingface.co/datasets/KumarXAI/used-smartphone-price-3000) | 3.000 | HF | 2025 | Sentetik | launch_price_inr, age, battery_health, screen_crack, repair_history, warranty → estimated_resale_price_inr. **SENTETİK** |
| **Mobile Price Classification** | [Kaggle](https://www.kaggle.com/datasets/iabhishekofficial/mobile-price-classification) | 2.000 | Kaggle | ~2019 | — | 20 spec kolonu → price_range (0-3 sınıf). Gerçek fiyat YOK, klasik eğitim dataseti. Modelleme pratiği için, fiyat tahmini için değil |
| **Phone Price Prediction (SmartLabsData)** | [HF](https://huggingface.co/datasets/SmartLabsData/Phone-Price-Prediction) | bilinmiyor | HF | — | — | Storage/Camera/Price kolonları; provenance belirsiz — doğrulanmadan kullanılmamalı |

### 1.2 Akademik çalışmaların datasetleri

- **"Predicting the Price of Old Mobile Phones"** — Zenodo DOI [10.5281/zenodo.17702209](https://doi.org/10.5281/zenodo.17702209). eBay + Craigslist'ten toplanmış gerçek ilanlar (brand, storage, RAM, kamera, yaş → resale). Verinin paylaşılıp paylaşılmadığı indirme aşamasında doğrulanmalı.
- **"Price Prediction of Second-Hand iPhones (Random Forest)"** — [ISTEK journal](https://ejournal.uinsgd.ac.id/index.php/istek/article/view/2154). Facebook Marketplace'ten **542 gerçek ilan**: tip, storage, garanti, **Face ID, TrueTone** durumu → fiyat. Endonezya pazarı ama feature set'i (biyometrik arıza = fiyat etkisi) bizim için çok öğretici.
- **"Analysing the Refurbished Smartphone Market with ML"** — [Türk akademik çalışma, trendbusecon](https://doi.org/10.16951/trendbusecon.1607949). XGB R²=0.99. Dataset muhtemelen ReCell türevi — makale okunup doğrulanmalı.
- **Emerald TQM: "smartphone exchange prices"** — [doi:10.1108/tqm-05-2024-0186](https://doi.org/10.1108/tqm-05-2024-0186). GSMArena + Amazon.com verisi; exchange/trade-in fiyat modeli + yorum sentimenti.
- **Pakistan resale estimator** — [doi:10.31645/jisrc.24.22.2.11](https://doi.org/10.31645/jisrc.24.22.2.11). storage, batarya sağlığı, ekran, garanti, kutu, PTA kaydı → resale. RF 0.97.

### 1.3 Aynı kaynaktan türeme — DEDUP uyarıları

- **ReCell verisi çok kopyalı**: Kaggle `ahsan81/used-handheld-device-data` = GitHub `falakian/Used-Phones-Tablets-Pricing-Dataset` = GitHub `JesusTorres98/ReCell` (`used_phone_data.csv`) = `rochitasundar/Regression-dynamic-price-prediction-ReCell` = HF `jason1966/ahsan81_used-handheld-device-data`. Hepsi aynı ~3.454 satır, kolon adları küçük farklı (`device_brand`↔`brand_name`, `normalized_*`↔düz isimler). **Sadece bir kopya kullanılmalı.**
- **Smartprix-scraped setler** (`githubmasterin/smartphones-cleaned-dataset`, `shivam2407/smartphone-dataset`, `linuso7/smartphones-indian-market-data`, `anujoraon799` GitHub SQL projesi): aynı smartprix.com kaynağından türemiş, örtüşen kayıtlar.
- Sentetik setler (sharmajicoder 1M, KumarXAI 3K, afaqkhan091 2K spec seti): gerçek piyasa değeri temsil ETMEZ — sadece pipeline/feature prototipi için.

### 1.4 Değerlendirme

| Dataset | Gerçek mi? | Model adı? | Gerçek fiyat? | Condition? | Bizim için değer |
|---|---|---|---|---|---|
| ReCell/ahsan81 | Kısmen (normalize edilmiş gerçek veri olduğu söyleniyor) | ❌ | ❌ (normalize) | ❌ (days_used proxy) | Pipeline + baseline model + feature ilişkileri için iyi başlangıç |
| mizan121 | Gerçeğe yakın görünüyor (Google Drive'dan) | ✅ | ✅ INR | ✅ + battery | En yakın "gerçek" açık set; INR→TR transfer öğrenme için sinyal |
| sharmajicoder | ❌ Sentetik | ✅ | Sentetik | ✅ zengin | Feature şeması referansı, stress-test |
| Akademik setler | Gerçek ilan | ✅ | ✅ | Kısmen | Yöntem + feature seçimi referansı |

**Sonuç**: Açık datasetler "iskelet + baseline" için yeterli ama Türkiye fiyat tahmini için yetersiz. Asıl veri aşağıdaki canlı kaynaklardan kurulmalı.

---

## 2. YENİ / SIFIR TELEFON FİYAT KAYNAKLARI

### 2.1 Türkiye

| Kaynak | Erişim | Fiyat tipi | Durum |
|---|---|---|---|
| **Akakçe** | Resmi public read API **yok**; üye işyeri XML feed modeli (siz feed verirsiniz). Veri: [Roketfy Data Engine](https://roketfy.com/rakip-fiyat-takip/) API ile Akakçe ürün detayı, satıcı teklifleri ve **fiyat geçmişi** (kredi başına ücretli) | TRY, çok satıcılı, geçmiş | Ticari API mevcut — en pratik TR fiyat kaynağı |
| **Cimri** | Aynı model (XML feed); Roketfy/Apify aktörü mevcut | TRY | Ticari |
| **Epey** | Public API yok; [Apify aktörü](https://apify.com/bovi/epey-prices) mevcut; teknik spec + fiyat + teknik skor | TRY | Ticari scraping |
| **Trendyol** | [developers.trendyol.com](https://developers.trendyol.com/) — **sadece satıcı API'si** (kendi ürünleriniz). Pazar verisi: Roketfy, Bright Data | TRY | Kısmi (satıcı olursanız kendi veriniz) |
| **Hepsiburada** | [developers.hepsiburada.com](https://developers.hepsiburada.com/) — satıcı API'si; pazar verisi ticari sağlayıcılar | TRY | Kısmi |
| **Amazon.com.tr** | Resmi product API yok (satıcı SP-API kendi envanteri). **SerpApi Amazon engine `amazon.com.tr` destekli**; Roketfy `amazon/offers`; **Keepa TR YOK** | TRY | Ticari API mevcut |
| **Google Shopping TR** | [SerpApi Google Shopping](https://serpapi.com/google-shopping-api) `gl=tr`, `google_domain=google.com.tr` — fiyat, satıcı, `second_hand_condition` alanı dahil | TRY | Ticari API — temiz, sürdürülebilir |
| **Marka resmi mağazaları** (apple.com/tr, samsung.com/tr, mi.com/tr, Turkcell Pasaj, Türk Telekom, Vatan, Teknosa, MediaMarkt) | Public sayfalar; API yok; scraping ToS'a takılır | TRY MSRP/güncel | Manuel periyodik örnekleme mümkün |
| **akillial.com** | Türk spec+fiyat agregatorü, public sayfalar | TRY | Küçük ölçek referans |

### 2.2 Global (yeni fiyat referansı / depreciation tabanı)

- **Keepa API** — Amazon fiyat geçmişi (new + used marketplace price serileri, list price). Domain listesi: com, co.uk, de, fr, co.jp, ca, it, es, in, com.mx, com.br — **TR yok**. Global fiyat eğrileri için güçlü. Ücretli token sistemi.
- **eBay Browse API** — aktif ilanlar (resmi, geliştirici onayı ile ücretsiz).
- **idealo** — API/data products mevcut ama TR pazarı yok (DE/UK/FR/IT/ES).
- **GSMArena `price` alanı** — EUR lansman fiyatları (spec datasetlerinde gömülü).

---

## 3. YENİLENMİŞ (REFURBISHED) TELEFON KAYNAKLARI

### 3.1 Türkiye — asıl hedef pazar

| Kaynak | Ne var | API/Erişim | Not |
|---|---|---|---|
| **Getmobil** | Yenilenmiş satış fiyatları (site), kozmetik sınıfı sayfası, **"Telefon Sat" buyback ön teklif motoru** ("Fiyatlandırma Motoru" — üyelik sözleşmesinde tanımlı), yenileme sertifikasında değişen parça bilgisi | **[api-documentation.getmobil.com](https://api-documentation.getmobil.com/)** — Marketplace API v1 (auth + SKU listesi + satıcı endpoint'leri; satıcı odaklı, client_id/secret gerekli → ortaklık kanalı). Site fiyatları public. Buyback teklifi form tabanlı | **Projenin en stratejik veri ortağı** — satış + alış + parça değişim verisi potansiyeli |
| **EasyCep** | Yenilenmiş satış fiyatları (site + 300+ mağaza), buyback ön teklif formu ("Mağazada Anında Nakit"), yılda ~340K cihaz; **Turkcell trade-in altyapısını EasyCep + Mobilfon yürütüyor** | Public API bulunamadı; site public | Pazar lideri — ortaklık/veri paylaşımı adayı |
| **Diğer lisanslı yenileme merkezleri** | Ticaret Bakanlığı resmi listesi: Garantili Teknoloji, Fonksiyon, Yenilenmiş Teknoloji, Mobilfon vb. | [tuketici.ticaret.gov.tr — Yenileme Merkezleri](https://tuketici.ticaret.gov.tr/yayinlar/belgelendirme-islemleri/yenileme-yetki-belgesi/yenileme-merkezleri) | Oyuncu evreni haritası için resmi kaynak |
| **Amazon.com.tr — "İkinci El ile Tasarruf" (Amazon Depo)** | İkinci el/yenilenmiş ilanlar, 4 kademeli durum sınıfı (Yeni Gibi/Çok İyi/İyi/Kabul Edilebilir), 1 yıl Amazon güvencesi | SerpApi Amazon engine ile çekilebilir | TR'de durum→fiyat ilişkisi için gerçek sinyal |
| **Turkcell/Vodafone trade-in** | Ön teklif formları (EasyCep/Mobilfon/Vodafone partnerleri) | Form tabanlı, API yok | Buyback fiyat örneklemesi için manuel/izinli yol |

### 3.2 Global refurbished kaynakları

- **Back Market** — [backmarket.com](https://www.backmarket.com/). Türkiye'de YOK (17 pazar: ABD, AB, JP vb.). Grade bazlı fiyat (Fair/Good/Excellent/Premium) + storage varyantları. Resmi public API yok; üçüncü taraf API: [parse.bot Back Market API](https://parse.bot/marketplace/f60c9c20-fdd6-4b31-a722-1fb352430188/backmarket-com-api) (kredili). Grade→fiyat yapısı modelleme için mükemmel referans.
- **Swappa** — [swappa.com/prices](https://swappa.com/prices): ücretsiz, güncel, model başına ortalama fiyat + ilan sayısı (doğrulanmış ilanlar → veri kalitesi yüksek). Resmi ücretli "data services" ürünü var. Scraping ToS'a aykırı (Cloudflare korumalı). Üçüncü taraf: [ReefAPI](https://reefapi.com/swappa-api), [parse.bot](https://parse.bot/marketplace/e98dec75-9771-4ab0-afe7-6df3eec2714f/swappa-com-api), Bright Data dataset ($250/100K kayıt). İlanlarda condition grade + battery health alanları mevcut.
- **gsmExchange** — [gsmexchange.com](https://www.gsmexchange.com/): B2B toptan (new/used/CPO/ASIS) telefon pazarı; üyelik onaylı, fiyat detayları üyeye açık, trading geçmişi erişilebilir. **Acquisition/wholesale taban fiyatı için ideal** — şirket üyeliğiyle legal erişim.
- **refurbed, Rebuy, musicMagpie/Decluttr, SellCell/BankMyCell** — Avrupa/ABD refurbished + trade-in fiyatları; public sayfalar, API yok. Trade-in agregatorleri (SellCell) buyback fiyat karşılaştırması yayınlıyor — metodoloji referansı.

---

## 4. İKİNCİ EL İLAN PLATFORMALARI — API / TERMS DURUMU

| Platform | Resmi API | Açık veri | Araştırma erişimi | Ticari kullanım | Scraping uygun mu? |
|---|---|---|---|---|---|
| **Sahibinden** | ❌ (sadece kurumsal emlak/vasıta veri taşıma API'si — Rekabet Kurulu kararı + EIDS; telefon/alışveriş kategorisini KAPSAMAZ) | ❌ | ❌ | ❌ | ❌ ToS ihlali; Apify/Bright Data aktörleri var ama gri/riskli |
| **letgo** | ❌ | ❌ | ❌ | ❌ | ❌ ToS ihlali (platform aktif, Hedef Filo sahibi; elektronik ~%30 hacim) |
| **Facebook Marketplace** | ❌ (Graph API'de yok) | ❌ | ❌ | ❌ | ❌ Meta ToS ihlali |
| **Getmobil** | ⚠️ Marketplace API var (satıcı odaklı; doküman public, credential gerekli) | Site fiyatları public | Ortaklıkla mümkün | Ortaklık gerekli | ToS kontrol edilmeli; API kanalı tercih edilmeli |
| **EasyCep** | ❌ bulunamadı | Site fiyatları public | Ortaklıkla mümkün | Ortaklık gerekli | ToS kontrol edilmeli |
| **Swappa** | Ücretli resmi data service | /prices public özet | Ücretli servis | ✅ ücretli lisansla | ❌ ToS + Cloudflare |
| **eBay** | ✅ Browse API (aktif ilan); Marketplace Insights API (SATILMIŞ ilanlar, 90 gün, GTIN/keyword — limited release, onay gerekli) | ❌ | ✅ resmi başvuru | ✅ API lisansıyla | ❌ (API var, gerek yok) |
| **Back Market** | ❌ | ❌ | ❌ | ❌ | ⚠️ üçüncü taraf API'ler mevcut (parse.bot) |
| **Amazon.com.tr** | Satıcı SP-API (kendi envanteri) | ❌ | ❌ | SerpApi/Roketfy ile | ❌ ToS — ticari API kullan |

**Not**: Sahibinden'den tek Kaggle dataseti bilgisayar donanımı içindi ([redim0/sahibinden-ankara-pc-fiyatlari](https://www.kaggle.com/datasets/redim0/sahibinden-ankara-pc-fiyatlari)) — telefon için public dataset yok.

---

## 5. PARÇA / YEDEK PARÇA VERİ KAYNAKLARI

| Kaynak | İçerik | Erişim | Türkiye? |
|---|---|---|---|
| **iFixit** | Tamir rehberleri (parça listesi + zorluk + adımlar), parça mağazası fiyatları | **[Resmi ücretsiz API v2.0](https://www.ifixit.com/api/2.0/doc)** (rehberler); mağaza fiyatları için [Bright Data dataset/scraper](https://brightdata.com/products/datasets/ifixit) | Parça USD fiyatı — global referans |
| **Apple Self Service Repair Store** | Resmi OEM parça fiyatları (ekran, batarya, kamera, arka cam, enclosure) — örn. iPhone 16 ekran $279-379, batarya $99-116 | Public web store (ABD + seçili AB); API yok; periyodik örnekleme mümkün | TR'de yok — global referans |
| **Samsung Türkiye resmi onarım ücret listesi** | **Model bazında TL**: ekran modül, eko onarım, çerçeve, dış ekran, batarya (₺2.950-3.750), parça+işçilik dahil | [samsung.com/tr/support/ekran-degisimi-fiyat-bilgisi](https://www.samsung.com/tr/support/ekran-degisimi-fiyat-bilgisi/) — public tablo | ✅ **En değerli TR parça+tamir kaynağı** |
| **Fransız Indice de Réparabilité** | Model bazında resmi skorlar: parça fiyatı/cihaz fiyatı oranı, parça bulunabilirliği, demontaj skoru | **[data.gouv.fr konsolide dataset](https://www.data.gouv.fr/datasets/fichiers-consolides-des-donnees-respectant-le-schema-indice-de-reparabilite)** — açık veri, şema: [etalab/schema-indice-reparabilite](https://github.com/etalab/schema-indice-reparabilite) | Fransa — ama model-global eşleştirilebilir; 2.109 ürün |
| **TR toptan parça siteleri** | Ekran/batarya/kamera/kasa/flex parça fiyatları TL: [Gemtech/toptantelefonparcasi](https://toptantelefonparcasi.com/) (5.000+ SKU), [MobilYedek](https://mobilyedek.com/), [ceptelefonparcasi.com](https://www.ceptelefonparcasi.com/), [mobilyenilik.com](https://www.mobilyenilik.com/elektronik/telefon-yedek-parca) | Public sayfalar, API yok | ✅ gerçek TR parça fiyatı |
| **TR tamir fiyat agregatorleri** | Şehir/model bazında ekran+batarya değişim fiyatı: [ekranborsasi.com](https://www.ekranborsasi.com/), [telefonprofesoru.com](https://telefonprofesoru.com/samsung-ekran-degisimi-fiyatlari/) (günlük güncelleniyor) | Public sayfalar | ✅ işçilik dahil gerçek TR tamir fiyatı |
| **B2B parça tedarikçileri** | MobileSentrix, ReplaceBase, eParts (ABD/EU toptan) | Üyelik/public | Global referans |

---

## 6. TAMİR / REFURBISHMENT MALİYETİ

- **Samsung TR listesi**: parça + işçilik dahil model×işlem matrisi → doğrudan `repair_cost` tablosu.
- **Apple "Get an Estimate"** ([support.apple.com/iphone/repair](https://support.apple.com/iphone/repair)) — ABD servis fiyatları; TR yetkili servis fiyatları public tablo olarak yok (sorgu bazlı).
- **iFixit**: rehber başına parça listesi + zorluk derecesi → işçilik süresi proxy'si (zorluk → tahmini süre → işçilik maliyeti kuralı kurulabilir).
- **Indice de Réparabilité**: parça/cihaz fiyat oranı → parça maliyeti imputasyonu için formül referansı.
- **Sundr.ca methodology** ([sundr.ca/methodology](https://sundr.ca/methodology)) — 305K+ topluluk tamir kaydı + iFixit + Keepa ile maliyet modeli; metodoloji public, veri kapalı. Modelleme yaklaşımı referansı.
- **Boşluk**: "arıza → işlem → parça + işçilik → toplam maliyet" formatında açık dataset YOK. Samsung TR tablosu + iFixit parça listesi + toptancı fiyatları birleştirilerek kurulabilir.

---

## 7. CİHAZ TEKNİK ÖZELLİK DATASETLERİ

| Kaynak | Kapsam | Erişim | Not |
|---|---|---|---|
| **GSMArena** | En kapsamlı spec DB (~10K+ cihaz, 60+ alan, EUR lansman fiyatı dahil) | Resmi API yok; ToS: ticari olmayan kullanım; robots.txt AI botlarını engelliyor, genel crawler'a telefon sayfaları açık — **gri alan** | En iyi spec kaynağı ama lisans riski → Kaggle aynaları kullan |
| Kaggle aynaları | `imprime/gsmarena-listed-brands` (9.814 cihaz × 60 kolon, price EUR dahil), `rajibdab/global-smartphone-database-2025` (4.144 cihaz, Temmuz 2025 scrape — **en güncel**), `arwinneil/gsmarena-phone-dataset`, `msainani/gsmarena-mobile-devices`, GitHub `foykes/gsm-arena-dataset` | Kaggle indirme | Tarihli snapshot; güncelleme gerekirse resmi izin gerekir |
| **Epey** | TR odaklı spec + teknik skor + fiyat | Apify aktörü | TR model adlandırmasıyla eşleşme kolaylığı |
| **Smartprix setleri** | ~1K cihaz, INR fiyat + spec | Kaggle | Hindistan ağırlıklı |
| **HF: jomarie04/smartphone-specifications-2020-2024** | brand, model, release_year, ram, storage, battery, price_usd | HF indirme | Hafif, hızlı entegrasyon |
| **Kimovil** | Global spec + mağaza fiyatları; varyant/model kodu (SM-S938B vb.) | Public site, API yok | Model kodu açısından zengin referans |

**Birleştirme**: GSMArena mirror'ı DEVICE MASTER'ın teknik omurgası olmalı; TR model kodları (SM-xxx, Axxxx) ile eşleştirme kritik.

---

## 8. TÜRKİYE ODAKLI KAYNAK MATRİSİ

| Kaynak | Erişilebilir? | API? | Ücretsiz? | Ticari kullanım? | Otomasyon? | TR kapsam | Güncellik |
|---|---|---|---|---|---|---|---|
| Akakçe | ✅ site | ❌ resmi; ✅ Roketfy API | ❌ (Roketfy ücretli) | ✅ Roketfy lisansıyla | ✅ | Tam | Güncel + fiyat geçmişi |
| Cimri | ✅ site | ❌ resmi; ✅ Roketfy/Apify | ❌ | ✅ ticari | ✅ | Tam | Güncel |
| Epey | ✅ site | ❌; ✅ Apify | ❌ | ⚠️ | ✅ | Tam | Güncel |
| Trendyol | ✅ site | Satıcı API'si; pazar verisi Roketfy/Bright Data | ❌ | ⚠️ | ✅ | Tam | Güncel |
| Hepsiburada | ✅ site | Satıcı API'si; pazar verisi ticari | ❌ | ⚠️ | ✅ | Tam | Güncel |
| Amazon.com.tr | ✅ site | SerpApi/Roketfy | ❌ | ✅ ticari API | ✅ | Tam | Güncel |
| Google Shopping TR | — | ✅ SerpApi (`gl=tr`) | ❌ | ✅ | ✅ | Tam | Güncel |
| Getmobil | ✅ site | ⚠️ Marketplace API (credential) | Site public | Ortaklıkla | ✅ API (ortaklık) | Tam (refurb odaklı) | Güncel |
| EasyCep | ✅ site | ❌ | Site public | Ortaklıkla | ❌/⚠️ | Tam (refurb lideri) | Güncel |
| Sahibinden | ✅ site | ❌ (telefon kategorisi yok) | ❌ | ❌ | ❌ (ToS) | Tam | Güncel |
| letgo | ✅ site | ❌ | ❌ | ❌ | ❌ (ToS) | Tam | Güncel |
| Samsung TR tamir listesi | ✅ | ❌ (public tablo) | ✅ | ⚠️ referans kullanımı | Periyodik fetch | Galaxy serisi | Güncel |
| Ticaret Bakanlığı yenileme merkezi listesi | ✅ | ❌ (public tablo) | ✅ | ✅ kamu verisi | ✅ | Tam | Güncel |
| TR parça toptancıları | ✅ siteler | ❌ | Public fiyat | ⚠️ | Periyodik | Tam | Güncel |
| ekranborsasi/telefonprofesoru | ✅ | ❌ | Public | ⚠️ | Periyodik | Tam | Günlük |

---

## 9. VERİ MİMARİSİ — BİRLEŞTİRME PLANI

```
DEVICE MASTER  (brand + model + variant + model_code[SM-*/A*] + release_year)
    │
    ├── TECH SPECS        (GSMArena mirror / Epey)         key: model_code veya normalized(brand,model)
    │
    ├── NEW PRICE         (Roketfy Akakçe+TY+HB / SerpApi  key: normalized model + storage (+renk)
    │                      Google Shopping / Amazon TR)
    │
    ├── MSRP / LAUNCH     (GSMArena EUR price, marka resmi) key: model + storage
    │
    ├── USED MARKET       (Swappa public / eBay sold API /  key: model + storage (+condition)
    │   GLOBAL              gsmExchange üyelik)
    │
    ├── USED MARKET TR    (Getmobil/EasyCep buyback + satış  key: model + storage + kozmetik sınıf + pil
    │                      fiyatları; sahibinden/letgo YOK   sağlığı + arıza seti)
    │
    ├── REFURBISHED PRICE (Getmobil, EasyCep, Back Market    key: model + storage + grade
    │                      global, Amazon Depo sınıfları)
    │
    ├── PART COST         (Samsung TR liste, iFixit parça,   key: model + part_type
    │                      TR toptancı, Apple SSR, Fr. indice)
    │
    ├── REPAIR COST       (Samsung TR tablo, ekranborsasi,   key: model + repair_type
    │                      telefonprofesoru, iFixit zorluk→işçilik)
    │
    └── TARGETS
         ├── expected_selling_price (TR, koşul bazlı)
         ├── refurbishment_cost     (parça + işçilik + test + garanti rezervi)
         └── max_acquisition_price  (selling_price − cost − margin − risk)
```

**Join key hiyerarşisi**: 1) `model_code` (SM-S928B, A3102 vb.) en güçlü key — GSMArena/Kimovil/Samsung listesinde var; 2) `normalized(brand, model, storage_gb, ram_gb)` string eşleşmesi — çoğu kaynakta çalışır; 3) `GTIN/EAN/UPC` — eBay/Amazon/Google Shopping için ideal ama TR kaynaklarında seyrek; 4) `release_year` doğrulama yardımcısı. Model adı normalizasyonu (alias tablosu: "iPhone 13" ↔ "Apple iPhone 13 128 GB") zorunlu bir ara tablo olacak.

---

## 10. SONUÇ — VERİ STRATEJİSİ

### A) CORE DATASET (başlangıç iskeleti)
1. **GSMArena mirror** (`rajibdab/global-smartphone-database-2025` güncel + `imprime` geniş kapsam) → DEVICE MASTER
2. **ReCell/ahsan81** (CC0) → baseline model + feature ilişkileri (dedupe: tek kopya)
3. **mizan121 Used Phone Dataset** → gerçek condition+battery fiyat sinyali (INR)
4. **sharmajicoder 1M sentetik** → feature şeması + pipeline stress test (gerçek sanılmamalı)

### B) PRICE ENRICHMENT
- TR yeni fiyat: **Roketfy API** (Akakçe fiyat geçmişi + TY/HB/Amazon offers) ve/veya **SerpApi Google Shopping TR + Amazon TR**
- Global ikinci el: **Swappa /prices** (ücretsiz özet) + ücretli data service; **eBay Marketplace Insights** (başvuru)
- TR ikinci el/yenilenmiş: **Getmobil + EasyCep public fiyatları** (ortaklıkla derinleşir), **Amazon Depo** sınıflı fiyatlar

### C) PART DATA
- **Samsung TR resmi liste** (TL, birincil), TR toptancı siteleri (Gemtech, MobilYedek, ceptelefonparcasi), **iFixit** parça+fiyat (USD referans), **Apple SSR** (USD/EUR), **Fransız indice** (oransal model)

### D) REPAIR DATA
- Samsung TR matrisi (ekran×model), ekranborsasi + telefonprofesoru (işçilik dahil, günlük), iFixit zorluk→işçilik kuralı, Sundr metodolojisi referans

### E) TURKEY DATA (öncelik sırası)
1. Roketfy Data Engine (Akakçe geçmiş + pazaryeri) — anında başlanabilir, ücretli
2. Getmobil site + Marketplace API (ortaklıkla alış/satış/parça-değişim verisi) — stratejik
3. EasyCep public fiyatlar + ortaklık görüşmesi
4. Samsung TR tamir listesi — ücretsiz, hemen
5. SerpApi gl=tr Google Shopping + amazon.com.tr — tamamlayıcı
6. Ticaret Bakanlığı yenileme merkezi listesi — oyuncu evreni

### F) DEVICE SPEC DATA
- GSMArena Kaggle mirror'ları (hukuki olarak temiz yol — canlı scrape yerine), Epey (TR varyant isimleri), Kimovil (model kodu referansı), HF jomarie04 (hafif alternatif)

### G) COMPANY DATA (Getmobil/ortak izniyle eklenebilecek alanlar)
- Geri alım işlem kayıtları: model, storage, IMEI-temiz yaşı, pil sağlığı %, kozmetik sınıf, fonksiyonel test sonuçları (41 adımlık QC), **ön teklif vs son teklif delta'sı**, alış fiyatı, satış fiyatı, satış süresi (days-to-sell)
- Yenileme kayıtları: değişen parça listesi (sertifikada var), parça maliyeti, işçilik, toplam refurb maliyeti
- Talep sinyalleri: model bazlı stok devir hızı, iade oranı, garanti talep oranı
- Bu veri, projeyi "tahmin"den "gerçek işlem verisiyle öğrenen sisteme" dönüştürür — en yüksek değerli tek kaynak

### H) DATA GAPS (hâlâ elde olmayanlar)
1. **TR'de koşul-detaylı gerçek C2C satış verisi** (sahibinden/letgo/FB — kapalı)
2. **TR buyback/alış fiyatı veri seti** — sadece şirketlerin elinde
3. **İşçilik maliyeti dataseti** — fiyat listelerinden türetilmeli
4. **Tarihsel TR ikinci el fiyat serisi** — Akakçe geçmişi kısmen kapatır (sıfır fiyat); ikinci el için biriktirme gerekir
5. **Model→parça uyumluluk açık DB'si** — iFixit + toptancı kataloglarından kurulmalı
6. **TR "yenilenmiş" kelimesinin standardize grade sınıfları** (A/B/C ↔ kozmetik sınıfı) — ortak mapping tablosu kurulmalı

### I) DATA ACQUISITION PLAN (önerilen sıra)
1. **Hafta 0**: Kaggle mirror'ları + ReCell + mizan121 indir → DEVICE MASTER + baseline
2. **Kısa vade**: Roketfy hesabı → TR yeni fiyat + Akakçe geçmiş; Samsung TR liste + TR toptancı fiyatlarının izinli/periyodik derlenmesi; Swappa /prices örneklemesi
3. **Orta vade**: Getmobil ortaklık görüşmesi (Marketplace API credential + buyback/sale geçmişi); eBay Marketplace Insights başvurusu; gsmExchange üyelik değerlendirmesi (wholesale taban fiyat)
4. **Sürekli**: kendi gözlem veri tabanını biriktir (her gün fiyat snapshot'ı → 3-6 ayda TR tarihsel seri); sahibinden/letgo için YALNIZCA resmi izin/ortaklık aranır — izinsiz scraping önerilmez

### J) FINAL MASTER DATASET — önerilen şema

| Kolon | Kaynak |
|---|---|
| `device_id` (PK) | üretilen |
| `brand`, `model`, `variant`, `model_code` | GSMArena mirror / Kimovil |
| `release_year`, `release_date` | GSMArena mirror |
| `ram_gb`, `storage_gb`, `screen_size`, `chipset`, `battery_mah`, `camera_mp`, `5g`, `os`, `weight` | GSMArena mirror / Epey |
| `msrp_eur`, `msrp_usd` | GSMArena price / marka sayfaları |
| `new_price_try`, `new_price_source`, `new_price_date` | Roketfy (Akakçe/TY/HB) / SerpApi |
| `used_price_tr_market` | Getmobil/EasyCep buyback + sahibinden (izin varsa) / ilan örneklemi |
| `used_price_global` (USD/EUR) | Swappa / eBay sold / gsmExchange |
| `refurbished_price_tr` | Getmobil / EasyCep / Amazon Depo |
| `condition_grade` (A/B/C ↔ kozmetik sınıfı) | kaynak alanı / mapping tablosu |
| `battery_health_pct` | ilan/ortak veri / NSYS-benzeri test |
| `defects` (ekran kırık, Face ID, su teması...) | ilan/ortak veri; sentetik set feature'ı |
| `repair_history`, `replaced_parts` | ortak veri (sertifika) |
| `warranty_months`, `box`, `charger` | ilan/ortak veri |
| `part_cost_{screen,battery,camera,back_cover,charge_port,board}` | Samsung TR liste + iFixit + TR toptancı |
| `labor_cost_est` | ekranborsasi/telefonprofesoru − parça fiyatı; iFixit zorluk kuralı |
| `refurb_cost_total` | part_cost + labor + test + garanti rezervi (hesaplanan) |
| `repairability_score`, `parts_price_ratio` | Fransız indice (model eşleşmeli) |
| `days_used` / `device_age_months` | türetilmiş (release_date, ilan/ortak) |
| `listing_date`, `snapshot_date` | toplama meta |
| `country`, `currency`, `source` | meta |
| **TARGET** `expected_selling_price_tr` | TR satış fiyatları (eğitim: Getmobil/EasyCep/Depo satış fiyatı) |
| **TARGET** `max_acquisition_price` | türetilmiş: expected_price − refurb_cost − hedef marj − risk primi |

---

## 11. KARARLAR VE KISITLI VERİ STRATEJİSİ (kullanıcı onayı sonrası)

**Kararlar:**
- Veri ortaklığı: henüz belli değil → bağımsız kurulur, ortaklık sonradan eklenebilir mimari
- Bütçe: **sadece ücretsiz kaynaklar** → Roketfy, SerpApi, Bright Data, Swappa paid, Keepa kullanılmayacak
- Gri kaynaklar: **tamamen hariç** → Sahibinden/Letgo/FB scraping yok; üçüncü taraf scraping-API'leri (Apify aktörleri, parse.bot, ReefAPI) kullanılmayacak
- Hedef: **çift target** — `expected_selling_price_tr` (yenilenmiş satış fiyatı) VE `max_acquisition_price` (maks. alış fiyatı)

**Kısıtlar altında geçerli kaynak seti (hepsi ücretsiz + yasal):**

| Veri alanı | Kaynak | Yöntem |
|---|---|---|
| DEVICE MASTER + SPEC | GSMArena Kaggle mirror'ları (`imprime` 9.814×60, `rajibdab` 4.144/2025), HF `jomarie04` | Kaggle/HF indirme (tek seferlik) |
| Baseline used modeli | ReCell `ahsan81` (CC0), `mizan121`, sentetik 1M set (sadece şema/test) | Kaggle indirme |
| TR tamir maliyeti | **Samsung TR resmi onarım listesi** (public tablo), ekranborsasi/telefonprofesoru public fiyatları | Manuel/periyodik kayıt (public bilgi, küçük ölçek); otomatik scraping ToS kontrolünden sonra |
| Parça fiyatı | iFixit **resmi ücretsiz API** (rehber+parça listesi), Apple SSR public fiyatları, TR toptancı public listeleri | API + manuel kayıt |
| Repairability/parça oranı | Fransız Indice de Réparabilité — **data.gouv.fr açık veri** | Doğrudan indirme |
| Global used fiyat | **Swappa /prices public özet sayfası** (model başına ort. fiyat — manuel periyodik snapshot; toplu scraping ToS ihlali olduğundan hariç), **eBay resmi Browse API** (ücretsiz developer başvurusu; sold-data için Marketplace Insights başvurusu ücretsiz) | Public sayfa kaydı + resmi API başvurusu |
| TR yenilenmiş satış fiyatı | Getmobil / EasyCep **public satış sayfaları** — düşük hacimli periyodik kayıt; ölçek için şirketten yazılı izin istenecek (Marketplace API credential başvurusu) | Manuel snapshot + izin başvurusu |
| TR yeni fiyat | Kamuya açık marka fiyat sayfaları (apple.com/tr, samsung.com/tr, mi.com/tr, Turkcell Pasaj) manuel/periyodik; Akakçe public sayfa gözlemi (sınırlı) | Manuel snapshot; kendi zaman-serisi biriktirme |
| Oyuncu evreni | Ticaret Bakanlığı yenileme merkezi listesi | Public sayfa |
| Buyback teklifi | Getmobil/EasyCep/Turkcell/Vodafone **form bazlı ön teklif motorları** — manuel sorgulamayla nokta örneklemi (model×koşul grid'i), toplu otomasyon yok | Manuel örnekleme |

**Kısıt sonucu değişen strateji noktaları:**
- TR fiyat tarihsel serisi ücretli API olmadan alınamaz → **kendi snapshot'ımızı biriktireceğiz** (günlük/haftalık manuel veya izinli kayıt; 3-6 ayda kullanılabilir seri oluşur).
- C2C ilan verisi tamamen dışarıda kaldı → condition→fiyat deltaları refurbished satıcı verisi + global Swappa/eBay verisinden transfer edilecek; TR'ye kurdan ziyade **oran bazlı** (yeni fiyata oranla değer kaybı eğrileri) transfer öğrenme uygulanacak.
- Buyback fiyatı için ana veri: şirketlerin public ön-teklif formlarından **manuel grid örneklemesi** (her model × koşul kombinasyonu için birkaç sorgu) + ortaklık gelirse gerçek işlem verisi.

**Gözden geçirilmiş edinim planı (ücretsiz-only):**
1. Kaggle/HF indirme seti → DEVICE MASTER + baseline (hemen)
2. Samsung TR tamir tablosu + Fransız indice + iFixit API → REPAIR/PART katmanı (hemen)
3. eBay developer başvurusu (Browse API; Marketplace Insights'a da başvur) → global used fiyat (başvuru süreci)
4. Getmobil/EasyCep public fiyatlarının izinli küçük ölçekli derlenmesi + buyback form grid örneklemesi → TR çekirdek target verisi
5. Günlük fiyat snapshot pipeline'ı (manuel/semi-otomatik, izinli kaynaklar) → TR zaman serisi biriktirme
6. Ortaklık netleşirse: Marketplace API credential → gerçek alım/satım/parça-değişim verisi tüm boşlukları kapatır

---

## Riskler / Dürüstlük Notları

- Sahibinden/Letgo/FB verisi olmadan TR "C2C gerçek ilan" dağılımı eksik kalır; model öncelikle "refurbished satış fiyatı + buyback" tahminine odaklanmalı, C2C sinyali ortaklık gelene kadar global veriden transfer edilmeli.
- Normalize fiyatlı ReCell verisiyle eğitilen model TL fiyat üretemez — sadece oran/feature yapısı öğretir.
- Sentetik setlerle eğitilmiş model gerçek pazarda sınanamaz; sadece engineering amaçlı.
- GSMArena ToS ticari kullanımı kısıtlıyor; Kaggle aynalarının lisansları da belirsiz — kurumsal kullanımda GSMArena'dan izin almak veya alternatif spec kaynağı (Epey + marka resmi sayfaları + Wikidata) değerlendirilmeli.
- Üçüncü taraf "API"lerin (parse.bot, ReefAPI, Apify aktörleri) çoğu scraping tabanlıdır; ToS riskini sağlayıcı üstlenir ama sözleşmede "compliance" şartlarını kontrol etmek gerekir.

---
---

# BÖLÜM II — STRATEJİ DOĞRULAMA VE GENİŞLETME (Eylül 2026)

Bu bölüm, Bölüm I'deki varsayımların 2026 itibarıyla yeniden doğrulanması, derinlemesine aranmış ek kaynaklar (Zenodo/Figshare/Mendeley/akademik/sığır-ekonomi/sağlık-verisi) ve istenen karar matrislerini içerir. Amaç: mevcut stratejiyi haklı çıkarmak değil, dürüst bir fizibilite değerlendirmesi üretmek.

## 12. SENATECH MAKALESİ — KESİN DOĞRULAMA

| Alan | Doğrulanan değer |
|---|---|
| Başlık | "Analysing the Refurbished Smart Phone Market with Machine Learning" / "Yenilenmiş Akıllı Telefon Pazarının Makine Öğrenmesi ile Analizi" |
| Yazarlar | Berrin Beyza Özen, Muhammed Fatih Alaeddinoğlu, Tolga Aydın — Atatürk Üniversitesi ([AVESIS kaydı](https://avesis.atauni.edu.tr/publication/details/8c046029-2b20-43ee-b7af-0590b9ee2754/oai)) |
| Yayın | Trends in Business and Economics, Cilt 40, Sayı 1, Ocak 2026, s. 42–59 — [DOI 10.16951/trendbusecon.1607949](https://doi.org/10.16951/trendbusecon.1607949), [DergiPark](https://dergipark.org.tr/en/pub/trendbusecon/article/1607949), [TRDizin](https://search.trdizin.gov.tr/en/yayin/detay/1375442/) |
| Dataset boyutu | **36.130 kayıt, 11 özellik** (36K iddiası doğru) |
| Özellikler | Brand, Model, **Title (ilan başlığı)**, device (ayrıntılı cihaz tanımı), **Price (target)**, Battery (kapasite), memory (depolama+aksesuar), Color, **cosmetics (sayısal kozmetik skor)**, **refurbished (kodlanmış)**, DataTransfer |
| Veri kaynağı | SENATECH'in iç **"AKILLICIHAZ" SQL Server veritabanı** (model/category/asset/entity tabloları); Python bot + pyodbc + sqlalchemy ile çıkarılmış |
| SENATECH katkısı | Makale teşekkür bölümünde açıkça: "gerçek piyasa verilerine ulaşma" için SENATECH Bilgi Teknolojileri'ne teşekkür — veri gerçekten şirketten |
| Sonuçlar | XGBoost R² = 0,9902; LSTM R² = 0,9870 |
| İndirilebilirlik | **Hayır.** Zenodo/Figshare/Mendeley/GitHub/Kaggle'da arandı — yok. GitHub'daki "AkilliCihaz" repoları ilgisiz öğrenci projeleri. Ek materyal/supplement yok |
| Yeniden yayın | Başka bir makalede aynı dataset kullanımı bulunamadı; Kaggle'a sızıntı olarak da bulunamadı |

**Kritik değerlendirme (dürüst):**

- Kayıtların **"Title = ilan başlığı"** içermesi bunların **ilan/asset kayıtları** olduğunu gösteriyor — doğrulanmış **satış işlemi değil**. Fiyat muhtemelen SENATECH'in listeleme/değerleme fiyatı.
- 11 özellikle R²=0,99 şu ihtimalleri akla getiriyor: (a) ilan fiyatları zaten model+depolama+kozmetik kombinasyonunun deterministik fonksiyonu olabilir (aynı fiyatlama motoru üretmişse model onu geri öğrenir); (b) Title/device serbest metinleri fiyatla korele bilgi sızdırıyor olabilir; (c) random split + aynı cihazın tekrarlanan kayıtları (entity duplication) ve zamansal sızıntı. Bu metriği "transfer edilebilir model başarısı" olarak okumamak gerekir.
- **En önemli sınır**: özellik setinde battery_health, fonksiyonel defekt, parça değişimi, **alış fiyatı, satış fiyatı ayrımı, satış tarihi, days_to_sell YOK**. Yani bu dataset yalnızca *yenilenmiş ilan fiyatı modelini* destekler; **alış fiyatı (acquisition) modelini desteklemez**.
- Ticari kullanım: veri SENATECH mülkiyetinde; makale veriye lisans vermiyor. Akademik kullanım için yazarlarla Atatürk Üniversitesi AVESIS üzerinden iletişim mümkün ama veri paylaşımı SENATECH onayı gerektirir — gerçekçi beklenti düşük tutulmalı.
- SENATECH'in kendi değerleme sitesi [cihazsat.senatech.com](https://cihazsat.senatech.com/) "binlerce satış verisi, ~140 özellik, ~20 risk faktörü" iddia ediyor — yani şirketin iç verisi makaledekinden çok daha zengin olabilir; ortaklık hedefi olarak değerli.

**Sonuç**: Makale gerçek şirket verisinin varlığını kanıtlıyor ama dataset **mevcut değil, indirilemez, yeniden kullanılamaz** — "kullanılabilir kaynak" değil, "böyle verinin Türkiye'de var olduğunun kanıtı + potansiyel ortak" olarak dosyalanmalı.

## 13. "MÜKEMMEL DATASET" VAR MI? — EN YAKIN GERÇEK ADAY: SHPhoneBench

Aranan kombinasyon (model + koşul + defekt + batarya + parça değişimi + alış fiyatı + satış fiyatı + days_to_sell) için tüm açık ekosistem tarandı. Sonuç:

**Hiçbir açık dataset tam kombinasyonu içermiyor.** En yakın gerçek aday:

**SHPhoneBench** — [Zenodo DOI 10.5281/zenodo.20077398](https://doi.org/10.5281/zenodo.20077398) (v2, Mayıs 2025; ek sürümler .20077399, .20078041, .20095512/13)

- Çin anakarasında **gerçek geri-dönüşüm iş akışlarından** (Oca 2024 – Mar 2026) toplanmış **73.200 işlem-hizalı kayıt**; küratörlü benchmark alt-kümesi **15.000 örnek**.
- Kayıt başına 4 sinyal: çok-açılı cihaz fotoğrafları (V), Çince teknisyen notları (T), yapılandırılmış CRM metadata JSON (S), masaüstü diagnostik aracı ekran görüntüleri (IS).
- Etiketler: 5 kademeli koşul derecesi, 18 kategorili defekt bounding-box, cross-modal tutarlılık, **fiyat (CNY)**.
- Görevler: koşul derecelendirme, defekt tespiti, tutarlılık kontrolü, %90 predictive interval'lı fiyat regresyonu.
- **~46 GB, 50 zip parçası, açık erişim**; Croissant 1.1 + MLCommons RAI metadata ile.

**Kısıtlar (kritik):**
- Fiyatlar **Laplace diferansiyel gizlilik (ε=0.1) ile gürültülenmiş "list price"** — ε=0.1 ciddi gürültü; mutlak fiyat öğrenilemez, dağılım/sıralama kısmen korunur. "Transaction-aligned" ifadesi işlem bağlantılı ama açıklanan fiyat alanı liste fiyatı.
- Çin pazarı + CNY + Çince metinler; Türkiye fiyat hedefi olarak kullanılamaz.
- Yazarlar anonim; eşlik eden makale/veri sayfası "intended-use restrictions" içeriyor — indirmeden önce okunmalı.
- Batarya sağlığı, parça-değişim, alış/satış ayrımı ve days_to_sell alanlarının varlığı manifest'ten teyit edilmeli.

**Değeri**: (1) inspection-feature şeması ve defekt taksonomisi referansı, (2) defekt→fiyat transfer-öğrenme deneyleri, (3) sentetik senaryo üretimi için gerçek dağılım temeli. Türk fiyat target'ı DEĞİL.

## 14. TAMİR / İNSPEKSİYON VERİSİ — DOĞRULAMA

### 14.1 Open Repair Alliance (Open Repair Data) — doğrulandı

- [Downloads](https://openrepair.org/open-data/downloads/) | [GitHub](https://github.com/openrepair/data) | [Standart ORDS](https://standard.openrepair.org/standard.html)
- **305.649 EEE tamir kaydı** (Ekim 2025 sürümü, Temmuz 2025'e kadar veri), **CC BY-SA 4.0**
- Alanlar: product_category, partner_product_category, **brand**, year_of_manufacture, **problem** (serbest metin), **repair_status** (Fixed/Repairable/End of life), repair_barrier, **country**, event_date, group_id
- **Kritik sınır**: standarttan **model alanı veri kalitesi nedeniyle kaldırılmış** → model bazlı defekt dağılımı ÇIKARAMAZSINIZ; yalnızca marka/kategori/yıl seviyesi.
- **Parça, maliyet, işçilik, fiyat alanı YOK.** Tamir sonucu var, maliyeti yok.
- Mobil telefon alt-kümesi **~1.900 kayıt** (MobiFix, gönüllü etiketli arıza tipleri).
- Örneklem sapması: repair-café/komünite etkinliği verisi — EU ağırlıklı, gönüllü, hayatta-kalma biası var (tamire getirilen cihazlar).
- **ML kullanımı**: kaba `P(arıza tipi | marka, kategori, cihaz yaşı)` prior'ları için EVET; tamir maliyeti veya ticari refurbishment oranı için HAYIR. CC BY-SA 4.0 ticari kullanıma izin verir ama türev çalışmada share-alike şartı doğar.

### 14.2 Diğer tamir/arıza kaynakları

| Kaynak | Durum |
|---|---|
| **Blancco "State of Mobile Device Repair & Security" raporları** (2016–2019) | Gerçek diagnostik-veri tabanlı (yüzlerce operatör/işlemciden test kayıtları): OS/model bazında arıza oranları, en sık başarısız testler (LCD, batarya şarj, hoparlör, WiFi). [PDF örneği](https://blancco.hu/wp-content/uploads/2019/02/en-rs-q3-2018-state-of-mobile-device-repair-and-security.pdf). **Aggregate, güncel değil, satır verisi yok** — niteliksel prior olarak iyi |
| **Fransız Indice de Réparabilité** | [data.gouv.fr](https://www.data.gouv.fr/datasets/fichiers-consolides-des-donnees-respectant-le-schema-indice-de-reparabilite) — açık devlet verisi; demontaj, parça bulunabilirliği, **parça-fiyat/cihaz-fiyat oranı** alt skorları. Yapısal maliyet/risk feature'ı olarak değerli |
| **Sigorta/garanti verisi (SquareTrade, Asurion, Allstate)** | PR istatistikleri yayınlıyorlar (düşme hasarı oranları vb.) ama **açık satır-seviyesi dataset yok** |
| **iFixit API v2.0** | [Doküman](https://www.ifixit.com/api/2.0/doc) — **hâlâ aktif**, çoğu public endpoint auth'suz; rehberler, parça listeleri, zorluk, kategori taksonomisi. Parça taksonomisi + işlem-zorluğu proxy'si için en iyi ücretsiz kaynak. Ticari lisans durumu sayfa bazında kontrol edilmeli (iFixit içeriği CC BY-NC-SA — **ticari kullanımda dikkat**) |
| **Cashify "The Great Indian Upgrade"** ([2026 özeti](https://www.cashify.in/cashify-whitepaper-2026)) | Gerçek platform verisi ama **aggregate rapor**: ort. buyback ₹8.573 (2025, +%34), marka/model payları (iPhone 13 = buyback'in %6,9'u, refurb satışın %15,5'i), fiyat bantları. Hindistan, satır verisi yok — pazar-yapısı prior'ı |
| **Counterpoint Global Pre-owned raporları** | Ücretli; basın özetleri kırıntı düzeyinde (örn. H1 2026: Samsung %30 pay) |

## 15. BATARYA SAĞLIĞI → FİYAT VERİSİ

**Doğrudan dataset yok** — bu açık bir boşluk. Ayrım net yapılmalı:

- **Batarya kimyası/aging datasetleri** (NASA, Stanford, [Nature Sci. Data 2024 NMC/C-SiO — 228 hücre, 3 milyar nokta](https://www.nature.com/articles/s41597-024-03831-x)): hücre seviyesi laboratuvar degradasyonu. Telefon yeniden-satış fiyatıyla İLGİSİZ — karıştırmayın. Tek kullanımı: `E[battery_health | yaş, döngü]` prior dağılımı için literatür eğrileri (Xu et al. 2018, AccuBattery'nin derlediği [metodoloji](https://accubattery.zendesk.com/hc/en-us/articles/210224725-Charging-research-and-methodology)).
- **Dolaylı ama gerçek yöntem — buyback grid örneklemesi**: Getmobil formu "pil gücü %91 üzeri/altı" soruyor; SENATECH dereceleri pil eşikleri içeriyor. Aynı model+koşul kombinasyonunda yalnız pil kademesini değiştirerek tekrarlanan ön-teklif sorgusu → **model bazlı deneysel Δfiyat(pil kademesi)** elde edilir. Bu, açık veriyle pil→fiyat etkisini ölçmenin tek gerçekçi yoludur.
- İkinci dolaylı yol: refurb satıcılarının aynı modelde dereceler arası fiyat farkı (A vs B vs C) + derece tanımlarındaki pil eşikleri → koşul-içi pil marjı tahmini.

## 16. API / KAYNAK DOĞRULAMALARI (2026 durumu — düzeltmeler dahil)

| Kaynak | 2026 durumu | Düzeltme/not |
|---|---|---|
| **Getmobil Marketplace API** | Var: [api-documentation.getmobil.com](https://api-documentation.getmobil.com/) — POST /marketplace/v1/auth (client_id+secret), GET /marketplace/v1/sku | **Düzeltme**: bu "public research API" değil, **onaylı satıcı/partner API'si** — kendi mağaza verinizi çeker. Pazar-çapında veri için ortaklık şart. Getmobil Aralık 2025'te $22M Seri A aldı; Reverse Marketplace + Vendor Panel aktif |
| **eBay Marketplace Insights** | Hâlâ Limited Release (v1_beta.2.2), **onay-gated**, sold-history son 90 gün, condition/price/country filtreleri. Finding API 5 Şub 2025'te kapatıldı | **eBay'in Türkiye pazarı yok** → sadece global benchmark. Başvuru ücretsiz ama onay garantisi yok |
| **Swappa /prices** | Canlı, [Eylül 2026 güncel](https://swappa.com/prices); model×koşul ort. fiyatlar; Swappa verisinin tamamlanmış-satış bazlı olduğu belirtiliyor | Ücretsiz public sayfa = manuel snapshot OK; toplu scraping ToS; paid data service (Bright Data) dışarıda |
| **iFixit API** | Aktif ve çalışıyor | CC BY-NC-SA içerik — ticari kullanım sınırı not edilmeli |
| **Apple Türkiye onarım fiyatları** | **Resmi ve public**: support.apple.com/tr-tr "Tahmini servis" + basına yansıyan tam tablo — pil ₺3.699–6.449, ekran ₺7.999–20.499, arka cam, arka kamera, cihaz değişim bedeli ₺81.999'a kadar ([Technopat tablosu](https://www.technopat.net/2026/07/14/iphone-onarim-ucretleri-tum-modeller/)) | Samsung TR listesiyle birlikte **TR tamir maliyeti için iki resmi kaynak** |
| **Samsung TR** | [Resmi liste](https://www.samsung.com/tr/support/ekran-degisimi-fiyat-bilgisi/) aktif | Güncel fiyat; tarihsel arşiv yok — snapshot'lamak gerekir |
| **Amazon Depo (amazon.com.tr)** | Gerçek TR ikinci-el kanalı: satıcı="Amazon Depo", 4 derece (Yeni Gibi/Çok İyi/İyi/Kabul Edilebilir), 1 yıl güvence, "İkinci El ile Tasarruf Et" seçeneği | Renewed TR'de yok; Depo onun yerine. API yok (PA-API affiliate-odaklı) → izinli/manuel gözlem |
| **Decluttr** | **KAPANDI Haziran 2025** | Önceki kaynak listelerinden çıkarılmalı |
| **musicMagpie** | AO World'ün parçası (Ara 2024 alım); ABD operasyonu kapatıldı; UK'de Timpson ortaklığıyla trade-in | Veri erişimi yok; UK aggregate bilgi |
| **Gazelle / Reebelo / Back Market** | Public data API yok; Reebelo Cobalt API'si satıcı-facing (x-api-key); parse.bot/Apify gibi üçüncü-taraf scraping API'leri = **dışarıda (gri)** | Koşul-bazlı refurbished fiyat şeması örneği olarak manuel bakılabilir |
| **gsmExchange** | B2B toptan trading floor; üyelik-gated; fiyatlar çoğunlukla "Negotiable", lot-bazlı | Birim fiyat modellemesi için uygun değil |
| **Trendyol/Hepsiburada API'leri** | Var ama **satıcı-facing** — kendi mağazanızın verisi | Pazar-çapında fiyat araştırması için kullanılamaz |
| **Keepa** | amazon.com.tr **desteklemiyor** (hâlâ) | — |
| **Roketfy / SerpApi / Bright Data / Apify aktörleri** | Mevcut ama ücretli → **bütçe kısıtıyla dışarıda** | — |
| **Sahibinden / Letgo** | Resmi API yok; scraping ToS ihlali → **dışarıda** (kullanıcı kararı) | — |
| **YÜBİS (Ticaret Bakanlığı)** | Yenilenmiş ürünlerin sertifika+karekod takip sistemi; Ağu 2026 yönetmeliği: TV'ler kapsama girdi, mağazada 14 gün cayma | Veri feed'i değil ama **"gerçek yenilenmiş ürün" doğrulaması** için altyapı; karekod sorgusu sınırlı bilgi verebilir |
| **Yenileme Merkezi listesi** | [Güncel liste](https://tuketici.ticaret.gov.tr/yayinlar/belgelendirme-islemleri/yenileme-yetki-belgesi/yenileme-merkezleri): Garantili Teknoloji, **EasyCep**, HB Bilişim, Ouno, **KVK**, BDH, Mobilfon, Delta GSM, **SENATECH** vb. | Ortaklık aday evreni buradan çıkar |

## 17. KAPSAMLI KAYNAK MATRİSİ

| Source | Data Type | Turkey | Real/Synthetic | Records | Key Fields | Price Type | Historical | API | License | ML Use | Commercial Use | Accessibility | Recommendation |
|---|---|---|---|---:|---|---|---|---|---|---|---|---|---|
| ReCell / ahsan81 Kaggle | Used+refurb pricing | ❌ | Gerçek (normalize) | ~3.454 | brand, spec, days_used, norm prices | Normalize used/new | 2021 sabit | Kaggle | CC0 | Baseline/depreciation | ✅ | Kolay | **P0 — core baseline** |
| mizan121 used-phone | Used listing | ❌ (IN) | Gerçeğe yakın | ~2.000 | model, condition, battery_health, resale | Listing (INR) | ~2024 | Kaggle | Belirsiz | Feature/prototype | ⚠️ lisans | Kolay | P1 — koşul şeması |
| sharmajicoder 1M | Used listing | ❌ | **Sentetik** | 1M | condition, battery, damage, resale | Sentetik | — | Kaggle | Kaggle | Sadece pipeline test | ⚠️ | Kolay | P2 — şema referansı |
| KumarXAI 3K | Used listing | ❌ | **Sentetik** | 3K | battery_health, repair_history, resale | Sentetik | — | HF | HF | Test only | ⚠️ | Kolay | P2 |
| **SHPhoneBench (Zenodo)** | **Inspection+defect+price** | ❌ (CN) | **Gerçek** | 73.200 (15K etiketli) | foto, teknisyen notu, CRM JSON, diag ekranı, 5-kademe grade, 18 defekt, fiyat | **DP'li liste fiyatı (CNY)** | 2024–26 | Zenodo | Açık (kullanım koşulu kontrol) | Defekt/grade ML, transfer | ⚠️ paper'daki kısıtlar | Orta (46GB) | **P1 — tek gerçek inspection seti** |
| SENATECH / AKILLICIHAZ | Refurb listing | ✅ | Gerçek | 36.130 | model, ilan başlığı, cosmetics, refurbished, price | Liste/varlık fiyatı | Bilinmiyor | Yok | Şirket mülkü | Referans değeri | ❌ izinsiz | **Yok** | P1 — ortaklık hedefi |
| Zenodo 17702209 ("old phones") | Used listing | ❌ | Gerçek ilan | ? | brand, storage, age → resale | Listing | — | Zenodo | Kontrol | Baseline | ⚠️ | Kolay | P2 |
| ISTEK iPhone 542 | Used listing | ❌ (ID) | Gerçek ilan | 542 | Face ID, TrueTone, garanti, storage → fiyat | Listing | ~2022 | Makale | Akademik | Feature referansı | ⚠️ | Makalede | P2 |
| **Open Repair Alliance** | Tamir olayı | Kısmen (country var) | Gerçek | 305.649 | category, brand, year, problem, repair_status, barrier, country, date | Yok | 2010'lar–2025 | GitHub/Zenodo | **CC BY-SA 4.0** | Arıza prior'ları | ✅ (share-alike) | Kolay | **P0 — defekt dağılımı** |
| MobiFix | Mobil tamir alt-kümesi | ❌ | Gerçek | ~1.900 | arıza tipi etiketleri | Yok | — | GitHub | CC BY-SA | Defekt taksonomisi | ✅ | Kolay | P1 |
| Blancco raporları | Diagnostik aggregate | ❌ | Gerçek (aggregate) | Rapor | OS/model arıza oranları, test tipleri | Yok | 2016–19 | PDF | Telifli rapor | Niteliksel prior | ⚠️ | Kolay | P2 |
| Indice de Réparabilité | Repairability skoru | ❌ (FR) | Gerçek (resmi) | yüzlerce model | demontaj, parça bulunabilirliği, parça-fiyat oranı | Oran | Güncel | data.gouv | Açık (Licence Ouverte) | Risk feature | ✅ | Kolay | **P0** |
| GSMArena Kaggle mirror'ları | Spec | ✅ | Gerçek | ~9.8K/4.1K | tam spec | Yok | Güncel | Kaggle | Belirsiz (ToS) | Device master | ⚠️ | Kolay | **P0** |
| HF jomarie04 spec | Spec+fiyat | ❌ | Gerçek | ~birkaç bin | spec, USD fiyat | USD launch | 2020–24 | HF | HF | Spec join | ⚠️ | Kolay | P1 |
| **Samsung TR onarım listesi** | Tamir fiyatı | ✅ | Gerçek (resmi) | ~yüzlerce satır | model → ekran/eco-ekran/frame fiyatı | Servis ücreti (parça+işçilik) | Sadece güncel | Yok (public sayfa) | Public bilgi | Maliyet lookup | ✅ | Orta | **P0** |
| **Apple TR onarım fiyatları** | Tamir fiyatı | ✅ | Gerçek (resmi) | ~tüm iPhone'lar | pil/ekran/arka cam/kamera/cihaz-değişim | Servis ücreti | Sadece güncel | Tahmin aracı | Public | Maliyet lookup | ✅ | Orta | **P0** |
| iFixit | Rehber+parça | ❌ | Gerçek | binlerce | rehber, parça adı, zorluk, taksonomi | Parça fiyatı (USD) | — | ✅ resmi | CC BY-NC-SA | Parça taksonomi | ⚠️ NC | Kolay | **P0 (taksonomi)** |
| TR parça toptancıları (Gemtech, MobilYedek, ekranborsasi vb.) | Parça fiyatı | ✅ | Gerçek | binlerce | parça, model, kalite, fiyat | Toptan liste | Güncel | Yok | Public sayfa | Maliyet lookup | ⚠️ ToS | Orta | **P0 (manuel snapshot)** |
| Amazon Depo TR | 2.el satış | ✅ | Gerçek | değişken | model, 4 derece, fiyat | **Liste fiyatı** | Güncel | Yok | ToS | TR target | ⚠️ | Orta | **P0 (izinli gözlem)** |
| Getmobil public sayfaları | Refurb satış + buyback teklifi | ✅ | Gerçek | değişken | model, storage, derece, fiyat; form: pil/durum→teklif | Liste + **buyback teklifi** | Güncel | Vendor-only | ToS | **TR target + buyback** | ⚠️ izinle | Orta | **P0 (grid örnekleme + izin)** |
| EasyCep | Refurb satış + buyback | ✅ | Gerçek | değişken | benzeri | Liste + teklif | Güncel | Yok | ToS | TR target | ⚠️ | Orta | **P0** |
| cihazsat.senatech.com | Buyback teklifi | ✅ | Gerçek | değişken | model, durum → teklif | **Buyback teklifi** | Güncel | Yok | ToS | Buyback target | ⚠️ | Orta | **P0** |
| Swappa /prices | Used satış özeti | ❌ (US) | Gerçek | model×koşul | ort. fiyat (completed-sale bazlı) | **İşlem bazlı özet** | Güncel | Yok (public) | Public | Global prior | ⚠️ | Kolay | **P1** |
| eBay Marketplace Insights | **Sold items** | ❌ | Gerçek | — | sold price, condition, tarih (90g) | **GERÇEK SATIŞ** | 90 gün | ✅ onaylı | eBay lisans | Sold-price prior | ⚠️ lisans | Başvuru | **P1 (başvur)** |
| gsmExchange | B2B toptan | ❌ | Gerçek | ~11K teklif | lot, model, "Negotiable" | Toptan teklif | Güncel | Üyelik | Üyelik | Hayır | Üyelik | Kapalı | P2 — değmez |
| Cashify whitepaper | Pazar aggregate | ❌ (IN) | Gerçek (aggregate) | Rapor | ort. buyback, pay, bant | Aggregate | 2024–26 | PDF | Telifli rapor | Pazar prior | ⚠️ | Kolay | P2 |
| Ticaret Bk. yenileme listesi | Oyuncu evreni | ✅ | Gerçek (resmi) | ~20+ merkez | ünvan, MERSİS, tarih | Yok | Güncel | Yok | Public | Ortak aday listesi | ✅ | Kolay | **P0** |
| YÜBİS karekod | Sertifika doğrulama | ✅ | Gerçek (resmi) | — | yenilenmiş ürün sertifikası | Yok | Güncel | Sorgu | Public | Doğrulama katmanı | ✅ | Sınırlı | P1 |
| KVK/Ouno/HB/Mobilfon | Refurb+servis oyuncuları | ✅ | — | — | ortaklık adayı | — | — | Yok | — | — | Ortaklık | — | P1 |

## 18. VERİ BOŞLUK MATRİSİ

| Required Feature | Best Current Source | Coverage | Reliability | Missing? | Proposed Solution |
|---|---|---|---|---|---|
| Device identity | GSMArena mirrors + marka resmi | ~%95 model | Yüksek | Varyant/SKU karışıklığı | model-code + normalized-name birleştirme |
| Specifications | GSMArena + HF jomarie04 | ~%90 | Yüksek | TR-spec varyantlar | Epey public sayfaları ile çapraz kontrol |
| New price (TR) | Marka resmi sayfaları + Amazon TR + Turkcell Pasaj | Ana modeller | Yüksek | **Tarihsel seri yok** | Kendi snapshot pipeline'ı (günlük kayıt) |
| Used listing price (TR) | Amazon Depo + refurb satıcılar | Kısmi | Orta | **C2C kanalı tamamen yok** (Sahibinden hariç tutuldu) | Refurb satıcı ilanları proxy; sınırı raporla |
| Used **sold** price | eBay Insights (US) + Swappa | Global only | Yüksek | **TR'de sold verisi yok** | Global prior + TR liste→satış düzeltme katsayısı (ortaklıkla kalibre) |
| Refurbished price (TR) | Getmobil/EasyCep/Amazon Depo liste | İyi | Orta-Yüksek | Liste≠satış | İzinli snapshot + satışa düşme oranı tahmini |
| Condition | SHPhoneBench taksonomi + satıcı dereceleri | Şema var | Orta | TR gözlemi seyrek | Grade-mapping tablosu (satıcı dereceleri → kanonik) |
| Battery health | **Doğrudan veri yok** | Yok | — | **EVET — kritik** | Buyback grid örnekleme (Δfiyat/pil kademesi) + yaş→pil prior (literatür) |
| Repair event | Open Repair Alliance | Marka/yıl seviyesi | Orta (biaslı) | Model seviyesi + TR | ORA prior + iFixit zorluk + servis fiyatlarıyla türetme |
| Replaced part | Sadece ortak veri | Yok | — | **EVET** | Ortaklık; o zamana dek "olası parça ihtiyacı" tahmini kuralla |
| Part cost (TR) | Samsung/Apple resmi + TR toptancı | Ana markalar iyi | Yüksek | Xiaomi/Oppo resmi liste seyrek | Toptancı listeleriyle kapat |
| Labor cost | Resmi servis ücretlerine gömülü | Kısmi ayrıştırma | Orta | Ayrı işçilik nadir | servis_ücreti − parça_fiyatı ≈ işçilik üst sınırı |
| Repair total | Samsung/Apple TR + toptancı+labor est. | İyi | Orta-Yüksek | Non-OEM senaryolar | 3 senaryo: OEM-servis / premium-aftermarket / ekonomi |
| Purchase price | Buyback teklif motorları | Model×koşul grid'i | Orta | Gerçek işlem fiyatı | Grid örnekleme → teklif modeli; ortaklıkla gerçek |
| Sale price | Refurb satıcı liste fiyatı | İyi | Orta | **Gerçek satış yok** | Ortaklık; liste fiyatına satış-iskonto prior'ı |
| Days to sell | **Yok** | Yok | — | **EVET** | Ortaklık; o zamana dek likidite proxy'si (model popülerliği, Cashify/Counterpoint payları) |

## 19. GOLD / SILVER / BRONZE DATASET TANIMLARI

### 🥇 GOLD — ideal (ortaklık gerektirir)

Şema (cihaz-işlem kaydı): `anon_device_id, brand, model, storage, ram, imei_band, purchase_offer_date(T0), offer_price, seller_type | inspection_date(T1), battery_health, cycle_count, screen_condition, body_condition, camera/face_id/fingerprint/speaker/mic/charging_port status, defect_codes, previous_repair | refurb_date(T2), parts_replaced[], part_quality[], part_cost[], labor_cost, refurb_total, final_grade | listing_date(T3), list_price, channel | sale_date(T4), sale_price, days_to_sell, return_flag, warranty_claims`

**Mümkün olan modeller**: tam pipeline — used-value, refurb-satış, tamir maliyeti, days-to-sell, marj-kalibreli acquisition engine; leakage'siz T0/T1 modelleri; gerçek kalibrasyon. **Sadece Getmobil/EasyCep/SENATECH/KVK tipi ortakla mümkün.**

### 🥈 SILVER — güçlü pratik (public + izinli)

`device master + spec + TR yeni-fiyat snapshot + refurb satıcı liste fiyatı snapshot (model×storage×derece) + buyback grid örnekleme (model×koşul×pil→teklif) + ORA arıza prior'ları + Samsung/Apple TR tamir fiyatları + TR parça listeleri + Fransız indice + Swappa/eBay global prior`

**Mümkün olan modeller**: refurb liste-fiyat modeli (iyi), buyback-teklif modeli (orta — teklif≠işlem), tamir-maliyet lookup+regresyon (iyi), kural-bazlı acquisition engine (iyi), days-to-sell YOK (likidite skoru proxy), satış-gerçekleşme olasılığı YOK.

### 🥉 BRONZE — MVP minimum

`device master + spec + ReCell baseline + global depreciation eğrileri (Swappa/eBay) + TR yeni fiyat + Samsung/Apple tamir listesi + iFixit taksonomi + az sayıda TR refurb liste gözlemi`

**Mümkün**: oran-bazlı değerleme ("bu model yeni fiyatın ~%X'i"), kural-bazlı max-acquisition formülü, maliyet lookup. **Yapılamayanlar**: koşul-duyarlı TR fiyat modeli, güvenilir buyback tahmini, satış-süresi, marj kalibrasyonu — bunlar Bronze'da **iddia edilmemeli**.

## 20. T0–T4 ÖZELLİK ZAMANLAMASI VE LEAKAGE

```
T0 = cihaz şirkete teklif edildi   T1 = inspeksiyon bitti   T2 = refurb bitti
T3 = ilan açıldı                   T4 = satıldı
```

| Özellik | T0 | T1 | T2 | T3 | T4 | Not |
|---|:-:|:-:|:-:|:-:|:-:|---|
| model, storage, spec, yaş | ✅ | | | | | T0'da ilan/müşteri beyanından; IMEI ile doğrulanır |
| beyan edilen koşul | ✅ | | | | | Güvenilmez — T1 ile düzeltilir |
| **önerilen alış fiyatı (target)** | **✅ karar** | revize | | | | T0 = birincil karar noktası |
| battery_health, defekt kodları, fonksiyon testleri | | ✅ | | | | **T0 modeline GİREMEZ** — beyanla proxy'lenir |
| gerçek parça ihtiyacı, parça maliyeti | | ~T1/T2 | ✅ | | | Teardown'a kadar belirsiz → T0'da E[maliyet\|görünen koşul] kullanılır |
| final_grade | | | ✅ | | | T0'a leakage: grade ancak refurb sonrası |
| list_price | | | | ✅ | | T0'a leakage |
| sale_price, sale_date, days_to_sell | | | | | ✅ | **Hiçbir karar modelinde feature olamaz** — yalnızca label/kalibrasyon |

**Kurallar:**
- T0 modeli yalnız T0 özelliklerini görür: model, depolama, yaş, *beyan edilen* koşul, piyasa snapshot'ları. Beklenen değerler (E[maliyet], E[satış]) model **çıktısı/prior** olarak girer, gözlem olarak değil.
- İki aşamalı fiyatlandırma gerçekçidir: **T0 ön-teklif** (aralık) → **T1 kesin teklif** (inspeksiyon sonrası). Sektör zaten böyle çalışır — mimari buna göre kurulmalı.
- Random split yasak: aynı modelin aynı dönemdeki kayıtları train/test'e dağılırsa sızıntı olur → **zaman bazlı split** (örn. son 2 ay test) + model-ailesi bazlı grup split.
- Target-encoding/market-aggregate feature'lar "o tarihe kadarki" veriyle hesaplanmalı (point-in-time).
- SENATECH makalesindeki R²=0,99'un muhtemel açıklamalarından biri de bu tip sızıntılardır — bizim pipeline'da T4 alanları asla feature'a girmez.

## 21. MİMARİ VE ACQUISITION ENGINE — DEĞERLENDİRME

Mevcut katmanlı tasarım **doğru yönde**; düzeltmeler:

- ✅ `all features → acquisition price` tek-model yaklaşımından **kaçınmak doğru** — veri bunu desteklemiyor ve açıklanabilirlik/marj kontrolü kaybolur.
- ✅ Katmanlı formül `max_acquisition = E[satış] − E[tamir] − opex − risk − kâr` **veri-gerçekçi**: her bileşen kendi kanıt seviyesinde.
- Bileşen başına realizm:

| Bileşen | Tip | Veri durumu |
|---|---|---|
| Used market value | ML (GBM) | Bronze'da global oran-bazlı; Silver'da TR liste verisiyle gerçek model |
| Refurbished selling price | ML (GBM + kural) | TR satıcı snapshot'larıyla eğitilebilir (liste fiyatı → satış düzeltmesi) |
| Repair cost | **Lookup + hafif ML** | Samsung/Apple resmi + toptancı: baştan deterministik tablo + "ihtiyaç olasılığı" regresyonu |
| E[maliyet \| T0 koşul] | Prior/kural | ORA dağılımları + buyback grid + uzman kuralları |
| Operational cost | **Deterministik** | İşletme parametresi — veriyle öğrenilmez, girdi alınır |
| Risk buffer | **Kural/senaryo** | Likidite proxy'si (model popülerliği, satış-hızı); Gold'da gerçek days-to-sell ile kalibre |
| Required profit | **Deterministik** | İş kararı |
| Acquisition engine | Deterministik formül + senaryo bandı | "Tek sayı" değil, **güven aralıklı teklif** çıkarmalı |

- Şema düzeltmeleri: `SALES/ACQUISITION TRANSACTIONS` tablosu Bronze/Silver'da **fiili işlem değil gözlem** tutacak (ilan=event, satış=ortaklıkla). `inspection` ve `condition` tek varlıkta birleşmeli; `part_price_observation` **event-sourced** (kaynaktan, tarihten bağımsız değer yok).
- `REPAIR EVENTS` Bronze'da "gözlenen olay" değil "senaryo maliyet tablosu" olacak — adını `repair_scenario_cost` koymak daha dürüst.

## 22. SENTETİK VERİ POLİTİKASI — KRİTİK DEĞERLENDİRME

Öneri (sentetik inspeksiyon senaryosu, sahte fiyat YOK) **doğru ve gerekli**; sınırlar:

- ✅ Meşru kullanım: backend/UI geliştirme, pricing-engine birim testleri, edge-case stres testi, şema validasyonu.
- ✅ Meşru ML kullanımı (dar): gerçek dağılımlardan örneklenen sentetik inspeksiyonlar **model giriş dağılımını test etmek** için — ORA arıza olasılıkları + buyback grid koşullarıyla üretilen senaryolar "synthetic-inspection" olarak etiketlenir ve **asla target eğitimine girmez**.
- ❌ Yasak: sentetik fiyat/satış target'ıyla eğitilmiş modeli "piyasa modeli" diye sunmak; sentetik kayıtları gerçek metriklere katmak.
- Zorunlu alanlar: `is_synthetic`, `generation_method`, `source_distribution_version` — etiketleme şemanın parçası.

## 23. PROVENANCE + GÜVEN TASARIMI

Önerilen provenance şeması doğru; ekler:

- `access_method` ∈ {official_api, public_page_manual, licensed_file, partner_feed, synthetic}
- `legal_basis` ∈ {license_permits, fair_use_research, partner_agreement, n/a}
- `price_kind` ∈ {list, sold, buyback_offer, wholesale, service_fee, synthetic} — **target karışımını önleyen en kritik alan**
- Güven sınıfı önerilen taxonomy iyi; **sayısal skor yerine kategorik + kural** öneriyorum: `official_manufacturer > authorized_refurbisher/verified_transaction > major_marketplace > public_listing > academic > commercial_api > synthetic`. Kural: model eğitiminde ağırlık = sınıf (örn. sold×1.0, list×0.7, buyback_offer×0.8, synthetic×0/eğitim-dışı).

## 24. MVP VERİ STRATEJİSİ — NİHAİ ÖNERİ (bulgulara dayalı)

```
GSMArena mirror + HF spec          → DEVICE_MASTER + SPEC
Apple TR + Samsung TR resmi listeler
  + TR toptancı snapshot            → REPAIR_COST_LOOKUP (parça+işçilik)
iFixit API                         → PART_TAXONOMY + REPAIR_GUIDE meta
Open Repair Alliance + MobiFix     → DEFECT_PRIORS (marka/yıl→arıza)
Fransız indice                     → REPAIRABILITY features
Swappa /prices + eBay Insights     → GLOBAL_USED_PRIORS (oran-bazlı)
Getmobil/EasyCep/Senatech cihazsat
  + Amazon Depo (izinli/manuel)     → TR_REFURB_LISTINGS + TR_BUYBACK_GRID
Marka resmi TR fiyat sayfaları     → TR_NEW_PRICE_SNAPSHOTS
Sentetik (etiketli)                → INSPECTION_SCENARIOS (target'siz, test)
```

**MVP çıktısı**: "Bu cihazın TR'de yenilenmiş liste değeri ≈ X TL (güven bandı), beklenen tamir maliyeti Y–Z TL, önerilen maksimum alış fiyatı aralığı A–B TL" — nokta tahmin değil **aralık + açıklama**.

## 25. ÖNCELİK SINIFLANDIRMASI

**P0 (olmazsa MVP anlamsız):**
1. GSMArena/spec device master
2. Apple TR + Samsung TR resmi tamir fiyat tablolarının yapılandırılması
3. Getmobil + EasyCep + SENATECH cihazsat + Amazon Depo'dan **izinli küçük-ölçekli** TR refurb liste + buyback grid örneklemesi (yazılı izin talebi gönderilmeli)
4. Open Repair Alliance indirmesi → arıza prior'ları
5. Provenance/price_kind/is_synthetic alanlı şema

**P1 (kaliteyi belirgin artırır):**
6. eBay Marketplace Insights başvurusu (global sold prior)
7. Swappa /prices periyodik snapshot
8. TR parça toptancı fiyat gözlemleri (izin kontrollü)
9. SHPhoneBench benchmark incelemesi (defekt taksonomisi + transfer deneyi)
10. Yeni-fiyat snapshot pipeline'ı başlangıcı
11. Pil-kademesi buyback grid deneyi (Δfiyat/pil)

**P2 (sonradan):**
12. YÜBİS karekod doğrulama entegrasyonu
13. Cashify/Counterpoint raporlarından pazar prior'ları
14. ReCell/akademik setlerle çapraz-doğrulama deneyleri
15. gsmExchange toptan referansı

## 26. NİHAİ DÜRÜST DEĞERLENDİRME

**1) Bu proje bugün yasal verilerle gerçekçi şekilde yapılabilir mi?**
Evet — ama **"değerleme + maliyet-muhasebesi motoru"** olarak, "tam öğrenilmiş acquisition modeli" olarak değil. Bronze→Silver yolu tamamen yasal kaynaklarla kurulabilir ve işe yarar bir karar-destek aracı çıkar.

**2) Şirket verisi olmadan ne yapılabilir?**
- Cihaz kimliği + spec + TR yeni fiyat + resmi tamir/parça maliyeti → sağlam **maliyet tarafı**
- Refurb satıcı liste fiyatları → **liste-değeri modeli** (satış değil!)
- Buyback formlarından grid örnekleme → **teklif taklidi modeli** (gerçek işlem değil!)
- ORA + iFixit + indice → **arıza/tamir-edilebilirlik prior'ları**
- Formül tabanlı, açıklanabilir, aralık çıkaran acquisition engine

**3) Şirket verisi olmadan inandırıcı yapılamayacaklar:**
- Gerçek satış fiyatı (listede duran ≠ satılan)
- Gerçek alış fiyatı kalibrasyonu (teklif ≠ kabul edilen işlem)
- days_to_sell / likidite — hiçbir public kaynakta yok
- Cihaz-bazlı parça-değişim geçmişi ve refurb maliyet gerçekleri
- Marj/kârlılık geri-testi (satış sonucu olmadan imkânsız)
- "Modelimiz piyasayı %X doğrulukla tahmin ediyor" iddiası — satış verisi yoksa bu iddia **yapılamaz**

**4) En büyük kalite sıçraması hangi ortaklıktan gelir?**
**Bir yenileme merkezi/pazar yeri ortaklığı** — öncelik sırası: **Getmobil** (en büyük hacim, API altyapısı zaten var, yeni fonlama sonrası büyüme döneminde) > **SENATECH** (akademik işbirliği kültürü kanıtlanmış, 140-özellikli iç veri iddiası) > **EasyCep** (yetkili merkez, büyük operasyon) > **KVK/Mobilfon/Ouno** (servis-ağırlıklı, maliyet verisi zengin). İstenecek minimum değerli alt-küme: `model, storage, T1 inspeksiyon özeti (battery_health, defekt listesi), parça_değişimleri + maliyetleri, T3 ilan fiyatı, T4 satış fiyatı+tarihi` — bu 6 alan bile Silver'ı Gold'a yaklaştırır.

**Stratejik öneri**: Bronze/Silver sistemi **ortaklık teklifi olarak tasarla** — "elinizdeki veriyi zenginleştiren değerleme motoru" sunumu, veri paylaşımını şirketin çıkarına çevirir.

---
---

# BÖLÜM III — MVP DATASET SEÇİMİ (NİHAİ KARAR)

Bu bölüm kaynak envanterini kapatıp **hangi datasetlerin gerçekten implementasyona gireceğine** karar verir. Pozisyonlama: "Getmobil/EasyCep'in gerçek alış fiyatını verileri olmadan üretebiliriz" iddiası **yapılmayacak**. İddia: "yasal gerçek veriyle inandırıcı bir değerleme + alış-karar motoru kurulabilir; şirket verisi aynı mimariyi güçlendirir."

## 27. KISA LİSTE — EN GÜÇLÜ 5 ADAY

| Dataset | Real? | Years | Records | Price Type | Model Name | Condition | Battery | Date | License | Primary Use |
|---|---|---|---:|---|---|---|---|---|---|---|
| **mizan121 used-phone** | Gerçeğe yakın* | ~2023-24 | ~2.000 | Resale listing INR | ✅ | ✅ 4-kademe | ✅ % | Kısmen | Kaggle (belirsiz) | **Koşul/batarya→fiyat ilişki öğrenme** |
| **ReCell / ahsan81** | Gerçek (normalize) | 2021 | 3.454 | Normalize used+new | ❌ sadece brand | ❌ (days_used) | ❌ | 2021 | **CC0** | **Depreciation-oran yapısı + baseline** |
| **SHPhoneBench** | Gerçek | 2024–26 | 15K etiketli (73K korpus) | DP'li liste fiyatı CNY | ✅ | ✅ 5-kademe + 18 defekt | ❓manifest | ✅ | Açık (koşullar kontrol) | **Defekt/grade taksonomisi + transfer deneyi** |
| **2026 TR gözlemleri (kendi topladığımız)** | Gerçek | 2026 | hedef ~500–2.000 | Liste fiyatı TRY + buyback teklifi | ✅ | ✅ satıcı derecesi | Kısmi (Getmobil formu) | ✅ | İzinli gözlem | **TR kalibrasyon katmanı — asıl target** |
| ISTEK iPhone 542 | Gerçek ilan | ~2022 | 542 | Listing (IDR) | ✅ | Kısmi | ❌ (Face ID/TrueTone var) | ✅ | Akademik | Feature-etki referansı (eğitim seti değil) |

\* mizan121 provenance'ı bulanık (Google Drive'dan Kaggle'a) — satırlar gerçek Hint ikinci-el ilanına benziyor (gerçek model adları, tutarlı INR fiyatları) ama doğrulanabilir kaynak yok. **Riskli**: eğitime girecekse "unverified-real" olarak etiketlenir ve hassasiyet analiziyle (onunla/onsuz) raporlanır.

**Elenenler**: Zenodo 17702209 ("Predicting the Price of Old Mobile Phones") — **kayıt kaldırılmış/erişilemez (HTTP 410)**, kullanılamaz. sharmajicoder 1M ve KumarXAI 3K — sentetik, eğitim target'ı değil. SENATECH/AKILLICIHAZ — erişilemez. gsmExchange — lot/"Negotiable" fiyat. Decluttr — kapandı.

## 28. NİHAİ SEÇİM — KİM NE İÇİN GİRİYOR

| Rol | Seçim | Gerekçe |
|---|---|---|
| **Ana yapı öğrenme (depreciation/condition ilişkisi)** | **mizan121 + ReCell** | mizan121: gerçek model adı + koşul + pil + INR fiyat — açık ekosistemde bu kombinasyona sahip tek set. ReCell: CC0, normalize fiyat → `used/new` oranı zaten hazır target; model adı yok ama marka+spec+yaş→oran yapısı öğretir |
| **TR güncel kalibrasyon** | **Kendi 2026 TR gözlem tablomuz** (Getmobil/EasyCep/Amazon Depo izinli snapshot + buyback grid) | Mutlak TRY seviyesi sadece buradan gelir; eski yabancı veriyi günümüz TL'sine kurla çevirmek YASAK |
| **Tamir maliyeti** | **Deterministik knowledge base** (Apple TR + Samsung TR resmi listeleri + TR toptancı gözlemleri) | ML değil — lookup+kural daha sağlam (§33) |
| **Arıza/defekt prior'ı** | Open Repair Alliance + MobiFix | C sınıfı istatistiksel prior — satır join'i YOK |
| **İnspeksiyon şeması referansı** | SHPhoneBench + iFixit taksonomisi | Defekt kategorileri, grade yapısı; fiyatları DP'li olduğu için target olarak değil |
| **Hariç tutulanlar** | Sentetik setler (sadece test), Sahibinden/Letgo (dışarıda), akademik makro raporlar | — |

**Tek cümlelik karar**: *Eski zengin veri göreli yapıyı öğretir, güncel TR gözlemi mutlak fiyatı verir — ikisi satır-seviyesinde join'lenmez, iki katmanlı modelle birleşir.*

## 29. "ESKİ AMA İYİ DATASET" STRATEJİSİ — İSTATİSTİKSEL OLARAK SAVUNULABİLİR Mİ?

**Evet, şu koşulla**: mutlak fiyat değil **oran/oran-yapısı** öğrenilirse.

Savunulabilir target'lar:
- `ratio = used_price / new_price_same_model_same_period` — aynı modelin aynı dönemdeki iki fiyatının oranı; enflasyon ve kur **pay ve paydada birlikte** bulunduğu için oran büyük ölçüde parasal etkiden arınır
- `depreciation_pct = 1 − ratio`
- Koşul/pil katsayıları: `ln(price) ~ β·condition + γ·battery_health + ...` → β,γ katsayıları para biriminden bağımsız yorumlanır

Savunulamaz olanlar:
- ❌ 2021 USD/INR fiyatı × güncel kur = "2026 TRY fiyat" — yasak
- ❌ Eski mutlak fiyatlarla eğitilip TR'ye doğrudan tahmin
- ⚠️ Enflasyon düzeltmesi (CPI deflator) ancak **aynı ülke-içi** zaman kaydırmada anlamlı; ülkeler arası transferde kur+enflasyon+vergi+ithalat-rejimi farkı kalıntı kalır

**Metodoloji — iki katmanlı model:**

```
KATMAN A (yapı — eski zengin veri):
  ratio_hat = f(brand_segment, storage, device_age, condition, battery_health)
  → f, mizan121 + ReCell üzerinde öğrenilir
  → zaman/model-grubu bazlı holdout ile doğrulanır

KATMAN B (seviye — 2026 TR gözlemleri):
  refurb_price_TR(model, grade, t)  ← gerçek snapshot'lar
  Yeni fiyat anchor'ı: new_price_TR(model, t)

BİRLEŞTİRME (satır join YOK, model-seviyesi kalibrasyon):
  tahmin = new_price_TR(model,t) × ratio_hat(features) × κ(segment)
  κ = TR gözlemlerinde medyan(gözlenen_ratio / öngörülen_ratio),
      marka×segment seviyesinde, gözlem sayısına göre shrinkage'lı
  κ için yeterli gözlem yoksa κ=1 ve geniş güven aralığı raporlanır
```

Bu tasarım sahte satır join'i yapmaz: eski veri hiçbir TR gözlemine satır olarak eklenmez; yalnızca fonksiyon f ve düzeltme faktörü κ üzerinden etki eder. κ hesaplanırken hiyerarşik shrinkage (marka→segment→global ortalama) küçük örneklemi korur.

## 30. JOIN SINIFLANDIRMASI (A/B/C/D)

| Kaynak | Hedef tabloyla ilişki | Sınıf | Anahtar/kural |
|---|---|---|---|
| GSMArena/HF spec | DEVICE_MASTER | **A — EXACT** | normalized model_code (brand+model+storage) |
| TR yeni fiyat snapshot | fiyat gözlemi | **B — ENRICHMENT** | device_id + en yakın observation tarihi |
| Apple/Samsung TR tamir listesi | REPAIR_KB | **B — ENRICHMENT** | device_id → model bazlı servis ücreti |
| TR toptancı parça fiyatları | REPAIR_KB | **B — ENRICHMENT** | device_id + part_type (+kalite) |
| iFixit taksonomi/zorluk | REPAIR_KB meta | **B** | part_type mapping |
| Fransız indice | DEVICE_MASTER | **B** | model eşleşmesi (FR katalog↔TR model adı doğrulanmalı) |
| mizan121 | yapı öğrenme | **C — STATISTICAL PRIOR** | satır join yok; katsayı/dağılım aktarımı |
| ReCell | yapı öğrenme | **C** | aynı |
| Open Repair Alliance | arıza prior'ı | **C** | marka×yaş→arıza olasılığı |
| SHPhoneBench | defekt/grade referansı | **C** | taksonomi + ayrı deney; TR satırlarına join YOK |
| Swappa/eBay | global oran prior'ı | **C** | depreciation eğrisi doğrulaması |
| SENATECH 36K | erişilemez | **D — NOT COMPATIBLE (şimdilik)** | — |
| Sentetik setler | test/stress | **D (eğitime girmez)** | is_synthetic etiketi, ayrı dünya |
| Sahibinden/Letgo | — | **D — dışarıda** | kullanıcı kararı |

## 31. ZAMAN NORMALİZASYONU — FİYAT GÖZLEM ŞEMASI

Her fiyat kaydı event-sourced:

```
price_observation_id | device_id | price | currency | country
observed_at | retrieved_at | source_id | price_kind
  ∈ {new_retail, refurb_listing, used_listing, buyback_offer,
     sold_transaction, service_fee, part_price}
confidence_class ∈ {official_manufacturer, authorized_refurbisher,
  major_marketplace, public_listing, academic, commercial_api, synthetic}
```

Türetilmiş feature'lar (hesaplanırken **observed_at** bazlı):
- `device_age_months = observed_at − release_date`
- `price_to_new_ratio` — yalnız aynı dönem/ülke new_price ile
- `months_since_release` — age ile aynı, birini tut
- **YAPMA**: FX-normalize ve CPI-deflate'i çapraz-ülke join'de kullanma; sadece aynı-ülke içi zaman karşılaştırmasında yardımcı feature olabilir

TR'de ekstra dikkat: yüksek enflasyon → **fiyat gözlemleri 90 günden eskiyse "stale" bayrağı**; eğitimde recency ağırlığı önerilir (örn. yarı-ömrü 90 gün olan üstel ağırlık).

## 32. KANONİK MVP EĞİTİM TABLOSU (minimum)

```
observation_id
device_id                      → DEVICE_MASTER (brand, model, storage, ram, release_date, segment)
condition_grade                → kanonik {A/like-new, B/good, C/fair, D/poor} (satıcı dereceleri map'lenir)
battery_health_pct             → ÇOĞUNLUKLA NaN — üretme! varsa gerçekten var
device_age_months
new_price_try_at_obs           → aynı modelin o tarihteki TR sıfır fiyatı
market_price_try               → TARGET (refurb_listing; price_kind ayrı tutulur)
price_to_new_ratio             → türetilmiş yardımcı target/feature
country, currency, observed_at, source, price_kind, confidence_class, is_synthetic
```

**Bilerek küçük tutuldu.** Ekran boyutu, kamera MP, ağırlık, chipset gibi spec kolonları eğitim tablosuna girmez — device_id üzerinden zaten model kimliği taşınıyor; spec'ler ancak model-bazlı genelleme (cold-start: hiç görülmemiş model) için gerekirse Katman A'da kullanılır.

| Feature | Sınıf | Not |
|---|---|---|
| device_id (brand/model/storage) | **P0** | Fiyatın ana belirleyicisi |
| device_age_months | **P0** | Depreciation sürücüsü |
| condition_grade | **P0** | Var olan tek bireysel-koşul sinyali |
| new_price_at_obs | **P0** | Oran target'ının paydası |
| observed_at | **P0** | Zaman bölmesi + staleness |
| price_to_new_ratio | **P0 (target formu)** | — |
| battery_health | P1 | Seyrek; imputation yok, varsa kullan |
| market popülerlik proxy'si | P1 | likidite sinyali (liste sayısı/model) |
| spec kolonları (ekran, kamera...) | P1→DROP çoğu | sadece cold-start genellemede |
| repair_history, defekt kodları, parts_replaced | **P2 — şirket verisi** | Public'te satır-seviyesi yok; uydurma YASAK |
| days_to_sell, sale_price | **P2** | Ortaklıkla gelir |
| seller_city, seller_type, garanti-ay | P1 | mizan121'de var, TR'de seyrek |
| days_used | DROP | Türkiye gözlemlerinde ölçülemez → yerine device_age |
| watermark: is_synthetic | — | Her zaman 0 (eğitim tablosunda) |

## 33. TAMİR MALİYETİ — AYRI VERİ ÜRÜNÜ (ML DEĞİL)

**Karar: lookup + kural tabanı, ML yok.** Gerekçe: gerçek TR maliyet gözlemi deterministik kaynaklarda zaten var (Apple TR, Samsung TR resmi listeleri); eğitilecek satır verisi yok — zayıf veriyle ML kurmak deterministik tablodan daha kötü sonuç verir.

```
REPAIR_KB:
device_variant_id | repair_type ∈ {screen, battery, rear_glass,
  rear_camera, charge_port, speaker, mic, biometric, mainboard, frame}
part_quality ∈ {original_service, oem, aftermarket_premium, aftermarket, used}
part_price | labor_cost | total_cost | currency=TRY | country=TR
source | observed_at | confidence_class
```

Üç senaryo katmanı: (1) OEM servis (Apple/Samsung resmi), (2) premium aftermarket (toptancı+ustalık işçilik tahmini), (3) ekonomi (en düşük uyumlu parça). İşçilik: `servis_ücreti − parça_fiyatı ≈ üst sınır`; iFixit zorluk skoru bağıl çarpan olarak.

Engine bağlantısı: `E[tamir | T0 koşul] = Σ_i P(arıza_i | beyan koşul, ORA prior'ı) × total_cost_i` — ORA olasılıkları prior, REPAIR_KB maliyetleri kesin.

## 34. MVP MODEL MİMARİSİ — ONAY

```
MODEL 1 — Piyasa Değeri (Katman A+B):
  Girdi: device_id, age, condition, battery(varsa), new_price_TR(t)
  Çıktı: E[refurb piyasa değeri] + güven aralığı (quantile GBM veya aralık tahmini)

COMPONENT 2 — Tamir Maliyeti:
  Deterministik REPAIR_KB lookup + arıza-olasılık prior'ı → E[maliyet] aralığı

COMPONENT 3 — Acquisition Engine (deterministik):
  max_acquisition = E[satış] − E[tamir] − opex − risk_buffer − required_profit
  Çıktı: nokta değil ARALIK + bileşen dökümü ("neden bu fiyat" raporu)
```

**Değerlendirme**: Bu tasarım MVP için doğru — acquisition price'ı doğrudan ML target'ı yapmak veri olmadan imkânsız ve gereksiz; deterministik motor her bileşenin kanıt seviyesini görünür kılar ve şirket verisi geldiğinde aynı arabirimle yükseltilir.

## 35. DÜRÜST DEĞERLENDİRME PLANI

- **Bölme**: kronolojik — son ~60-90 günün TR gözlemleri test; ayrıca **unseen model-family** testi (örn. bir marka serisi tamamen dışarıda) → genelleme ölçümü.
- **Sızıntı kontrolü**: aynı cihazın tekrarlanan snapshot'ları train ve teste dağılmaz (grup bazlı bölme); point-in-time feature'lar; target-encoding yalnız geçmiş veriyle.
- **Metrikler**: TRY cinsinden **MAE** (birincil), **sMAPE** (ölçek-bağımsız, MAPE'in sıfır-sorunu olmadan), **R²** yalnız referans. Kategorik rapor: segment×marka bazında hata.
- **"İyi"nin kanıtlı tanımı**: rastgele hedef yerine — (a) naif baseline'ı (aynı modelin son medyan fiyatı) anlamlı geçmek, (b) marka×yaş sabitli oran modelini (κ'sız Katman A) geçmek, (c) %90 tahmin aralığı kapsaması ~%90'a yakın olmalı. Somut sayı hedefi ancak baseline ölçülünce konur.
- **Dürüstlük kuralı**: raporda "liste fiyatı tahmini" denir; "satış fiyatı" denmez. Buyback tarafında "önerilen teklif" denir; "gerçek işlem fiyatı" denmez.

## 36. ŞİRKET-VERİSİ YÜKSELTME YOLU — DEMONSTRASYON HARİTASI

| Şirket alanı | Güçlenen bileşen | Mekanizma |
|---|---|---|
| `purchase_price` (T0 işlemi) | Engine kalibrasyonu | Teklif≠işlem sapması ölçülür; risk_buffer gerçek veriyle kalibre |
| `battery_health` (T1) | Model 1 | Seyrek P1 feature → yoğun gerçek feature; koşul-pil etkileşimi öğrenilir |
| `defect_codes`, fonksiyon testleri (T1) | Maliyet + risk | ORA prior'ı → gerçek P(arıza\|model,yaş) posterior; maliyet belirsizliği daralır |
| `parts_replaced`, `part_cost`, `labor_cost` (T2) | REPAIR_KB | Lookup → gerçek dağılımlı maliyet modeli; üç senaryo → gözlenen gerçek |
| `final_grade` (T2) | Model 1 label'ı | Satıcı-derecesi map'leme tahmini → gerçek grade; grade→fiyat katsayısı keskinleşir |
| `list_price`+`sale_price`+`sale_date` (T3-T4) | Model 1 + yeni model | **Liste→satış iskontosu ve days_to_sell öğrenilir** — şu an var olmayan iki model açılır |
| `returns`, `warranty_claims` | risk_buffer | Kural → öğrenilmiş risk skoru |

**Demo'nun göstereceği**: aynı pipeline'ın public-veri konfigürasyonu çalışır; her şirket alanının hangi bileşene takılacağı şema-seviyesinde hazır. **Yapılmayacak**: sahte şirket verisiyle "doğruluk %X arttı" gösterisi. Gösterilebilir deney (etiketli): SHPhoneBench'in gerçek defekt+grade verisiyle "inspection feature'ları varsa koşul tahmini ne kadar iyileşir" — **external proxy** olarak sunulur, TR sonucu olarak değil.

## 37. NİHAİ CEVAPLAR

1. **Birincil eğitim dataseti?** Tek bir "primary" yok — tasarım gereği iki katman: yapı öğrenimi **mizan121+ReCell**, mutlak seviye **kendi 2026 TR gözlem tablomuz**. TR tablosu target'tır; eski setler yalnız yapı sağlar.
2. **Eski zengin mi, yeni seyrek mi?** İkisi de — ama farklı rollerde. Eski zengin veri ilişkileri (oran/katsayı), yeni seyrek veri seviyeyi verir. Sıfır TR gözlemiyle "TR fiyat modeli" kurulamaz; sıfır yapı verisiyle de seyrek TR verisi tek başına ML için ince kalır.
3. **Nasıl birleşir?** §29: oran-target öğrenimi + marka×segment shrinkage'lı κ kalibrasyonu. Satır join YOK.
4. **Önceki araştırmadan atılacaklar**: Zenodo 17702209 (erişilemez), sentetik setler (eğitimden), SENATECH (erişilemez — ortaklık hedefi olarak sakla), gsmExchange, Decluttr, Keepa/ücretli servisler, Sahibinden/Letgo.
5. **En küçük inandırıcı mimari**: DEVICE_MASTER (spec mirror) + PRICE_OBS (TR 2026 snapshot, ~500+ kayıt hedefi) + REPAIR_KB (Apple/Samsung TR + toptancı) + DEFECT_PRIORS (ORA) + yapı-modeli (mizan121+ReCell). Bu 5 parça ile aralık-çıkışlı acquisition engine kurulur.
6. **Kural kalacaklar**: tamir maliyeti (lookup), opex/kâr/risk (iş parametresi), grade map'leme, κ kalibrasyonu, staleness kuralları.
7. **Şirket verisine ertelenecekler**: satış-fiyat modeli, days_to_sell, gerçek alış-fiyatı kalibrasyonu, parça-değişim geçmişi feature'ları, iade/garanti riski.
8. **Demo mesajı**: "Public veriyle: TRY aralıklı piyasa değeri + maliyet-muhasebesiyle gerekçelendirilmiş maksimum alış fiyatı. Şirket verisi takıldığında: liste→satış, teklif→işlem ve inspeksiyon→maliyet belirsizliklerinin üçü de öğrenilmiş olur — mimari bunun için hazır."
