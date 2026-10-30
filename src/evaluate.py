"""
FAZ 8 — Değerlendirme: iki sistemin altın standarda göre karşılaştırılması (kapsam §6; yontem §7)

Girdi:
  --gold      altın standart CSV'si (parent_asin, gap_var, 7 tip sütunu, seviye; 'not' sütunu okunmaz)
  --multi     3 ajanlı sistemin koşu klasörü  (outputs/runs/<split>/<run_id>/, sonuclar.csv)
  --baseline  baseline'ın koşu klasörü
  --out       çıktı klasörü (varsayılan reports/degerlendirme/<tarih>/)

Gerçek altın standart klasöründeki bir dosya ancak gold kilidi açıkken okunur (pipeline.gold_lock).
Testler sahte bir gold dosyasıyla çalışır.

Metrikler (her sistem; değerlendirme yalnızca altın standarttaki ürünler üzerinde):
  Ana:     gap tipi micro-F1 ve macro-F1 (6 tip; Eksik Bilgi hariç), tip bazında P/R/F1
  İkincil: gap var/yok iki sınıf P/R/F1 + Macro F1 + accuracy (çoğunluk referansı: hep "Evet");
           seviye isabeti (çoğunluk referansı: en sık gold seviyesi) + 3 seviye macro-F1
  Süreç:   tutarsız karar sayısı, eşdeğer maliyet ve süre
  Eksik Bilgi: support ve yanlış pozitif sayısı ayrıca
Tanımsız sınıf kuralı: bir sınıfta TP + FP + FN = 0 ise (ne destek ne tahmin) F1 tanımsızdır ve o
örneklemde macro ortalamaya katılmaz. P veya R'nin paydası 0 ise o değer 0 sayılır.
Bootstrap: config.yaml > bootstrap_n tekrar, bootstrap_seed tohum; her tekrarda AYNI ürün örneklemi
iki sisteme uygulanır (eşleştirilmiş); fark = çok ajanlı − baseline; %95 yüzdelik güven aralığı.

Çıktılar (yontem §7.3): girdi.json, metrikler.csv, tip_bazinda.csv, karsilastirma.csv,
urun_bazinda.csv, rapor.md

Kullanım (Faz 8, kilit açıkken kullanıcı veya asistan):
    python src/evaluate.py --gold <altın standart CSV> --multi outputs/runs/<split>/<koşu> \\
                           --baseline outputs/runs/<split>/<koşu>
"""
import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

from schemas import EVAL_TYPES, GOLD_COLS, LEVELS

ROOT = Path(__file__).resolve().parents[1]
GOLD_DIR = ROOT / "data" / "gold"
EB = "Eksik Bilgi"
SYSTEMS = ("multi_agent", "baseline")
BOOT_METRICS = ["tip_micro_f1", "tip_macro_f1", "gapvar_macro_f1", "gapvar_accuracy",
                "seviye_isabet", "seviye_macro_f1"]
LABELS = {"tip_micro_f1": "Gap tipi micro-F1 (ana)", "tip_macro_f1": "Gap tipi macro-F1 (6 tip)",
          "tip_micro_precision": "Gap tipi micro precision", "tip_micro_recall": "Gap tipi micro recall",
          "gapvar_macro_f1": "Gap var/yok Macro F1", "gapvar_accuracy": "Gap var/yok accuracy",
          "gapvar_evet_f1": "Gap var/yok F1 (Evet)", "gapvar_hayir_f1": "Gap var/yok F1 (Hayır)",
          "seviye_isabet": "Seviye isabeti", "seviye_macro_f1": "Seviye macro-F1 (3 seviye)"}


# ---------------------------------------------------------------- okuma
def read_table(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def to_record(row):
    """CSV satırı -> {gap_var, types: {tip: 0/1}, seviye} (gold ve sistem sonuçları aynı sütun adlarını kullanır)."""
    return {"gap_var": int(row["gap_var"]), "types": {t: int(row[c]) for t, c in GOLD_COLS.items()},
            "seviye": row["seviye"]}


def load_gold(path):
    rows = read_table(path)
    gold = {r["parent_asin"]: to_record(r) for r in rows}
    if len(gold) != len(rows):
        raise ValueError("altın standartta tekrar eden parent_asin var")
    return gold


def load_run(run_dir):
    run_dir = Path(run_dir)
    man = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    rows = read_table(run_dir / "sonuclar.csv")
    return man, {r["parent_asin"]: {**to_record(r), "tutarsiz": int(r["tutarsiz"]),
                                    "maliyet": float(r["maliyet_esdeger_usd"] or 0),
                                    "sure": float(r["sure_esdeger_sn"] or 0)} for r in rows}


# ---------------------------------------------------------------- metrikler
def prf(tp, fp, fn):
    """(P, R, F1); TP + FP + FN = 0 ise F1 = nan (tanımsız)."""
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    if tp + fp + fn == 0:
        return p, r, math.nan
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def counts(gold_vals, pred_vals, positive):
    tp = sum(g == positive and p == positive for g, p in zip(gold_vals, pred_vals))
    fp = sum(g != positive and p == positive for g, p in zip(gold_vals, pred_vals))
    fn = sum(g == positive and p != positive for g, p in zip(gold_vals, pred_vals))
    return tp, fp, fn


def nanmean(vals):
    vals = [v for v in vals if not math.isnan(v)]
    return sum(vals) / len(vals) if vals else math.nan


def type_table(gold, pred):
    """Tip bazında TP/FP/FN/P/R/F1/support (7 tip; Eksik Bilgi hesaplamaya dahil değil)."""
    out = []
    for t in GOLD_COLS:
        tp, fp, fn = counts([g["types"][t] for g in gold], [p["types"][t] for p in pred], 1)
        p, r, f = prf(tp, fp, fn)
        out.append({"tip": t, "TP": tp, "FP": fp, "FN": fn, "P": p, "R": r, "F1": f, "support": tp + fn,
                    "hesaplamaya_dahil": int(t in EVAL_TYPES)})
    return out


def metrics(gold, pred):
    """gold, pred: aynı sırada kayıt listeleri. Tüm noktasal metrikler (sözlük)."""
    m = {}
    tt = [r for r in type_table(gold, pred) if r["hesaplamaya_dahil"]]
    tp, fp, fn = (sum(r[k] for r in tt) for k in ("TP", "FP", "FN"))
    m["tip_micro_precision"], m["tip_micro_recall"], m["tip_micro_f1"] = prf(tp, fp, fn)
    m["tip_macro_f1"] = nanmean([r["F1"] for r in tt])

    gv, pv = [g["gap_var"] for g in gold], [p["gap_var"] for p in pred]
    m["gapvar_evet_f1"] = prf(*counts(gv, pv, 1))[2]
    m["gapvar_hayir_f1"] = prf(*counts(gv, pv, 0))[2]
    m["gapvar_macro_f1"] = nanmean([m["gapvar_evet_f1"], m["gapvar_hayir_f1"]])
    m["gapvar_accuracy"] = sum(g == p for g, p in zip(gv, pv)) / len(gv)

    gs, ps = [g["seviye"] for g in gold], [p["seviye"] for p in pred]
    m["seviye_isabet"] = sum(g == p for g, p in zip(gs, ps)) / len(gs)
    m["seviye_macro_f1"] = nanmean([prf(*counts(gs, ps, lvl))[2] for lvl in LEVELS])
    return m


def majority_reference(gold):
    """Çoğunluk referansları: gap var/yok için hep 'Evet', seviye için en sık gold seviyesi."""
    top = max(LEVELS, key=lambda lvl: (sum(g["seviye"] == lvl for g in gold), -LEVELS.index(lvl)))
    ref = [{"gap_var": 1, "types": {t: 0 for t in GOLD_COLS}, "seviye": top} for _ in gold]
    m = metrics(gold, ref)
    return {"gapvar_accuracy": m["gapvar_accuracy"], "gapvar_macro_f1": m["gapvar_macro_f1"],
            "seviye_isabet": m["seviye_isabet"], "seviye_macro_f1": m["seviye_macro_f1"], "seviye": top}


# ---------------------------------------------------------------- bootstrap
def bootstrap(gold, preds, n, seed):
    """Eşleştirilmiş bootstrap. preds: {sistem: kayıt listesi}. {metrik: {sistem: [değerler], 'fark': [..]}}."""
    idx = np.random.default_rng(seed).integers(0, len(gold), size=(n, len(gold)))
    out = {k: {**{s: [] for s in preds}, "fark": []} for k in BOOT_METRICS}
    for row in idx:
        g = [gold[i] for i in row]
        ms = {s: metrics(g, [p[i] for i in row]) for s, p in preds.items()}
        for k in BOOT_METRICS:
            for s in preds:
                out[k][s].append(ms[s][k])
            out[k]["fark"].append(ms[SYSTEMS[0]][k] - ms[SYSTEMS[1]][k])
    return out


def ci(vals):
    a = np.array(vals, dtype=float)
    a = a[~np.isnan(a)]
    if not len(a):
        return math.nan, math.nan, 0
    lo, hi = np.percentile(a, [2.5, 97.5])
    return float(lo), float(hi), int(len(a))


# ---------------------------------------------------------------- çalıştırma
def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def is_real_gold(path):
    return GOLD_DIR.resolve() in Path(path).resolve().parents


def fmt(x, nd=3):
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{nd}f}"


def evaluate(gold_path, multi_dir, baseline_dir, out_dir, n=None, seed=None, now=None):
    """Değerlendirmeyi yapar ve yontem §7.3 dosyalarını out_dir'e yazar. (metrikler, karşılaştırma) döndürür."""
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    n = n or cfg.get("bootstrap_n", 1000)
    seed = cfg.get("bootstrap_seed", 42) if seed is None else seed
    gold_map = load_gold(gold_path)
    asins = list(gold_map)
    gold = [gold_map[a] for a in asins]

    runs, preds, warnings = {}, {}, []
    for system, d in zip(SYSTEMS, (multi_dir, baseline_dir)):
        man, res = load_run(d)
        if man.get("sistem") != system:
            raise ValueError(f"{d}: sistem '{man.get('sistem')}', beklenen '{system}'")
        missing = [a for a in asins if a not in res]
        if missing:
            raise ValueError(f"{system} koşusunda altın standart ürünlerinden {len(missing)} tanesi yok: "
                             f"{missing[:5]}... (koşuyu aynı komutla tamamlayın)")
        if not man.get("tamamlandi"):
            warnings.append(f"{system} koşusu 'tamamlandı' değil (altın standart ürünleri yine de eksiksiz)")
        runs[system], preds[system] = man, [res[a] for a in asins]
    if runs[SYSTEMS[0]].get("model") != runs[SYSTEMS[1]].get("model"):
        warnings.append("iki koşunun modeli farklı: " + ", ".join(str(runs[s].get("model")) for s in SYSTEMS))

    point = {s: metrics(gold, preds[s]) for s in SYSTEMS}
    boot = bootstrap(gold, preds, n, seed)
    majority = majority_reference(gold)
    types = {s: type_table(gold, preds[s]) for s in SYSTEMS}
    process = {s: {"tutarsiz": sum(p["tutarsiz"] for p in preds[s]),
                   "maliyet_esdeger_usd": round(sum(p["maliyet"] for p in preds[s]), 6),
                   "sure_esdeger_sn": round(sum(p["sure"] for p in preds[s]), 1),
                   "eksik_bilgi_yanlis_pozitif": next(r["FP"] for r in types[s] if r["tip"] == EB)}
               for s in SYSTEMS}

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    girdi = {"zaman": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
             "altin_standart": {"dosya_sha256": sha256_file(gold_path), "urun": len(asins),
                                "surum_etiketi": "v0.1-data"},
             "kosular": {s: {"run_id": runs[s].get("run_id"), "split": runs[s].get("split"),
                             "model": runs[s].get("model"), "git_commit": runs[s].get("git_commit"),
                             "prompt_hash": runs[s].get("hash", {}).get("prompt_toplam")} for s in SYSTEMS},
             "bootstrap": {"tekrar": n, "tohum": seed, "yontem": "eşleştirilmiş, ürünler yerine koyarak; "
                           "%95 yüzdelik güven aralığı; fark = multi_agent - baseline"},
             "tanimsiz_sinif_kurali": "TP + FP + FN = 0 olan sınıf o örneklemde macro ortalamaya katılmaz",
             "uyarilar": warnings}
    (out / "girdi.json").write_text(json.dumps(girdi, ensure_ascii=False, indent=2), encoding="utf-8")

    rows = []
    for s in SYSTEMS:
        for k, v in point[s].items():
            lo, hi, valid = ci(boot[k][s]) if k in boot else (math.nan, math.nan, 0)
            rows.append({"sistem": s, "metrik": k, "deger": v, "ci_alt": lo, "ci_ust": hi, "gecerli_tekrar": valid})
    for k in ("gapvar_accuracy", "gapvar_macro_f1", "seviye_isabet", "seviye_macro_f1"):
        rows.append({"sistem": f"cogunluk_referansi ({'Evet' if k.startswith('gapvar') else majority['seviye']})",
                     "metrik": k, "deger": majority[k], "ci_alt": "", "ci_ust": "", "gecerli_tekrar": ""})
    write_csv(out / "metrikler.csv", rows)

    write_csv(out / "tip_bazinda.csv", [{"sistem": s, **r} for s in SYSTEMS for r in types[s]])

    comp = []
    for k in BOOT_METRICS:
        lo, hi, valid = ci(boot[k]["fark"])
        diffs = np.array(boot[k]["fark"], dtype=float)
        diffs = diffs[~np.isnan(diffs)]
        comp.append({"metrik": k, "multi_agent": point[SYSTEMS[0]][k], "baseline": point[SYSTEMS[1]][k],
                     "fark": point[SYSTEMS[0]][k] - point[SYSTEMS[1]][k], "ci_alt": lo, "ci_ust": hi,
                     "oran_fark_le_0": float(np.mean(diffs <= 0)) if len(diffs) else math.nan,
                     "gecerli_tekrar": valid, "anlamli": "evet" if valid and (lo > 0 or hi < 0) else "hayır"})
    write_csv(out / "karsilastirma.csv", comp)

    prod = []
    for a, g, pm, pb in zip(asins, gold, preds[SYSTEMS[0]], preds[SYSTEMS[1]]):
        row = {"parent_asin": a}
        for name, r in (("gold", g), ("multi_agent", pm), ("baseline", pb)):
            row[f"{name}_gap_var"] = r["gap_var"]
            row[f"{name}_tipler"] = ";".join(t for t in GOLD_COLS if r["types"][t])
            row[f"{name}_seviye"] = r["seviye"]
        for name, r in (("multi_agent", pm), ("baseline", pb)):
            row[f"{name}_tip_dogru"] = int(all(r["types"][t] == g["types"][t] for t in EVAL_TYPES))
            row[f"{name}_seviye_dogru"] = int(r["seviye"] == g["seviye"])
            row[f"{name}_tutarsiz"] = r["tutarsiz"]
        prod.append(row)
    write_csv(out / "urun_bazinda.csv", prod)

    (out / "rapor.md").write_text(report(girdi, point, majority, comp, types, process), encoding="utf-8")
    return point, comp


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 6) if isinstance(v, float) and not math.isnan(v) else
                            ("" if isinstance(v, float) else v)) for k, v in r.items()})


def report(girdi, point, majority, comp, types, process):
    L = ["# Değerlendirme Raporu", "",
         f"Altın standart: {girdi['altin_standart']['urun']} ürün (`{girdi['altin_standart']['surum_etiketi']}`, "
         f"sha256 `{girdi['altin_standart']['dosya_sha256'][:12]}`) · Koşular: "
         + ", ".join(f"{s} `{girdi['kosular'][s]['run_id']}`" for s in SYSTEMS)
         + f" · Bootstrap: {girdi['bootstrap']['tekrar']} tekrar, tohum {girdi['bootstrap']['tohum']}", ""]
    if girdi["uyarilar"]:
        L += ["**Uyarılar:** " + "; ".join(girdi["uyarilar"]), ""]
    L += ["## Metrikler ve eşleştirilmiş karşılaştırma", "",
          "| Metrik | 3 ajan | Baseline | Fark (3 ajan − baseline) [%95 GA] | Fark ≤ 0 oranı | Anlamlı |",
          "|---|---|---|---|---|---|"]
    for c in comp:
        L.append(f"| {LABELS[c['metrik']]} | {fmt(c['multi_agent'])} | {fmt(c['baseline'])} | "
                 f"{fmt(c['fark'])} [{fmt(c['ci_alt'])}, {fmt(c['ci_ust'])}] | {fmt(c['oran_fark_le_0'])} | {c['anlamli']} |")
    L += ["", f"Çoğunluk referansları: hep \"Evet\" → accuracy {fmt(majority['gapvar_accuracy'])}, Macro F1 "
          f"{fmt(majority['gapvar_macro_f1'])}; hep \"{majority['seviye']}\" → seviye isabeti "
          f"{fmt(majority['seviye_isabet'])}, 3 seviye macro-F1 {fmt(majority['seviye_macro_f1'])}.", "",
          "## Tip bazında (6 tip; Eksik Bilgi ayrıca)", "",
          "| Tip | Support | 3 ajan P / R / F1 | Baseline P / R / F1 |", "|---|---|---|---|"]
    for rm, rb in zip(types[SYSTEMS[0]], types[SYSTEMS[1]]):
        note = "" if rm["hesaplamaya_dahil"] else " (hesaplama dışı)"
        L.append(f"| {rm['tip']}{note} | {rm['support']} | {fmt(rm['P'], 2)} / {fmt(rm['R'], 2)} / {fmt(rm['F1'], 2)} | "
                 f"{fmt(rb['P'], 2)} / {fmt(rb['R'], 2)} / {fmt(rb['F1'], 2)} |")
    L += ["", "## Süreç", "", "| | 3 ajan | Baseline |", "|---|---|---|"]
    for k, label in (("tutarsiz", "Tutarsız karar"), ("eksik_bilgi_yanlis_pozitif", "Eksik Bilgi yanlış pozitif"),
                     ("maliyet_esdeger_usd", "Eşdeğer maliyet ($)"), ("sure_esdeger_sn", "Eşdeğer API süresi (sn)")):
        L.append(f"| {label} | {process[SYSTEMS[0]][k]} | {process[SYSTEMS[1]][k]} |")
    L += ["", "Noktasal değerler tüm test kümesi üzerindendir; güven aralıkları `metrikler.csv` ve "
          "`karsilastirma.csv` dosyalarındadır. Tanımsız sınıf kuralı ve bootstrap ayrıntısı: `girdi.json`.", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gold", required=True, help="altın standart CSV'si")
    ap.add_argument("--multi", required=True, help="3 ajanlı sistemin koşu klasörü")
    ap.add_argument("--baseline", required=True, help="baseline'ın koşu klasörü")
    ap.add_argument("--out", help="çıktı klasörü (varsayılan reports/degerlendirme/<tarih>)")
    args = ap.parse_args(argv)
    if is_real_gold(args.gold):
        import pipeline
        pipeline.gold_lock()                                   # gerçek altın standart: yalnızca kilit açıkken
    out = args.out or ROOT / "reports" / "degerlendirme" / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    evaluate(args.gold, args.multi, args.baseline, out)
    print(f"Yazıldı: {out}")
    print((Path(out) / "rapor.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    sys.exit(main())
