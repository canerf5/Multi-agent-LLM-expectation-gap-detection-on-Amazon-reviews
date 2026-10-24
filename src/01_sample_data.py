"""
FAZ 2 — Veri toplama ve örneklem oluşturma

Amazon Reviews 2023'ten kriterlere uyan ürünler arasından BASİT RASTGELE
ÖRNEKLEM ile 200 ürün seçer, her ürün için sayfa bilgisi + negatif yorumları
tek dosyaya yazar ve hocaya gösterilecek bir örneklem raporu üretir.

Örneklem kuralları (config.yaml):
  1) En az 10 yorumu olan ürünler
  2) En az 3 negatif yorumu (puan <= 2, en az 5 kelime) olan ürünler
  3) Kategori yolunun bir seviyesi include listesinde (Clothing, Shoes, Boot Shop,
     Sport Specific Clothing) olan ve hiçbir seviyesi exclude listesinde (Jewelry,
     Watches, Accessories, ...) olmayan ürünler (kapsam filtresi)
  4) Sayfa bilgisi boş olmayan ürünler; tekrarlı negatif yorumlar tek sayılır
  5) Kuralları sağlayan TÜM ürünler arasından seed=42 ile rastgele 200 ürün (+10 yedek)
  6) 200 ürün -> 40 gold (test) / 5 dev (prompt denemesi) / 155 rest

Akış (dosya sırasından bağımsız seçim için):
  Geçiş 1  Yorum dosyasının TAMAMI okunur; her ürün için sadece yorum ve
           negatif yorum SAYISI tutulur (bellek dostu).
  Meta     Meta dosyasının TAMAMI okunur; kategori (Kural 3) ve sayfa
           bilgisi (Kural 4) kontrol edilir.
  Seçim    Uygun ürünler seed ile karıştırılır; karışık sıranın başından
           bir havuz alınır.
  Geçiş 2  Yorum dosyası tekrar okunur; havuzdaki ürünlerin negatif yorumları
           toplanır, birebir tekrarlar ayıklanır. Ayıklamadan sonra hâlâ
           Kural 2'yi sağlayan ilk 200 (+10 yedek) ürün seçilir.

Çıktılar:
  data/processed/products_200.jsonl   sistemin kullanacağı veri
  reports/orneklem_listesi.csv        200 ürünün özet listesi (Excel)
  reports/orneklem_raporu.md          eleme hunisi + istatistikler (hocaya)

Kullanım (dosyalar bilgisayardaysa — önerilen):
    python src/01_sample_data.py --reviews-file data/raw/Clothing_Shoes_and_Jewelry.jsonl --meta-file data/raw/meta_Clothing_Shoes_and_Jewelry.jsonl
"""
import argparse
import csv
import html
import json
import random
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

import yaml
from tqdm import tqdm

try:
    import orjson
    loads = orjson.loads
except ImportError:  # orjson yoksa standart json (daha yavaş)
    loads = json.loads

ROOT = Path(__file__).resolve().parents[1]
HF_REPO = "datasets/McAuley-Lab/Amazon-Reviews-2023/raw"
NEG_SHIFT = 32  # tek sayıda iki sayaç: toplam + (negatif << 32)

_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")
_BRACKET = re.compile(r"\[\[[^\]]*\]\]")  # [[VIDEOID:...]], [[ASIN:...]] vb. Amazon yer tutucuları


def open_lines(local_path, hf_path):
    if local_path:
        return open(local_path, "r", encoding="utf-8")
    from huggingface_hub import HfFileSystem
    return HfFileSystem().open(hf_path, "r", encoding="utf-8", block_size=8 * 1024 * 1024)


def clean_text(s):
    """HTML entity'lerini çözer, <br /> ve diğer etiketleri, [[...]] yer tutucularını siler,
    boşlukları sadeleştirir."""
    s = html.unescape(str(s or ""))
    s = _BR.sub(" ", s)
    s = _TAG.sub(" ", s)
    s = _BRACKET.sub(" ", s)
    return " ".join(s.split())


def to_price(p):
    try:
        return float(str(p).replace("$", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def to_date(ts):
    try:
        ts = float(ts)
        if ts > 1e11:
            ts /= 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc).date()
    except (TypeError, ValueError, OSError):
        return None


_NONWORD = re.compile(r"[^a-z0-9 ]+")


def norm_key(text):
    """Tekrar kontrolü için: küçük harf, sadece harf/rakam, sade boşluk."""
    return " ".join(_NONWORD.sub(" ", text.lower()).split())


def is_valid_negative(r, cfg):
    return (float(r.get("rating", 0)) <= cfg["negative_max_rating"]
            and len(clean_text(r.get("text")).split()) >= cfg["min_words"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reviews-file", default=None)
    ap.add_argument("--meta-file", default=None)
    args = ap.parse_args()

    cfg = yaml.safe_load(open(ROOT / "config.yaml", encoding="utf-8"))
    cat = cfg["category"]
    max_reviews = cfg.get("max_reviews")  # None -> dosyanın tamamı
    rng = random.Random(cfg["seed"])
    rev_path = f"{HF_REPO}/review_categories/{cat}.jsonl"
    meta_path = f"{HF_REPO}/meta_categories/meta_{cat}.jsonl"
    funnel = []
    t0 = time.time()

    # ---------- Geçiş 1: sayım ----------
    print(f"[1/4] Yorum dosyası okunuyor (geçiş 1, sayım): {cat}")
    counts = {}
    lines_read = 0
    with open_lines(args.reviews_file, rev_path) as f:
        for line in tqdm(f, total=max_reviews, unit=" yorum", mininterval=2):
            if max_reviews and lines_read >= max_reviews:
                break
            lines_read += 1
            try:
                r = loads(line)
            except ValueError:
                continue
            pid = r.get("parent_asin") or r.get("asin")
            if not pid:
                continue
            inc = 1 + ((1 << NEG_SHIFT) if is_valid_negative(r, cfg) else 0)
            counts[pid] = counts.get(pid, 0) + inc

    mask = (1 << NEG_SHIFT) - 1
    n_total = lambda v: v & mask
    n_neg = lambda v: v >> NEG_SHIFT

    funnel.append(("Okunan yorum satırı", lines_read))
    funnel.append(("Farklı ürün (parent_asin)", len(counts)))
    step1 = {p for p, v in counts.items() if n_total(v) >= cfg["min_reviews"]}
    funnel.append((f"Kural 1: en az {cfg['min_reviews']} yorum", len(step1)))
    step2 = {p for p in step1 if n_neg(counts[p]) >= cfg["min_negative"]}
    funnel.append((f"Kural 2: en az {cfg['min_negative']} negatif yorum (≥{cfg['min_words']} kelime)",
                   len(step2)))
    print(f"      Kural 1-2'yi sağlayan ürün: {len(step2):,}")

    # ---------- Meta: tamamı okunur ----------
    print("[2/4] Meta dosyası okunuyor (tamamı)")
    meta = {}
    empty_page = out_of_scope = cat_filled = 0
    cat_paths = Counter()
    out_examples = []
    include = {c.lower() for c in (cfg.get("include_categories") or [])}
    exclude = {c.lower() for c in (cfg.get("exclude_categories") or [])}
    with open_lines(args.meta_file, meta_path) as f:
        for line in tqdm(f, unit=" ürün", mininterval=2):
            try:
                m = loads(line)
            except ValueError:
                continue
            pid = m.get("parent_asin")
            if pid not in step2 or pid in meta:
                continue
            cats = [clean_text(c) for c in (m.get("categories") or []) if clean_text(c)]
            if cats:
                cat_filled += 1
                cat_paths[" > ".join(cats[:3])] += 1
            levels = {c.lower() for c in cats}
            if (include and not levels & include) or levels & exclude:
                out_of_scope += 1
                if len(out_examples) < 15:
                    out_examples.append(f"{clean_text(m.get('title'))[:60]}  [{' > '.join(cats[:3]) or 'kategori yok'}]")
                continue
            title = clean_text(m.get("title"))
            features = [clean_text(x) for x in (m.get("features") or []) if clean_text(x)]
            description = " ".join(clean_text(x) for x in (m.get("description") or []) if clean_text(x))
            if not title or not (features or description):
                empty_page += 1
                continue
            meta[pid] = {
                "title": title,
                "main_category": m.get("main_category"),
                "categories": cats,
                "features": features,
                "description": description,
                "details": {k: clean_text(v) for k, v in (m.get("details") or {}).items()},
                "price": to_price(m.get("price")),
                "store": clean_text(m.get("store")),
                "average_rating": m.get("average_rating"),
                "rating_number": m.get("rating_number"),
            }
    no_meta = len(step2) - len(meta) - empty_page - out_of_scope
    if include or exclude:
        funnel.append((f"Kural 3: kategori yolu kapsam içinde (dahil: {' / '.join(cfg.get('include_categories') or [])}; "
                       f"hariç: {' / '.join(cfg.get('exclude_categories') or [])}) "
                       f"(elenen kapsam dışı: {out_of_scope:,})", len(step2) - out_of_scope - no_meta))
    funnel.append((f"Kural 4: sayfa bilgisi dolu (elenen: boş sayfa {empty_page:,}, "
                   f"meta kaydı yok {no_meta:,})", len(meta)))
    print(f"      Kategori alanı dolu aday: {cat_filled:,} / {len(step2) - no_meta:,}")

    # ---------- Seçim: basit rastgele örneklem ----------
    # Uygun ürünler seed ile karıştırılır. Tekrarlı yorumlar ancak geçiş 2'de
    # görülebildiği için karıştırılmış sıradan bir HAVUZ alınır; tekrarlar
    # ayıklandıktan sonra Kural 2'yi hâlâ sağlayan ilk ürünler seçilir.
    # (Rastgele sırayla tek tek çekip uygun olmayanı atlamak = uygunlar
    # arasından basit rastgele örneklem.)
    eligible = sorted(meta)
    rng.shuffle(eligible)
    need = cfg["n_products"] + cfg.get("n_reserve", 0)
    if len(eligible) < need:
        raise SystemExit(f"Yeterli ürün yok ({len(eligible)}). include_categories / exclude_categories filtresini kontrol et.")
    pool = eligible[: min(len(eligible), need * 3)]
    pool_set = set(pool)
    print(f"[3/4] {len(eligible):,} uygun ürün karıştırıldı; ilk {len(pool)} ürün havuza alındı")

    # ---------- Geçiş 2: havuzdaki ürünlerin yorumları ----------
    print("[4/4] Yorum dosyası okunuyor (geçiş 2, sadece havuzdaki ürünler)")
    negatives = defaultdict(list)
    neg_keys = defaultdict(set)
    dup_count = defaultdict(int)
    ratings = defaultdict(list)
    dates = defaultdict(list)
    seen = 0
    chosen_set = pool_set
    with open_lines(args.reviews_file, rev_path) as f:
        for line in tqdm(f, total=lines_read, unit=" yorum", mininterval=2):
            if seen >= lines_read:
                break
            seen += 1
            # Hızlı ön kontrol: satırdaki parent_asin'i JSON çözmeden oku
            k = line.find('"parent_asin": "')
            if k != -1:
                pid = line[k + 16: line.find('"', k + 16)]
                if pid not in chosen_set:
                    continue
            try:
                r = loads(line)
            except ValueError:
                continue
            pid = r.get("parent_asin") or r.get("asin")
            if pid not in chosen_set:
                continue
            rating = float(r.get("rating", 0))
            ratings[pid].append(rating)
            d = to_date(r.get("timestamp"))
            if d:
                dates[pid].append(d)
            if is_valid_negative(r, cfg):
                text = clean_text(r.get("text"))
                key = norm_key(text)
                if cfg.get("dedupe_reviews", True) and key in neg_keys[pid]:
                    dup_count[pid] += 1
                    continue
                neg_keys[pid].add(key)
                negatives[pid].append({
                    "rating": rating,
                    "title": clean_text(r.get("title")),
                    "text": text,
                    "date": d.isoformat() if d else None,
                })

    # Tekrarlar ayıklandıktan sonra Kural 2'yi sağlayan ilk ürünler (karışık sırayla)
    chosen, dropped_dup = [], 0
    for pid in pool:
        if len(negatives[pid]) >= cfg["min_negative"]:
            chosen.append(pid)
            if len(chosen) == need:
                break
        else:
            dropped_dup += 1
    if len(chosen) < need:
        raise SystemExit(f"Havuz yetmedi ({len(chosen)}/{need}). Havuz katsayısını büyüt.")
    funnel.append((f"Tekrarlı yorumlar ayıklandı (Kural 2'nin altına düşen: {dropped_dup}, "
                   f"toplam ayıklanan kopya: {sum(dup_count[p] for p in chosen)})", len(chosen)))
    funnel.append((f"Kural 5: seed={cfg['seed']} ile rastgele seçilen örneklem "
                   f"(+{cfg.get('n_reserve', 0)} yedek)", cfg["n_products"]))

    # ---------- Yaz ----------
    records = []
    for idx, pid in enumerate(chosen):
        if idx < cfg["n_gold"]:
            split = "gold"
        elif idx < cfg["n_gold"] + cfg["n_dev"]:
            split = "dev"
        elif idx < cfg["n_products"]:
            split = "rest"
        else:
            split = "reserve"
        records.append({
            "parent_asin": pid,
            "split": split,
            **meta[pid],
            "n_reviews": len(ratings[pid]),
            "n_negative": len(negatives[pid]),
            "mean_rating_sample": round(mean(ratings[pid]), 2) if ratings[pid] else None,
            "first_review": min(dates[pid]).isoformat() if dates[pid] else None,
            "last_review": max(dates[pid]).isoformat() if dates[pid] else None,
            "n_duplicates_removed": dup_count[pid],
            "negative_reviews": negatives[pid][: cfg["max_neg_per_product"]],
        })

    out = ROOT / "data" / "processed" / f"products_{cfg['n_products']}.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    with open(reports / "orneklem_listesi.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["no", "parent_asin", "split", "baslik", "kategori", "magaza", "fiyat",
                    "yorum_sayisi", "negatif_sayisi", "ort_puan", "aciklama_var",
                    "ilk_yorum", "son_yorum"])
        for i, r in enumerate(records, 1):
            w.writerow([i, r["parent_asin"], r["split"], r["title"][:90], " > ".join(r["categories"][:3]),
                        r["store"], r["price"], r["n_reviews"], r["n_negative"],
                        r["mean_rating_sample"], "evet" if r["description"] else "hayır",
                        r["first_review"], r["last_review"]])

    minutes = (time.time() - t0) / 60
    diag = {"cat_filled": cat_filled, "cat_paths": cat_paths, "out_examples": out_examples}
    write_report(reports / "orneklem_raporu.md", cfg, funnel, records, dates, minutes, diag)
    print(f"Bitti ({minutes:.1f} dk)")
    print(f"  Veri:   {out}")
    print(f"  Rapor:  {reports / 'orneklem_raporu.md'}")
    print(f"  Liste:  {reports / 'orneklem_listesi.csv'}")


def write_report(path, cfg, funnel, records, dates, minutes, diag):
    def stats(vals):
        return f"{mean(vals):.1f} (medyan {median(vals):.0f}, min {min(vals)}, max {max(vals)})"

    reserve = [r for r in records if r["split"] == "reserve"]
    records = [r for r in records if r["split"] != "reserve"]

    n = len(records)
    all_dates = [d for r in records for d in dates[r["parent_asin"]]]
    split_counts = Counter(r["split"] for r in records)
    prices = [r["price"] for r in records if r["price"] is not None]
    neg_ratings = Counter(int(x["rating"]) for r in records for x in r["negative_reviews"])
    with_desc = sum(1 for r in records if r["description"])
    cats = Counter(r["main_category"] or "(boş)" for r in records)
    stores = Counter(r["store"] or "(boş)" for r in records)
    html_left = sum(1 for r in records for x in r["negative_reviews"] if "<" in x["text"] and ">" in x["text"])

    L = ["# Örneklem Raporu\n",
         f"Oluşturulma: {datetime.now().strftime('%Y-%m-%d %H:%M')} (süre {minutes:.1f} dk)  ",
         "Veri seti: Amazon Reviews 2023 (McAuley Lab)  ",
         f"Kategori: {cfg['category']}  ",
         f"Okunan kısım: {'yorum dosyasının tamamı' if not cfg.get('max_reviews') else 'ilk ' + format(cfg['max_reviews'], ',') + ' yorum'}, meta dosyasının tamamı  ",
         f"Seed: {cfg['seed']} (aynı ayarlarla her çalıştırmada aynı örneklem çıkar)\n",
         "## 1. Örneklem Yöntemi\n",
         f"1. En az {cfg['min_reviews']} yorumu olan ürünler",
         f"2. En az {cfg['min_negative']} negatif yorumu olan ürünler "
         f"(negatif: puan ≤ {cfg['negative_max_rating']}, en az {cfg['min_words']} kelime)",
         f"3. Kategori yolunun herhangi bir seviyesi şunlardan biri olan: "
         f"{' / '.join(cfg.get('include_categories') or ['(filtre kapalı)'])}; ve hiçbir seviyesi şunlardan biri "
         f"olmayan: {' / '.join(cfg.get('exclude_categories') or ['(yok)'])} "
         "(büyük-küçük harf duyarsız, tam eşleşme). Böylece giyim ve ayakkabı kapsama girer; takı, saat, "
         "çanta, bavul, aksesuar ve kostümler dışarıda kalır.",
         "4. Sayfa bilgisi (başlık ve özellik listesi veya açıklama) boş olmayan ürünler",
         "   Aynı ürün altında birebir aynı metne sahip negatif yorumlar tek sayılır; bu ayıklamadan sonra Kural 2 yeniden uygulanır.",
         f"5. 1-4. kuralları sağlayan tüm ürünler arasından seed={cfg['seed']} ile basit rastgele örneklem "
         f"({cfg['n_products']} ürün). Seçim, dosyalardaki satır sırasından bağımsızdır.",
         f"6. Bölme: {cfg['n_gold']} test (gold) / {cfg['n_dev']} geliştirme (dev) / "
         f"{cfg['n_products'] - cfg['n_gold'] - cfg['n_dev']} kalan (rest) + {len(reserve)} yedek (reserve; "
         "gold'da veri sorunu çıkan ürünün yerine sırayla konur)",
         "\nMetin temizliği: HTML entity'leri çözüldü, `<br />` ve diğer HTML etiketleri ile `[[VIDEOID:...]]` gibi Amazon yer tutucuları silindi.\n",
         "## 2. Eleme Hunisi\n",
         "| Adım | Sayı |", "|---|---|"]
    L += [f"| {name} | {v:,} |" for name, v in funnel]

    L += ["\n## 3. Veri Bölme\n",
          "| Küme | Ürün | Kullanım |", "|---|---|---|",
          f"| gold | {split_counts['gold']} | Elle etiketlenir; iki sistem bu kümede değerlendirilir |",
          f"| dev | {split_counts['dev']} | Prompt denemesi; test kümesinden ayrıdır |",
          f"| rest | {split_counts['rest']} | Tam koşu ve Alt Soru 2 analizi |\n",
          "## 4. Örneklem İstatistikleri\n",
          "| Ölçü | Değer |", "|---|---|",
          f"| Ürün başına yorum | {stats([r['n_reviews'] for r in records])} |",
          f"| Ürün başına negatif yorum | {stats([r['n_negative'] for r in records])} |",
          f"| Ürün başına ortalama puan | {mean(r['mean_rating_sample'] for r in records if r['mean_rating_sample'] is not None):.2f} |",
          f"| Açıklaması dolu ürün | {with_desc}/{n} (%{100 * with_desc / n:.0f}) |",
          f"| Özellik listesi dolu ürün | {sum(1 for r in records if r['features'])}/{n} |"]
    if prices:
        L.append(f"| Fiyat ($), fiyatı olan {len(prices)} ürün | ort. {mean(prices):.2f}, medyan {median(prices):.2f} |")
    if all_dates:
        L.append(f"| Yorum tarih aralığı | {min(all_dates)} – {max(all_dates)} |")
    L.append("| Negatif yorumların puan dağılımı | "
             + ", ".join(f"{k}★: {v}" for k, v in sorted(neg_ratings.items())) + " |")
    L.append(f"| Temizlik sonrası HTML etiketi kalan yorum | {html_left} |")
    L.append(f"| Ayıklanan tekrarlı negatif yorum (200 üründe) | {sum(r['n_duplicates_removed'] for r in records)} |")

    L += ["\n## 5. Ana Kategori Dağılımı (main_category)\n", "| Kategori | Ürün |", "|---|---|"]
    L += [f"| {c} | {k} |" for c, k in cats.most_common()]
    L += ["\n## 5b. Kategori Yolu (ilk 3 seviye) — örneklemdeki en sık 10\n",
          "| Kategori yolu | Ürün |", "|---|---|"]
    paths = Counter(" > ".join(r["categories"][:3]) or "(boş)" for r in records)
    L += [f"| {p} | {k} |" for p, k in paths.most_common(10)]
    L += [f"\nAdaylar içinde kategori alanı dolu olan: {diag['cat_filled']:,}\n",
          "Kapsam dışı bırakılan ürünlerden örnekler:\n"]
    L += [f"- {e}" for e in diag["out_examples"]] or ["- (yok)"]
    L += ["\n## 6. En Sık 10 Mağaza\n",
          f"Farklı mağaza sayısı: {len(stores)}\n", "| Mağaza | Ürün |", "|---|---|"]
    L += [f"| {s} | {k} |" for s, k in stores.most_common(10)]

    L += ["\n## 7. Örnek Ürünler (ilk 10)\n",
          "| parent_asin | Küme | Mağaza | Başlık | Yorum | Negatif |", "|---|---|---|---|---|---|"]
    L += [f"| {r['parent_asin']} | {r['split']} | {r['store']} | {r['title'][:55]} | "
          f"{r['n_reviews']} | {r['n_negative']} |" for r in records[:10]]
    L.append("\nTam liste: `reports/orneklem_listesi.csv`")
    path.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
