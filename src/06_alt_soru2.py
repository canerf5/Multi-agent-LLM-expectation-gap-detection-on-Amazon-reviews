"""
FAZ 9 — Alt Soru 2: gap tiplerinin sıklığı ve ürün puanıyla ilişkisi (kapsam §6; yontem §7.4)

Veri: 200 ürünün (test + geliştirme + kalan) 3 ajanlı sistem çıktısı (Faz 7 tam koşusu) ve
ürünün veri setindeki tüm yorumlarından hesaplanan ortalama puan (products_200.jsonl >
mean_rating_sample; meta verisindeki average_rating KULLANILMAZ, gerekçe yontem §7.4).

Her tip için:
  - sıklık: tipin tespit edildiği ürün sayısı ve oranı
  - tipe sahip olan / olmayan ürünlerin ortalama ve medyan puanı
  - Mann-Whitney U (iki yönlü); etki büyüklüğü: rank-biserial korelasyon r = 1 − 2U / (n1·n2)
    (U, tipe sahip olan grup için; r > 0 → tipe sahip ürünlerin puanı daha düşük)
  - Holm düzeltmesi (α = 0,05), test edilebilen tipler üzerinden; bir grubu boş kalan tip test edilmez
Sınırlılık: analiz elle etiket yerine sistem çıktısına dayanır.

Çıktılar: reports/alt_soru2/sonuc.csv, reports/alt_soru2/rapor.md

Kullanım:
    python src/06_alt_soru2.py
"""
import csv
import json
import sys
from pathlib import Path
from statistics import mean, median

from scipy.stats import mannwhitneyu

import pipeline
from schemas import GOLD_COLS

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "outputs" / "runs" / "all" / "2026-10-30_204205_multi_agent_faz7-tam-kosu"
OUT = ROOT / "reports" / "alt_soru2"
ALPHA = 0.05


def holm(pvals):
    """Holm düzeltmeli p-değerleri (girdi sırasıyla)."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj, running = [0.0] * m, 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvals[i]))
        adj[i] = running
    return adj


def analyse(results, ratings):
    """results: {asin: {tip: 0/1}}, ratings: {asin: puan}. Tip başına satırlar."""
    asins = sorted(results)
    rows = []
    for t in GOLD_COLS:
        has = [ratings[a] for a in asins if results[a][t]]
        not_ = [ratings[a] for a in asins if not results[a][t]]
        row = {"tip": t, "urun_var": len(has), "oran_var": len(has) / len(asins), "urun_yok": len(not_),
               "ort_puan_var": mean(has) if has else None, "ort_puan_yok": mean(not_) if not_ else None,
               "medyan_var": median(has) if has else None, "medyan_yok": median(not_) if not_ else None,
               "U": None, "p": None, "r_rank_biserial": None, "p_holm": None, "anlamli": "test edilemedi"}
        if has and not_:
            res = mannwhitneyu(has, not_, alternative="two-sided")
            row.update({"U": float(res.statistic), "p": float(res.pvalue),
                        "r_rank_biserial": 1 - 2 * float(res.statistic) / (len(has) * len(not_))})
        rows.append(row)
    tested = [r for r in rows if r["p"] is not None]
    for r, adj in zip(tested, holm([r["p"] for r in tested])):
        r["p_holm"] = adj
        r["anlamli"] = "evet" if adj < ALPHA else "hayır"
    return rows


def f(x, nd=3):
    return "—" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def main(run_dir=RUN, out_dir=OUT):
    with open(Path(run_dir) / "sonuclar.csv", encoding="utf-8") as fh:
        results = {r["parent_asin"]: {t: int(r[c]) for t, c in GOLD_COLS.items()} for r in csv.DictReader(fh)}
    man = json.loads((Path(run_dir) / "manifest.json").read_text(encoding="utf-8"))
    ratings = {}
    with open(ROOT / "data" / "processed" / "products_200.jsonl", encoding="utf-8") as fh:
        for line in fh:
            p = json.loads(line)
            if p["parent_asin"] in results:
                ratings[p["parent_asin"]] = p["mean_rating_sample"]
    if set(ratings) != set(results) or len(results) != 200:
        raise SystemExit(f"ürün sayısı/eşleşme hatalı: sonuç {len(results)}, puan {len(ratings)}")
    rows = analyse(results, ratings)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "sonuc.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    n_gap = sum(any(v.values()) for v in results.values())
    L = ["# Alt Soru 2 — Gap tipleri ve ürün puanı", "",
         f"Veri: 200 ürünün 3 ajanlı sistem çıktısı (koşu `{man['run_id']}`); puan = ürünün veri setindeki tüm "
         f"yorumlarından hesaplanan ortalama (tüm ürünlerde ortalama {mean(ratings.values()):.2f}). "
         f"Gap tespit edilen ürün: {n_gap}/200.", "",
         "Mann-Whitney U (iki yönlü), Holm düzeltmesi (α = 0,05). r = rank-biserial korelasyon "
         "(r > 0: tipe sahip ürünlerin puanı daha düşük).", "",
         "| Tip | Ürün (oran) | Ort. puan: var / yok | Medyan: var / yok | U | p | p (Holm) | r | Anlamlı |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['tip']} | {r['urun_var']} ({r['oran_var']:.1%}) | {f(r['ort_puan_var'], 2)} / {f(r['ort_puan_yok'], 2)} | "
                 f"{f(r['medyan_var'], 2)} / {f(r['medyan_yok'], 2)} | {f(r['U'], 1)} | {f(r['p'], 4)} | "
                 f"{f(r['p_holm'], 4)} | {f(r['r_rank_biserial'], 3)} | {r['anlamli']} |")
    L += ["", "Sınırlılık: analiz elle etiket yerine sistem çıktısına dayanır; sistemin test kümesindeki başarısı "
          "(gap tipi micro-F1 0,683) bu analizin güvenilirliği için referanstır.", ""]
    (out_dir / "rapor.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    sys.exit(main())
