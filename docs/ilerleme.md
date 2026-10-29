# İlerleme

Son güncelleme: 29 Ekim 2026

| Faz | Durum | Bitiş | Kanıt |
|---|---|---|---|
| 1. Kurulum | ✅ Bitti | 24 Ekim 2026 | `3c90537` |
| 2. Veri toplama | ✅ Bitti | 24 Ekim 2026 | `e5a9619`, tag `v0.1-sample` |
| 3. Etiketleme kuralları | ✅ Bitti (sürüm 2) | 29 Ekim 2026 | `docs/etiketleme_kurallari.md` |
| 4. 40 ürün gold etiketleme | ✅ Bitti | 29 Ekim 2026 | `726c41d`, tag `v0.1-data` |
| **5. 3 ajan** | ⏭ **Sıradaki** | — | — |
| 6. Baseline + 5 dev ürünle deneme | Bekliyor | — | tag `v0.2-agents` |
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

## Sıradaki: Faz 5 — 3 ajan
- Ajan 1 (Expectation), Ajan 2 (Review Mining), Ajan 3 (Gap + Fix); JSON şemaları; OpenAI SDK, `temperature = 0`, önbellek, ara çıktıların `outputs/` altına kaydı.
- Ajan 2'nin ilgisiz saydığı şikayetler etiketleme kurallarındaki "Sayılmayanlar" ile aynı olmalı.
- Sistemlere yorumların tam metni verilir.
- Deneme SADECE 5 dev ürünle (gold'a dokunulmaz).
- Gerekli: `.env` içinde `OPENAI_API_KEY`.

## Açık notlar
- Az örnekli tipler (Görsel 2, Renk 5, Kalite 5) ve "gap yok" sınıfının 4 ürüne dayanması sınırlılıklarda belirtildi.
- `kapsam.md` §4 "Zaman tutarlılığı": yorum tarih aralığı örneklem raporunda var (2008-06-17 – 2023-09-02); tez metnine taşınacak.
- `kapsam.md` §10: Gold kümesinde birleştirilmiş (başka ürüne ait yorumlu) kayıt bulunmadı; tez metninde bu bulgu belirtilecek.
