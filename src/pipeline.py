"""
FAZ 5 — Çok ajanlı sistem: Ajan 1 -> Ajan 2 -> Ajan 3

Varsayılan olarak YALNIZCA dev ürünlerde çalışır. gold / rest için açıkça --split
verilmelidir. GOLD KİLİDİ: --split gold ancak repo kökünde .gold_unlock varsa (kilidi yalnızca kullanıcı
açar: touch .gold_unlock), data/gold/ altında commit'lenmemiş değişiklik yoksa, v0.1-data
tag'i varsa ve data/gold/ tag'deki haliyle aynıysa çalışır.

Çıktılar:
  outputs/multi_agent/<split>/<asin>/agent1.json, agent2.json, agent3.json, meta.json
  outputs/multi_agent/<split>/tutarsiz.jsonl   (ikinci denemede de tutarsız kalanlar)
  outputs/llm_log.jsonl, outputs/cache/         (src/llm.py)

Kullanım:
    python src/pipeline.py --estimate                 # çağrı sayısı + tahmini maliyet (API yok)
    python src/pipeline.py --asin B08V4QYTR6          # tek dev ürün
    python src/pipeline.py                            # 5 dev ürünün hepsi
    python src/pipeline.py --split gold               # yalnızca kilit koşulları sağlanırsa
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

import agents
import llm
from schemas import EXPECTATION_SCHEMA, RESULT_SCHEMA, REVIEW_MINING_SCHEMA

ROOT = Path(__file__).resolve().parents[1]
GOLD_TAG = "v0.1-data"
UNLOCK_FILE = ROOT / ".gold_unlock"   # yalnızca kullanıcı oluşturur (kendi terminalinde)


class GoldLockError(RuntimeError):
    pass


def load_cfg():
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_products(split):
    cfg = load_cfg()
    with open(ROOT / "data" / "processed" / f"products_{cfg['n_products']}.jsonl", encoding="utf-8") as f:
        return [p for p in map(json.loads, f) if p["split"] == split]


def gold_lock(run=subprocess.run, unlock_file=None):
    """Gold üzerinde çalışmaya izin verilip verilmediğini denetler; değilse GoldLockError.
    Sıra: kullanıcı kilidi (.gold_unlock) -> commit'lenmemiş değişiklik yok -> tag var -> tag ile aynı."""
    if not Path(unlock_file or UNLOCK_FILE).exists():
        raise GoldLockError("Kilidi kullanıcı açmalı: touch .gold_unlock")
    def git(*a):
        return run(["git", *a], cwd=ROOT, capture_output=True, text=True)
    st = git("status", "--porcelain", "--", "data/gold/")
    if st.returncode != 0:
        raise GoldLockError(f"git status çalışmadı: {st.stderr.strip()}")
    if st.stdout.strip():
        raise GoldLockError("data/gold/ altında commit'lenmemiş değişiklik var:\n" + st.stdout.rstrip())
    if git("rev-parse", "-q", "--verify", f"refs/tags/{GOLD_TAG}").returncode != 0:
        raise GoldLockError(f"{GOLD_TAG} tag'i bulunamadı (gold etiketleri dondurulmamış)")
    if git("diff", "--quiet", GOLD_TAG, "--", "data/gold/").returncode != 0:
        raise GoldLockError(f"data/gold/ içeriği {GOLD_TAG} tag'indeki halinden farklı")


def estimate(products, out_tokens=(600, 900, 700)):
    """API'siz kaba tahmin: girdi token ≈ karakter / 4 (+ şema), çıktı token sabit varsayım."""
    cfg = load_cfg()
    p1, p2, p3 = (agents.load_prompt(n) for n in ("expectation", "review_mining", "gap_fix"))
    sch = {k: len(json.dumps(s["schema"])) for k, s in
           (("a1", EXPECTATION_SCHEMA), ("a2", REVIEW_MINING_SCHEMA), ("a3", RESULT_SCHEMA))}
    tin = tout = 0
    rows = []
    for p in products:
        i1 = (len(p1) + len(agents.page_text(p)) + sch["a1"]) / 4
        i2 = (len(p2) + len(agents.reviews_text(p)) + sch["a2"]) / 4
        i3 = (len(p3) + 4 * (out_tokens[0] + out_tokens[1]) + sch["a3"]) / 4
        ins, outs = i1 + i2 + i3, sum(out_tokens)
        tin, tout = tin + ins, tout + outs
        rows.append((p["parent_asin"], round(ins), outs))
    cost = tin * cfg["price_input_per_1m"] / 1e6 + tout * cfg["price_output_per_1m"] / 1e6
    return {"urun": len(products), "cagri": 3 * len(products), "cagri_tekrar_dahil_en_fazla": 4 * len(products),
            "girdi_token": round(tin), "cikti_token": tout, "maliyet_usd": cost,
            "maliyet_usd_tekrar_dahil_en_fazla": cost * 4 / 3, "satirlar": rows}


def run_product(p, split, out_root):
    page, reviews = agents.page_text(p), agents.reviews_text(p)
    errs = agents.check_input(p, page, reviews)
    if errs:
        raise ValueError(f"{p['parent_asin']}: girdi kontrolü başarısız: {errs}")
    d = out_root / split / p["parent_asin"]
    d.mkdir(parents=True, exist_ok=True)

    a1 = agents.agent1(p)
    (d / "agent1.json").write_text(json.dumps(a1, ensure_ascii=False, indent=2), encoding="utf-8")
    a2 = agents.agent2(p)
    (d / "agent2.json").write_text(json.dumps(a2, ensure_ascii=False, indent=2), encoding="utf-8")
    a3, meta = agents.agent3(a1, a2, len(p["negative_reviews"]), p["parent_asin"])
    (d / "agent3.json").write_text(json.dumps(a3, ensure_ascii=False, indent=2), encoding="utf-8")

    meta.update({"parent_asin": p["parent_asin"], "split": split, "n_reviews": len(p["negative_reviews"]),
                 "agent2_uyarilari": agents.review_mining_warnings(a2, len(p["negative_reviews"])),
                 "time": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    if meta["tutarsiz"]:
        with open(out_root / split / "tutarsiz.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"parent_asin": p["parent_asin"], "ihlaller": meta["ihlaller"],
                                "time": meta["time"]}, ensure_ascii=False) + "\n")
    return a3, meta


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", choices=["dev", "gold", "rest"], default="dev")
    ap.add_argument("--asin", action="append", help="yalnızca bu ürün(ler); seçili split içinde olmalı")
    ap.add_argument("--estimate", action="store_true", help="API çağırmadan çağrı sayısı ve maliyet tahmini")
    args = ap.parse_args(argv)

    if args.split == "gold":
        gold_lock()
    products = load_products(args.split)
    if args.asin:
        wanted = set(args.asin)
        unknown = wanted - {p["parent_asin"] for p in products}
        if unknown:
            raise SystemExit(f"{sorted(unknown)} '{args.split}' kümesinde değil")
        products = [p for p in products if p["parent_asin"] in wanted]

    if args.estimate:
        e = estimate(products)
        print(f"Küme: {args.split} | ürün: {e['urun']} | çağrı: {e['cagri']} "
              f"(tutarlılık tekrarıyla en fazla {e['cagri_tekrar_dahil_en_fazla']})")
        print(f"Tahmini token: girdi ~{e['girdi_token']:,}, çıktı ~{e['cikti_token']:,}")
        print(f"Tahmini maliyet: ~${e['maliyet_usd']:.4f} (tekrarlarla en fazla ~${e['maliyet_usd_tekrar_dahil_en_fazla']:.4f}) "
              f"| fiyat: ${load_cfg()['price_input_per_1m']}/{load_cfg()['price_output_per_1m']} per 1M "
              f"(doğrulandı: {load_cfg().get('model_verified')})")
        return

    out_root = llm.OUT_DIR / "multi_agent"
    n_log_before = sum(1 for _ in open(llm.OUT_DIR / "llm_log.jsonl", encoding="utf-8")) \
        if (llm.OUT_DIR / "llm_log.jsonl").exists() else 0
    for p in products:
        a3, meta = run_product(p, args.split, out_root)
        flag = " TUTARSIZ" if meta["tutarsiz"] else (" (tekrar ile düzeldi)" if meta["deneme"] == 2 else "")
        print(f"{p['parent_asin']}: gap_var={a3['gap_var']} tipler={a3['gap_tipleri']} seviye={a3['seviye']}{flag}")
    new = []
    if (llm.OUT_DIR / "llm_log.jsonl").exists():
        with open(llm.OUT_DIR / "llm_log.jsonl", encoding="utf-8") as f:
            new = [json.loads(l) for l in list(f)[n_log_before:]]
    cost = sum(e.get("cost_usd") or 0 for e in new)
    print(f"\nÇağrı: {len(new)} (önbellekten: {sum(e.get('cache_hit', False) for e in new)}) | "
          f"token: girdi {sum(e.get('input_tokens', 0) for e in new):,}, çıktı {sum(e.get('output_tokens', 0) for e in new):,} | "
          f"maliyet: ${cost:.6f}")


if __name__ == "__main__":
    sys.exit(main())
