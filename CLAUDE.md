# CLAUDE.md

Bu dosya, bu repoda çalışan yapay zeka asistanları (Claude Code vb.) için proje kılavuzudur.

## Proje
Bitirme tezi: Amazon ürün sayfalarının vaadi ile negatif müşteri yorumları arasındaki beklenti uyumsuzluğunu (gap) 3 ajanlı bir LLM sistemiyle tespit etmek ve tek prompt'luk bir baseline ile 40 ürünlük elle etiketlenmiş test setinde karşılaştırmak.

- Kapsam, yöntem, metrikler: `docs/kapsam.md` (tezin dayanağı; yöntemle ilgili her karar buraya işlenir)
- Etiketleme kuralları (sürüm 2): `docs/etiketleme_kurallari.md`
- Güncel durum ve sıradaki iş: `docs/ilerleme.md`
- Dil: Kullanıcıyla Türkçe yazış. Kod yorumları ve dokümanlar Türkçe.

## Klasörler ve script'ler
```
config.yaml                    tüm ayarlar (kategori, örneklem, seed, model) — script'ler buradan okur
src/01_sample_data.py          Faz 2: ham veriden 200 (+10 yedek) ürünlük örneklem
src/02_make_labeling_sheet.py  Faz 4: etiketleme.xlsx (dosya varsa çalışmayı reddeder)
src/03_export_gold.py          Faz 4: etiketleme.xlsx -> data/gold/gold_40.csv (doğrulamalı)
src/04_review_gold.py          Faz 4: gözden geçirme dosyası (make) ve uygulama (apply)
data/raw/                      ham Amazon dosyaları (~43 GB), git'e GİRMEZ
data/processed/products_200.jsonl  örneklem (gold 40 / dev 5 / rest 155 / reserve 10)
data/gold/gold_40.csv          ALTIN STANDART (değerlendirmede tek kaynak)
reports/                       örneklem raporu, ileride metrikler
outputs/                       LLM çıktıları + önbellek (Faz 5–7)
```
Python ortamı: `.venv` (`.venv/bin/python`). Ham veriyle örneklem komutu README'deki "Çalıştırma sırası" tablosunda.

## Değişmez kurallar
1. **Altın standart donduruldu** (`v0.1-data` tag'i). `data/gold/etiketleme.xlsx` ve `data/gold/gold_40.csv` artık DEĞİŞTİRİLMEZ. Değişiklik gerekiyorsa önce kullanıcıya sor; yapılırsa gerekçesi `docs/kapsam.md` revizyon notlarına yazılır.
2. **Örneklem donduruldu** (`v0.1-sample` tag'i). `products_200.jsonl`, `config.yaml` örneklem ayarları ve `seed: 42` değiştirilmez.
3. **Test seti izolasyonu:** Prompt geliştirme ve deneme SADECE `dev` (5 ürün) ile yapılır. Gold ürünler prompt ayarlamak için kullanılmaz, gold sonuçlarına bakarak prompt değiştirilmez.
4. **Aynı girdi, aynı kurallar:** İki sistem (3 ajan ve baseline) aynı modeli, aynı girdiyi ve aynı JSON şemasını kullanır; tek fark mimaridir. Sistemlere yorumların TAM metni verilir (jsonl'deki hali). Ajan 2'nin ilgisiz saydığı şikayetler, etiketleme kurallarındaki "Sayılmayanlar" ile aynıdır (kargo/paketleme, satıcı/iade süreci, kullanılmış ürün gönderimi, kişisel zevk).
5. **Tekrarlanabilirlik:** LLM çağrıları `temperature = 0` ve önbellekli; her ajanın ara çıktısı `outputs/` altında saklanır.
6. **Metrikler** (`docs/kapsam.md` §6): ana metrik gap tipi micro-F1 (+ 6 tip macro-F1); Eksik Bilgi (support = 0) hesaplamadan çıkarılır ve raporda ayrıca gösterilir; gap var/yok Macro F1 ve seviye isabeti ikincil; accuracy yalnızca çoğunluk referansıyla; iki sistem farkı 1000 tekrarlı eşleştirilmiş bootstrap ile sınanır. Değerlendirme yalnızca `gold_40.csv`'yi okur (Yedekler sayfası kullanılmaz).

## Güvenlik
- Repo **public**. API anahtarı yalnızca `.env` dosyasında durur (`.gitignore`'da). Anahtarı koda, dokümana, çıktıya veya commit mesajına yazma.
- `data/raw/` ve büyük dosyalar commit'lenmez.

## Git
- Commit ve push yalnızca kullanıcı isteyince. Tag'ler README'deki faz listesine göre (`v0.2-agents`, `v0.3-results`, `v1.0-final`).
- Bir şeyi commit'lemeden önce kullanıcıya değişen dosyaları ve özeti göster.
- Silme veya üzerine yazma öncesi hedefi kontrol et; elle girilmiş etiket içeren dosyaları yeniden üretme.
