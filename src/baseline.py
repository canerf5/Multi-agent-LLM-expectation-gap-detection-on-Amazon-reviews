"""
FAZ 6 — Tek LLM baseline (kapsam §3; yontem §4.4)

Tek prompt (prompts/baseline.md): sayfa metni + numaralı negatif yorumlar birlikte verilir, model
doğrudan ORTAK SONUÇ şemasında (RESULT_SCHEMA) cevap verir. 3 ajanlı sistemle AYNI: model,
temperature, girdi metni (page_text + reviews_text), kural bölümleri ({KURALLAR}, {ORNEK}),
sonuç şeması, tutarlılık kontrolü ve tek tekrar (agents.checked_call), gold kilidi, seçenekler ve
koşu kaydı (src/runs.py). Tek fark mimari: ara çıktı yoktur. Alıntı kaynağı sayfa metnidir.

Çıktılar:
  outputs/runs/<split>/<run_id>/                KOŞU KAYDI (sistem = "baseline")
  outputs/baseline/<split>/<asin>/              SON koşunun kopyası: baseline.json, meta.json, ozet.txt
  outputs/llm_log.jsonl, outputs/cache/         (src/llm.py)

Kullanım:
    python src/baseline.py --estimate                 # çağrı sayısı + tahmini maliyet (API yok)
    python src/baseline.py --asin B08V4QYTR6          # tek dev ürün
    python src/baseline.py --not "deneme1"            # 5 dev ürünün hepsi; koşuya kısa not
"""
import json
import sys
import time
from datetime import datetime, timezone

import agents
import pipeline
from schemas import RESULT_SCHEMA

SYSTEM = "baseline"


def estimate(products, out_tokens=900):
    """API'siz kaba tahmin: girdi token ≈ karakter / 4 (+ şema), çıktı token sabit varsayım."""
    cfg = pipeline.load_cfg()
    prompt = agents.load_prompt("baseline")
    sch = len(json.dumps(RESULT_SCHEMA["schema"]))
    tin = sum((len(prompt) + len(agents.baseline_input(agents.page_text(p), agents.reviews_text(p))) + sch) / 4
              for p in products)
    tout = out_tokens * len(products)
    cost = tin * cfg["price_input_per_1m"] / 1e6 + tout * cfg["price_output_per_1m"] / 1e6
    # tekrar çağrısı: aynı girdi + önceki cevap; en fazla yaklaşık 2 kat
    return {"urun": len(products), "cagri": len(products), "cagri_tekrar_dahil_en_fazla": 2 * len(products),
            "girdi_token": round(tin), "cikti_token": tout, "maliyet_usd": cost,
            "maliyet_usd_tekrar_dahil_en_fazla": cost * 2}


def run_product(p, run_dir):
    """Bir ürünü baseline'dan geçirir; çıktıları run_dir/<asin>/ altına yazar. (sonuç, meta) döndürür."""
    t0 = time.perf_counter()
    page, reviews = agents.page_text(p), agents.reviews_text(p)
    errs = agents.check_input(p, page, reviews)
    if errs:
        raise ValueError(f"{p['parent_asin']}: girdi kontrolü başarısız: {errs}")
    d = run_dir / p["parent_asin"]
    d.mkdir(parents=True, exist_ok=True)

    res, meta = agents.baseline(p)
    (d / "baseline.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    (d / "ozet.txt").write_text(agents.render_text(p["parent_asin"], res) + "\n", encoding="utf-8")
    meta.update({"parent_asin": p["parent_asin"], "split": p["split"], "run_id": run_dir.name,
                 "n_reviews": len(p["negative_reviews"]),
                 "sure_duvar_sn": round(time.perf_counter() - t0, 3),
                 "time": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return res, meta


def main(argv=None):
    args = pipeline.parse_args(argv, __doc__)
    products = pipeline.select_products(args)
    if args.estimate:
        pipeline.print_estimate(args, estimate(products))
        return
    prompts = {"baseline": agents.load_prompt("baseline")}
    return 1 if pipeline.execute(args, products, SYSTEM, prompts, run_product) else None


if __name__ == "__main__":
    sys.exit(main())
