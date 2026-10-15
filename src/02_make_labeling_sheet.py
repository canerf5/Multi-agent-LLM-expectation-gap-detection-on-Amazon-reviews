"""
FAZ 4 — Etiketleme dosyasını hazırla

products_200.jsonl içindeki 40 "gold" ürünü bir Excel dosyasına yazar.
Sen sadece sağdaki sarı sütunları doldurursun.

Çıktı: data/gold/etiketleme.xlsx

Kullanım:
    python src/02_make_labeling_sheet.py
"""
import json
from pathlib import Path

import yaml
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]

GAP_TYPES = ["Beden/Kalıp", "Renk", "Görsel", "Kalite", "Malzeme", "Dayanıklılık", "Eksik Bilgi"]


def page_text(p):
    parts = [f"BAŞLIK: {p['title']}"]
    if p.get("price") is not None:
        parts.append(f"FİYAT: ${p['price']}")
    if p.get("features"):
        parts.append("ÖZELLİKLER:\n" + "\n".join(f"• {x}" for x in p["features"]))
    if p.get("description"):
        parts.append("AÇIKLAMA: " + p["description"][:800])
    if p.get("details"):
        d = "; ".join(f"{k}: {v}" for k, v in list(p["details"].items())[:8])
        parts.append("DETAYLAR: " + d)
    return "\n\n".join(parts)


def reviews_text(p):
    lines = []
    for i, r in enumerate(p["negative_reviews"], 1):
        t = r["text"][:500]
        lines.append(f"{i}) [{int(r['rating'])}★] {r['title']} — {t}")
    return "\n\n".join(lines)


def main():
    cfg = yaml.safe_load(open(ROOT / "config.yaml", encoding="utf-8"))
    src = ROOT / "data" / "processed" / f"products_{cfg['n_products']}.jsonl"
    products = [json.loads(l) for l in open(src, encoding="utf-8")]
    gold = [p for p in products if p["split"] == "gold"]

    wb = Workbook()

    # ---------- Talimat sayfası ----------
    ins = wb.active
    ins.title = "Talimatlar"
    rules = [
        "ETİKETLEME TALİMATI",
        "",
        "Her satırda bir ürün var. Ürünü GÖRMENE gerek yok; sadece 'Sayfada yazan' ve 'Negatif yorumlar' sütunlarını oku.",
        "Soru: Sayfanın verdiği söz ile müşterilerin şikayeti arasında çelişki var mı?",
        "",
        "1) gap_var: Evet / Hayır",
        "2) Konu sütunları: çelişki hangi konudaysa o sütuna X koy (birden fazla olabilir).",
        "   Kural: Bir konu ancak EN AZ 2 yorum o sorundan bahsediyorsa işaretlenir.",
        "3) seviye:",
        "   Yüksek = Sayfa açıkça bir şey iddia etmiş, yorumlar tersini söylüyor (ör. 'su geçirmez' yazıyor, 'su aldı' diyorlar)",
        "   Orta   = Sayfa o konuda bilgi vermemiş, yorumlar şikayet ediyor (ör. beden bilgisi yok, 'küçük geldi' diyorlar)",
        "   Yok    = Çelişki yok (gap_var = Hayır ise seviye de Yok)",
        "4) not: Neden bu kararı verdin, 1 cümle.",
        "",
        "SAYILMAYANLAR: kargo/paketleme, satıcı/iade süreci, 'beğenmedim' gibi kişisel zevk, tek seferlik arıza (1 yorum).",
        "",
        "ÖRNEK: Sayfa 'Waterproof leather boot' diyor; 2 yorum 'su aldı', 1 yorum 'kargo geç'.",
        "        -> gap_var = Evet | Malzeme = X (su geçirmezlik malzeme iddiası) | seviye = Yüksek | not: 'Su geçirmez diyor, 2/2 ilgili yorum su aldı diyor'",
        "",
        "ÖNEMLİ: Bu dosyayı bitirip GitHub'a commit etmeden yapay zeka sistemini ÇALIŞTIRMA.",
    ]
    for i, r in enumerate(rules, 1):
        ins.cell(row=i, column=1, value=r)
    ins["A1"].font = Font(bold=True, size=14)
    ins.column_dimensions["A"].width = 130

    # ---------- Etiket sayfası ----------
    ws = wb.create_sheet("Etiketler")
    headers = ["no", "parent_asin", "Sayfada yazan", "Negatif yorumlar", "gap_var"] + GAP_TYPES + ["seviye", "not"]
    ws.append(headers)
    for i, p in enumerate(gold, 1):
        ws.append([i, p["parent_asin"], page_text(p), reviews_text(p), None]
                  + [None] * len(GAP_TYPES) + [None, None])

    head_fill = PatternFill("solid", fgColor="1F3A5F")
    input_fill = PatternFill("solid", fgColor="FFF4CC")
    n = len(gold) + 1
    first_input = 5
    last_input = len(headers)
    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = head_fill
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    for r in range(2, n + 1):
        ws.row_dimensions[r].height = 300
        for c in range(1, len(headers) + 1):
            cell = ws.cell(row=r, column=c)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if c >= first_input:
                cell.fill = input_fill

    widths = {"A": 5, "B": 13, "C": 55, "D": 75, "E": 9}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w
    from openpyxl.utils import get_column_letter
    for c in range(6, 6 + len(GAP_TYPES)):
        ws.column_dimensions[get_column_letter(c)].width = 9
    ws.column_dimensions[get_column_letter(last_input - 1)].width = 10
    ws.column_dimensions[get_column_letter(last_input)].width = 35
    ws.freeze_panes = "C2"

    # Açılır listeler
    def dv(options, col_from, col_to):
        v = DataValidation(type="list", formula1='"' + ",".join(options) + '"', allow_blank=True)
        ws.add_data_validation(v)
        v.add(f"{get_column_letter(col_from)}2:{get_column_letter(col_to)}{n}")

    dv(["Evet", "Hayır"], 5, 5)
    dv(["X"], 6, 5 + len(GAP_TYPES))
    dv(["Yok", "Orta", "Yüksek"], last_input - 1, last_input - 1)

    out = ROOT / "data" / "gold" / "etiketleme.xlsx"
    wb.save(out)
    print(f"Yazıldı: {out}  ({len(gold)} ürün)")


if __name__ == "__main__":
    main()
