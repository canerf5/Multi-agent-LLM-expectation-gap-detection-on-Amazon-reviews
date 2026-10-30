# Tez Kapsamı ve Önerisi

**Öğrenci:** Caner Erenler (21058025) · Yıldız Teknik Üniversitesi, Matematik Mühendisliği
**Sürüm:** 2.1 · 29 Ekim 2026

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
- Çıktı: Gap var mı, tip(ler), seviye (Yok / Orta / Yüksek), her tip için destekleyen yorumlar ve ilgili sayfa iddiası, ana risk, iyileştirme önerileri (JSON). Her öneri bir gap tipine dayanır ve şunları içerir: düzeltilecek sayfa ifadesi (Ajan 1'in alıntısı) veya "bilgi yok", müşterilerin yaşadığı sorun (yorum numaralarıyla), işlem (kaldır / değiştir / ekle) ve sayfada yapılacak somut düzeltme. Öneriler yalnızca ürün sayfası değişikliğidir; ürünün kendisine yönelik değildir.

**Tutarlılık kontrolü:** Ajan 3'ün kararı kodla kurallara göre denetlenir: her gap tipinin en az 2 farklı yorumu olması, bir yorumun tek tipe sayılması, sayfa iddiası olmayan tipin Yüksek olamaması, sayfa alıntılarının birebir geçmesi ve her gap tipine en az bir öneri düşmesi. İhlal varsa model, ihlaller açıklanarak bir kez daha sorgulanır; ikinci cevap da tutarsızsa sonuç değiştirilmeden "tutarsız" olarak işaretlenir. Aynı kontrol ve tek tekrar hakkı tek LLM baseline'ına da uygulanır.

**Yapılandırılmış çıktı:** Tüm ajanlar, önceden tanımlanmış JSON şemalarına uygun çıktı üretir; gap tipleri sabit bir listeyle sınırlandırılır. Böylece sonuçlar otomatik olarak analiz edilebilir ve karşılaştırılabilir.

**Uygulama:** Pipeline sabit ve sıralı olduğundan bir orkestrasyon framework'ü kullanılmamış, sistem doğrudan Python ve OpenAI SDK ile gerçekleştirilmiştir. Tüm çağrılar `temperature = 0` ile yapılır ve önbelleğe alınır; böylece sonuçlar tekrarlanabilir. Her ajanın ara çıktısı ayrıca kaydedilir. Her koşu, modele giden prompt'ların tam metniyle birlikte ayrı bir klasörde saklanır ve hiçbir koşu bir öncekinin üzerine yazmaz (bkz. §6, "Sonuçların ve ölçümlerin kaydı").

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

- HTML etiketleri, kodlanmış karakterler ve `[[VIDEOID:...]]` gibi Amazon yer tutucuları: ön işleme aşamasında temizlenir
- Çok kısa ve içeriksiz yorumlar (5 kelimeden kısa): ön işleme aşamasında kodla
- Kargo ve paketleme kaynaklı şikayetler: Review Mining Agent tarafından
- Satıcı ve iade süreci şikayetleri ile kullanılmış/iade edilmiş ürün gönderimi: Review Mining Agent tarafından
- Kişisel zevk beyanları ("beğenmedim", "bana uymadı"): Review Mining Agent tarafından

Bu ayıklama kuralları, altın standart etiketlemesinde uygulanan kurallarla (`docs/etiketleme_kurallari.md`, "Sayılmayanlar") aynıdır.

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
| Yüksek | Sayfada ürüne özgü somut bir iddia (ölçü aralığı, kalıp uyarısı, materyal, "waterproof", "memory foam", renk adı vb.) var ve yorumlar bu iddiayla doğrudan çelişiyor |
| Orta | Sayfa ilgili konuda bilgi vermemiş veya yalnızca genel pazarlama dili ("high quality", "premium", "perfect fit") kullanmış; yorumlar bu konuda şikayet ediyor |
| Yok | Sayfa ile yorumlar arasında çelişki yok |

Tip tanımları, tek konu kuralı (bir şikayet yalnızca tek tipe sayılır) ve öncelik sırası etiketleme kurallarında (`docs/etiketleme_kurallari.md`, sürüm 2) ayrıntılı olarak verilmiştir.

Seviye, tek etiketleyicili değerlendirmede tutarlılığı artırmak amacıyla 0–10 sayısal skor yerine kurala dayalı üç kademeli bir ölçekle tanımlanmıştır.

## 6. Değerlendirme Metodolojisi

**Altın standart (gold standard):** 40 ürün, yazılı etiketleme kurallarına göre araştırmacı tarafından manuel olarak etiketlenir:

- Gap var mı? (Evet / Hayır)
- Gap tipi/tipleri
- Gap seviyesi (Yok / Orta / Yüksek)

Etiketleme, sistemler çalıştırılmadan önce tamamlanır ve sürüm kontrolüne (git) işlenir. Etiketleme kuralları tezin ekinde yer alır. Altın standart etiketlere erişim, sistem geliştirme sürecinde teknik olarak engellenmiş; prompt geliştirme yalnızca geliştirme kümesiyle yapılmıştır.

**Karşılaştırma:**

- Çok ajanlı sistem: 3 ajanlı sıralı mimari
- Tek LLM baseline: Tüm analizi tek prompt ile yapan model

İki sistem aynı modeli, aynı girdiyi ve aynı çıktı şemasını kullanır; tek fark mimaridir. Her iki sistem de aynı 40 test ürünü üzerinde değerlendirilir.

**Metrikler:**

*Ana metrik:* **Gap tipi micro-F1** (çoklu etiket; 40 ürün × 6 tip). Yanında **6 tip üzerinden macro-F1** verilir. Test setinde 36 üründe toplam 62 tip etiketi bulunduğundan iki sistem asıl olarak bu düzeyde ayrışır.

- Gap tipi sınıflandırma: Precision (kesinlik), Recall (duyarlılık) ve F1; micro ve macro ortalama
- Tip bazında F1: Hangi gap tiplerinde başarılı/başarısız olunduğu
- Eksik Bilgi tipi: Test setinde bu tipe hiç rastlanmamıştır (frekans 0). Recall ve F1 bu sınıf için tanımsız olduğundan (sıfıra bölme), Eksik Bilgi micro ve macro hesaplamadan çıkarılır (6 tip) ve sınıflandırma raporunda support = 0 olarak açıkça gösterilir. Bir sistemin bu tipte yaptığı tahminler (yanlış pozitifler) ayrıca sayılarak raporlanır.

*İkincil metrikler:*

- Seviye isabeti: Gap seviyesinin doğru tahmin oranı
- Gap var/yok tespiti: Her iki sınıf (Evet/Hayır) için Precision, Recall, F1 ve Macro F1. "Hayır" sınıfı yalnızca 4 ürüne dayanır; bu sınıftaki tek bir hata sınıfın recall değerini 1/4 oranında değiştirir. Bu yüzden gap var/yok sonucu ana metrik olarak kullanılmaz ve bu notla birlikte raporlanır. Her ürüne "Evet" diyen bir model %90 accuracy elde eder (Macro F1 = 0,47); accuracy yanıltıcı olduğundan yalnızca bu çoğunluk sınıfı referansıyla (majority baseline) birlikte verilir.

*İstatistiksel karşılaştırma:* 40 ürünlük test seti küçük olduğundan iki sistem arasındaki farkın tesadüf olup olmadığı ayrıca sınanır:

- Her metrik için 1000 tekrarlı bootstrap (ürünler yerine koyarak yeniden örneklenir) ile %95 güven aralığı
- Eşleştirilmiş bootstrap karşılaştırması: Her tekrarda aynı ürün örneklemi iki sisteme birlikte uygulanır ve fark (çok ajanlı − tek LLM) hesaplanır. Farkın %95 güven aralığı ve farkın 0'dan küçük ya da 0'a eşit çıktığı tekrarların oranı raporlanır. Güven aralığı 0'ı içeriyorsa fark anlamlı kabul edilmez.

**Alt sorular için ek analizler:**

- Alt Soru 2: 200 ürün üzerinde gap tiplerinin sıklığı ve ortalama puanla ilişkisi
- Alt Soru 3: Rastgele seçilen 20 ürünün önerileri, sayfa bağlamıyla tutarlılık açısından araştırmacı tarafından 1–5 ölçeğinde puanlanır
- Hata analizi: Yanlış tahmin edilen ürünlerde hatanın hangi ajandan kaynaklandığı incelenir

**Sonuçların ve ölçümlerin kaydı:** Karşılaştırmaların her adımı yeniden üretilebilir ve izlenebilir olacak biçimde kaydedilir.

*Koşu kaydı (her iki sistem, her koşu):* `outputs/runs/<küme>/<koşu>/` klasörü:

- `manifest.json`: sistem, küme, ürünler, model sürümü, temperature, git commit'i, prompt / kural / şema / config dosyalarının hash'leri, koşu notu, tamamlanıp tamamlanmadığı
- `prompts/`: modele giden prompt'ların tam metni
- ürün başına ara çıktılar (her ajanın JSON çıktısı, tutarlılık kontrolü bilgisi, §9 biçiminde özet)
- `sonuclar.csv`: ürün başına tek satır; gap tipleri altın standartla aynı sütun adlarıyla
- `llm_calls.jsonl`: koşunun tüm LLM çağrıları
- `olcumler.json`: gold gerektirmeyen süreç ölçümleri: gap var oranı, tip ve seviye dağılımı; tekrar gereken ve tutarsız kalan ürün oranı ile ihlal türleri; ajan uyarı sayıları; öneri sayısı ve işlem dağılımı; çağrı, token, maliyet ve süre
- `outputs/runs/index.csv`: her koşu için tek satır (prompt geliştirme geçmişi; iki sistemin geliştirme kümesinde kaç kez denendiği)

Maliyet, token ve süre hem "ödenen" (önbellekten gelen çağrı 0) hem "eşdeğer" (önbellekten gelen çağrı için ilk ücretli çağrının değeri) olarak kaydedilir; sistemler arası karşılaştırmada eşdeğer değerler kullanılır.

*Değerlendirme kaydı (test kümesi, Faz 8):* `reports/degerlendirme/<tarih>/` klasörü: karşılaştırılan koşuların kimlikleri, altın standart dosyasının hash'i, sürüm etiketi ve bootstrap ayarları (`girdi.json`); her sistem için yukarıdaki metrikler ve %95 güven aralıkları (`metrikler.csv`); tip bazında TP / FP / FN / P / R / F1 / support (`tip_bazinda.csv`); eşleştirilmiş bootstrap farkları (`karsilastirma.csv`); ürün bazında altın standart ve iki sistemin kararları (`urun_bazinda.csv`); teze girecek tablolar (`rapor.md`). Alt Soru 3 puanlaması (`oneri_puanlama.csv`) ve hata analizi (`hata_analizi.csv`, hatanın kaynağı olan ajan) da aynı klasörde saklanır. Bootstrap tekrar sayısı ve rastgelelik tohumu `config.yaml`'da sabitlenir.

**Beklenti:** Çok ajanlı sistemin tek LLM'i her metrikte geçmesi zorunlu değildir. Ancak açıklanabilirlik, hata izlenebilirliği ve adım bazlı analiz açısından üstünlük sağlaması beklenmektedir. Sonuçlar objektif olarak raporlanacaktır.

## 7. Kapsam

| Alan | Sınır |
|---|---|
| Platform | Amazon |
| Kategori | Clothing_Shoes_and_Jewelry |
| Veri | Amazon Reviews 2023 |
| Ürün sayısı | 200 |
| Ajan sayısı | 3 |
| Model | OpenAI GPT-4o-mini (`gpt-4o-mini-2024-07-18`; erişim ve fiyat 30 Ekim 2026'da doğrulandı) |
| Değerlendirme | 40 ürün manuel etiket; ana metrik gap tipi micro-F1 (+ 6 tip macro-F1); ikincil: seviye isabeti, gap var/yok Macro F1; bootstrap %95 güven aralığı ve eşleştirilmiş karşılaştırma |
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
gap_var:      Evet
gap_tipleri:  Beden/Kalıp, Malzeme
seviye:       Yüksek
gerekçeler:
  - Beden/Kalıp: yorum 1, 3, 5 | sayfa iddiası: 'True to size'
  - Malzeme: yorum 2, 4 | sayfa iddiası: 'bilgi yok'
ana_risk:     Sayfa 'true to size' diyor ama müşteriler 1-2 beden küçük geldiğini söylüyor.
öneriler:
  - [Beden/Kalıp | değiştir] "True to size" ifadesini kaldır; "bir beden büyük almanız önerilir" notu ekle
      sayfa: 'True to size' | müşteri: Yorum 1, 3, 5: 1-2 beden küçük geliyor
  - [Malzeme | ekle] Kumaş kalınlığı ve şeffaflık bilgisini açıklamaya ekle
      sayfa: 'bilgi yok' | müşteri: Yorum 2, 4: kumaş ince ve şeffaf
```

Bu metin, sistemin JSON çıktısından otomatik üretilir (`ozet.txt`).

## 10. Sınırlılıklar

- Gerçek iade verisi bulunmadığı için iade riski dolaylı olarak ölçülmektedir.
- Tek kategori ile sınırlıdır; genellenebilirlik sınırlıdır.
- Tek etiketleyici ile değerlendirme yapılacaktır; etiketleyiciler arası uyum hesaplanmayacaktır.
- Test setinde sınıf dağılımı dengesizdir: 40 ürünün 36'sında gap vardır, yalnızca 4'ünde yoktur. "Gap yok" sınıfına ilişkin sonuçlar 4 ürüne dayandığı için istatistiksel olarak zayıftır.
- Eksik Bilgi tipine test setinde rastlanmamıştır; bu tip değerlendirme metriklerinin kapsamı dışında kalmıştır ve sistemlerin bu tipteki başarısı ölçülememiştir.
- Bazı gap tipleri test setinde az örneklidir (Görsel 2, Renk 5, Kalite 5 ürün). Bu tiplerin F1 değerleri birkaç tahmine bağlı olarak büyük ölçüde değişebilir ve 6 tip üzerinden hesaplanan macro-F1'i belirgin biçimde etkiler; bu nedenle ana metrik micro-F1 olarak seçilmiş, tip bazında sonuçlar bu uyarıyla birlikte yorumlanmıştır.
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
- Gap tipi micro-F1 ve macro-F1 (ana), seviye isabeti ve gap var/yok Macro F1 (ikincil) hesaplanmış; iki sistem farkı için 1000 tekrarlı bootstrap ile %95 güven aralığı ve eşleştirilmiş karşılaştırma yapılmış olmalıdır.
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
| Metrikler | Accuracy, P/R/F1 | Ana: gap tipi micro-F1 (+ 6 tip macro-F1); ikincil: seviye isabeti, gap var/yok Macro F1; tip bazında F1; accuracy yalnızca çoğunluk sınıfı referansıyla; Eksik Bilgi (support = 0) hesaplamadan çıkarıldı; 1000 tekrarlı bootstrap %95 güven aralığı ve eşleştirilmiş karşılaştırma | Test setinde 36 Evet / 4 Hayır: "hep Evet" diyen model %90 accuracy alıyor (Macro F1 = 0,47) ve "Hayır" sınıfı 4 ürüne dayandığı için gap var/yok iki sistemi ayırmıyor; asıl ayrışma 62 tip etiketinde. 40 ürün küçük olduğundan farkın anlamlılığı bootstrap ile sınanıyor; Eksik Bilgi test setinde hiç geçmiyor |
| Filtreleme | Yöntem belirtilmemiş | Kısa yorum: kod; kargo/zevk: Ajan 2 | Kural tabanlı ayıklama bu şikayetleri güvenilir yakalayamıyor |
| Veri bölme | — | 40 test / 5 geliştirme / 155 kalan + 10 yedek | Prompt ayarının test setini etkilememesi; veri sorunu olan gold ürünlerin yerine yedek |
| Kapsam filtresi | — | Giyim ve ayakkabı: kategori yolunda Clothing / Shoes / Boot Shop / Sport Specific Clothing geçen, Jewelry / Watches / Accessories / Handbags & Wallets / Luggage & Travel Gear / Shoe, Jewelry & Watch Accessories / Costumes & Accessories geçmeyen ürünler | Kategoride giyim dışı ürünler (bavul, saat, şemsiye) var; taksonomi bu ürünlere uymuyor. Yalnızca "Clothing/Shoes" araması botları (Boot Shop) ve spor giyimi (Sport Specific Clothing) dışarıda bırakıyordu |
| Tekrarlı yorumlar | — | Birebir aynı negatif yorumlar tek sayılır | Kopyalar "en az 2 yorum" kuralını yanıltıyor |
| Etiketleme kuralları (sürüm 2) | Tip tanımları yalnızca örnekle; seviye "Yüksek" için "sayfa açıkça iddiada bulunmuş" | Tek konu kuralı (bir şikayet yalnızca tek tipe sayılır, her tipin kendi en az 2 yorumu olmalı); tip tanımları ve öncelik (Malzeme ve Dayanıklılık, Kalite'den önce; Kalite yalnızca ilk günden işçilik/üretim hatası ve genel "cheap/poor quality"); "Yüksek" için ürüne özgü somut iddia şartı (genel pazarlama dili en fazla Orta; renk adı + soluk/donuk = Orta, başka renk = Yüksek); kullanılmış/iade edilmiş ürün gönderimi satıcı hatası (sayılmaz), hasarlı/defolu yeni ürün Kalite | Etiketleme sonrası tutarlılık kontrolünde tip sınırları ve "açık iddia" tanımı netleştirildi; sistem çalıştırılmadan önce 40 ürünün tamamı yeni kurallarla yeniden gözden geçirildi |
| Bölüm numaraları | 8, 11, 13 eksik | Sıralı (1–13) | Biçim |
| Öneri formatı ve tutarlılık kontrolü (30 Ekim 2026) | Öneriler serbest metin listesi; tutarlılık kontrolü belgelenmemiş | Her öneri gap tipi, sayfa ifadesi, müşteri deneyimi, işlem (kaldır/değiştir/ekle) ve düzeltme içerir; kodla tutarlılık kontrolü ve tek tekrar hakkı (§3), iki sisteme aynı | Geliştirme kümesindeki (5 ürün) ilk denemede öneriler hangi vaadin tutmadığını ve sayfanın neresinin düzeltileceğini göstermiyordu; Alt Soru 3 puanlaması için öneri ile sayfa bağlamı arasındaki bağ açık olmalı. Gold kümesi kullanılmadı |
| Sonuç ve ölçüm kaydı (30 Ekim 2026) | Her koşu ürün çıktılarının üzerine yazıyordu; ölçümlerin kaydı tanımlı değildi | Her koşu ayrı klasörde (manifest, prompt'lar, ürün çıktıları, sonuç tablosu, süreç ölçümleri); değerlendirme çıktılarının dosya yapısı tanımlandı (§6) | Koşuların ve iki sistemin tezde karşılaştırılabilmesi, prompt geliştirme geçmişinin ve maliyet/sürenin raporlanabilmesi |
