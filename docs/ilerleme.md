# İlerleme

Son güncelleme: 30 Ekim 2026

| Faz | Durum | Bitiş | Kanıt |
|---|---|---|---|
| 1. Kurulum | ✅ Bitti | 24 Ekim 2026 | `3c90537` |
| 2. Veri toplama | ✅ Bitti | 24 Ekim 2026 | `e5a9619`, tag `v0.1-sample` |
| 3. Etiketleme kuralları | ✅ Bitti (sürüm 2) | 29 Ekim 2026 | `docs/etiketleme_kurallari.md` |
| 4. 40 ürün gold etiketleme | ✅ Bitti | 29 Ekim 2026 | `726c41d`, tag `v0.1-data` |
| 5. 3 ajan | ✅ Bitti (prompt'lar donduruldu) | 30 Ekim 2026 | `7d5646a` + bu commit; `outputs/runs/index.csv` (dev deneme 1–3) |
| **6. Baseline + 5 dev ürünle deneme** | 🔧 **Sıradaki** | — | tag `v0.2-agents` |
| 7. 200 ürün tam koşu | Bekliyor | — | — |
| 8. Değerlendirme | Bekliyor | — | tag `v0.3-results` |
| 9. Hata analizi + alt sorular | Bekliyor | — | — |
| 10. Tez yazımı | Bekliyor | — | tag `v1.0-final` |

## Biten fazların özeti

**Faz 1 — Kurulum:** `.venv`, bağımlılıklar, GitHub bağlantısı.

**Faz 2 — Veri toplama:** Amazon Reviews 2023, Clothing_Shoes_and_Jewelry; yorum ve meta dosyalarının tamamı okundu (66 milyon yorum, 7,2 milyon ürün). Kurallar: ≥10 yorum, ≥3 negatif yorum, kapsam filtresi (giyim, ayakkabı, bot, spor giyim; takı/saat/çanta/aksesuar/kostüm hariç), dolu sayfa, tekrarlı yorum ayıklama. 204.789 uygun ürün arasından seed = 42 ile 200 ürün + 10 yedek. Rapor: `reports/orneklem_raporu.md`.

**Faz 3–4 — Etiketleme:**
- İlk etiketleme yapıldı ve ayrı commit olarak saklandı (`4c6896a`).
- Tutarlılık kontrolünde iki belirsizlik bulundu: "Kalite" tipinin Malzeme/Dayanıklılık ile örtüşmesi (aynı yorumların iki tipe sayılması) ve "açık iddia" tanımı.
- Kurallar sürüm 2: tek konu kuralı, tip tanımları ve öncelik, "somut iddia" şartı, kullanılmış ürün gönderimi = satıcı hatası.
- 40 ürün yeni kurallarla yeniden gözden geçirildi: 29 üründe 91 alan değişti (`data/gold/gozden_gecirme_degisiklikler.csv`).
- Altın standart (`data/gold/gold_40.csv`): 36 gap var / 4 yok; 62 tip etiketi (Beden/Kalıp 24, Malzeme 13, Dayanıklılık 13, Renk 5, Kalite 5, Görsel 2, Eksik Bilgi 0); seviye 8 Yüksek / 28 Orta / 4 Yok. Hiçbir gold ürün "veri uygun değil" çıkmadı, yedek kullanılmadı.
- Metrik kararları `docs/kapsam.md` §6'ya işlendi (ana metrik gap tipi micro-F1, bootstrap güven aralığı).

## Faz 5 — 3 ajan (bitti, 30 Ekim 2026)

**Model:** `gpt-4o-mini-2024-07-18`; erişim (model listesi) ve fiyat ($0,15 / $0,60 per 1M token) 30 Ekim 2026'da doğrulandı, `config.yaml` > `model_verified: true`.

**Dev denemeleri** (her biri 5 ürün; kayıt `outputs/runs/dev/`, özet `outputs/runs/index.csv`):

| Koşu | Değişiklik | Tekrar gereken | Tutarsız | Eşdeğer maliyet |
|---|---|---|---|---|
| deneme1 (geriye dönük arşiv) | İlk prompt'lar | 4/5 | 2/5 | $0,0086 |
| deneme2 | Yapılandırılmış öneri (tip, sayfa iddiası, müşteri deneyimi, işlem, düzeltme); yeni tutarlılık kontrolleri (iddia yokken Yüksek, alıntı doğruluğu, öneri–tip eşleşmesi); Ajan 1/2 netleştirmeleri | 3/5 | 1/5 | $0,0097 |
| deneme3 | Ajan 2 Eksik Bilgi tanımı, Ajan 3 "son kontrol" listesi ve öneri içeriği, Ajan 1 somut = doğrulanabilir | 2/5 | 1/5 | $0,0092 |
| dogrulama-nihai-prompt | Geliştirme denemesi değil: şablonlar değişmedi, kurallara "aynı sorun" tanımı eklendi; sonrasında hiçbir şey değiştirilmedi | 1/5 | 0/5 | $0,0085 |

**Dondurma:** Kapsam §6 "Prompt geliştirme sınırı" (her sistem en fazla 3 dev koşusu) gereği 3 ajanlı sistemin prompt'ları deneme3 haliyle donduruldu. Seçim, önceden belirlenen kurala ve süreç ölçülerine (tekrar/tutarsız) dayanır; ürün bazında "en iyi" deneme seçilmedi (dev ürünlerinin etiketi yok).

**Dev'de gözlenen ve düzeltilmeden bırakılan hatalar** (hata analizi ve tezde bulgu olarak): Ajan 3'ün 2 yorumlu bir tipi atlaması (B08V4QYTR6, Kalite); tekrar sorulunca çelişkili cevap (B0747LCQB1: gap var ama tip yok → tutarsız); somut iddiayla doğrudan çelişmeyen şikayete Yüksek verme (B08V4QYTR6, B06XGZMBL2); öneride şikayetlerde geçmeyen ayrıntı; Ajan 1'in materyal içeren ifadeyi Görsel'e koyması (B000XRJK5Q).

**Kayıt altyapısı:** `src/runs.py` (her koşu ayrı klasör: manifest, prompt'lar, ürün çıktıları, `sonuclar.csv`, `olcumler.json`; `index.csv`); `llm.py` çağrı süresi ve önbellekli çağrılar için eşdeğer maliyet. Değerlendirme kaydının yapısı kapsam §6'da tanımlı (Faz 8).

**Testler:** `tests/test_faz5.py` (27) + `tests/test_bariyer.py` (9) = 36 API'siz test geçti.

**İlk hazırlık (29 Ekim 2026):** `src/schemas.py`, `src/llm.py`, `src/agents.py`, `src/pipeline.py`, `prompts/*.md`; önbellek, maliyet logu, tutarlılık kontrolü (1 tekrar, sonra "tutarsız" işareti), girdi bütünlüğü kontrolü ve gold kilidi (kullanıcı kilidi + git kontrolleri) çalışıyor.

**Gold bariyeri (29 Ekim 2026):** izin kuralları + tüm araçlar için PreToolUse hook'u; ayrıntı CLAUDE.md "Gold bariyeri" bölümünde. Gerçek oturumda denendi: yasak kalıp içeren zararsız komut engellendi, dev işleri geçti. Gold sızıntı denetimi için `src/audit_gold.py` (kullanıcı çalıştırır).

## Sıradaki: Faz 6 — Baseline

1. Tek prompt'luk baseline: aynı girdi (`page_text` + `reviews_text`), aynı kural bölümleri, aynı sonuç şeması, aynı tutarlılık kontrolü ve tek tekrar hakkı (alıntı kaynağı sayfa metni); kayıt `src/runs.py` ile.
2. Baseline için de en fazla 3 dev koşusu, sonra dondurma → tag `v0.2-agents`.
3. Değerlendirme + bootstrap script'i (sahte etiketlerle test; gold okunmaz).
4. Kullanıcı: Faz 7 öncesi denetim script'ini kendi terminalinde çalıştırır (beklenen: hiç iz yok).

**Kapanan kararlar (30 Ekim 2026):** fiyat/detay girdi farkı belgelendi (`docs/yontem.md` §3, kapsam sınırlılıkları); "markası" kapsamdan çıkarıldı; tutarsız kararlar olduğu gibi değerlendirilir, sayısı raporlanır; seviye isabeti çoğunluk referansı (%70) ve 3 seviye macro-F1 ile verilir; "aynı sorun" (yön farkı ayrı sorundur) kurallara eklendi; Alt Soru 2 (Mann-Whitney U) ve Alt Soru 3 (kalan kümeden 20 ürün, kör puanlama, rubrik) tanımlandı. Kapsam teknik ayrıntılardan arındırıldı, ayrıntılar `docs/yontem.md`'ye taşındı.

## Takvim (teslim: 8 Kasım 2026)

| Tarih | İş |
|---|---|
| 31 Ekim 2026 | Faz 6 (baseline + 3 dev koşusu, değerlendirme script'i) ve Faz 7 (200 ürün koşusu; kullanıcı kilidi ve denetim) |
| 1 Kasım 2026 | Faz 8 (değerlendirme, bootstrap) ve Faz 9 (hata analizi, Alt Soru 2 ve 3) |
| 2–4 Kasım 2026 | Tez yazımı |
| 5 Kasım 2026 | Taslak danışmana |
| 8 Kasım 2026 | Teslim |

### Faz 5 planı (ilk hali)
- Ajan 1 (Expectation), Ajan 2 (Review Mining), Ajan 3 (Gap + Fix); JSON şemaları; OpenAI SDK, `temperature = 0`, önbellek, ara çıktıların `outputs/` altına kaydı.
- Ajan 2'nin ilgisiz saydığı şikayetler etiketleme kurallarındaki "Sayılmayanlar" ile aynı olmalı.
- Sistemlere yorumların tam metni verilir.
- Deneme SADECE 5 dev ürünle (gold'a dokunulmaz).
- Gerekli: `.env` içinde `OPENAI_API_KEY`.

## Karar kaydı

| Tarih | Olay | Etki | Alınan önlem |
|---|---|---|---|
| 29 Ekim 2026 | Faz 5 geliştirmesi sırasında asistan, gold kilidinin çalıştığını görmek için `pipeline.py --split gold --estimate` komutunu çalıştırdı. Komut maliyet tahmini için 40 gold ürünün sayfa ve yorum METNİNİ okudu (`products_200.jsonl` üzerinden, uzunluk hesabı için). | LLM çağrısı yapılmadı, hiçbir çıktı/dosya yazılmadı, gold etiketlerine (`data/gold/`) erişilmedi. Prompt'lar bu olaydan sonra gold içeriğine göre değiştirilmedi. | Gold bariyeri kuruldu: `.claude/settings.json` (Read/Edit deny) + PreToolUse hook `.claude/hooks/gold_guard.py`; `--split gold` için kullanıcı kilidi (`.gold_unlock`); test script'leri gold içeriği okumayacak şekilde değiştirildi; Faz 7 öncesi `src/audit_gold.py` denetimi kullanıcı tarafından çalıştırılacak. |
| 30 Ekim 2026 | Tutarlılık taramasında asistan `reports/orneklem_raporu.md` içinde grep yaptı; raporun ürün tablosu nedeniyle çıktıda 2 gold ürünün ASIN'i ve başlığı göründü. | Etiket görülmedi; bu bilgi hiçbir prompt'ta veya kararda kullanılmadı. | Kullanıcı ürün başlıklı tabloyu rapordan çıkardı, örneklem listesini hook'un koruduğu klasöre taşıdı (gold kilidinin tag karşılaştırması dışında), `.ignore` ile arama araçlarından gizledi. |
| 30 Ekim 2026 | 3 ajanlı sistemin prompt'ları 3 dev koşusundan sonra donduruldu. | Bundan sonra 3 ajanlı sistemin prompt'ları değiştirilmez. | Kapsam §6 "Prompt geliştirme sınırı"; aynı sınır baseline için geçerli. |

## Açık notlar
- Az örnekli tipler (Görsel 2, Renk 5, Kalite 5) ve "gap yok" sınıfının 4 ürüne dayanması sınırlılıklarda belirtildi.
- `kapsam.md` §4 "Zaman tutarlılığı": yorum tarih aralığı örneklem raporunda var (2008-06-17 – 2023-09-02); tez metnine taşınacak.
- `kapsam.md` §10: Gold kümesinde birleştirilmiş (başka ürüne ait yorumlu) kayıt bulunmadı; tez metninde bu bulgu belirtilecek.
