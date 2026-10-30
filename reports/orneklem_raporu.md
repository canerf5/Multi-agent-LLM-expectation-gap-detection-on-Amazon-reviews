# Örneklem Raporu

Oluşturulma: 2026-10-24 13:32 (süre 3.7 dk)  
Veri seti: Amazon Reviews 2023 (McAuley Lab)  
Kategori: Clothing_Shoes_and_Jewelry  
Okunan kısım: yorum dosyasının tamamı, meta dosyasının tamamı  
Seed: 42 (aynı ayarlarla her çalıştırmada aynı örneklem çıkar)

## 1. Örneklem Yöntemi

1. En az 10 yorumu olan ürünler
2. En az 3 negatif yorumu olan ürünler (negatif: puan ≤ 2, en az 5 kelime)
3. Kategori yolunun herhangi bir seviyesi şunlardan biri olan: Clothing / Shoes / Boot Shop / Sport Specific Clothing; ve hiçbir seviyesi şunlardan biri olmayan: Jewelry / Watches / Accessories / Handbags & Wallets / Luggage & Travel Gear / Shoe, Jewelry & Watch Accessories / Costumes & Accessories (büyük-küçük harf duyarsız, tam eşleşme). Böylece giyim ve ayakkabı kapsama girer; takı, saat, çanta, bavul, aksesuar ve kostümler dışarıda kalır.
4. Sayfa bilgisi (başlık ve özellik listesi veya açıklama) boş olmayan ürünler
   Aynı ürün altında birebir aynı metne sahip negatif yorumlar tek sayılır; bu ayıklamadan sonra Kural 2 yeniden uygulanır.
5. 1-4. kuralları sağlayan tüm ürünler arasından seed=42 ile basit rastgele örneklem (200 ürün). Seçim, dosyalardaki satır sırasından bağımsızdır.
6. Bölme: 40 test (gold) / 5 geliştirme (dev) / 155 kalan (rest) + 10 yedek (reserve; gold'da veri sorunu çıkan ürünün yerine sırayla konur)

Metin temizliği: HTML entity'leri çözüldü, `<br />` ve diğer HTML etiketleri ile `[[VIDEOID:...]]` gibi Amazon yer tutucuları silindi.

## 2. Eleme Hunisi

| Adım | Sayı |
|---|---|
| Okunan yorum satırı | 66,033,346 |
| Farklı ürün (parent_asin) | 7,216,886 |
| Kural 1: en az 10 yorum | 707,604 |
| Kural 2: en az 3 negatif yorum (≥5 kelime) | 361,400 |
| Kural 3: kategori yolu kapsam içinde (dahil: Clothing / Shoes / Boot Shop / Sport Specific Clothing; hariç: Jewelry / Watches / Accessories / Handbags & Wallets / Luggage & Travel Gear / Shoe, Jewelry & Watch Accessories / Costumes & Accessories) (elenen kapsam dışı: 152,358) | 209,042 |
| Kural 4: sayfa bilgisi dolu (elenen: boş sayfa 4,253, meta kaydı yok 0) | 204,789 |
| Tekrarlı yorumlar ayıklandı (Kural 2'nin altına düşen: 0, toplam ayıklanan kopya: 124) | 210 |
| Kural 5: seed=42 ile rastgele seçilen örneklem (+10 yedek) | 200 |

## 3. Veri Bölme

| Küme | Ürün | Kullanım |
|---|---|---|
| gold | 40 | Elle etiketlenir; iki sistem bu kümede değerlendirilir |
| dev | 5 | Prompt denemesi; test kümesinden ayrıdır |
| rest | 155 | Tam koşu ve Alt Soru 2 analizi |

## 4. Örneklem İstatistikleri

| Ölçü | Değer |
|---|---|
| Ürün başına yorum | 129.7 (medyan 38, min 10, max 4115) |
| Ürün başına negatif yorum | 18.4 (medyan 6, min 3, max 642) |
| Ürün başına ortalama puan | 3.89 |
| Açıklaması dolu ürün | 112/200 (%56) |
| Özellik listesi dolu ürün | 200/200 |
| Fiyat ($), fiyatı olan 132 ürün | ort. 33.65, medyan 26.49 |
| Yorum tarih aralığı | 2008-06-17 – 2023-09-02 |
| Negatif yorumların puan dağılımı | 1★: 867, 2★: 647 |
| Temizlik sonrası HTML etiketi kalan yorum | 0 |
| Ayıklanan tekrarlı negatif yorum (200 üründe) | 123 |

## 5. Ana Kategori Dağılımı (main_category)

| Kategori | Ürün |
|---|---|
| AMAZON FASHION | 194 |
| Sports & Outdoors | 4 |
| Amazon Home | 1 |
| (boş) | 1 |

## 5b. Kategori Yolu (ilk 3 seviye) — örneklemdeki en sık 10

| Kategori yolu | Ürün |
|---|---|
| Clothing, Shoes & Jewelry > Women > Clothing | 64 |
| Clothing, Shoes & Jewelry > Women > Shoes | 38 |
| Clothing, Shoes & Jewelry > Men > Clothing | 35 |
| Clothing, Shoes & Jewelry > Men > Shoes | 14 |
| Clothing, Shoes & Jewelry > Novelty & More > Clothing | 14 |
| Clothing, Shoes & Jewelry > Men > Uniforms, Work & Safety | 5 |
| Clothing, Shoes & Jewelry > Girls > Clothing | 5 |
| Clothing, Shoes & Jewelry > Girls > Shoes | 4 |
| Clothing, Shoes & Jewelry > Baby > Baby Girls | 4 |
| Clothing, Shoes & Jewelry > Boys > Clothing | 3 |

Adaylar içinde kategori alanı dolu olan: 361,400

Kapsam dışı bırakılan ürünlerden örnekler:

- Joyci Fashion Faux Rabbit Fur Collar Shawl Wrap Stole Fake C  [Clothing, Shoes & Jewelry > Women > Accessories]
- ColorGround Kids Size Prestyled Bald Wig for Halloween and C  [Clothing, Shoes & Jewelry > Costumes & Accessories > Kids & Baby]
- C.C Hatsandscarf Exclusives Unisex Solid Ribbed Beanie with   [Clothing, Shoes & Jewelry > Women > Accessories]
- Hipsy Women's Adjustable NO Slip Skinny Tech Sport Headband   [Clothing, Shoes & Jewelry > Women > Accessories]
- Claw Earrings Cuff for Women Zircon Needle Stud Earrings for  [Clothing, Shoes & Jewelry > Women > Jewelry]
- AWAYTR Sunflower Headband Women Hippie Headwear Bohomia Feat  [Clothing, Shoes & Jewelry > Women > Accessories]
- Vanlison Large Sling Bag Chest Shoulder Bag Purse Backpack C  [Clothing, Shoes & Jewelry > Luggage & Travel Gear > Backpacks]
- Family Charms, 925 Sterling Silver Mother Father Daughter So  [Clothing, Shoes & Jewelry > Women > Jewelry]
- ThunderFit Women’s Silicone Wedding Ring - Rubber Wedding Ba  [Clothing, Shoes & Jewelry > Women > Jewelry]
- Deluxe Cowboy Hat Team Spirit Adult Unisex Fan Gear Party Ha  [Clothing, Shoes & Jewelry > Costumes & Accessories > Men]
- Royce Leather Passport Holder and Travel Document Organizer   [Clothing, Shoes & Jewelry > Luggage & Travel Gear > Travel Accessories]
- Hanna Nikole Women Wide Patent Leather Belt Fashion Square H  [Clothing, Shoes & Jewelry > Women > Accessories]
- LED Light Up Flashing Sequin Bow Ties Tie by Mammoth Sales (  [Clothing, Shoes & Jewelry > Men > Accessories]
- Solid 100% Cotton Unisex Bandana - 12 Pack  [Clothing, Shoes & Jewelry > Novelty & More > Clothing]
- Gildan Adult Fleece Hooded Sweatshirt, Style G18500  [Clothing, Shoes & Jewelry > Westlake]

## 6. En Sık 10 Mağaza

Farklı mağaza sayısı: 181

| Mağaza | Ürün |
|---|---|
| Hanes | 5 |
| Columbia | 3 |
| adidas | 3 |
| Merrell | 3 |
| Crocs | 2 |
| LifeStride | 2 |
| Touch Ups | 2 |
| Clarks | 2 |
| Fruit of the Loom | 2 |
| Champion | 2 |
