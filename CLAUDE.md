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
src/schemas.py                 Faz 5: GAP_TYPES/LEVELS, gold sütun eşlemesi, strict JSON şemaları
src/llm.py                     Faz 5: tek ortak call_llm (önbellek, log, maliyet, tekrar deneme)
src/agents.py                  Faz 5: 3 ajan, girdi metni ve kontrolü, tutarlılık kontrolü
src/pipeline.py                Faz 5: Ajan 1 -> 2 -> 3; varsayılan dev; gold kilidi
src/runs.py                    Faz 5: koşu kaydı (manifest, sonuclar.csv, olcumler.json, index.csv); iki sisteme ortak
src/audit_gold.py              gold sızıntı denetimi (yalnızca kullanıcı çalıştırır)
prompts/*.md                   ajan prompt'ları; {KURALLAR} çalışma anında kurallar dosyasından doldurulur
tests/test_faz5.py             API'siz testler (sahte LLM)
tests/test_bariyer.py          gold bariyeri testleri
data/raw/                      ham Amazon dosyaları (~43 GB), git'e GİRMEZ
data/processed/products_200.jsonl  örneklem (gold 40 / dev 5 / rest 155 / reserve 10)
data/gold/gold_40.csv          ALTIN STANDART (değerlendirmede tek kaynak)
reports/                       örneklem raporu, ileride metrikler
outputs/                       LLM çıktıları: runs/<split>/<koşu>/ (her koşu ayrı, üzerine yazılmaz) + runs/index.csv,
                               multi_agent/<split>/<asin>/ (son koşunun kopyası), cache/, llm_log.jsonl
```
Python ortamı: `.venv` (`.venv/bin/python`). Ham veriyle örneklem komutu README'deki "Çalıştırma sırası" tablosunda.

## Değişmez kurallar
1. **Altın standart donduruldu** (`v0.1-data` tag'i). `data/gold/etiketleme.xlsx` ve `data/gold/gold_40.csv` artık DEĞİŞTİRİLMEZ. Değişiklik gerekiyorsa önce kullanıcıya sor; yapılırsa gerekçesi `docs/kapsam.md` revizyon notlarına yazılır.
2. **Örneklem donduruldu** (`v0.1-sample` tag'i). `products_200.jsonl`, `config.yaml` örneklem ayarları ve `seed: 42` değiştirilmez.
3. **Test seti izolasyonu:** Prompt geliştirme ve deneme SADECE `dev` (5 ürün) ile yapılır. Gold ürünler prompt ayarlamak için kullanılmaz, gold sonuçlarına bakarak prompt değiştirilmez.
4. **Aynı girdi, aynı kurallar:** İki sistem (3 ajan ve baseline) aynı modeli, aynı girdiyi ve aynı JSON şemasını kullanır; tek fark mimaridir. Sistemlere yorumların TAM metni verilir (jsonl'deki hali). Ajan 2'nin ilgisiz saydığı şikayetler, etiketleme kurallarındaki "Sayılmayanlar" ile aynıdır (kargo/paketleme, satıcı/iade süreci, kullanılmış ürün gönderimi, kişisel zevk).
5. **Tekrarlanabilirlik:** LLM çağrıları `temperature = 0` ve önbellekli; her ajanın ara çıktısı `outputs/` altında saklanır.
6. **Metrikler** (`docs/kapsam.md` §6): ana metrik gap tipi micro-F1 (+ 6 tip macro-F1); Eksik Bilgi (support = 0) hesaplamadan çıkarılır ve raporda ayrıca gösterilir; gap var/yok Macro F1 ve seviye isabeti ikincil; accuracy yalnızca çoğunluk referansıyla; iki sistem farkı 1000 tekrarlı eşleştirilmiş bootstrap ile sınanır. Değerlendirme yalnızca `gold_40.csv`'yi okur (Yedekler sayfası kullanılmaz).

## LLM çağrıları
- Tüm çağrılar `src/llm.py` > `call_llm` üzerinden; doğrudan OpenAI çağrısı yazma.
- `config.yaml` > `model_verified: false` iken gerçek API çağrısı yapılmaz (kilit). Model sürümü ve fiyat doğrulanınca `true` yapılır.
- Gerçek API çağrısından önce `python src/pipeline.py --estimate` ile maliyet tahmini verilir ve kullanıcı onayı alınır.
- Prompt'lara kural metni elle kopyalanmaz; kurallar `docs/etiketleme_kurallari.md`'den çalışma anında okunur. Prompt'larda gold ürün örneği kullanılmaz.
- Gold ürünleri (tahmin dahil) yalnızca kullanıcı açıkça isteyince ve `--split gold` ile işlenir.

## Gold bariyeri
Altın standarda erişim talimatla değil, **teknik engelle** kapalıdır (`.claude/settings.json`):

- **İzin kuralları:** `Read(/data/gold/**)` ve `Edit(/data/gold/**)` deny. (`Edit` kuralı Write ve NotebookEdit'i de kapsar; `Write(...)` kuralı Claude Code'da hiç eşleşmediği için kullanılmaz.)
- **PreToolUse hook** (`.claude/hooks/gold_guard.py`, tüm araçlar): araç girdisinde şunlar geçerse çağrı engellenir (çıkış kodu 2):
  - gold: `data/gold`, `gold_40`, `etiketleme.xlsx`, `gozden_gecirme`, `--split gold` / `--split=gold`, ve Bash'te gold dosyalarına erişen script'lerin çalıştırılması (`audit_gold`, `02_make_labeling_sheet`, `03_export_gold`, `04_review_gold`)
  - her zaman: `.gold_unlock` kilit dosyası (oluşturma, silme, okuma)
  - her zaman: `.claude/settings*.json` ve `.claude/hooks/` dosyalarını değiştirme, `gold_guard` / `disableAllHooks` geçen komutlar (bariyeri kapatmayı önlemek için; okumak serbest)
- **Kilit:** Yalnızca KULLANICI, kendi terminalinde `touch .gold_unlock` ile açar. Kilit açıkken yalnızca gold maddeleri serbest kalır; kilit dosyası ve `.claude/` kuralları her durumda geçerlidir. İş bitince kullanıcı `rm .gold_unlock` ile kapatır. `src/pipeline.py --split gold` de kilit dosyası yoksa çalışmaz.
- **Denetim:** Faz 7 öncesi kullanıcı `.venv/bin/python src/audit_gold.py` çalıştırır (gold ASIN/başlıklarını prompts/, src/, outputs/cache/, llm_log ve outputs/multi_agent/dev içinde arar; beklenen: hiç iz yok).
- Asistan bariyere takılırsa dolanmaya çalışmaz; kullanıcıya ne yapması gerektiğini söyler.
- **Sınırları:** Hook komut METNİNE bakar; metinde geçmeyen dolaylı erişimi (ör. yolu parçalayıp birleştiren bir script) tam olarak yakalayamaz. Bu yüzden denetim script'i ve "gold'a bakarak prompt değiştirilmez" kuralı ayrıca geçerlidir. Testler: `python -m unittest tests.test_bariyer -v`.

## Güvenlik
- Repo **public**. API anahtarı yalnızca `.env` dosyasında durur (`.gitignore`'da). Anahtarı koda, dokümana, çıktıya veya commit mesajına yazma.
- `data/raw/` ve büyük dosyalar commit'lenmez.

## Git
- Commit ve push yalnızca kullanıcı isteyince. Tag'ler README'deki faz listesine göre (`v0.2-agents`, `v0.3-results`, `v1.0-final`).
- Bir şeyi commit'lemeden önce kullanıcıya değişen dosyaları ve özeti göster.
- Silme veya üzerine yazma öncesi hedefi kontrol et; elle girilmiş etiket içeren dosyaları yeniden üretme.
