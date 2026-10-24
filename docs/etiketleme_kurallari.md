# Etiketleme Kuralları (Gold Standard)

Bu kurallar 40 ürünlük test setini elle etiketlerken kullanılır ve tezin ekine girer.

## Ne okunur?
Sadece sistemin de gördüğü metin: ürün sayfası (başlık, özellikler, açıklama, detaylar, fiyat) ve negatif yorumlar (rating ≤ 2). Ürünün kendisi değerlendirilmez.

## Önce: veri uygun mu?
Her ürün için önce `veri_uygun` alanı doldurulur. Aşağıdakilerden biri varsa **Hayır** yazılır, not düşülür ve diğer alanlar boş bırakılır:
- Yorumlar sayfadaki ürünle ilgili değil (Amazon farklı ürünleri aynı `parent_asin` altında birleştirmiş; ör. kapüşonlu ürünün yorumlarında başka sweatshirt'ler anlatılıyor)
- Ürün giyim veya ayakkabı değil (kategori filtresine rağmen kaçan)
- Konu dışı yorumlar çıkarıldığında değerlendirilebilecek 2'den az yorum kalıyor

**Yedek kuralı:** `veri_uygun = Hayır` olan her gold ürünün yerine, `Yedekler` sayfasındaki **sıradaki** ürün etiketlenir (atlama yapılmaz). Sonuçta `veri_uygun = Evet` olan 40 ürün elde edilir. Kaç ürünün neden çıkarıldığı tezde veri kalitesi bulgusu olarak raporlanır.

## Sorulan soru
Sayfanın verdiği söz ile müşterilerin şikayeti arasında çelişki var mı?

## Alanlar

| Alan | Değerler | Kural |
|---|---|---|
| gap_var | Evet / Hayır | En az bir konu işaretlendiyse Evet |
| Konular (çoklu) | Beden/Kalıp, Renk, Görsel, Kalite, Malzeme, Dayanıklılık, Eksik Bilgi | Bir konu ancak **en az 2 yorum** aynı sorundan bahsediyorsa işaretlenir |
| seviye | Yok / Orta / Yüksek | Aşağıdaki tabloya göre |
| not | Serbest metin | Kararın 1 cümlelik gerekçesi |

## Seviye kuralı

| Durum | Seviye |
|---|---|
| Sayfa açıkça bir iddiada bulunmuş, yorumlar tersini söylüyor | **Yüksek** |
| Sayfa o konuda bilgi vermemiş, yorumlar şikayet ediyor | **Orta** |
| Çelişki yok | **Yok** |

Birden fazla konu varsa en yüksek seviye yazılır.

## Sayılmayanlar
- Kargo, paketleme, satıcı veya iade süreci şikayetleri
- Kişisel zevk ("beğenmedim", "bana yakışmadı")
- Tek bir yorumda geçen sorun
- Aynı yorumun kopyaları (birebir aynı olanlar script tarafından zaten ayıklanır; neredeyse aynı olanları da tek say)
- 5 kelimeden kısa yorumlar (otomatik olarak çıkarılır)

## Konu tanımları

| Konu | Örnek şikayet |
|---|---|
| Beden/Kalıp | "Çok küçük geldi", "bir beden büyük alın" |
| Renk | "Rengi fotoğraftakinden farklı" |
| Görsel | "Fotoğraftaki ürünle alakası yok" (renk dışı görünüm) |
| Kalite | "İşçilik kötü", "dikişler çarpık" |
| Malzeme | "Kumaş ince", "deri değil plastik", "su geçirmez değil" |
| Dayanıklılık | "İki yıkamada söküldü", "bir haftada koptu" |
| Eksik Bilgi | "Açıklamada yazmıyordu" (ölçü, bakım vb. bilginin hiç olmaması) |

## Örnek
**Sayfa:** "Men's leather boot. Waterproof. Non-slip sole."
**Yorumlar:** (1) "İlk yağmurda içi su doldu." (2) "Su geçirmez yazıyor ama ayaklarım ıslandı." (3) "Kargo kutusu ezik geldi."

→ gap_var = **Evet** · Malzeme = **X** · seviye = **Yüksek** · not: "Su geçirmez iddiası var, ilgili 2/2 yorum su aldığını söylüyor; kargo yorumu sayılmadı."

## Süreç kuralı
Etiketleme bitip `data/gold/etiketleme.xlsx` GitHub'a commit edilmeden LLM sistemi çalıştırılmaz. Commit tarihi, etiketlerin sistem çıktısından önce hazırlandığının kanıtıdır.
