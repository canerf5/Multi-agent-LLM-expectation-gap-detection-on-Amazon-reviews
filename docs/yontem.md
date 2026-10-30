# Yöntem Ayrıntıları

**Sürüm:** 1.0 · 30 Ekim 2026 · Kapsam: `docs/kapsam.md` sürüm 2.1

Bu doküman, kapsamda (`docs/kapsam.md`) tanımlanan çalışmanın uygulama ayrıntılarını içerir ve tezin Yöntem bölümüne kaynak olacak biçimde yazılmıştır. Buradaki her madde kapsamdaki bir maddeye dayanır; kapsamı genişletmez. Etiketleme kuralları ayrıca `docs/etiketleme_kurallari.md`'dedir.

## 1. Veri

**Kaynak:** Amazon Reviews 2023 (McAuley Lab, Hugging Face: `McAuley-Lab/Amazon-Reviews-2023`), tek kategori: Clothing_Shoes_and_Jewelry. Ham dosyalar elle indirilip yerelde okunmuştur (~43 GB; git'e girmez).

**Dosyalar:**

- Ürün yorumları: puan (rating), başlık, metin, zaman damgası
- Ürün meta verisi: başlık, özellikler, açıklama, detaylar, fiyat, mağaza

**Birleştirme:** İki dosya `parent_asin` anahtarı üzerinden birleştirilir. Böylece aynı ürünün beden ve renk varyantlarına ait yorumlar tek ürün altında toplanır.

## 2. Örneklem

### 2.1 Uygunluk kuralları

1. En az 10 yorumu olan ürünler
2. En az 3 negatif yorumu olan ürünler (negatif: puan ≤ 2 ve en az 5 kelime)
3. Kapsam filtresi: kategori yolunun herhangi bir seviyesi "Clothing", "Shoes", "Boot Shop" veya "Sport Specific Clothing" olan ve hiçbir seviyesi "Jewelry", "Watches", "Accessories", "Handbags & Wallets", "Luggage & Travel Gear", "Shoe, Jewelry & Watch Accessories" veya "Costumes & Accessories" olmayan ürünler (büyük-küçük harf duyarsız, tam eşleşme). Böylece giyim, ayakkabı, bot ve spor giyim kapsama girer; Amazon'un bu kategoriye koyduğu takı, saat, çanta, bavul, aksesuar ve kostümler kapsam dışı kalır.
4. Sayfa bilgisi (başlık ve özellik listesi veya açıklama) boş olmayan ürünler
5. Aynı ürün altında birebir aynı metne sahip negatif yorumlar tek sayılır (karşılaştırma küçük harfe çevrilmiş ve noktalama dışı bırakılmış metin üzerinden yapılır); bu ayıklamadan sonra 2. kural yeniden uygulanır.

### 2.2 Eleme hunisi

Yorum ve meta dosyalarının tamamı okunmuştur (`reports/orneklem_raporu.md`):

| Adım | Ürün |
|---|---|
| Okunan yorum satırı | 66.033.346 |
| Farklı ürün (`parent_asin`) | 7.216.886 |
| Kural 1: en az 10 yorum | 707.604 |
| Kural 2: en az 3 negatif yorum (≥ 5 kelime) | 361.400 |
| Kural 3: kapsam filtresi (elenen 152.358) | 209.042 |
| Kural 4: sayfa bilgisi dolu (elenen 4.253) | 204.789 |
| Seçim: seed = 42 ile rastgele (tekrar ayıklama sonrası; 2. kuralın altına düşen 0) | 200 + 10 yedek |

### 2.3 Seçim ve bölme

Uygun ürünler sabit tohumla (seed = 42) karıştırılır; seçim dosyalardaki satır sırasından bağımsızdır (önce tüm yorumlar sayılır, sonra meta verisi okunur, ardından seçilen havuz için negatif yorumlar toplanır). Karışık sıranın başından tekrar ayıklamasından sonra da 2. kuralı sağlayan ilk 210 ürün alınır:

| Küme | Ürün | Kullanım |
|---|---|---|
| Test (gold) | 40 | Elle etiketlenir; iki sistem bu kümede değerlendirilir |
| Geliştirme (dev) | 5 | Prompt denemesi; test kümesinden ayrıdır |
| Kalan (rest) | 155 | Tam koşu, Alt Soru 2, Alt Soru 3 örneklemi |
| Yedek (reserve) | 10 | Veri sorunu çıkan test ürününün yerine sırayla konur |

**Yedek kuralı:** Etiketleme sırasında verisi uygun olmadığı belirlenen (ör. yorumları başka bir ürüne ait) test ürünlerinin yerine yedekler sırayla (atlamadan) konur. Test kümesinde hiçbir ürün "veri uygun değil" çıkmamış, yedek kullanılmamıştır; birleştirilmiş (başka ürüne ait yorumlu) kayıt bulunmamıştır.

### 2.4 Yorum sınırı

Ürün başına en fazla 15 negatif yorum kullanılır: tekrar ayıklamasından sonra **dosya sırasına göre ilk 15** yorum alınır (rastgele seçim yapılmaz). Örneklemde ürün başına negatif yorum sayısı ortalama 18,4, medyan 6, en fazla 642'dir; geliştirme ve kalan kümelerdeki 160 üründen 29'unda 15'ten fazla negatif yorum vardır (test kümesi bu amaçla incelenmemiştir). Aynı 15 yorum hem etiketleyiciye hem sistemlere verilmiştir.

### 2.5 Metin temizliği

- HTML entity'leri çözülür; `<br />` ve diğer HTML etiketleri ile `[[VIDEOID:...]]` gibi Amazon yer tutucuları silinir; fazla boşluklar tekleştirilir. Temizlik sonrası HTML etiketi kalan yorum yoktur.
- 5 kelimeden kısa ve içeriksiz yorumlar ön işlemede kodla çıkarılır.
- Kargo ve paketleme kaynaklı şikayetler, satıcı ve iade süreci şikayetleri, kullanılmış/iade edilmiş ürün gönderimi ve kişisel zevk beyanları ("beğenmedim", "bana uymadı") metinden silinmez; Ajan 2 tarafından ilgisiz olarak işaretlenir. Bu ayıklama kuralları altın standart etiketlemesindeki "Sayılmayanlar" ile aynıdır.

### 2.6 Zaman tutarlılığı

Amazon veri setinde ürün sayfası içeriği zaman içinde değişebilmektedir; kullanıcının yorum yaptığı tarihteki sayfa içeriği ile sistemin kullandığı içerik arasında fark olabilir. Örneklemdeki yorumların tarih aralığı 17 Haziran 2008 – 2 Eylül 2023'tür. Bu durum sınırlılıklar arasında belirtilmiştir.

## 3. Girdi alanları ve "Ne okunur?" farkı

Etiketleme kuralları ("Ne okunur?") etiketleyicinin sayfa için başlık, özellikler, açıklama, detaylar ve fiyatı okuduğunu söyler. Sistemlere verilen girdi ile etiketleme dosyalarının etiketleyiciye gösterdiği alanlar karşılaştırıldığında:

| Alan | Kural "Ne okunur?" | Sistem girdisi | Etiketleme 1. tur | Gözden geçirme (son etiket) |
|---|---|---|---|---|
| Başlık | ✓ | ✓ | ✓ | ✓ |
| Fiyat | ✓ | ✓ (yoksa "(yok)") | ✓ (yoksa gösterilmez) | ✗ |
| Özellikler | ✓ | ✓ tam | ✓ tam | ✓ tam |
| Açıklama | ✓ | ✓ tam | ilk 800 karakter | ✓ tam |
| Detaylar | ✓ | ✓ tümü | ilk 8 alan | ✗ |
| Mağaza / marka | — | ✗ | ✗ | ✗ |
| Negatif yorumlar | tam | tam (en fazla 15) | her yorum ilk 500 karakter | tam |

Son etiketler (kurallar sürüm 2 ile gözden geçirme) başlık, özellikler, tam açıklama ve tam yorumlar üzerinden verilmiştir; sistemler ek olarak fiyatı ve detayları görür. Geliştirme kümesinde detay alanları paket ölçüsü, bölüm (department), listelenme tarihi, üretici ve model numarasından oluşmaktadır; gap konularıyla ilgili somut iddia içermemektedir. Mağaza/marka alanı ne sisteme ne etiketleyiciye verilir.

## 4. Sistemler

### 4.1 Çok ajanlı sistem: girdiler ve görünürlük

| Ajan | Gördüğü | Görmediği |
|---|---|---|
| Ajan 1 (Expectation) | Sayfa metni: başlık, fiyat, özellikler, açıklama, detaylar | Yorumlar |
| Ajan 2 (Review Mining) | Numaralı negatif yorumlar: "[puan★] başlık — metin" | Sayfa |
| Ajan 3 (Gap + Fix) | Ajan 1 ve Ajan 2'nin JSON çıktıları | Ham sayfa ve yorum metni |

Sayfa ve yorum metni kesilmeden verilir; her çağrıdan önce girdinin ürün kaydının tamamını içerdiği kodla doğrulanır.

**Kurallar:** Etiketleme kurallarının "Tek konu kuralı", "Seviye kuralı", "Sayılmayanlar" ve "Konu tanımları" bölümleri, kurallar dosyasından çalışma anında okunarak her prompt'a eklenir (prompt'lara elle kopyalanmaz); Ajan 3'e ayrıca kurallardaki örnek verilir. Böylece etiketleyici ile sistem aynı kural metnini kullanır. Prompt'larda test ürünü örneği kullanılmaz.

### 4.2 Çıktı şemaları

Tüm çağrılar OpenAI Structured Outputs (strict JSON şeması) ile yapılır; dönen JSON ayrıca yerel olarak şemaya göre doğrulanır.

- **Ajan 1:** `beklentiler[]`: `konu` (Eksik Bilgi dışındaki 6 tip veya "Diğer"; Eksik Bilgi sayfada bilginin olmaması olduğundan sayfa iddiasının konusu olamaz), `iddia` (sayfadan birebir alıntı), `iddia_turu` (somut / genel).
- **Ajan 2:** `sikayet_gruplari[]`: `tip` (7 tipten biri; ilgisizse boş), `ozet`, `yorum_numaralari`, `ilgili`, `ilgisiz_sebebi` (kargo/paketleme, satıcı/iade, kullanılmış ürün, kişisel zevk).
- **Ortak sonuç (Ajan 3 ve baseline):** `gap_var`, `gap_tipleri`, `seviye`, `tip_gerekceleri[]` (`tip`, `yorum_numaralari`, `sayfa_iddiasi`: alıntı veya "bilgi yok"), `ana_risk`, `oneriler[]`.

**Öneri şeması:** Her öneri şu alanları içerir: `tip` (dayandığı gap tipi), `sayfa_iddiasi` (düzeltilecek sayfa ifadesi; Ajan 1'in alıntısı veya "bilgi yok"), `musteri_deneyimi` (müşterilerin yaşadığı sorun, yorum numaralarıyla), `islem` (kaldır: yanlış/yanıltıcı ifade silinir; değiştir: ifade düzeltilir; ekle: sayfada olmayan bilgi eklenir), `duzeltme` (sayfada yapılacak somut değişiklik). Öneriler yalnızca ürün sayfası değişikliğidir; ürünün kendisine yönelik değildir. Öneriler şikayetlerde geçmeyen ölçü veya değer içermez. Kapsamdaki metin biçimi (§9) bu JSON'dan otomatik üretilir.

### 4.3 Tutarlılık kontrolü ve tek tekrar

Ajan 3'ün (ve baseline'ın) kararı kodla kurallara göre denetlenir:

- `gap_var` ile tip, seviye, gerekçe ve öneri alanlarının uyumu (gap yoksa hepsi boş ve seviye "Yok"; gap varsa en az bir tip, seviye Orta veya Yüksek)
- Her gap tipinin en az 2 farklı destekleyen yorumu olması ve yorum numaralarının geçerli olması
- Tek konu kuralı: bir yorumun yalnızca bir tipin gerekçesinde yer alması
- Seviye kuralı: hiçbir tipte sayfa iddiası yoksa (hepsi "bilgi yok") seviye Yüksek olamaz
- Alıntı doğruluğu: `sayfa_iddiasi` alıntıları kaynakta birebir geçmelidir (boşluk ve büyük-küçük harf farkı yok sayılır). Ajan 3 için kaynak Ajan 1'in alıntılarıdır (Ajan 3 sayfayı görmez); baseline için kaynak sayfa metnidir.
- Öneriler: her öneri bir gap tipine dayanır, her gap tipine en az bir öneri düşer, sayfa iddiası "bilgi yok" olan önerinin işlemi "ekle"dir.

İhlal varsa model, ihlaller açıklanarak ve önceki cevabı gösterilerek **bir kez** daha sorgulanır. İkinci cevap da ihlal içeriyorsa sonuç değiştirilmeden "tutarsız" olarak işaretlenir. Aynı kontrol ve tek tekrar hakkı baseline'a da aynen uygulanır.

**Uyarılar (kararı değiştirmez, kaydedilir):** Ajan 1'in sayfada birebir geçmeyen alıntıları; Ajan 2'de ilgili/ilgisiz alanlarının uyumsuzluğu, geçersiz yorum numarası ve bir yorumun birden fazla ilgili grupta yer alması.

### 4.4 Tek LLM baseline

Baseline, çok ajanlı sistemle aynı girdiyi (aynı sayfa ve yorum metni), aynı kural bölümlerini, aynı ortak sonuç şemasını, aynı tutarlılık kontrolünü ve aynı tek tekrar hakkını kullanır; analizin tamamını tek prompt'ta yapar. Tek fark mimaridir.

- **Girdi:** "ÜRÜN SAYFASI" başlığı altında Ajan 1'e giden sayfa metninin, "NEGATİF YORUMLAR" başlığı altında Ajan 2'ye giden numaralı yorum metninin aynısı.
- **Prompt:** `prompts/baseline.md`. Üç ajan prompt'undaki görev talimatlarının toplamıdır; ara çıktıya yapılan atıflar ("Ajan 1'in alıntısı", "Ajan 2'nin özeti") sayfaya ve yorumlara yapılan atıflara uyarlanmış, yalnızca ara çıktıya veya görünürlüğe özgü talimatlar çıkarılmıştır. Üç prompt'ta olmayan talimat eklenmemiştir. Talimat karşılaştırması Ek B'dedir; kritik talimatların baseline'da birebir bulunduğu otomatik testle denetlenir.
- **Kontrol ve tekrar:** Ajan 3 ile aynı fonksiyon (aynı ihlal listesi, aynı tekrar mesajı, en fazla bir tekrar). Alıntı kaynağı sayfa metnidir.

### 4.5 Prompt geliştirme sınırı

Her sistemin prompt'ları yalnızca geliştirme kümesinde (5 ürün) ve **en fazla 3 koşu** ile geliştirilir; üçüncü koşudan sonra prompt'lar dondurulur. Prompt değişiklikleri yalnızca etiketleme kurallarından türetilen genel düzeltmelerdir; ürüne özgü ayar yapılmaz ve geliştirme ürünlerinden örnek kullanılmaz. Koşuların sayısı ve içeriği koşu kaydında (`outputs/runs/index.csv`) belgelenir. Dondurulan sistemde kalan hatalar (ör. tutarsız kalan kararlar) düzeltilmeye çalışılmaz, bulgu olarak raporlanır.

Çok ajanlı sistem 30 Ekim 2026'da 3 geliştirme koşusundan sonra dondurulmuştur:

| Koşu | Değişiklik | Tekrar gereken | Tutarsız |
|---|---|---|---|
| 1 | İlk prompt'lar | 4/5 | 2/5 |
| 2 | Yapılandırılmış öneri; yeni tutarlılık kontrolleri; Ajan 1 ve 2 netleştirmeleri | 3/5 | 1/5 |
| 3 | Ajan 2 Eksik Bilgi tanımı; Ajan 3 son kontrol listesi ve öneri içeriği; Ajan 1 somut = doğrulanabilir | 2/5 | 1/5 |
| Doğrulama (geliştirme denemesi değil) | Şablon değişikliği yok; kurallara "aynı sorun" tanımı eklendi | 1/5 | 0/5 |

Dondurulan sürüm seçilirken önceden belirlenen kural (3. koşudan sonra dondurma) ve süreç ölçüleri esas alınmıştır; geliştirme ürünlerinin etiketi olmadığından ürün bazında "en iyi" koşu seçilmemiştir.

**Nihai prompt doğrulaması:** Dondurmadan sonra etiketleme kurallarına "aynı sorun" tanımı eklenmiştir (kurallar, "Tek konu kuralı" bölümü çalışma anında prompt'lara eklendiği için modele giden prompt metni değişmiş, prompt şablonları değişmemiştir). Bu nedenle prompt şablonları değiştirilmeden 5 geliştirme ürününde bir doğrulama koşusu yapılmıştır (koşu notu: "dogrulama-nihai-prompt"). Bu koşu bir geliştirme denemesi değil, nihai prompt doğrulamasıdır: amacı nihai prompt metninin geliştirme kümesinde bir kez çalıştığını kayda geçirmektir; koşudan sonra hiçbir şey değiştirilmemiştir. Sonucu yukarıdaki tabloya eklenmiştir.

**Baseline:** Baseline prompt'u, 3 ajanlı sistemin 3 koşuda geliştirilmiş ve dondurulmuş talimatlarından birebir türetildi; dolayısıyla iki sistem aynı geliştirme emeğinden yararlanır. Baseline'da 1 dev koşusu yapıldı. Gözlenen hataların tümü talimat uyumsuzluğuydu; uyarlama hatası bulunmadı. Ek koşular, ya üç prompt'ta olmayan talimat eklemeyi ya da baseline'a ara adım yaptırmayı (mimari farkı ortadan kaldırmayı) gerektireceği için yapılmadı. Baseline 30 Ekim 2026'da bu haliyle dondurulmuştur.

| Koşu | Sistem | Tekrar gereken | Tutarsız | Eşdeğer maliyet |
|---|---|---|---|---|
| Doğrulama (nihai prompt) | 3 ajan | 1/5 | 0/5 | $0,0085 (16 çağrı) |
| 1 | Baseline | 5/5 | 4/5 | $0,0098 (10 çağrı) |

Baseline'ın ilk denemedeki ihlalleri: 2 yorum şartı (7), tek konu kuralı (3), iddia yokken Yüksek (1); tekrardan sonra kalan: 2 yorum şartı (7), tek konu kuralı (1).

## 5. Tekrarlanabilirlik

- **Model:** `gpt-4o-mini-2024-07-18` (tarihli sürüm). Erişim, hesabın model listesinden; fiyat (girdi $0,15, çıktı $0,60 / 1 milyon token, standart katman) OpenAI fiyat sayfasından 30 Ekim 2026'da doğrulanmıştır.
- **temperature = 0:** Çağrılar `temperature = 0` ile yapılır; ancak bu, OpenAI modellerinde tam belirlenimcilik sağlamaz. Tekrarlanabilirlik tarihli model sürümü ve önbellekle sağlanır.
- **Önbellek:** Anahtar = model + sistem prompt'u + kullanıcı girdisi + şemanın SHA-256 özeti; aynı girdi ikinci kez API'ye gönderilmez, önbellekteki cevap kullanılır. Önbellek dosyaları isteğin tam metnini ve cevabı içerir.
- **Çağrı kaydı:** Her çağrı zaman, ajan/ürün etiketi, model, token, maliyet, süre ve önbellek isabetiyle loglanır. Hata veya zaman aşımında en fazla 3 kez artan beklemeyle (2, 4, 8 sn) tekrar denenir.
- **Sürüm kontrolü:** Örneklem (`v0.1-sample`) ve altın standart (`v0.1-data`) git etiketleriyle dondurulmuştur; sonraki aşamalar `v0.2-agents`, `v0.3-results`, `v1.0-final` etiketleriyle işaretlenir.

## 6. Koşu ve ölçüm kaydı

Karşılaştırmaların her adımı yeniden üretilebilir ve izlenebilir olacak biçimde kaydedilir. Hiçbir koşu bir öncekinin üzerine yazmaz.

**Koşu kaydı (her iki sistem, her koşu):** `outputs/runs/<küme>/<koşu>/` klasörü:

- `manifest.json`: sistem, küme, ürünler, model sürümü, temperature, git commit'i ve commit'lenmemiş değişiklik bilgisi, prompt / kural / şema / config dosyalarının hash'leri, koşu notu, tamamlanıp tamamlanmadığı
- `prompts/`: modele giden prompt'ların tam metni
- ürün başına ara çıktılar (her ajanın JSON çıktısı, tutarlılık kontrolü bilgisi, kapsam §9 biçiminde özet)
- `sonuclar.csv`: ürün başına tek satır; gap tipleri altın standartla aynı sütun adlarıyla
- `llm_calls.jsonl`: koşunun tüm LLM çağrıları
- `olcumler.json`: altın standart gerektirmeyen süreç ölçümleri: gap var oranı, tip ve seviye dağılımı; tekrar gereken ve tutarsız kalan ürün oranı ile ihlal türleri; ajan uyarı sayıları; öneri sayısı ve işlem dağılımı; çağrı, token, maliyet ve süre
- `outputs/runs/index.csv`: her koşu için tek satır (prompt geliştirme geçmişi; iki sistemin geliştirme kümesinde kaç kez denendiği)

Maliyet, token ve süre hem "ödenen" (önbellekten gelen çağrı 0) hem "eşdeğer" (önbellekten gelen çağrı için ilk ücretli çağrının değeri) olarak kaydedilir; sistemler arası karşılaştırmada eşdeğer değerler kullanılır.

**Hata ve devam:** Bir üründe hata olursa (ör. API hatası, şema ihlali) o ürün atlanır, koşu diğer ürünlerle devam eder; hatalı ürünler ve hata metinleri manifest'e yazılır ve koşu "tamamlanmadı" olarak işaretlenir. Aynı komut yeniden çalıştırıldığında tamamlanmış çağrılar önbellekten (ücretsiz) gelir, yalnızca eksik çağrılar yapılır. Koşu dışarıdan durdurulursa (ör. Ctrl+C) o ana kadarki kayıt yine yazılır. Tam koşu (Faz 7) `--split all` (test + geliştirme + kalan = 200 ürün) ile yapılır; test ürünlerini içerdiği için gold kilidi gerektirir.

## 7. Değerlendirme

### 7.1 Metrikler

**Ana metrik:** Gap tipi micro-F1 (çoklu etiket; 40 ürün × 6 tip). Yanında 6 tip üzerinden macro-F1 verilir. Test kümesinde 36 üründe toplam 62 tip etiketi bulunduğundan (Beden/Kalıp 24, Malzeme 13, Dayanıklılık 13, Renk 5, Kalite 5, Görsel 2) iki sistem asıl olarak bu düzeyde ayrışır.

- Gap tipi sınıflandırma: precision, recall ve F1; micro ve macro ortalama
- Tip bazında F1: hangi gap tiplerinde başarılı/başarısız olunduğu
- Eksik Bilgi: test kümesinde bu tipe hiç rastlanmamıştır (frekans 0). Recall ve F1 bu sınıf için tanımsız olduğundan (sıfıra bölme) Eksik Bilgi micro ve macro hesaplamadan çıkarılır (6 tip) ve sınıflandırma raporunda support = 0 olarak açıkça gösterilir. Bir sistemin bu tipte yaptığı tahminler (yanlış pozitifler) ayrıca sayılarak raporlanır.

**İkincil metrikler:**

- Gap var/yok tespiti: her iki sınıf (Evet / Hayır) için precision, recall, F1 ve Macro F1. "Hayır" sınıfı yalnızca 4 ürüne dayanır; bu sınıftaki tek bir hata sınıfın recall değerini 1/4 oranında değiştirir. Bu yüzden gap var/yok sonucu ana metrik olarak kullanılmaz ve bu notla birlikte raporlanır. Her ürüne "Evet" diyen bir model %90 accuracy elde eder (Macro F1 = 0,47); accuracy yanıltıcı olduğundan yalnızca bu çoğunluk sınıfı referansıyla (majority baseline) birlikte verilir.
- Seviye isabeti: gap seviyesinin doğru tahmin oranı. Test kümesinde seviye dağılımı 8 Yüksek / 28 Orta / 4 Yok olduğundan her ürüne "Orta" diyen bir model %70 isabet alır; isabet bu çoğunluk referansıyla birlikte verilir. Yanında 3 seviye üzerinden macro-F1 raporlanır.
- Süreç: her sistem için tutarsız karar sayısı, eşdeğer maliyet ve süre.

**Tanımsız sınıflar:** Precision veya recall'un paydası 0 ise o değer 0 sayılır. Bir sınıfta (tip veya seviye) TP + FP + FN = 0 ise, yani o sınıf ne altın standartta ne tahminde geçiyorsa, F1 tanımsızdır ve o örneklemde macro ortalamaya katılmaz. Tam test kümesinde 6 tipin ve 3 seviyenin hepsinin desteği olduğundan bu kural noktasal değerleri etkilemez; desteği az olan sınıfların (ör. Görsel, "gap yok") bazı bootstrap örneklemlerinde hiç geçmediği durumlarda uygulanır.

**Tutarsız kararlar:** Tutarlılık kontrolünden ikinci denemede de geçemeyen kararlar olduğu gibi değerlendirilir (`gap_var`, `gap_tipleri`, `seviye` doğrudan alınır); elle düzeltilmez ve değerlendirmeden çıkarılmaz. Her sistem için tutarsız karar sayısı raporlanır.

### 7.2 İstatistiksel karşılaştırma

40 ürünlük test kümesi küçük olduğundan iki sistem arasındaki farkın tesadüf olup olmadığı ayrıca sınanır:

- Her metrik için 1000 tekrarlı bootstrap (ürünler yerine koyarak yeniden örneklenir) ile %95 güven aralığı
- Eşleştirilmiş bootstrap karşılaştırması: her tekrarda aynı ürün örneklemi iki sisteme birlikte uygulanır ve fark (çok ajanlı − tek LLM) hesaplanır. Farkın %95 güven aralığı ve farkın 0'dan küçük ya da 0'a eşit çıktığı tekrarların oranı raporlanır. Güven aralığı 0'ı içeriyorsa fark anlamlı kabul edilmez.
- Bootstrap tekrar sayısı ve rastgelelik tohumu `config.yaml`'da sabitlenir.

### 7.3 Değerlendirme kaydı

Değerlendirme (Faz 8) `reports/degerlendirme/<tarih>/` klasörüne yazılır:

- `girdi.json`: karşılaştırılan koşuların kimlikleri, altın standart dosyasının hash'i, sürüm etiketi ve bootstrap ayarları
- `metrikler.csv`: her sistem için 7.1'deki metrikler ve %95 güven aralıkları
- `tip_bazinda.csv`: tip bazında TP / FP / FN / precision / recall / F1 / support
- `karsilastirma.csv`: eşleştirilmiş bootstrap farkları
- `urun_bazinda.csv`: ürün bazında altın standart ve iki sistemin kararları
- `rapor.md`: teze girecek tablolar
- `oneri_puanlama.csv` (Alt Soru 3) ve `hata_analizi.csv` (hatanın kaynağı olan ajan)

Değerlendirme `src/evaluate.py` ile yapılır: altın standart dosyası, iki sistemin koşu klasörleri ve çıktı klasörü açıkça verilir. Script altın standartta yalnızca `parent_asin`, gap var, tip ve seviye sütunlarını okur (not sütununu okumaz); iki koşunun sistem adlarını, modelini ve her altın standart ürününün sonucunun bulunduğunu denetler. Altın standart klasöründeki dosya yalnızca gold kilidi açıkken okunur. Bootstrap tekrar sayısı ve tohumu `config.yaml`'dan alınır (`bootstrap_n: 1000`, `bootstrap_seed: 42`); güven aralıkları yüzdelik (2,5 ve 97,5) yöntemiyle hesaplanır. Script, elle hesaplanmış iki örnek ve sahte altın standartla test edilmiştir.

### 7.4 Alt Soru 2

- **Veri:** 200 ürünün (test, geliştirme, kalan) çok ajanlı sistem çıktısı.
- **Sıklık:** Her gap tipinin kaç üründe tespit edildiği (sayı ve oran).
- **Puanla ilişki:** Her tip için, o tipe sahip olan ve olmayan ürünlerin ortalama puanları Mann-Whitney U testiyle (iki yönlü) karşılaştırılır.
- **Çoklu karşılaştırma:** 7 tip için ayrı testler yapıldığından p-değerlerine Holm düzeltmesi uygulanır (α = 0,05). Gruplardan biri boş kalan tip (ör. hiçbir üründe tespit edilmeyen) test edilemez; düzeltme test edilebilen tipler üzerinden yapılır ve test edilemeyen tipler ayrıca belirtilir.
- **Ortalama puan:** Ürünün veri setindeki tüm yorumlarından (yalnızca negatifler değil) hesaplanan ortalama puan kullanılır. Meta verisindeki `average_rating` alanı kullanılmaz: bu alan Amazon sayfasında verinin toplandığı anda gösterilen puandır ve veri setinde bulunmayan yorumları da içerebilir; veri setindeki yorumlardan hesaplanan ortalama, analizdeki yorumlarla aynı kaynağa ve aynı zaman aralığına dayanır ve yeniden hesaplanabilir.
- **Sınırlılık:** Analiz elle etiket yerine sistem çıktısına dayanır; sistemin hataları (yanlış pozitif ve negatif tipler) sonuçlara yansır. Test kümesindeki sistem başarısı bu analizin güvenilirliği için referans olarak birlikte raporlanır.

### 7.5 Alt Soru 3

- **Örneklem:** Kalan kümeden (155 ürün) sabit tohumla (seed = 42) 20 ürün seçilir.
- **Körleme:** Her ürün için iki sistemin önerileri sistem adı gizlenerek ve sistem sırası ürün başına rastgele (sabit tohumla) karıştırılarak sunulur; eşleme puanlama bittikten sonra açılır.
- **Puanlama birimi:** Her ürün için her sistemin önerilerinin tamamı tek puan alır. Sayfa metni ve yorumlar puanlayıcıya birlikte gösterilir. Bir sistem o üründe gap bulmamışsa (öneri yoksa) puan verilmez ve bu durum ayrıca raporlanır.
- **Rubrik (sayfa bağlamıyla tutarlılık, 1–5):**

| Puan | Tanım |
|---|---|
| 5 | Öneriler sayfadaki ilgili ifadeye veya eksikliğe ve yorumlardaki şikayete doğrudan dayanıyor; düzeltme somut ve uygulanabilir; uydurma ayrıntı yok |
| 4 | Öneriler sayfa ve şikayetle tutarlı ve uygulanabilir; küçük bir eksik var (ör. düzeltme içeriği biraz genel) |
| 3 | Öneriler ilgili ama genel veya belirsiz ("bilgi ekle" düzeyinde) ya da bir kısmı dayanaksız |
| 2 | Sayfa veya şikayetle bağ zayıf; sayfada olmayan bir iddiaya dayanıyor ya da şikayetlerde geçmeyen ayrıntı içeriyor |
| 1 | Öneriler ilgisiz, yanlış ya da sayfa yerine ürünün kendisini değiştirmeyi öneriyor |

### 7.6 Hata analizi

Test kümesinde yanlış tahmin edilen ürünlerde (yanlış/eksik tip veya seviye) ajanların ara çıktıları incelenerek hatanın kaynağı belirlenir: Ajan 1 (iddia kaçırma, yanlış konu veya somut/genel ayrımı), Ajan 2 (yanlış gruplama, yanlış tip, uydurma şikayet, ilgisiz şikayeti ilgili sayma), Ajan 3 (kural uygulama veya seviye hatası) ya da tutarsız kalan karar. Geliştirme kümesinde gözlenen ve düzeltilmeden bırakılan hatalar `docs/ilerleme.md`'de listelenmiştir.

## 8. Altın standart koruması (gold bariyeri)

**İlke:** Altın standart etiketler sistemler çalıştırılmadan önce tamamlanıp git'e işlenmiş (`v0.1-data`) ve sonrasında değiştirilmemiştir. Prompt geliştirme yalnızca geliştirme kümesiyle yapılır; test ürünleri prompt ayarlamak için kullanılmaz ve test sonuçlarına bakarak prompt değiştirilmez.

**Teknik engel (29 Ekim 2026'dan itibaren):** Geliştirmede kullanılan yapay zeka asistanının (Claude Code) altın standart klasörüne erişimi talimatla değil, teknik olarak kapatılmıştır:

- İzin kuralları: altın standart klasörü için okuma ve düzenleme reddedilir.
- Her araç çağrısından önce çalışan bir denetim betiği (hook): araç girdisinde altın standart dosyalarının yolu veya adı, test kümesiyle çalıştırma seçeneği ya da bu dosyalara erişen script'lerin çalıştırılması geçerse çağrı engellenir. Kilit dosyasına ve bariyerin kendi ayar dosyalarına müdahale her durumda engellenir.
- Kilit: Test kümesiyle çalışma yalnızca araştırmacının kendi terminalinde oluşturduğu bir kilit dosyası varken mümkündür; pipeline ayrıca altın standart dosyalarının sürüm etiketindeki haliyle aynı olduğunu ve commit'lenmemiş değişiklik olmadığını denetler.
- Denetim: Test koşusundan önce araştırmacı, test ürünlerinin ASIN ve başlıklarını prompt, kod, önbellek, log ve geliştirme çıktılarında arayan bir denetim script'i çalıştırır (beklenen: hiç iz yok).
- Sınırlar: Denetim betiği komut metnine bakar; metinde geçmeyen dolaylı erişimi tam olarak yakalayamaz. Bu nedenle denetim script'i ve "test sonuçlarına bakarak prompt değiştirilmez" kuralı ayrıca geçerlidir.

**Olay kaydı:** 29 Ekim 2026'da (bariyer kurulmadan önce) bir maliyet tahmini komutu test ürünlerinin sayfa ve yorum metnini uzunluk hesabı için okumuştur; LLM çağrısı yapılmamış, etiketlere erişilmemiş ve prompt'lar bu içeriğe göre değiştirilmemiştir. 30 Ekim 2026'da bir arama çıktısında örneklem raporundaki ürün tablosu nedeniyle 2 test ürününün ASIN'i ve başlığı görünmüş; etiket görülmemiş ve bu bilgi kullanılmamıştır. Ardından ürün tablosu rapordan çıkarılmış ve örneklem listesi korunan bir klasöre taşınmıştır. Ayrıntılar `docs/ilerleme.md` > Karar kaydı'ndadır.

## Ek B. Baseline talimat karşılaştırması

Üç ajan prompt'u (A1: `prompts/expectation.md`, A2: `prompts/review_mining.md`, A3: `prompts/gap_fix.md`) ile baseline prompt'unun (`prompts/baseline.md`) talimat karşılaştırması. Kural bölümleri ("Tek konu kuralı", "Seviye kuralı", "Sayılmayanlar", "Konu tanımları") ve kurallardaki örnek her iki sisteme de aynı kurallar dosyasından çalışma anında eklenir.

| Talimat | A1 | A2 | A3 | Baseline | Not |
|---|---|---|---|---|---|
| Sayfanın tüm bölümlerini tara, açıklamadaki iddialar dahil | ✓ | | | ✓ | |
| Konu: Eksik Bilgi dışındaki 6 konu; "Diğer" yalnızca hiçbiri uymazsa | ✓ | | | ✓ | |
| İddia = birebir İngilizce alıntı | ✓ | | | ✓ | |
| Somut / genel ayrımı ("doğrulanabilir" ölçütü) | ✓ | | (eşleme) | ✓ | |
| Sayfada olmayan vaadi ekleme | ✓ | | | ✓ | |
| Kayıt bilgileri (paket ölçüsü, tarih, model no) vaat değildir | ✓ | | | ✓ | |
| Materyal adı içeren ifadenin konularından biri Malzeme | ✓ | | | ✓ | |
| Sayfanın bilgi vermemesi de önemlidir | ✓ | | | ✓ | A1'deki "onu sen yazma" kısmı ara çıktıya özgü olduğundan çıkarıldı |
| Yorumları görmüyorsun; yorum tahmini yapma | ✓ | | | — | Görünürlüğe özgü (baseline yorumları görür); "ürünü değerlendirme" korundu |
| Aynı alıntıyı aynı konu için tekrarlama | ✓ | | | — | Ajan 1'in liste çıktısına özgü |
| Aynı sorun → tek grup (farklı kelimelerle de olsa); farklı sorun → ayrı grup | | ✓ | | ✓ | |
| Eksik Bilgi yalnızca yorum sayfada yazmadığını açıkça söylüyorsa | | ✓ | | ✓ | |
| Tek konu kuralı ve öncelik sırası | | ✓ | ✓ | ✓ | |
| "Sayılmayanlar" ilgisizdir (4 sebep) | | ✓ | ✓ | ✓ | |
| Sadece yorumlarda yazanı kullan; geçerli yorum numaraları | | ✓ | | ✓ | |
| Tek yorumluk sorunu da grup olarak yaz ("sonraki aşama karar verir") | | ✓ | | — | Ara çıktıya özgü |
| `ozet` / `ilgisiz_sebebi` alanları | | ✓ | | — | Ajan 2 şemasına özgü |
| Karar adımları 1–9 (2 yorum şartı, tamamen çıkar, gap yok normaldir, gerekçe, seviye, ana risk) | | | ✓ | ✓ | "Ajan 1'in alıntısı" → "sayfadan aynen alıntı" |
| Öneri alanları ve öneri kuralları | | | ✓ | ✓ | "Ajan 2'nin özetine dayan" → "yorumlara dayan" |
| SON KONTROL listesi | | | ✓ | ✓ | Aynı uyarlama |

## Ek A. Revizyon gerekçeleri (ayrıntılı)

Kapsamın 13. bölümündeki kısa revizyon tablosunun ayrıntılı hali:

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
| Öneri formatı ve tutarlılık kontrolü (30 Ekim 2026) | Öneriler serbest metin listesi; tutarlılık kontrolü belgelenmemiş | Her öneri gap tipi, sayfa ifadesi, müşteri deneyimi, işlem (kaldır/değiştir/ekle) ve düzeltme içerir; kodla tutarlılık kontrolü ve tek tekrar hakkı, iki sisteme aynı | Geliştirme kümesindeki (5 ürün) ilk denemede öneriler hangi vaadin tutmadığını ve sayfanın neresinin düzeltileceğini göstermiyordu; Alt Soru 3 puanlaması için öneri ile sayfa bağlamı arasındaki bağ açık olmalı. Gold kümesi kullanılmadı |
| Prompt geliştirme sınırı (30 Ekim 2026) | Tanımsız | Her sistem için geliştirme kümesinde en fazla 3 koşu, ardından dondurma | 5 ürünlük geliştirme kümesine aşırı uyumu önlemek ve iki sisteme eşit geliştirme emeği vermek |
| Sonuç ve ölçüm kaydı (30 Ekim 2026) | Her koşu ürün çıktılarının üzerine yazıyordu; ölçümlerin kaydı tanımlı değildi | Her koşu ayrı klasörde (manifest, prompt'lar, ürün çıktıları, sonuç tablosu, süreç ölçümleri); değerlendirme çıktılarının dosya yapısı tanımlandı | Koşuların ve iki sistemin tezde karşılaştırılabilmesi, prompt geliştirme geçmişinin ve maliyet/sürenin raporlanabilmesi |
| Kapsam / yöntem ayrımı (30 Ekim 2026) | Teknik ayrıntılar kapsam dokümanındaydı | Kapsam yalnızca problem, sorular, mimari, veri özeti, taksonomi, değerlendirme özeti, sınırlılık ve kriterleri içerir; ayrıntılar bu dokümandadır | Kapsamın okunabilirliği; tezin Yöntem bölümüne kaynak |
| Açık kararlar (30 Ekim 2026) | Ajan 1 girdisinde "marka"; tutarsız kararların ve seviye metriğinin değerlendirmesi tanımsız | "Marka" çıkarıldı (ne sisteme ne etiketleyiciye verilir); tutarsız kararlar olduğu gibi değerlendirilir; seviye isabeti çoğunluk referansı (%70) ve 3 seviye macro-F1 ile verilir | Girdi tanımının gerçek girdiyle uyumu; seviye isabetinin de çoğunluk sınıfı nedeniyle yanıltıcı olabilmesi |
| Alt Soru 2 ve 3 yöntemi (30 Ekim 2026) | "Sıklık ve puanla ilişki"; "rastgele 20 ürün, 1–5" | Mann-Whitney U, 7 tip için Holm düzeltmesi, puan veri setindeki yorumlardan hesaplanır; kalan kümeden seed = 42 ile 20 ürün, iki sistem kör ve karışık sırada, rubrikle | Analizlerin önceden ve tekrarlanabilir biçimde tanımlanması |
| Girdi sınırı (30 Ekim 2026) | Belgelenmemiş | Ürün başına en fazla 15 negatif yorum, dosya sırasına göre ilk 15 | Örneklem script'inde uygulanan sınırın belgelenmesi |
