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
| Konular (çoklu) | Beden/Kalıp, Renk, Görsel, Kalite, Malzeme, Dayanıklılık, Eksik Bilgi | Bir konu ancak **en az 2 yorum** aynı sorundan bahsediyorsa işaretlenir. Bir şikayet yalnızca **tek** konuya sayılır (aşağıdaki "Tek konu kuralı") |
| seviye | Yok / Orta / Yüksek | Aşağıdaki tabloya göre |
| not | Serbest metin | Kararın 1 cümlelik gerekçesi |

## Tek konu kuralı
Bir şikayet grubu yalnızca **tek** konuya sayılır. Ürünün birden fazla konusu olabilir, ama her konunun **kendi** en az 2 yorumu olmalıdır; aynı yorumlar iki konuyu birden desteklemek için kullanılamaz.

Bir şikayet birden fazla konuya uyuyorsa **en spesifik** olana gider: Malzeme ve Dayanıklılık, Kalite'den önce gelir. Kalite yalnızca aşağıdaki tanımdaki durumlar için kullanılır.

## Seviye kuralı

| Durum | Seviye |
|---|---|
| Sayfada ürüne özgü **somut bir iddia** var ve yorumlar bu iddiayla **doğrudan** çelişiyor | **Yüksek** |
| Sayfa o konuda bilgi vermemiş **veya** yalnızca genel pazarlama dili kullanmış; yorumlar şikayet ediyor | **Orta** |
| Çelişki yok | **Yok** |

Birden fazla konu varsa en yüksek seviye yazılır.

**Somut iddia:** Ürüne özgü, doğrulanabilir bir bilgi. Örnekler: ölçü/numara aralığı ("XXL fits sizes 15-18"), kalıp uyarısı ("runs 2 sizes smaller"), materyal ("100% leather", "fleece"), işlev ("waterproof", "memory foam"), renk adı.

**Somut iddia sayılmayanlar** (en fazla **Orta**): Genel pazarlama dili ("high quality", "premium", "perfect fit", "ultimate comfort") ve markanın her üründe kullandığı standart metin.

**Renk:** Sayfada renk adı var ve şikayet "soluk/donuk" ise **Orta**; başka bir renk geldiyse **Yüksek**.

## Sayılmayanlar
- Kargo, paketleme, satıcı veya iade süreci şikayetleri
- Kullanılmış / iade edilmiş ürün gönderimi (satıcı hatası). Buna karşılık hasarlı, delikli, lekeli veya defolu **yeni** ürün gelmesi **Kalite**'dir
- Kişisel zevk ("beğenmedim", "bana yakışmadı")
- Tek bir yorumda geçen sorun
- Aynı yorumun kopyaları (birebir aynı olanlar script tarafından zaten ayıklanır; neredeyse aynı olanları da tek say)
- 5 kelimeden kısa yorumlar (otomatik olarak çıkarılır)

## Konu tanımları

| Konu | Tanım | Örnek şikayet |
|---|---|---|
| Beden/Kalıp | Ölçü, kalıp, oturuş | "Çok küçük geldi", "bir beden büyük alın" |
| Renk | Renk farklı veya soluk | "Rengi fotoğraftakinden farklı", "çok soluk" |
| Görsel | Fotoğraftaki görünümden farklı (renk hariç) | "Fotoğraftaki ürünle alakası yok" |
| Malzeme | Kumaşın/materyalin özelliği | "Kumaş ince", "şeffaf", "plastik gibi", "su geçirmiyor", "kaşındırıyor", "sert" |
| Dayanıklılık | Zamanla bozulma | "İki yıkamada söküldü", "bir haftada koptu", "X kullanımdan sonra yırtıldı" |
| Kalite | **Yalnızca** ilk günden var olan işçilik/üretim hatası ve somut sebep belirtmeyen genel kalite şikayeti | "Dikişler çarpık geldi", "düğme kutudan çıkınca koptu", "fermuar takılıyor", "defolu/lekeli geldi", "cheap", "poor quality" |
| Eksik Bilgi | Sayfada bilginin hiç olmaması | "Açıklamada yazmıyordu" (ölçü, bakım vb.) |

Öncelik: Bir şikayet birden fazla konuya uyuyorsa en spesifik olana gider; **Malzeme ve Dayanıklılık, Kalite'den önce** gelir. Örnek: "Kumaş ucuz ve ince" → Malzeme (Kalite değil). "Üç yıkamada dikişleri söküldü" → Dayanıklılık (Kalite değil). "Dikişler kutudan söküklü çıktı" → Kalite.

## Örnek
**Sayfa:** "Men's leather boot. Waterproof. Non-slip sole."
**Yorumlar:** (1) "İlk yağmurda içi su doldu." (2) "Su geçirmez yazıyor ama ayaklarım ıslandı." (3) "Kargo kutusu ezik geldi."

→ gap_var = **Evet** · Malzeme = **X** · seviye = **Yüksek** · not: "Su geçirmez iddiası var, ilgili 2/2 yorum su aldığını söylüyor; kargo yorumu sayılmadı."

## Süreç kuralı
Etiketleme bitip `data/gold/etiketleme.xlsx` GitHub'a commit edilmeden LLM sistemi çalıştırılmaz. Commit tarihi, etiketlerin sistem çıktısından önce hazırlandığının kanıtıdır.

**Kural revizyonu (sürüm 2):** İlk etiketlemeden sonra yapılan tutarlılık kontrolünde tip sınırlarının ("Kalite"nin Malzeme ve Dayanıklılık ile örtüşmesi; aynı yorumların iki konuya birden sayılması) ve "açık iddia" tanımının belirsiz olduğu görüldü. "Tek konu kuralı", konu tanımları/öncelik sırası ve "somut iddia" tanımı eklendi. Sistem çalıştırılmadan önce 40 ürünün tamamı yeni kurallarla yeniden gözden geçirildi. İlk etiketleme ayrı bir commit olarak saklanmaktadır ("Faz 4: ilk etiketleme (kural netleştirme öncesi)").
