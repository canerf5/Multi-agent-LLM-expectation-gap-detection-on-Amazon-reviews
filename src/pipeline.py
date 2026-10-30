"""
FAZ 5 — Çok ajanlı sistem: Ajan 1 -> Ajan 2 -> Ajan 3

Varsayılan olarak YALNIZCA dev ürünlerde çalışır. gold / rest için açıkça --split
verilmelidir. GOLD KİLİDİ: --split gold ancak repo kökünde .gold_unlock varsa (kilidi yalnızca kullanıcı
açar: touch .gold_unlock), data/gold/ altında commit'lenmemiş değişiklik yoksa, v0.1-data
tag'i varsa ve data/gold/ tag'deki haliyle aynıysa çalışır.

Çıktılar:
  outputs/runs/<split>/<run_id>/                KOŞU KAYDI (src/runs.py): her koşu ayrı klasör; manifest,
                                                prompt'lar, <asin>/ ara çıktıları, sonuclar.csv, ozetler.txt,
                                                llm_calls.jsonl, olcumler.json; outputs/runs/index.csv
  outputs/multi_agent/<split>/<asin>/           SON koşunun kopyası: agent1.json, agent2.json, agent3.json,
                                                meta.json, ozet.txt (kapsam §9 metin biçimi)
  outputs/multi_agent/<split>/tutarsiz.jsonl    (ikinci denemede de tutarsız kalanlar)
  outputs/llm_log.jsonl, outputs/cache/         (src/llm.py)

Kullanım:
    python src/pipeline.py --estimate                 # çağrı sayısı + tahmini maliyet (API yok)
    python src/pipeline.py --asin B08V4QYTR6          # tek dev ürün
    python src/pipeline.py --not "oneri formati"      # 5 dev ürünün hepsi; koşuya kısa not
    python src/pipeline.py --split gold               # yalnızca kilit koşulları sağlanırsa
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

import agents
import llm
import runs
from schemas import EXPECTATION_SCHEMA, RESULT_SCHEMA, REVIEW_MINING_SCHEMA

ROOT = Path(__file__).resolve().parents[1]
GOLD_TAG = "v0.1-data"
UNLOCK_FILE = ROOT / ".gold_unlock"   # yalnızca kullanıcı oluşturur (kendi terminalinde)


class GoldLockError(RuntimeError):
    pass


def load_cfg():
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


SPLITS = {"dev": ("dev",), "gold": ("gold",), "rest": ("rest",), "all": ("gold", "dev", "rest")}   # all = 200 ürün


def load_products(split):
    cfg = load_cfg()
    with open(ROOT / "data" / "processed" / f"products_{cfg['n_products']}.jsonl", encoding="utf-8") as f:
        return [p for p in map(json.loads, f) if p["split"] in SPLITS[split]]


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


def run_product(p, run_dir):
    """Bir ürünü 3 ajandan geçirir; ara çıktıları run_dir/<asin>/ altına yazar. (sonuç, meta) döndürür."""
    t0 = time.perf_counter()
    page, reviews = agents.page_text(p), agents.reviews_text(p)
    errs = agents.check_input(p, page, reviews)
    if errs:
        raise ValueError(f"{p['parent_asin']}: girdi kontrolü başarısız: {errs}")
    d = run_dir / p["parent_asin"]
    d.mkdir(parents=True, exist_ok=True)

    a1 = agents.agent1(p)
    (d / "agent1.json").write_text(json.dumps(a1, ensure_ascii=False, indent=2), encoding="utf-8")
    a2 = agents.agent2(p)
    (d / "agent2.json").write_text(json.dumps(a2, ensure_ascii=False, indent=2), encoding="utf-8")
    a3, meta = agents.agent3(a1, a2, len(p["negative_reviews"]), p["parent_asin"])
    (d / "agent3.json").write_text(json.dumps(a3, ensure_ascii=False, indent=2), encoding="utf-8")
    (d / "ozet.txt").write_text(agents.render_text(p["parent_asin"], a3) + "\n", encoding="utf-8")

    meta.update({"parent_asin": p["parent_asin"], "split": p["split"], "run_id": run_dir.name,
                 "n_reviews": len(p["negative_reviews"]),
                 "agent1_uyarilari": agents.expectation_warnings(a1, page),
                 "agent2_uyarilari": agents.review_mining_warnings(a2, len(p["negative_reviews"])),
                 "sure_duvar_sn": round(time.perf_counter() - t0, 3),
                 "time": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return a3, meta


def update_latest(run_dir, split, metas, system="multi_agent"):
    """Son koşunun ürün klasörlerini outputs/<sistem>/<split>/ altına kopyalar."""
    latest = llm.OUT_DIR / system / split
    for m in metas:
        shutil.copytree(run_dir / m["parent_asin"], latest / m["parent_asin"], dirs_exist_ok=True)
        if m["tutarsiz"]:
            with open(latest / "tutarsiz.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"parent_asin": m["parent_asin"], "ihlaller": m["ihlaller"], "time": m["time"],
                                    "run_id": run_dir.name}, ensure_ascii=False) + "\n")


def read_log_from(n):
    path = llm.OUT_DIR / "llm_log.jsonl"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in list(f)[n:]]


def parse_args(argv, doc):
    ap = argparse.ArgumentParser(description=doc, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", choices=list(SPLITS), default="dev",
                    help="dev (varsayılan) | rest | gold | all (= gold + dev + rest, 200 ürün; gold kilidi gerekir)")
    ap.add_argument("--asin", action="append", help="yalnızca bu ürün(ler); seçili split içinde olmalı")
    ap.add_argument("--estimate", action="store_true", help="API çağırmadan çağrı sayısı ve maliyet tahmini")
    ap.add_argument("--not", dest="note", help="koşu kaydına kısa not (ör. 'oneri formati'); klasör adına da girer")
    return ap.parse_args(argv)


def select_products(args):
    """Kilit denetimi (gold içeren kümelerde) + ürün seçimi. 3 ajanlı sistem ve baseline için ortak."""
    if "gold" in SPLITS[args.split]:
        gold_lock()
    products = load_products(args.split)
    if args.asin:
        wanted = set(args.asin)
        unknown = wanted - {p["parent_asin"] for p in products}
        if unknown:
            raise SystemExit(f"{sorted(unknown)} '{args.split}' kümesinde değil")
        products = [p for p in products if p["parent_asin"] in wanted]
    return products


def print_estimate(args, e):
    cfg = load_cfg()
    print(f"Küme: {args.split} | ürün: {e['urun']} | çağrı: {e['cagri']} "
          f"(tutarlılık tekrarıyla en fazla {e['cagri_tekrar_dahil_en_fazla']})")
    print(f"Tahmini token: girdi ~{e['girdi_token']:,}, çıktı ~{e['cikti_token']:,}")
    print(f"Tahmini maliyet: ~${e['maliyet_usd']:.4f} (tekrarlarla en fazla ~${e['maliyet_usd_tekrar_dahil_en_fazla']:.4f}) "
          f"| fiyat: ${cfg['price_input_per_1m']}/{cfg['price_output_per_1m']} per 1M "
          f"(doğrulandı: {cfg.get('model_verified')})")


def execute(args, products, system, prompts, run_one):
    """Koşuyu yürütür ve kaydeder (3 ajanlı sistem ve baseline için ortak).
    Ürün bazında hata yakalanır: hatalı ürün atlanır, diğerleri devam eder, hatalar manifest'e yazılır.
    Kaldığı yerden devam: aynı komut yeniden çalıştırılınca tamamlanan ürünler önbellekten (ücretsiz) gelir.
    Döndürür: hatalı ürün sayısı."""
    run_dir = runs.new_run_dir(llm.OUT_DIR, system, args.split, args.note)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    n_log_before = len(read_log_from(0))
    t0 = time.perf_counter()
    results, metas, failed, error = [], [], [], None
    try:
        for p in products:
            try:
                res, meta = run_one(p, run_dir)
            except Exception as exc:                 # ürün bazında: kaydet ve devam et
                failed.append({"parent_asin": p["parent_asin"], "hata": f"{type(exc).__name__}: {exc}"})
                print(f"{p['parent_asin']}: HATA {type(exc).__name__}: {str(exc)[:200]}")
                continue
            results.append(res)
            metas.append(meta)
            flag = " TUTARSIZ" if meta["tutarsiz"] else (" (tekrar ile düzeldi)" if meta["deneme"] == 2 else "")
            print(f"{p['parent_asin']}: gap_var={res['gap_var']} tipler={res['gap_tipleri']} seviye={res['seviye']}{flag}")
    except BaseException as exc:                     # ör. Ctrl+C: kayıt yine yazılır, hata yukarı iletilir
        error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        if failed and error is None:
            error = f"{len(failed)} ürün hatalı (ayrıntı: hatali_urunler); aynı komutla yeniden çalıştırılabilir"
        calls = read_log_from(n_log_before)
        _, m = runs.write_run(run_dir, system=system, split=args.split, note=args.note, products=products,
                              results=results, metas=metas, calls=calls, prompts=prompts, started=started,
                              wall_sn=time.perf_counter() - t0, completed=error is None, error=error,
                              failed=failed)
        update_latest(run_dir, args.split, metas, system)
        print(f"\nÇağrı: {m['cagri']['toplam']} (önbellekten: {m['cagri']['onbellekten']}) | "
              f"token: girdi {m['token']['girdi_odenen']:,}, çıktı {m['token']['cikti_odenen']:,} | "
              f"maliyet: ${m['maliyet_usd']['odenen']:.6f} (eşdeğer ${m['maliyet_usd']['esdeger']:.6f})")
        print(f"Koşu kaydı: {run_dir}" + ("" if error is None else f"  (TAMAMLANMADI: {error})"))
    return len(failed)


def main(argv=None):
    args = parse_args(argv, __doc__)
    products = select_products(args)
    if args.estimate:
        print_estimate(args, estimate(products))
        return
    prompts = {n: agents.load_prompt(n) for n in ("expectation", "review_mining", "gap_fix")}
    return 1 if execute(args, products, "multi_agent", prompts, run_product) else None


if __name__ == "__main__":
    sys.exit(main())
