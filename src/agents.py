"""
FAZ 5 — Üç ajan ve ortak yardımcılar

- Kurallar: docs/etiketleme_kurallari.md çalışma anında okunur; RULE_SECTIONS
  bölümleri prompts/*.md içindeki {KURALLAR} yerine, "Örnek" bölümü {ORNEK} yerine konur.
  Böylece insan etiketleyici ile sistem aynı kural metnini kullanır.
- Girdi: page_text() ve reviews_text() ürünün jsonl kaydını KESMEDEN metne çevirir;
  check_input() bunu doğrular.
- Görünürlük: Ajan 1 yalnızca sayfayı, Ajan 2 yalnızca numaralı yorumları, Ajan 3 yalnızca
  Ajan 1 + Ajan 2 çıktılarını görür.
- result_violations(): ORTAK SONUÇ şemasındaki bir kararın kurallarla tutarlılığı (Ajan 3
  ve ileride baseline için aynı).
"""
import json
import re
from pathlib import Path

import llm
from schemas import (EXPECTATION_SCHEMA, GAP_TYPES, NO_INFO, RESULT_SCHEMA, REVIEW_MINING_SCHEMA)

ROOT = Path(__file__).resolve().parents[1]
RULES_FILE = ROOT / "docs" / "etiketleme_kurallari.md"
PROMPTS_DIR = ROOT / "prompts"
RULE_SECTIONS = ["Tek konu kuralı", "Seviye kuralı", "Sayılmayanlar", "Konu tanımları"]
EXAMPLE_SECTION = "Örnek"


# ---------------------------------------------------------------- kurallar ve prompt'lar
def rule_sections(path=None):
    """Kurallar dosyasındaki '## Başlık' bölümlerini {başlık: metin} olarak döndürür."""
    text = Path(path or RULES_FILE).read_text(encoding="utf-8")
    parts = re.split(r"^## +(.+?)\s*$", text, flags=re.M)
    return {parts[i].strip(): parts[i + 1].strip() for i in range(1, len(parts), 2)}


def rules_block(path=None, names=RULE_SECTIONS):
    sec = rule_sections(path)
    missing = [n for n in names if n not in sec]
    if missing:
        raise ValueError(f"Kurallar dosyasında bölüm bulunamadı: {missing}")
    return "\n\n".join(f"## {n}\n{sec[n]}" for n in names)


def load_prompt(name, rules_path=None):
    """prompts/<name>.md'yi okur, {KURALLAR} ve {ORNEK} yer tutucularını doldurur."""
    tpl = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    if "{KURALLAR}" not in tpl:
        raise ValueError(f"prompts/{name}.md içinde {{KURALLAR}} yok")
    out = tpl.replace("{KURALLAR}", rules_block(rules_path))
    if "{ORNEK}" in out:
        sec = rule_sections(rules_path)
        if EXAMPLE_SECTION not in sec:
            raise ValueError(f"Kurallar dosyasında '{EXAMPLE_SECTION}' bölümü yok")
        out = out.replace("{ORNEK}", sec[EXAMPLE_SECTION])
    left = re.findall(r"\{[A-ZÇĞİÖŞÜ_]+\}", out)
    if left:
        raise ValueError(f"prompts/{name}.md doldurulmamış yer tutucu içeriyor: {left}")
    return out


# ---------------------------------------------------------------- girdi metinleri
def page_text(p):
    """Ajan 1 girdisi: başlık, fiyat, özellikler, açıklama, detaylar — kesmeden."""
    parts = [f"BAŞLIK: {p['title']}"]
    parts.append(f"FİYAT: ${p['price']}" if p.get("price") is not None else "FİYAT: (yok)")
    parts.append("ÖZELLİKLER:\n" + ("\n".join(f"• {x}" for x in p["features"]) if p.get("features") else "(yok)"))
    parts.append("AÇIKLAMA: " + (p["description"] or "(yok)"))
    det = p.get("details") or {}
    parts.append("DETAYLAR:\n" + ("\n".join(f"- {k}: {v}" for k, v in det.items()) if det else "(yok)"))
    return "\n\n".join(parts)


def reviews_text(p):
    """Ajan 2 girdisi: numaralı negatif yorumlar (gözden geçirme dosyasıyla aynı biçim) — kesmeden."""
    return "\n\n".join(f"{i}) [{int(r['rating'])}★] {r['title']} — {r['text']}"
                       for i, r in enumerate(p["negative_reviews"], 1))


def check_input(p, page, reviews, max_reviews=15):
    """Girdinin ürün kaydının tamamını kesmeden içerdiğini doğrular; hata listesi döndürür."""
    errs = []
    if not page.startswith(f"BAŞLIK: {p['title']}"):
        errs.append("başlık eksik/değişmiş")
    for f in p.get("features") or []:
        if f"• {f}" not in page:
            errs.append(f"özellik eksik/kesik: {f[:40]!r}")
    if p.get("description") and p["description"] not in page:
        errs.append("açıklama eksik/kesik")
    for k, v in (p.get("details") or {}).items():
        if f"- {k}: {v}" not in page:
            errs.append(f"detay eksik: {k}")
    if p.get("price") is not None and f"${p['price']}" not in page:
        errs.append("fiyat eksik")
    revs = p["negative_reviews"]
    if len(revs) > max_reviews:
        errs.append(f"{len(revs)} yorum > {max_reviews}")
    for i, r in enumerate(revs, 1):
        if f"{i}) [{int(r['rating'])}★] {r['title']} — {r['text']}" not in reviews:
            errs.append(f"yorum {i} eksik/kesik")
    if f"{len(revs) + 1}) [" in reviews:
        errs.append("girdide üründe olmayan fazladan yorum var")
    return errs


# ---------------------------------------------------------------- tutarlılık
def result_violations(res, n_reviews):
    """ORTAK SONUÇ kararının kurallarla tutarlılığı; ihlal metinleri listesi."""
    v = []
    types = res["gap_tipleri"]
    if len(set(types)) != len(types):
        v.append("gap_tipleri içinde tekrar eden tip var")
    if not res["gap_var"]:
        if types:
            v.append(f"gap_var = false ama gap_tipleri dolu: {types}")
        if res["seviye"] != "Yok":
            v.append(f"gap_var = false ama seviye '{res['seviye']}' (Yok olmalı)")
        if res["tip_gerekceleri"]:
            v.append("gap_var = false ama tip_gerekceleri dolu")
        return v
    if not types:
        v.append("gap_var = true ama hiç gap tipi yok")
    if res["seviye"] not in ("Orta", "Yüksek"):
        v.append(f"gap_var = true ama seviye '{res['seviye']}' (Orta veya Yüksek olmalı)")
    by_type = {}
    for g in res["tip_gerekceleri"]:
        if g["tip"] in by_type:
            v.append(f"{g['tip']}: tip_gerekceleri içinde birden fazla kayıt")
        by_type[g["tip"]] = g
    for t in types:
        g = by_type.get(t)
        if g is None:
            v.append(f"{t}: tip_gerekceleri içinde kaydı yok")
            continue
        nums = set(g["yorum_numaralari"])
        if len(nums) < 2:
            v.append(f"{t}: en az 2 farklı destekleyen yorum gerekli, {len(nums)} var {sorted(nums)}")
        bad = sorted(n for n in nums if not 1 <= n <= n_reviews)
        if bad:
            v.append(f"{t}: geçersiz yorum numarası {bad} (ürünün {n_reviews} yorumu var)")
        if not str(g["sayfa_iddiasi"]).strip():
            v.append(f"{t}: sayfa_iddiasi boş (iddia yoksa '{NO_INFO}' yazılmalı)")
    extra = sorted(set(by_type) - set(types))
    if extra:
        v.append(f"tip_gerekceleri gap_tipleri dışında tip içeriyor: {extra}")
    seen = {}
    for t in types:
        for n in set(by_type.get(t, {}).get("yorum_numaralari", [])):
            if n in seen:
                v.append(f"tek konu kuralı: yorum {n} hem {seen[n]} hem {t} için sayılmış")
            seen[n] = t
    return v


def review_mining_warnings(out, n_reviews):
    """Ajan 2 çıktısı için uyarılar (çıktıyı değiştirmez, yalnızca kaydedilir)."""
    w = []
    for i, g in enumerate(out["sikayet_gruplari"], 1):
        if g["ilgili"] and (g["tip"] is None or g["ilgisiz_sebebi"] is not None):
            w.append(f"grup {i}: ilgili = true ise tip dolu ve ilgisiz_sebebi null olmalı")
        if not g["ilgili"] and g["ilgisiz_sebebi"] is None:
            w.append(f"grup {i}: ilgili = false ama ilgisiz_sebebi yok")
        bad = sorted(n for n in g["yorum_numaralari"] if not 1 <= n <= n_reviews)
        if bad:
            w.append(f"grup {i}: geçersiz yorum numarası {bad}")
    seen = {}
    for i, g in enumerate(out["sikayet_gruplari"], 1):
        if g["ilgili"]:
            for n in set(g["yorum_numaralari"]):
                if n in seen:
                    w.append(f"yorum {n} birden fazla ilgili grupta (grup {seen[n]} ve {i})")
                seen[n] = i
    return w


# ---------------------------------------------------------------- ajanlar
def agent1(p):
    return llm.call_llm(load_prompt("expectation"), page_text(p), EXPECTATION_SCHEMA,
                        tag=f"agent1:{p['parent_asin']}")


def agent2(p):
    return llm.call_llm(load_prompt("review_mining"), reviews_text(p), REVIEW_MINING_SCHEMA,
                        tag=f"agent2:{p['parent_asin']}")


def agent3_input(a1, a2):
    return ("SAYFA BEKLENTİLERİ (Ajan 1):\n" + json.dumps(a1, ensure_ascii=False, indent=2)
            + "\n\nŞİKAYET GRUPLARI (Ajan 2):\n" + json.dumps(a2, ensure_ascii=False, indent=2))


def agent3(a1, a2, n_reviews, asin):
    """Karar + öneri. Tutarsızlıkta ihlali açıklayıp 1 kez tekrar sorar.
    (sonuç, meta) döndürür; ikinci deneme de tutarsızsa sonuç DEĞİŞTİRİLMEDEN meta['tutarsiz'] = True."""
    system, user = load_prompt("gap_fix"), agent3_input(a1, a2)
    res = llm.call_llm(system, user, RESULT_SCHEMA, tag=f"agent3:{asin}")
    viol = result_violations(res, n_reviews)
    meta = {"deneme": 1, "ilk_ihlaller": viol, "tutarsiz": False, "ihlaller": []}
    if not viol:
        return res, meta
    retry_user = (user + "\n\nÖNCEKİ CEVABIN AŞAĞIDAKİ KURAL İHLALLERİNİ İÇERİYOR:\n"
                  + "\n".join(f"- {x}" for x in viol)
                  + "\n\nÖnceki cevap:\n" + json.dumps(res, ensure_ascii=False, indent=2)
                  + "\n\nKurallara uyan düzeltilmiş cevabı ver.")
    res2 = llm.call_llm(system, retry_user, RESULT_SCHEMA, tag=f"agent3_retry:{asin}")
    viol2 = result_violations(res2, n_reviews)
    meta.update({"deneme": 2, "ihlaller": viol2, "tutarsiz": bool(viol2)})
    return res2, meta


__all__ = ["GAP_TYPES", "agent1", "agent2", "agent3", "check_input", "load_prompt", "page_text",
           "result_violations", "review_mining_warnings", "reviews_text", "rule_sections", "rules_block"]
