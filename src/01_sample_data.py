"""
FAZ 2 — Veri toplama

Amazon Reviews 2023'ten (Hugging Face) kriterlere uyan ürünleri seçer ve
her ürün için sayfa bilgisi + negatif yorumları tek dosyaya yazar.

Dosyalar satır satır okunur (yerel dosya ya da Hugging Face stream):
  1) Yorum dosyasının ilk `max_reviews` satırı okunur, parent_asin'e göre gruplanır.
  2) Kriteri sağlayan ürünler -> aday havuzu.
  3) Meta dosyasının TAMAMI okunur; sayfa bilgisi dolu olan adaylar toplanır.
  4) Bu adaylar karıştırılır (seed sabit) ve ilk `n_products` tanesi seçilir.
     Böylece örneklem dosya sırasından bağımsız, gerçekten rastgele olur.

Çıktı: data/processed/products_200.jsonl
Her ürüne bir "split" alanı atanır: gold (40) / dev (5) / rest (155)

Kullanım (önerilen: yerel dosyalar, birkaç dakika):
    python src/01_sample_data.py \
        --reviews-file data/raw/Clothing_Shoes_and_Jewelry.jsonl \
        --meta-file data/raw/meta_Clothing_Shoes_and_Jewelry.jsonl
    # dosya verilmezse Hugging Face'ten stream eder (meta'nın tamamı okunduğu için çok yavaş)
"""
import argparse
import html
import json
import random
import re
from collections import defaultdict
from pathlib import Path

import yaml
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
HF_REPO = "datasets/McAuley-Lab/Amazon-Reviews-2023/raw"


def open_lines(local_path, hf_path):
    """Yerel dosya verilmişse onu, yoksa Hugging Face dosyasını stream eder."""
    if local_path:
        return open(local_path, "r", encoding="utf-8")
    from huggingface_hub import HfFileSystem
    fs = HfFileSystem()
    return fs.open(hf_path, "r", encoding="utf-8", block_size=8 * 1024 * 1024)


TAG_RE = re.compile(r"<[^>]+>")
ASIN_RE = re.compile(r'"parent_asin":\s*"([^"]+)"')


def clean_text(s):
    """HTML etiketlerini (<br /> vb.) ve &amp; gibi kodları temizler, boşlukları sadeleştirir."""
    s = html.unescape(TAG_RE.sub(" ", str(s or "")))
    return " ".join(s.split())


def to_price(p):
    try:
        return float(str(p).replace("$", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reviews-file", default=None)
    ap.add_argument("--meta-file", default=None)
    args = ap.parse_args()

    cfg = yaml.safe_load(open(ROOT / "config.yaml", encoding="utf-8"))
    cat = cfg["category"]
    rng = random.Random(cfg["seed"])

    # ---------- 1) Yorumları oku ----------
    n_reviews = defaultdict(int)
    negatives = defaultdict(list)
    ratings = defaultdict(list)

    print(f"[1/3] Yorumlar okunuyor: {cat} (en fazla {cfg['max_reviews']:,} satır)")
    with open_lines(args.reviews_file, f"{HF_REPO}/review_categories/{cat}.jsonl") as f:
        for i, line in enumerate(tqdm(f, total=cfg["max_reviews"], unit=" yorum")):
            if i >= cfg["max_reviews"]:
                break
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            pid = r.get("parent_asin") or r.get("asin")
            if not pid:
                continue
            rating = float(r.get("rating", 0))
            n_reviews[pid] += 1
            ratings[pid].append(rating)
            if rating <= cfg["negative_max_rating"]:
                text = clean_text(r.get("text"))
                if len(text.split()) >= cfg["min_words"]:
                    negatives[pid].append({
                        "rating": rating,
                        "title": clean_text(r.get("title")),
                        "text": text,
                    })

    candidates = [p for p in n_reviews
                  if n_reviews[p] >= cfg["min_reviews"]
                  and len(negatives[p]) >= cfg["min_negative"]]
    candidates.sort()           # sıralama sabit olsun -> tekrarlanabilir
    rng.shuffle(candidates)
    print(f"      Kriteri sağlayan ürün: {len(candidates):,}")
    if len(candidates) < cfg["n_products"]:
        raise SystemExit("Yeterli ürün yok. config.yaml'da max_reviews değerini artır.")

    pool = set(candidates)

    # ---------- 2) Metadata'nın tamamını oku, adayların sayfa bilgisini topla ----------
    print(f"[2/3] Metadata okunuyor (dosyanın tamamı, {len(pool):,} aday aranıyor)")
    found = {}
    with open_lines(args.meta_file, f"{HF_REPO}/meta_categories/meta_{cat}.jsonl") as f:
        for line in tqdm(f, unit=" ürün"):
            # Hız için: aday olmayan satırı JSON'a çevirmeden atla
            hit = ASIN_RE.search(line)
            if hit and hit.group(1) not in pool:
                continue
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            pid = m.get("parent_asin")
            if pid not in pool or pid in found:
                continue
            title = clean_text(m.get("title"))
            features = [clean_text(x) for x in (m.get("features") or []) if clean_text(x)]
            description = [clean_text(x) for x in (m.get("description") or []) if clean_text(x)]
            if not title or not (features or description):
                continue  # sayfa bilgisi boş olan ürünü alma
            found[pid] = {
                "title": title,
                "features": features,
                "description": " ".join(description),
                "details": m.get("details") or {},
                "price": to_price(m.get("price")),
                "store": clean_text(m.get("store")),
                "average_rating": m.get("average_rating"),
            }

    print(f"      Sayfa bilgisi dolu aday: {len(found):,}")
    if len(found) < cfg["n_products"]:
        print(f"UYARI: sadece {len(found)} ürünün metadata'sı bulundu.")

    # ---------- 3) Rastgele seç, split ata, yaz ----------
    # candidates zaten seed ile karıştırıldı -> sırayı koruyarak ilk n_products tanesi
    pids = [p for p in candidates if p in found][: cfg["n_products"]]
    out = ROOT / "data" / "processed" / f"products_{cfg['n_products']}.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for idx, pid in enumerate(pids):
            if idx < cfg["n_gold"]:
                split = "gold"
            elif idx < cfg["n_gold"] + cfg["n_dev"]:
                split = "dev"
            else:
                split = "rest"
            negs = negatives[pid][: cfg["max_neg_per_product"]]
            rec = {
                "parent_asin": pid,
                "split": split,
                **found[pid],
                "n_reviews": n_reviews[pid],
                "n_negative": len(negatives[pid]),
                "mean_rating_sample": round(sum(ratings[pid]) / len(ratings[pid]), 2),
                "negative_reviews": negs,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"[3/3] Yazıldı: {out}  ({len(pids)} ürün: "
          f"{cfg['n_gold']} gold / {cfg['n_dev']} dev / {len(pids) - cfg['n_gold'] - cfg['n_dev']} rest)")


if __name__ == "__main__":
    main()
