# Alt Soru 2 — Gap tipleri ve ürün puanı

Veri: 200 ürünün 3 ajanlı sistem çıktısı (koşu `2026-10-30_204205_multi_agent_faz7-tam-kosu`); puan = ürünün veri setindeki tüm yorumlarından hesaplanan ortalama (tüm ürünlerde ortalama 3.89). Gap tespit edilen ürün: 176/200.

Mann-Whitney U (iki yönlü), Holm düzeltmesi (α = 0,05). r = rank-biserial korelasyon (r > 0: tipe sahip ürünlerin puanı daha düşük).

| Tip | Ürün (oran) | Ort. puan: var / yok | Medyan: var / yok | U | p | p (Holm) | r | Anlamlı |
|---|---|---|---|---|---|---|---|---|
| Beden/Kalıp | 134 (67.0%) | 3.88 / 3.90 | 4.00 / 4.00 | 4355.0 | 0.8628 | 1.0000 | 0.015 | hayır |
| Renk | 5 (2.5%) | 4.07 / 3.88 | 4.19 / 4.00 | 602.0 | 0.3723 | 1.0000 | -0.235 | hayır |
| Görsel | 15 (7.5%) | 3.70 / 3.90 | 3.81 / 4.00 | 1180.5 | 0.3381 | 1.0000 | 0.149 | hayır |
| Kalite | 40 (20.0%) | 3.95 / 3.87 | 4.12 / 3.94 | 3490.0 | 0.3765 | 1.0000 | -0.091 | hayır |
| Malzeme | 83 (41.5%) | 3.88 / 3.89 | 4.01 / 4.00 | 4877.0 | 0.9585 | 1.0000 | -0.004 | hayır |
| Dayanıklılık | 27 (13.5%) | 3.80 / 3.90 | 4.00 / 4.00 | 2135.0 | 0.4746 | 1.0000 | 0.086 | hayır |
| Eksik Bilgi | 6 (3.0%) | 3.86 / 3.89 | 4.11 / 4.00 | 583.0 | 0.9971 | 1.0000 | -0.002 | hayır |

Sınırlılık: analiz elle etiket yerine sistem çıktısına dayanır; sistemin test kümesindeki başarısı (gap tipi micro-F1 0,683) bu analizin güvenilirliği için referanstır.
