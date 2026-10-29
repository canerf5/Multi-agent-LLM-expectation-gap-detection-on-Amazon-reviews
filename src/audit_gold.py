"""
Gold sızıntı denetimi — KULLANICI tarafından çalıştırılır (gold bariyeri bu script'i
Claude Code için engeller).

Gold ürünlerinin ASIN'lerini ve başlıklarını sistem geliştirme alanlarında arar:
  prompts/, src/, outputs/cache/, outputs/llm_log.jsonl, outputs/multi_agent/dev/
Faz 7 öncesi beklenen sonuç: HİÇ İZ YOK.

Okunanlar:
  - data/gold/gold_40.csv: YALNIZCA parent_asin sütunu (etiket sütunları okunmaz)
  - data/processed/products_200.jsonl: yalnızca bu ASIN'lerin başlıkları

Kullanım (kendi terminalinde):
    .venv/bin/python src/audit_gold.py
Çıkış kodu: 0 = iz yok, 1 = iz bulundu
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ["prompts", "src", "outputs/cache", "outputs/llm_log.jsonl", "outputs/multi_agent/dev"]
SKIP_DIRS = {"__pycache__"}
TITLE_PREFIX = 40      # başlığın ilk N karakteri de aranır (kısaltılmış alıntıları yakalamak için)


def gold_asins():
    with open(ROOT / "data" / "gold" / "gold_40.csv", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        i = header.index("parent_asin")
        return [row[i] for row in reader if row]          # yalnızca ASIN sütunu kullanılır


def gold_titles(asins):
    wanted, out = set(asins), {}
    with open(ROOT / "data" / "processed" / "products_200.jsonl", encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            if p["parent_asin"] in wanted:
                out[p["parent_asin"]] = p["title"]
    return out


def files_to_scan():
    me = Path(__file__).resolve()
    for t in TARGETS:
        path = ROOT / t
        if path.is_file():
            yield path
        elif path.is_dir():
            for f in sorted(path.rglob("*")):
                if f.is_file() and not (set(f.relative_to(ROOT).parts) & SKIP_DIRS) and f.resolve() != me:
                    yield f


def main():
    asins = gold_asins()
    titles = gold_titles(asins)
    needles = [(a, "ASIN", a) for a in asins]
    for a, t in titles.items():
        needles.append((a, "başlık", t))
        if len(t) > TITLE_PREFIX:
            needles.append((a, f"başlığın ilk {TITLE_PREFIX} karakteri", t[:TITLE_PREFIX]))

    scanned, hits = 0, []
    for f in files_to_scan():
        scanned += 1
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = f.read_bytes().decode("utf-8", errors="ignore")
        for asin, kind, needle in needles:
            if needle and needle in text:
                hits.append((f.relative_to(ROOT), asin, kind))

    print(f"Gold ASIN: {len(asins)} | başlığı bulunan: {len(titles)} | taranan dosya: {scanned}")
    print("Taranan alanlar:", ", ".join(t for t in TARGETS if (ROOT / t).exists()) or "(hiçbiri yok)")
    missing = [t for t in TARGETS if not (ROOT / t).exists()]
    if missing:
        print("Henüz oluşmamış alanlar:", ", ".join(missing))
    if not hits:
        print("SONUÇ: Hiç iz yok ✓")
        return 0
    print(f"SONUÇ: {len(hits)} iz bulundu ✗")
    for path, asin, kind in sorted(set(hits)):
        print(f"  - {path}: {asin} ({kind})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
