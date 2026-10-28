# Multi-Agent LLM Expectation Gap Detection on Amazon Reviews

**Bitirme projesi:** E-ticaret ürün sayfalarında çok ajanlı LLM tabanlı beklenti uyumsuzluğu tespiti.
Veri: Amazon Reviews 2023 (McAuley Lab) · Kategori: Clothing_Shoes_and_Jewelry

Sistem, bir ürün sayfasının **vaadi** ile müşterilerin **şikayetleri** arasındaki farkı (gap) bulur,
tipini ve seviyesini belirler ve sayfa için iyileştirme önerisi üretir. 3 ajanlı sistem, tek prompt'luk
bir baseline ile 40 ürünlük elle etiketlenmiş test seti üzerinde karşılaştırılır.

## Kurulum (Faz 1)

```bash
git clone https://github.com/canerf5/Multi-agent-LLM-expectation-gap-detection-on-Amazon-reviews.git
cd Multi-agent-LLM-expectation-gap-detection-on-Amazon-reviews

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

`.env.example` dosyasını kopyalayıp adını `.env` yap, içine OpenAI anahtarını yaz (Faz 5'te gerekecek).

## Çalıştırma sırası

| Faz | Komut | Çıktı |
|---|---|---|
| 2. Veri | `python src/01_sample_data.py --reviews-file data/raw/Clothing_Shoes_and_Jewelry.jsonl --meta-file data/raw/meta_Clothing_Shoes_and_Jewelry.jsonl` | `data/processed/products_200.jsonl` |
| 4. Etiketleme dosyası | `python src/02_make_labeling_sheet.py` | `data/gold/etiketleme.xlsx` |
| 4. Etiketleme | Excel'de sarı sütunları doldur → commit | — |
| 4. Gold dışa aktarma | `python src/03_export_gold.py` | `data/gold/gold_40.csv` |
| 5–6. Ajanlar + baseline | *(eklenecek)* | — |
| 7. Tam koşu | *(eklenecek)* | `outputs/` |
| 8. Değerlendirme | *(eklenecek)* | `reports/` |

> Ham dosyalar (Hugging Face → McAuley-Lab/Amazon-Reviews-2023, `raw/review_categories/` ve `raw/meta_categories/`) elle indirilip `data/raw/` altına konur (~43 GB, git'e girmez). Dosya verilmezse script Hugging Face'ten stream eder ama meta dosyasının tamamını okuduğu için çok yavaştır.

## Klasörler

```
config.yaml          # tüm ayarlar (kategori, örneklem, model)
src/                 # script'ler (numara sırasıyla çalışır)
prompts/             # ajan prompt'ları
data/raw/            # git'e girmez
data/processed/      # seçilen 200 ürün
data/gold/           # elle etiketler (cevap anahtarı)
docs/                # etiketleme kuralları
outputs/             # LLM çıktıları + cache
reports/             # metrikler, grafikler
```

## Fazlar

- [x] 1. Kurulum
- [x] 2. Veri toplama
- [x] 3. Etiketleme kuralları (`docs/etiketleme_kurallari.md`)
- [x] 4. 40 ürün etiketleme → `v0.1-data` tag
- [ ] 5. 3 ajan
- [ ] 6. Baseline + 5 dev ürünle deneme → `v0.2-agents` tag
- [ ] 7. 200 ürün tam koşu
- [ ] 8. Değerlendirme → `v0.3-results` tag
- [ ] 9. Hata analizi + alt sorular
- [ ] 10. Tez yazımı → `v1.0-final` tag

## Tekrarlanabilirlik
- `seed: 42` sabit; örneklem her çalıştırmada aynı çıkar.
- LLM çağrıları `temperature=0` ve cache'lenir.
- Gold etiketler, sistem çalıştırılmadan önce commit edilir.
