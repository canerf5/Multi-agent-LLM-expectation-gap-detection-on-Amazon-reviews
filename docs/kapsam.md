# Tez Kapsamı ve Önerisi

**Öğrenci:** Caner Erenler (21058025) · Yıldız Teknik Üniversitesi, Matematik Mühendisliği
**Sürüm:** 2.0 · 16 Ekim 2026

**Tez Başlığı (Öneri):**
E-Ticaret Ürün Sayfalarında Çok Ajanlı LLM Tabanlı Beklenti Uyumsuzluğu Tespiti: Amazon Ürün Yorumları Üzerine Bir Uygulama

*(Multi-Agent LLM-Based Expectation Gap Detection for E-Commerce Product Pages: A Case Study on Amazon Reviews)*

## 1. Problem Tanımı

E-ticaret ürün sayfaları, müşteride gerçek ürün deneyimiyle uyuşmayan bir beklenti oluşturabilmektedir. Müşteri ürünü satın aldıktan sonra beklediğini bulamadığında düşük puan verir, olumsuz yorum yazar veya iade eder. Bu durum satıcı için doğrudan maliyet oluşturur.

Mevcut sistemlerde yorum madenciliği ve iade tahmini ayrı ayrı ele alınmaktadır. Ancak ürün sayfasının vaadi ile gerçek müşteri deneyimi arasındaki farkı bütünleşik olarak tespit eden bir çerçeve yaygın değildir.

**Temel motivasyon:** Ürün sayfası yayına çıkmadan önce iyileştirilirse müşteri yanlış beklentiyle satın almaz ve iade/şikayet riski azalır.

## 2. Araştırma Sorusu

E-ticaret ürün sayfalarındaki beklenti uyumsuzlukları, çok ajanlı LLM mimarisi kullanılarak ne ölçüde tespit edilebilir ve ürün sayfası iyileştirme önerisine dönüştürülebilir?

**Alt Sorular:**

1. Çok ajanlı LLM sistemi, tek LLM baseline'ına göre beklenti uyumsuzluğu tespitinde daha başarılı mıdır?
2. Hangi beklenti uyumsuzluğu tipleri negatif yorumlarla daha güçlü ilişkilidir?
3. Üretilen iyileştirme önerileri, ürün sayfası bağlamıyla tutarlı mıdır?

## 3. Yöntem ve Sistem Mimarisi

Sistem, sıralı çalışan üç LLM ajanından oluşmaktadır.

**Ajan 1: Expectation Agent**

- Girdi: Ürün başlığı, açıklaması, özellikleri, detayları, fiyatı, markası
- Görev: "Bu ürün sayfası müşteriye ne vaat ediyor?"
- Çıktı: Madde madde beklenti listesi (JSON)

**Ajan 2: Review Mining Agent**

- Girdi: Aynı ürünün negatif yorumları (rating ≤ 2)
- Görev: "Müşteriler gerçekte neyden şikayet ediyor?"
- Çıktı: Gruplandırılmış şikayet listesi, tip, sıklık ve ilgililik işareti (JSON). Beklenti uyumsuzluğuyla ilgisi olmayan şikayetler (kargo, kişisel zevk vb.) bu ajan tarafından ilgisiz olarak işaretlenir.

**Ajan 3: Gap + Fix Agent**

- Girdi: Ajan 1 ve Ajan 2'nin çıktıları
- Görev: "Beklenti ile deneyim arasındaki fark ne? Tipi ne? Seviyesi ne? Sayfada ne değişmeli?"
- Çıktı: Gap var mı, tip(ler), seviye (Yok / Orta / Yüksek), ana risk, iyileştirme önerileri (JSON)

**Yapılandırılmış çıktı:** Tüm ajanlar, önceden tanımlanmış JSON şemalarına uygun çıktı üretir; gap tipleri sabit bir listeyle sınırlandırılır. Böylece sonuçlar otomatik olarak analiz edilebilir ve karşılaştırılabilir.

**Uygulama:** Pipeline sabit ve sıralı olduğundan bir orkestrasyon framework'ü kullanılmamış, sistem doğrudan Python ve OpenAI SDK ile gerçekleştirilmiştir. Tüm çağrılar `temperature = 0` ile yapılır ve önbelleğe alınır; böylece sonuçlar tekrarlanabilir. Her ajanın ara çıktısı ayrıca kaydedilir.

## 4. Veri Seti ve Ön İşleme

**Veri kaynağı:** Amazon Reviews 2023 (McAuley Lab, Hugging Face: `McAuley-Lab/Amazon-Reviews-2023`)

**Kategori:** Clothing_Shoes_and_Jewelry (tek kategori)

**Dosyalar:**

- Ürün yorumları (rating, başlık, metin, zaman damgası)
- Ürün metadata (başlık, özellikler, açıklama, detaylar, fiyat, mağaza)

**Veri birleştirme:** İki dosya `parent_asin` anahtarı üzerinden birleştirilir. Böylece aynı ürünün beden ve renk varyantlarına ait yorumlar tek ürün altında toplanır.

**Örneklem:**

- En az 10 yorumu olan ürünler
- En az 3 negatif yorumu (rating ≤ 2) olan ürünler
- Kategori yolunun herhangi bir seviyesi "Clothing", "Shoes", "Boot Shop" veya "Sport Specific Clothing" olan ve hiçbir seviyesi "Jewelry", "Watches", "Accessories", "Handbags & Wallets", "Luggage & Travel Gear", "Shoe, Jewelry & Watch Accessories" veya "Costumes & Accessories" olmayan ürünler (büyük-küçük harf duyarsız, tam eşleşme). Böylece giyim, ayakkabı, bot ve spor giyim kapsama girer; Amazon'un bu kategoriye koyduğu takı, saat, çanta, bavul, aksesuar ve kostümler kapsam dışı kalır
- Sayfa bilgisi (başlık ve özellik/açıklama) boş olmayan ürünler
- Aynı ürün altında birebir aynı metne sahip negatif yorumlar tek sayılır; bu ayıklamadan sonra negatif yorum şartı yeniden uygulanır
- Yorum ve metadata dosyalarının tamamı okunur; kuralları sağlayan tüm ürünler arasından sabit rastgelelik tohumuyla (seed = 42) basit rastgele örneklemle 200 ürün seçilir
- 200 ürün; 40 test (gold), 5 geliştirme (prompt denemesi) ve 155 kalan ürün olarak ayrılır. Geliştirme ürünleri test setinden ayrıdır.
- Ayrıca 10 yedek ürün seçilir. Etiketleme sırasında verisi uygun olmadığı belirlenen (ör. yorumları başka bir ürüne ait) gold ürünlerin yerine yedekler sırayla konur.

**Veri filtreleme:** Beklenti uyumsuzluğu ile ilgisi olmayan yorumlar ayıklanır:

- HTML etiketleri ve kodlanmış karakterler: ön işleme aşamasında temizlenir
- Çok kısa ve içeriksiz yorumlar (5 kelimeden kısa): ön işleme aşamasında kodla
- Kargo ve paketleme kaynaklı şikayetler: Review Mining Agent tarafından
- Kişisel zevk beyanları ("beğenmedim", "bana uymadı"): Review Mining Agent tarafından

**Zaman tutarlılığı:** Amazon veri setinde ürün sayfası içeriği zaman içinde değişebilmektedir. Kullanıcının yorum yaptığı tarihteki sayfa içeriği ile sistemin kullandığı içerik arasında fark olabilir. Örneklemdeki yorumların tarih aralığı raporlanacak ve bu durum sınırlılıklar arasında belirtilecektir.

## 5. Gap Taksonomisi

| Gap Tipi | Örnek Yorum |
|---|---|
| Beden / Kalıp | "Çok küçük geldi" |
| Renk | "Rengi fotoğraftan farklı" |
| Görsel Uyumsuzluk | "Fotoğraftaki gibi değil" |
| Kalite | "Kalitesi kötü" |
| Malzeme | "Kumaş ince" |
| Dayanıklılık | "Hemen bozuldu" |
| Eksik Bilgi | "Açıklamada yazmıyordu" |

Bir ürün birden fazla gap tipine sahip olabilir (çoklu etiket).

**Gap seviyesi:**

| Seviye | Tanım |
|---|---|
| Yüksek | Sayfa açıkça bir iddiada bulunmuş, yorumlar bunun tersini söylüyor |
| Orta | Sayfa ilgili konuda bilgi vermemiş, yorumlar bu konuda şikayet ediyor |
| Yok | Sayfa ile yorumlar arasında çelişki yok |

Seviye, tek etiketleyicili değerlendirmede tutarlılığı artırmak amacıyla 0–10 sayısal skor yerine kurala dayalı üç kademeli bir ölçekle tanımlanmıştır.

## 6. Değerlendirme Metodolojisi

**Altın standart (gold standard):** 40 ürün, yazılı etiketleme kurallarına göre araştırmacı tarafından manuel olarak etiketlenir:

- Gap var mı? (Evet / Hayır)
- Gap tipi/tipleri
- Gap seviyesi (Yok / Orta / Yüksek)

Etiketleme, sistemler çalıştırılmadan önce tamamlanır ve sürüm kontrolüne (git) işlenir. Etiketleme kuralları tezin ekinde yer alır.

**Karşılaştırma:**

- Çok ajanlı sistem: 3 ajanlı sıralı mimari
- Tek LLM baseline: Tüm analizi tek prompt ile yapan model

İki sistem aynı modeli, aynı girdiyi ve aynı çıktı şemasını kullanır; tek fark mimaridir.

**Metrikler:**

- Accuracy: Gap var/yok tespiti
- Precision, Recall, F1 (micro ve macro): Gap tipi sınıflandırma
- Tip bazında F1: Hangi gap tiplerinde başarılı/başarısız olunduğu
- Seviye isabeti: Gap seviyesinin doğru tahmin oranı
- Karşılaştırma: İki sistemin aynı 40 ürün üzerindeki performansı

**Alt sorular için ek analizler:**

- Alt Soru 2: 200 ürün üzerinde gap tiplerinin sıklığı ve ortalama puanla ilişkisi
- Alt Soru 3: Rastgele seçilen 20 ürünün önerileri, sayfa bağlamıyla tutarlılık açısından araştırmacı tarafından 1–5 ölçeğinde puanlanır
- Hata analizi: Yanlış tahmin edilen ürünlerde hatanın hangi ajandan kaynaklandığı incelenir

**Beklenti:** Çok ajanlı sistemin tek LLM'i her metrikte geçmesi zorunlu değildir. Ancak açıklanabilirlik, hata izlenebilirliği ve adım bazlı analiz açısından üstünlük sağlaması beklenmektedir. Sonuçlar objektif olarak raporlanacaktır.

## 7. Kapsam

| Alan | Sınır |
|---|---|
| Platform | Amazon |
| Kategori | Clothing_Shoes_and_Jewelry |
| Veri | Amazon Reviews 2023 |
| Ürün sayısı | 200 |
| Ajan sayısı | 3 |
| Model | GPT-4o-mini veya benzeri API tabanlı LLM |
| Değerlendirme | 40 ürün manuel etiket; Accuracy, P/R/F1, seviye isabeti |
| Karşılaştırma | Çok ajanlı sistem vs tek LLM |
| Çıktı formatı | JSON (yapılandırılmış) |
| Çalışma şekli | Offline analiz |
| Proje yönetimi | Git / GitHub (sürüm etiketleri ile) |

## 8. Özgün Katkı

Sektörde yorum madenciliği ve iade tahmini ayrı ayrı yapılmaktadır. Bu çalışma:

- Ürün sayfası vaadi ile gerçek müşteri deneyimini birleştiren bütünleşik bir çerçeve sunar.
- Beklenti uyumsuzluğunu tip ve seviye bazında tespit eder.
- Tespit edilen farkı somut ürün sayfası iyileştirme önerisine dönüştürür.
- Çok ajanlı LLM mimarisini tek LLM ile karşılaştırarak bu özel görev için en uygun yaklaşımı araştırır.

## 9. Beklenen Çıktı

Her ürün için sistem aşağıdaki formatta çıktı üretecektir:

```
ASIN:         B07XXXXXXX
Gap var mı:   Evet
Gap tipleri:  Beden / Kalıp, Malzeme
Gap seviyesi: Yüksek
Ana risk:     Beden uyumsuzluğu
Öneriler:
  - Beden tablosu ekle
  - Gerçek çekim fotoğraf koy
  - Kumaş kalınlığını açıklamaya ekle
```

## 10. Sınırlılıklar

- Gerçek iade verisi bulunmadığı için iade riski dolaylı olarak ölçülmektedir.
- Tek kategori ile sınırlıdır; genellenebilirlik sınırlıdır.
- Tek etiketleyici ile değerlendirme yapılacaktır; etiketleyiciler arası uyum hesaplanmayacaktır.
- Amazon veri setinde ürün sayfası içeriği zaman içinde değişmiş olabilir; bu durum veri tutarlılığını etkileyebilir.
- İngilizce veri ile çalışılmaktadır; dil bağımlılığı vardır.
- Görsel analiz yapılmamaktadır; görsel kaynaklı beklenti uyumsuzlukları dolaylı olarak ele alınmaktadır.
- Kapsam giyim ve ayakkabı ile sınırlandırılmıştır; takı, saat ve aksesuar ürünleri değerlendirme dışıdır.
- Kategori yolu yalnızca iki seviyeden oluşan veya 'Westlake' gibi içeriği belirsiz düğümlerdeki ürünler ile kostümler kapsam dışıdır.
- Amazon bazı farklı ürünleri aynı ürün kimliği altında birleştirmektedir; bu tür kayıtlar gold kümesinde elle tespit edilip çıkarılmakta, kalan kümelerde ise sistem çıktısını etkileyebilmektedir.

## 11. Başarı Kriterleri

- Üç ajanlı sistem çalışır durumda olmalıdır.
- 200 ürün için gap analizi üretilmiş olmalıdır.
- 40 ürün manuel olarak etiketlenmiş olmalıdır.
- Accuracy, F1 ve seviye isabeti metrikleri hesaplanmış ve karşılaştırılmaya hazır olmalıdır.
- Tek LLM baseline ile karşılaştırma yapılmış olmalıdır.

## 12. Özet

Bu çalışma, e-ticaret ürün sayfalarındaki beklenti uyumsuzluğunu çok ajanlı LLM mimarisiyle tespit eden ve ürün sayfası iyileştirme önerisi üreten bir çerçeve sunmaktadır. Amazon Reviews 2023 veri seti üzerinde 200 ürün ile test edilecek, 40 ürün manuel etiketlenerek doğrulanacak ve tek LLM baseline ile karşılaştırılacaktır. Çalışma, 4 haftalık yoğun bir program dahilinde tamamlanacaktır.

## 13. Revizyon Notları (Sürüm 1.0'a göre değişiklikler)

| Konu | Önceki | Yeni | Gerekçe |
|---|---|---|---|
| Veri seti | Amazon Reviews 2018 | Amazon Reviews 2023 | Daha güncel; Hugging Face üzerinden indirmeden (streaming) okunabiliyor; daha zengin metadata |
| Birleştirme anahtarı | asin | parent_asin | Beden/renk varyantlarının yorumları tek ürün altında toplanıyor |
| Örneklem kriteri | ≥5 yorum, ≥1 negatif | ≥10 yorum, ≥3 negatif | Tek negatif yorumla şikayet örüntüsü oluşmuyor; Review Mining Agent'ın gruplayacağı veri sağlanıyor |
| Gap skoru | 0–10 sayısal | Yok / Orta / Yüksek | Tek etiketleyicide 0–10 ölçeği tutarsız; kurala dayalı 3 seviye tekrarlanabilir |
| Metrikler | Accuracy, P/R/F1 | + micro/macro F1, tip bazında F1, seviye isabeti | Seviye alanı da değerlendiriliyor |
| Filtreleme | Yöntem belirtilmemiş | Kısa yorum: kod; kargo/zevk: Ajan 2 | Kural tabanlı ayıklama bu şikayetleri güvenilir yakalayamıyor |
| Veri bölme | — | 40 test / 5 geliştirme / 155 kalan + 10 yedek | Prompt ayarının test setini etkilememesi; veri sorunu olan gold ürünlerin yerine yedek |
| Kapsam filtresi | — | Giyim ve ayakkabı: kategori yolunda Clothing / Shoes / Boot Shop / Sport Specific Clothing geçen, Jewelry / Watches / Accessories / Handbags & Wallets / Luggage & Travel Gear / Shoe, Jewelry & Watch Accessories / Costumes & Accessories geçmeyen ürünler | Kategoride giyim dışı ürünler (bavul, saat, şemsiye) var; taksonomi bu ürünlere uymuyor. Yalnızca "Clothing/Shoes" araması botları (Boot Shop) ve spor giyimi (Sport Specific Clothing) dışarıda bırakıyordu |
| Tekrarlı yorumlar | — | Birebir aynı negatif yorumlar tek sayılır | Kopyalar "en az 2 yorum" kuralını yanıltıyor |
| Bölüm numaraları | 8, 11, 13 eksik | Sıralı (1–13) | Biçim |
