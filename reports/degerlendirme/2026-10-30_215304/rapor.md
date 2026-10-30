# Değerlendirme Raporu

Altın standart: 40 ürün (`v0.1-data`, sha256 `76dd9c6fbc3b`) · Koşular: multi_agent `2026-10-30_204205_multi_agent_faz7-tam-kosu`, baseline `2026-10-30_212510_baseline_faz7-tam-kosu` · Bootstrap: 1000 tekrar, tohum 42

## Metrikler ve eşleştirilmiş karşılaştırma

| Metrik | 3 ajan | Baseline | Fark (3 ajan − baseline) [%95 GA] | Fark ≤ 0 oranı | Anlamlı |
|---|---|---|---|---|---|
| Gap tipi micro-F1 (ana) | 0.683 | 0.653 | 0.030 [-0.062, 0.119] | 0.287 | hayır |
| Gap tipi macro-F1 (6 tip) | 0.565 | 0.530 | 0.034 [-0.126, 0.154] | 0.383 | hayır |
| Gap var/yok Macro F1 | 0.657 | 0.474 | 0.183 [-0.051, 0.381] | 0.135 | hayır |
| Gap var/yok accuracy | 0.850 | 0.900 | -0.050 [-0.175, 0.051] | 0.860 | hayır |
| Seviye isabeti | 0.450 | 0.375 | 0.075 [-0.100, 0.250] | 0.260 | hayır |
| Seviye macro-F1 (3 seviye) | 0.439 | 0.257 | 0.182 [-0.026, 0.353] | 0.043 | hayır |

Çoğunluk referansları: hep "Evet" → accuracy 0.900, Macro F1 0.474; hep "Orta" → seviye isabeti 0.700, 3 seviye macro-F1 0.275.

## Tip bazında (6 tip; Eksik Bilgi ayrıca)

| Tip | Support | 3 ajan P / R / F1 | Baseline P / R / F1 |
|---|---|---|---|
| Beden/Kalıp | 24 | 0.91 / 0.88 / 0.89 | 0.68 / 0.96 / 0.79 |
| Renk | 5 | 0.67 / 0.40 / 0.50 | 0.75 / 0.60 / 0.67 |
| Görsel | 2 | 0.33 / 0.50 / 0.40 | 0.00 / 0.00 / 0.00 |
| Kalite | 5 | 0.38 / 0.60 / 0.46 | 0.25 / 1.00 / 0.40 |
| Malzeme | 13 | 0.62 / 0.77 / 0.69 | 0.67 / 0.77 / 0.71 |
| Dayanıklılık | 13 | 0.80 / 0.31 / 0.44 | 0.70 / 0.54 / 0.61 |
| Eksik Bilgi (hesaplama dışı) | 0 | 0.00 / 0.00 / — | 0.00 / 0.00 / 0.00 |

## Süreç

| | 3 ajan | Baseline |
|---|---|---|
| Tutarsız karar | 2 | 21 |
| Eksik Bilgi yanlış pozitif | 0 | 2 |
| Eşdeğer maliyet ($) | 0.08661 | 0.070389 |
| Eşdeğer API süresi (sn) | 481.6 | 328.0 |

Noktasal değerler tüm test kümesi üzerindendir; güven aralıkları `metrikler.csv` ve `karsilastirma.csv` dosyalarındadır. Tanımsız sınıf kuralı ve bootstrap ayrıntısı: `girdi.json`.
