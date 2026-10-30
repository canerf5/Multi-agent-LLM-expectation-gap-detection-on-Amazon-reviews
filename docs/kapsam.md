# Tez Kapsamı ve Önerisi

**Öğrenci:** Caner Erenler (21058025) · Yıldız Teknik Üniversitesi, Matematik Mühendisliği
**Sürüm:** 2.1 · 30 Ekim 2026

**Tez Başlığı (Öneri):**
E-Ticaret Ürün Sayfalarında Çok Ajanlı LLM Tabanlı Beklenti Uyumsuzluğu Tespiti: Amazon Ürün Yorumları Üzerine Bir Uygulama

*(Multi-Agent LLM-Based Expectation Gap Detection for E-Commerce Product Pages: A Case Study on Amazon Reviews)*

Bu doküman çalışmanın kapsamını tanımlar. Uygulamaya ilişkin teknik ayrıntılar (filtreler, şemalar, kontroller, kayıt yapısı, istatistik ayrıntıları) `docs/yontem.md`'dedir; etiketleme kuralları `docs/etiketleme_kurallari.md`'dedir.

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

## 3. Sistem Mimarisi

**Çok ajanlı sistem:** Sıralı çalışan üç LLM ajanı.

| Ajan | Girdi | Görev | Çıktı (JSON) |
|---|---|---|---|
| 1. Expectation Agent | Ürün sayfası: başlık, özellikler, açıklama, detaylar, fiyat | "Bu sayfa müşteriye ne vaat ediyor?" | Beklenti listesi: sayfadan alıntı, konu, somut / genel iddia ayrımı |
| 2. Review Mining Agent | Aynı ürünün negatif yorumları (puan ≤ 2) | "Müşteriler gerçekte neyden şikayet ediyor?" | Gruplandırılmış şikayetler: tip, destekleyen yorumlar, ilgililik. Beklenti uyumsuzluğuyla ilgisiz şikayetler (kargo/paketleme, satıcı/iade, kullanılmış ürün gönderimi, kişisel zevk) ilgisiz işaretlenir |
| 3. Gap + Fix Agent | Ajan 1 ve Ajan 2'nin çıktıları | "Fark ne, tipi ne, seviyesi ne, sayfada ne değişmeli?" | Gap var mı, tip(ler), seviye, her tip için gerekçe (yorumlar + sayfa iddiası), ana risk, iyileştirme önerileri |

**Tek LLM baseline:** Tüm analizi tek prompt ile yapan model.

İki sistem aynı modeli, aynı girdiyi, aynı etiketleme kurallarını, aynı çıktı şemasını ve aynı tutarlılık kontrolünü kullanır; tek fark mimaridir. Çıktılar sabit JSON şemalarına bağlıdır ve gap tipleri sabit bir listeyle sınırlandırılmıştır. Her kararın kurallara uygunluğu kodla denetlenir; ihlal varsa model bir kez daha sorgulanır. Sistem doğrudan Python ve OpenAI SDK ile, orkestrasyon framework'ü olmadan gerçekleştirilmiştir. Tekrarlanabilirlik tarihli model sürümü ve önbellekle sağlanır; her koşu, modele giden prompt'larla birlikte ayrı olarak saklanır.

## 4. Veri ve Örneklem

- **Veri:** Amazon Reviews 2023 (McAuley Lab), Clothing_Shoes_and_Jewelry kategorisi. Yorum ve ürün meta dosyaları `parent_asin` üzerinden birleştirilir; böylece beden ve renk varyantlarının yorumları tek ürün altında toplanır.
- **Uygunluk:** En az 10 yorum; en az 3 negatif yorum (puan ≤ 2, en az 5 kelime); kategori yolu giyim, ayakkabı, bot veya spor giyim (takı, saat, çanta, bavul, aksesuar, kostüm hariç); sayfa bilgisi dolu; birebir aynı negatif yorumlar tek sayılır.
- **Örneklem:** Kuralları sağlayan tüm ürünler (204.789) arasından sabit tohumla (seed = 42) basit rastgele örneklemle 200 ürün: 40 test (altın standart), 5 geliştirme (prompt denemesi), 155 kalan. Ayrıca veri sorunu çıkan test ürünlerinin yerine konmak üzere 10 yedek.
- **Girdi:** Ürün başına en fazla 15 negatif yorum (dosya sırasına göre ilk 15) kullanılır; sistemlere yorumların ve sayfanın tam metni verilir.
- **Ayıklama:** Çok kısa yorumlar ön işlemede, ilgisiz şikayetler Ajan 2 tarafından ayıklanır; ayıklama kuralları altın standart etiketlemesindekilerle aynıdır.

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

Bir ürün birden fazla gap tipine sahip olabilir (çoklu etiket). Bir tip, en az 2 yorum aynı sorundan bahsediyorsa işaretlenir; bir şikayet yalnızca tek tipe sayılır. Tip tanımları, öncelik sırası ve "aynı sorun" tanımı etiketleme kurallarındadır (`docs/etiketleme_kurallari.md`, sürüm 2).

**Gap seviyesi:**

| Seviye | Tanım |
|---|---|
| Yüksek | Sayfada ürüne özgü somut bir iddia (ölçü aralığı, kalıp uyarısı, materyal, "waterproof", "memory foam", renk adı vb.) var ve yorumlar bu iddiayla doğrudan çelişiyor |
| Orta | Sayfa ilgili konuda bilgi vermemiş veya yalnızca genel pazarlama dili ("high quality", "premium", "perfect fit") kullanmış; yorumlar bu konuda şikayet ediyor |
| Yok | Sayfa ile yorumlar arasında çelişki yok |

Seviye, tek etiketleyicili değerlendirmede tutarlılığı artırmak amacıyla 0–10 sayısal skor yerine kurala dayalı üç kademeli bir ölçekle tanımlanmıştır.

## 6. Değerlendirme

**Altın standart:** 40 test ürünü, yazılı etiketleme kurallarına göre araştırmacı tarafından elle etiketlenir: gap var mı (Evet / Hayır), gap tip(ler)i, gap seviyesi (Yok / Orta / Yüksek). Etiketleme sistemler çalıştırılmadan önce tamamlanmış ve git'e işlenmiştir; kurallar tezin ekinde yer alır. Altın standart etiketlere erişim 29 Ekim 2026'dan itibaren teknik olarak engellenmiştir. Prompt geliştirme yalnızca 5 ürünlük geliştirme kümesiyle ve her sistem için en fazla 3 koşu ile yapılır; ardından prompt'lar dondurulur.

**Karşılaştırma:** Çok ajanlı sistem ve tek LLM baseline aynı 40 test ürünü üzerinde değerlendirilir.

**Metrikler:**

| Düzey | Metrik |
|---|---|
| Ana | **Gap tipi micro-F1** (çoklu etiket, 40 ürün × 6 tip) ve 6 tip macro-F1; tip bazında precision / recall / F1. Eksik Bilgi test kümesinde hiç geçmediği için (support = 0) hesaplamadan çıkarılır; bu tipteki yanlış pozitifler ayrıca raporlanır |
| İkincil | Gap var/yok: iki sınıf için precision / recall / F1 ve Macro F1; accuracy yalnızca çoğunluk referansıyla (hep "Evet": %90, Macro F1 = 0,47) |
| İkincil | Seviye isabeti, çoğunluk referansıyla (hep "Orta": %70) ve 3 seviye macro-F1 |
| Süreç | Her sistem için tutarsız karar sayısı, maliyet ve süre |

Tutarlılık kontrolünden ikinci denemede de geçemeyen ("tutarsız") kararlar olduğu gibi değerlendirilir (gap var, tipler ve seviye doğrudan alınır); elle düzeltilmez.

**İstatistiksel karşılaştırma:** Test kümesi küçük olduğundan her metrik için 1000 tekrarlı bootstrap ile %95 güven aralığı verilir. İki sistem, eşleştirilmiş bootstrap ile karşılaştırılır (her tekrarda aynı ürün örneklemi; fark = çok ajanlı − tek LLM); farkın %95 güven aralığı ve farkın ≤ 0 çıktığı tekrarların oranı raporlanır. Güven aralığı 0'ı içeriyorsa fark anlamlı kabul edilmez.

**Alt sorular ve hata analizi:**

- **Alt Soru 2:** 200 ürünün çok ajanlı sistem çıktısı üzerinde gap tiplerinin sıklığı ve her tip için tipe sahip olan / olmayan ürünlerin ortalama puan farkı (Mann-Whitney U, 7 tip için Holm düzeltmesi); puan, veri setindeki yorumlardan hesaplanır.
- **Alt Soru 3:** Kalan (155) kümeden sabit tohumla (seed = 42) seçilen 20 ürünün önerileri, iki sistemin önerileri sistem adı gizlenip karışık sırada sunularak araştırmacı tarafından sayfa bağlamıyla tutarlılık açısından 1–5 ölçeğinde puanlanır (rubrik: `docs/yontem.md`).
- **Hata analizi:** Yanlış tahmin edilen test ürünlerinde hatanın hangi ajandan kaynaklandığı incelenir.

**Beklenti:** Çok ajanlı sistemin tek LLM'i her metrikte geçmesi zorunlu değildir. Ancak açıklanabilirlik, hata izlenebilirliği ve adım bazlı analiz açısından üstünlük sağlaması beklenmektedir. Sonuçlar objektif olarak raporlanacaktır.

## 7. Kapsam

| Alan | Sınır |
|---|---|
| Platform | Amazon |
| Kategori | Clothing_Shoes_and_Jewelry (giyim ve ayakkabı) |
| Veri | Amazon Reviews 2023 |
| Ürün sayısı | 200 (40 test / 5 geliştirme / 155 kalan) + 10 yedek |
| Ajan sayısı | 3 |
| Model | OpenAI GPT-4o-mini (`gpt-4o-mini-2024-07-18`) |
| Değerlendirme | 40 ürün elle etiket; ana metrik gap tipi micro-F1 (+ 6 tip macro-F1); ikincil: gap var/yok Macro F1, seviye isabeti (+ 3 seviye macro-F1); bootstrap %95 güven aralığı ve eşleştirilmiş karşılaştırma |
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

Her ürün için sistem aşağıdaki formatta çıktı üretir. Her öneri bir gap tipine dayanır; düzeltilecek sayfa ifadesini (veya "bilgi yok"), müşterilerin yaşadığı sorunu, işlemi (kaldır / değiştir / ekle) ve sayfada yapılacak somut düzeltmeyi içerir. Öneriler yalnızca ürün sayfası değişikliğidir.

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

## 10. Sınırlılıklar

- Gerçek iade verisi bulunmadığı için iade riski dolaylı olarak ölçülmektedir.
- Tek kategori ile sınırlıdır; genellenebilirlik sınırlıdır.
- Tek etiketleyici ile değerlendirme yapılacaktır; etiketleyiciler arası uyum hesaplanmayacaktır.
- Test setinde sınıf dağılımı dengesizdir: 40 ürünün 36'sında gap vardır, yalnızca 4'ünde yoktur. "Gap yok" sınıfına ilişkin sonuçlar 4 ürüne dayandığı için istatistiksel olarak zayıftır.
- Eksik Bilgi tipine test setinde rastlanmamıştır; bu tip değerlendirme metriklerinin kapsamı dışında kalmıştır ve sistemlerin bu tipteki başarısı ölçülememiştir.
- Bazı gap tipleri test setinde az örneklidir (Görsel 2, Renk 5, Kalite 5 ürün). Bu tiplerin F1 değerleri birkaç tahmine bağlı olarak büyük ölçüde değişebilir ve 6 tip üzerinden hesaplanan macro-F1'i belirgin biçimde etkiler; bu nedenle ana metrik micro-F1 olarak seçilmiş, tip bazında sonuçlar bu uyarıyla birlikte yorumlanmıştır.
- Alt Soru 2, elle etiket yerine çok ajanlı sistemin çıktısına dayanır; sistem hataları bu analize yansır.
- Ürün başına en fazla 15 negatif yorum kullanılır; daha fazla yorumu olan ürünlerde kalan şikayetler değerlendirilmez.
- Altın standart etiketlemenin son turunda fiyat ve detay alanları etiketleyiciye gösterilmemiştir; sistemler bu alanları görür (`docs/yontem.md`).
- Amazon veri setinde ürün sayfası içeriği zaman içinde değişmiş olabilir; bu durum veri tutarlılığını etkileyebilir. Örneklemdeki yorumlar 2008–2023 arasına yayılmaktadır.
- İngilizce veri ile çalışılmaktadır; dil bağımlılığı vardır.
- Görsel analiz yapılmamaktadır; görsel kaynaklı beklenti uyumsuzlukları dolaylı olarak ele alınmaktadır.
- Kapsam giyim ve ayakkabı ile sınırlandırılmıştır; takı, saat ve aksesuar ürünleri değerlendirme dışıdır.
- Kategori yolu yalnızca iki seviyeden oluşan veya 'Westlake' gibi içeriği belirsiz düğümlerdeki ürünler ile kostümler kapsam dışıdır.
- Amazon bazı farklı ürünleri aynı ürün kimliği altında birleştirmektedir; bu tür kayıtlar gold kümesinde elle tespit edilip çıkarılmakta, kalan kümelerde ise sistem çıktısını etkileyebilmektedir.

## 11. Başarı Kriterleri

- Üç ajanlı sistem çalışır durumda olmalıdır.
- 200 ürün için gap analizi üretilmiş olmalıdır.
- 40 ürün manuel olarak etiketlenmiş olmalıdır.
- Gap tipi micro-F1 ve macro-F1 (ana), gap var/yok Macro F1 ve seviye isabeti (ikincil) hesaplanmış; iki sistem farkı için 1000 tekrarlı bootstrap ile %95 güven aralığı ve eşleştirilmiş karşılaştırma yapılmış olmalıdır.
- Tek LLM baseline ile karşılaştırma yapılmış olmalıdır.

## 12. Özet

Bu çalışma, e-ticaret ürün sayfalarındaki beklenti uyumsuzluğunu çok ajanlı LLM mimarisiyle tespit eden ve ürün sayfası iyileştirme önerisi üreten bir çerçeve sunmaktadır. Amazon Reviews 2023 veri seti üzerinde 200 ürün ile test edilecek, 40 ürün manuel etiketlenerek doğrulanacak ve tek LLM baseline ile karşılaştırılacaktır. Çalışma, 4 haftalık yoğun bir program dahilinde tamamlanacaktır (teslim: 8 Kasım 2026).

## 13. Revizyon Notları (Sürüm 1.0'a göre)

Ayrıntılı gerekçeler: `docs/yontem.md`, Ek A.

| Sürüm | Konu | Değişiklik |
|---|---|---|
| 2.0 | Veri seti | Amazon Reviews 2018 yerine daha güncel ve zengin metadata'lı Amazon Reviews 2023 kullanıldı. |
| 2.0 | Birleştirme anahtarı | Varyant yorumlarını tek üründe toplamak için `asin` yerine `parent_asin` kullanıldı. |
| 2.0 | Örneklem kriteri | Şikayet örüntüsü oluşabilmesi için ≥5 yorum / ≥1 negatif yerine ≥10 yorum / ≥3 negatif şartı kondu. |
| 2.0 | Gap skoru | Tek etiketleyicide tutarlılık için 0–10 skor yerine kurala dayalı Yok / Orta / Yüksek kullanıldı. |
| 2.0 | Metrikler | Accuracy ve P/R/F1'e micro/macro F1, tip bazında F1 ve seviye isabeti eklendi. |
| 2.0 | Filtreleme | Kısa yorumlar kodla, kargo ve kişisel zevk şikayetleri Ajan 2 ile ayıklanır. |
| 2.0 | Veri bölme | Prompt ayarının test kümesini etkilememesi için 40 test / 5 geliştirme / 155 kalan + 10 yedek ayrıldı. |
| 2.0 | Kapsam filtresi | Taksonomiye uymayan giyim dışı ürünleri çıkarmak için kategori yoluna göre giyim/ayakkabı filtresi eklendi. |
| 2.0 | Tekrarlı yorumlar | "En az 2 yorum" kuralını yanıltmaması için birebir aynı negatif yorumlar tek sayılır. |
| 2.0 | Bölüm numaraları | Bölümler sıralı numaralandı. |
| 2.1 | Etiketleme kuralları sürüm 2 | Tutarlılık kontrolünden sonra tek konu kuralı, tip öncelikleri ve "somut iddia" şartı eklendi; 40 ürün yeniden gözden geçirildi. |
| 2.1 | Metrikler | 36 Evet / 4 Hayır dağılımı nedeniyle ana metrik gap tipi micro-F1 oldu; bootstrap karşılaştırması eklendi, Eksik Bilgi (support = 0) hesaplamadan çıkarıldı. |
| 2.1 | Öneri formatı | Önerilerin hangi vaade ve şikayete dayandığını göstermek için yapılandırılmış öneri formatı ve kodla tutarlılık kontrolü (tek tekrar, iki sisteme aynı) eklendi. |
| 2.1 | Prompt geliştirme sınırı | Aşırı uyumu önlemek için her sistem geliştirme kümesinde en fazla 3 koşu ile geliştirilir, sonra dondurulur. |
| 2.1 | Sonuç ve ölçüm kaydı | Koşuların ve sistemlerin karşılaştırılabilmesi için her koşu ve ölçüm ayrı kaydedilir. |
| 2.1 | Kapsam / yöntem ayrımı | Teknik ayrıntılar kapsamdan `docs/yontem.md`'ye taşındı; kapsamın özü değişmedi. |
| 2.1 | Açık kararlar | Ajan 1 girdisinden "marka" çıkarıldı; tutarsız kararlar olduğu gibi değerlendirilir; seviye isabetine çoğunluk referansı ve 3 seviye macro-F1 eklendi. |
| 2.1 | Alt Soru 2 ve 3 yöntemi | Alt Soru 2 için Mann-Whitney U (Holm düzeltmeli), Alt Soru 3 için kalan kümeden 20 ürünlük kör puanlama tanımlandı. |
| 2.1 | Girdi sınırı | Ürün başına en fazla 15 negatif yorum (dosya sırasına göre) kullanıldığı belgelendi. |
