"""
FAZ 5 — Koşu kaydı ve süreç ölçümleri (3 ajan ve baseline için ORTAK)

Her koşu kendi klasörüne yazılır; hiçbir koşu bir öncekinin üzerine yazmaz:

  outputs/runs/<split>/<run_id>/
    manifest.json     kimlik: sistem, küme, ürünler, model, git commit, dosya hash'leri, config, not
    prompts/          modele giden (doldurulmuş) prompt'ların tam metni
    <asin>/           ürün bazında ara çıktılar (sistemin yazdığı JSON'lar, meta.json, ozet.txt)
    sonuclar.csv      ürün başına 1 satır; gap tipleri altın standart CSV'si ile AYNI sütun adlarıyla
                      (schemas.GOLD_COLS)
    ozetler.txt       tüm ürünlerin kapsam §9 metin biçimi
    llm_calls.jsonl   bu koşunun LLM çağrıları (outputs/llm_log.jsonl'dan)
    olcumler.json     süreç ölçümleri (gold gerektirmez)
  outputs/runs/index.csv   her koşu için tek satır (prompt geliştirme geçmişi)

Maliyet / token / süre iki türlü verilir:
  odenen  = bu koşuda gerçekten ödenen (önbellekten gelen çağrı 0)
  esdeger = önbellekten gelen çağrı için ilk (ücretli) çağrının değeri; sistemler arası
            karşılaştırmada bu kullanılır (önbellek durumundan bağımsızdır).
"""
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

from agents import render_text
from schemas import ALL_SCHEMAS, FIX_ACTIONS, GAP_TYPES, GOLD_COLS, LEVELS

ROOT = Path(__file__).resolve().parents[1]
RULES_FILE = ROOT / "docs" / "etiketleme_kurallari.md"
CONFIG_FILE = ROOT / "config.yaml"

RESULT_COLS = (["parent_asin", "gap_var"] + list(GOLD_COLS.values())
               + ["seviye", "tutarsiz", "deneme", "n_oneri", "maliyet_esdeger_usd", "sure_esdeger_sn"])
INDEX_COLS = ["run_id", "sistem", "split", "urun", "tamamlandi", "not", "git_commit", "kod_degisikligi_var",
              "prompt_hash", "tekrar_gereken", "tutarsiz", "cagri", "onbellekten",
              "maliyet_odenen_usd", "maliyet_esdeger_usd", "sure_duvar_sn"]

# ilk denemedeki ihlal metni -> tür (olcumler.json'da sayılır)
VIOLATION_KINDS = [
    ("en az 2 farklı", "2 yorum şartı"),
    ("tek konu", "tek konu kuralı"),
    ("seviye Yüksek ama", "iddia yokken Yüksek"),
    ("birebir geçmiyor", "alıntı kaynakta yok"),
    ("öneri yok", "eksik öneri"),
    ("oneriler boş", "eksik öneri"),
    ("'ekle' olmalı", "işlem uyumsuz"),
    ("gap_tipleri içinde yok", "öneri tipi gap dışı"),
    ("gap_var = false ama", "gap yok ama alanlar dolu"),
    ("gap_var = true ama", "gap var ama alanlar eksik"),
]

_TR = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slug(text):
    s = re.sub(r"[^0-9a-z]+", "-", str(text or "").translate(_TR).lower()).strip("-")
    return s[:40].rstrip("-")


def violation_kind(msg):
    return next((kind for key, kind in VIOLATION_KINDS if key in msg), "diğer")


def new_run_dir(out_dir, system, split, note=None, now=None):
    """outputs/runs/<split>/<YYYY-MM-DD_HHMMSS>_<sistem>[_<not>]/ klasörünü oluşturur (var olanı ezmez)."""
    now = now or datetime.now()
    run_id = f"{now:%Y-%m-%d_%H%M%S}_{system}" + (f"_{slug(note)}" if slug(note) else "")
    base = Path(out_dir) / "runs" / split
    d, i = base / run_id, 2
    while d.exists():
        d, i = base / f"{run_id}_{i}", i + 1
    d.mkdir(parents=True)
    return d


def git_state(run=subprocess.run):
    def git(*a):
        r = run(["git", *a], cwd=ROOT, capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None
    dirty = git("status", "--porcelain", "--", "src", "prompts", "docs", "config.yaml")
    return {"git_commit": git("rev-parse", "HEAD"), "kod_degisikligi_var": None if dirty is None else bool(dirty)}


# ---------------------------------------------------------------- çağrı değerleri
def _paid(c, key):
    return c.get(key) or 0


def _equiv(c, key):
    return (c.get(f"orig_{key}") if c.get("cache_hit") else c.get(key)) or 0


def calls_of(calls, asin):
    """Bir ürünün çağrıları (tag 'ajan:ASIN' biçiminde)."""
    return [c for c in calls if str(c.get("tag", "")).endswith(f":{asin}")]


def result_row(asin, res, meta, calls):
    types = set(res["gap_tipleri"])
    return {"parent_asin": asin, "gap_var": int(res["gap_var"]),
            **{col: int(t in types) for t, col in GOLD_COLS.items()},
            "seviye": res["seviye"], "tutarsiz": int(bool(meta.get("tutarsiz"))), "deneme": meta.get("deneme", 1),
            "n_oneri": len(res["oneriler"]),
            "maliyet_esdeger_usd": round(sum(_equiv(c, "cost_usd") for c in calls), 8),
            "sure_esdeger_sn": round(sum(_equiv(c, "sure_sn") for c in calls), 3)}


def process_metrics(results, metas, calls, wall_sn):
    """Gold gerektirmeyen süreç ölçümleri (kapsam §6, 'Sonuçların ve ölçümlerin kaydı')."""
    n = len(results)

    def rate(k):
        return round(k / n, 4) if n else None

    retried = sum(m.get("deneme", 1) > 1 for m in metas)
    inconsistent = sum(bool(m.get("tutarsiz")) for m in metas)
    first = Counter(violation_kind(v) for m in metas for v in m.get("ilk_ihlaller", []))
    final = Counter(violation_kind(v) for m in metas for v in m.get("ihlaller", []))
    n_sug = sum(len(r["oneriler"]) for r in results)
    actions = Counter(o.get("islem") for r in results for o in r["oneriler"] if isinstance(o, dict))
    equiv_cost = sum(_equiv(c, "cost_usd") for c in calls)
    equiv_dur = sum(_equiv(c, "sure_sn") for c in calls)
    return {
        "urun": n,
        "karar": {
            "gap_var": sum(bool(r["gap_var"]) for r in results),
            "gap_var_orani": rate(sum(bool(r["gap_var"]) for r in results)),
            "tip_sayilari": {t: sum(t in r["gap_tipleri"] for r in results) for t in GAP_TYPES},
            "seviye_dagilimi": {lvl: sum(r["seviye"] == lvl for r in results) for lvl in LEVELS},
        },
        "tutarlilik": {
            "tekrar_gereken": retried, "tekrar_gereken_orani": rate(retried),
            "tutarsiz": inconsistent, "tutarsiz_orani": rate(inconsistent),
            "ilk_ihlal_turleri": dict(first.most_common()), "kalan_ihlal_turleri": dict(final.most_common()),
        },
        "uyarilar": {
            "agent1": sum(len(m.get("agent1_uyarilari", [])) for m in metas),
            "agent2": sum(len(m.get("agent2_uyarilari", [])) for m in metas),
        },
        "oneriler": {
            "toplam": n_sug, "urun_basina": round(n_sug / n, 2) if n else None,
            "islem_dagilimi": {a: actions[a] for a in FIX_ACTIONS},
        },
        "cagri": {"toplam": len(calls), "onbellekten": sum(bool(c.get("cache_hit")) for c in calls),
                  "hatali": sum("error" in c for c in calls)},
        "token": {"girdi_odenen": sum(_paid(c, "input_tokens") for c in calls),
                  "cikti_odenen": sum(_paid(c, "output_tokens") for c in calls),
                  "girdi_esdeger": sum(_equiv(c, "input_tokens") for c in calls),
                  "cikti_esdeger": sum(_equiv(c, "output_tokens") for c in calls)},
        "maliyet_usd": {"odenen": round(sum(_paid(c, "cost_usd") for c in calls), 8),
                        "esdeger": round(equiv_cost, 8),
                        "urun_basina_esdeger": round(equiv_cost / n, 8) if n else None},
        "sure_sn": {"api_esdeger": round(equiv_dur, 3),
                    "urun_basina_api_esdeger": round(equiv_dur / n, 3) if n else None,
                    "duvar_saati": round(wall_sn, 3)},
        "aciklama": "esdeger = önbellekten gelen çağrılar için ilk (ücretli) çağrının değerleri; "
                    "sistemler arası karşılaştırmada esdeger kullanılır",
    }


# ---------------------------------------------------------------- yazma
def write_run(run_dir, *, system, split, note, products, results, metas, calls, prompts, started, wall_sn,
              completed=True, error=None, git=None):
    """Koşu kayıtlarını yazar ve index.csv'ye ekler. results/metas: tamamlanan ürünler (sıra korunur).
    prompts: {ad: modele giden tam metin}. Ürün klasörlerini (<asin>/) sistem kendisi yazar."""
    run_dir = Path(run_dir)
    cfg = yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8"))
    (run_dir / "prompts").mkdir(exist_ok=True)
    for name, text in prompts.items():
        (run_dir / "prompts" / f"{name}.md").write_text(text, encoding="utf-8")

    done = [m["parent_asin"] for m in metas]
    rows = [result_row(a, r, m, calls_of(calls, a)) for a, r, m in zip(done, results, metas)]
    with open(run_dir / "sonuclar.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RESULT_COLS)
        w.writeheader()
        w.writerows(rows)
    (run_dir / "ozetler.txt").write_text("\n\n".join(render_text(a, r) for a, r in zip(done, results)) + "\n",
                                         encoding="utf-8")
    with open(run_dir / "llm_calls.jsonl", "w", encoding="utf-8") as f:
        f.writelines(json.dumps(c, ensure_ascii=False) + "\n" for c in calls)
    metrics = process_metrics(results, metas, calls, wall_sn)
    (run_dir / "olcumler.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    prompt_hash = sha256_text("".join(f"{k}\n{v}" for k, v in sorted(prompts.items())))
    manifest = {
        "run_id": run_dir.name, "sistem": system, "split": split, "not": note or "",
        "tamamlandi": completed, "hata": error,
        "baslangic": started, "bitis": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "urunler_istenen": [p["parent_asin"] for p in products], "urunler_tamamlanan": done,
        "model": cfg.get("model"), "temperature": cfg.get("temperature"), "model_verified": cfg.get("model_verified"),
        **(git or git_state()),
        "hash": {"prompts": {k: sha256_text(v) for k, v in sorted(prompts.items())}, "prompt_toplam": prompt_hash,
                 "kurallar": sha256_text(RULES_FILE.read_text(encoding="utf-8")),
                 "semalar": sha256_text(json.dumps(ALL_SCHEMAS, ensure_ascii=False, sort_keys=True)),
                 "config": sha256_text(CONFIG_FILE.read_text(encoding="utf-8"))},
        "config": cfg,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    index = run_dir.parents[1] / "index.csv"
    new = not index.exists()
    with open(index, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=INDEX_COLS)
        if new:
            w.writeheader()
        w.writerow({"run_id": run_dir.name, "sistem": system, "split": split, "urun": len(done),
                    "tamamlandi": int(completed), "not": note or "", "git_commit": (manifest["git_commit"] or "")[:10],
                    "kod_degisikligi_var": manifest["kod_degisikligi_var"], "prompt_hash": prompt_hash[:12],
                    "tekrar_gereken": metrics["tutarlilik"]["tekrar_gereken"],
                    "tutarsiz": metrics["tutarlilik"]["tutarsiz"], "cagri": metrics["cagri"]["toplam"],
                    "onbellekten": metrics["cagri"]["onbellekten"],
                    "maliyet_odenen_usd": metrics["maliyet_usd"]["odenen"],
                    "maliyet_esdeger_usd": metrics["maliyet_usd"]["esdeger"],
                    "sure_duvar_sn": metrics["sure_sn"]["duvar_saati"]})
    return manifest, metrics
