"""
FAZ 5 — Ortak sabitler ve JSON şemaları

- GAP_TYPES / LEVELS: docs/etiketleme_kurallari.md ile birebir aynı.
- GOLD_COLS: gap tipi -> data/gold/gold_40.csv sütun adı.
- Ajan 1, Ajan 2 ve ORTAK SONUÇ (Ajan 3 + baseline) şemaları OpenAI Structured
  Outputs (strict) kurallarına uygun üretilir: her nesnede tüm alanlar zorunlu,
  additionalProperties = false, null gereken yerde ["tip", "null"].
- validate(): şemaya göre basit yerel doğrulama (testler ve sahte LLM için).
"""

GAP_TYPES = ["Beden/Kalıp", "Renk", "Görsel", "Kalite", "Malzeme", "Dayanıklılık", "Eksik Bilgi"]
LEVELS = ["Yok", "Orta", "Yüksek"]
GOLD_COLS = {
    "Beden/Kalıp": "beden_kalip",
    "Renk": "renk",
    "Görsel": "gorsel",
    "Kalite": "kalite",
    "Malzeme": "malzeme",
    "Dayanıklılık": "dayaniklilik",
    "Eksik Bilgi": "eksik_bilgi",
}
# Değerlendirmede kullanılan tipler (Eksik Bilgi test setinde support = 0; kapsam.md §6)
EVAL_TYPES = [t for t in GAP_TYPES if t != "Eksik Bilgi"]

EXPECTATION_TOPICS = GAP_TYPES + ["Diğer"]
CLAIM_KINDS = ["somut", "genel"]
IRRELEVANT_REASONS = ["kargo/paketleme", "satıcı/iade", "kullanılmış ürün", "kişisel zevk"]
NO_INFO = "bilgi yok"


def _obj(props):
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def _str(desc=None, enum=None, nullable=False):
    s = {"type": ["string", "null"] if nullable else "string"}
    if enum is not None:
        s["enum"] = enum + ([None] if nullable else [])
    if desc:
        s["description"] = desc
    return s


def _arr(items, desc=None):
    s = {"type": "array", "items": items}
    if desc:
        s["description"] = desc
    return s


# ---------------- Ajan 1: Expectation Agent
EXPECTATION_SCHEMA = {
    "name": "expectation",
    "schema": _obj({
        "beklentiler": _arr(_obj({
            "konu": _str("7 gap tipinden biri veya 'Diğer'", EXPECTATION_TOPICS),
            "iddia": _str("Sayfadan birebir alıntı (İngilizce, değiştirmeden)"),
            "iddia_turu": _str("'somut' = ürüne özgü doğrulanabilir bilgi; 'genel' = genel pazarlama dili",
                               CLAIM_KINDS),
        })),
    }),
}

# ---------------- Ajan 2: Review Mining Agent
REVIEW_MINING_SCHEMA = {
    "name": "review_mining",
    "schema": _obj({
        "sikayet_gruplari": _arr(_obj({
            "tip": _str("7 gap tipinden biri; ilgisiz şikayette null", GAP_TYPES, nullable=True),
            "ozet": _str("Şikayetin kısa Türkçe özeti"),
            "yorum_numaralari": _arr({"type": "integer"}, "Bu şikayeti dile getiren yorumların numaraları"),
            "ilgili": {"type": "boolean", "description": "Beklenti uyumsuzluğuyla ilgili mi"},
            "ilgisiz_sebebi": _str("ilgili = false ise sebep; aksi halde null", IRRELEVANT_REASONS,
                                   nullable=True),
        })),
    }),
}

# ---------------- Ortak sonuç: Ajan 3 (Gap + Fix) ve baseline
RESULT_SCHEMA = {
    "name": "gap_result",
    "schema": _obj({
        "gap_var": {"type": "boolean"},
        "gap_tipleri": _arr(_str(enum=GAP_TYPES)),
        "seviye": _str(enum=LEVELS),
        "tip_gerekceleri": _arr(_obj({
            "tip": _str(enum=GAP_TYPES),
            "yorum_numaralari": _arr({"type": "integer"}, "Bu tipi destekleyen yorum numaraları"),
            "sayfa_iddiasi": _str(f"İlgili sayfa iddiası (alıntı) veya '{NO_INFO}'"),
        })),
        "ana_risk": _str("Tek cümlelik ana risk; gap yoksa boş metin"),
        "oneriler": _arr(_str(), "Sayfa iyileştirme önerileri; gap yoksa boş liste"),
    }),
}

ALL_SCHEMAS = [EXPECTATION_SCHEMA, REVIEW_MINING_SCHEMA, RESULT_SCHEMA]


def response_format(spec):
    """OpenAI chat.completions response_format değeri (strict Structured Outputs)."""
    return {"type": "json_schema", "json_schema": {"name": spec["name"], "strict": True, "schema": spec["schema"]}}


# ---------------- Yerel doğrulama (şemada kullanılan alt küme)
def validate(value, schema, path="$"):
    """Şemaya uymayan her nokta için bir hata metni döndürür (boş liste = geçerli)."""
    errs = []
    types = schema.get("type")
    types = types if isinstance(types, list) else [types]
    py = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool, "null": type(None)}
    ok = any(isinstance(value, py[t]) and not (t == "integer" and isinstance(value, bool)) for t in types)
    if not ok:
        return [f"{path}: beklenen {types}, gelen {type(value).__name__}"]
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path}: {value!r} izinli değerlerden değil")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for k in schema.get("required", []):
            if k not in value:
                errs.append(f"{path}.{k}: eksik")
        if schema.get("additionalProperties") is False:
            errs += [f"{path}.{k}: şemada yok" for k in value if k not in props]
        for k, v in value.items():
            if k in props:
                errs += validate(v, props[k], f"{path}.{k}")
    if isinstance(value, list) and "items" in schema:
        for i, v in enumerate(value):
            errs += validate(v, schema["items"], f"{path}[{i}]")
    return errs


def check_strict(schema, path="$"):
    """Strict mod kurallarını denetler: her nesnede tüm alanlar zorunlu ve additionalProperties = false."""
    errs = []
    if schema.get("type") == "object" or "properties" in schema:
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is not False:
            errs.append(f"{path}: additionalProperties false değil")
        if set(schema.get("required", [])) != set(props):
            errs.append(f"{path}: required tüm alanları içermiyor")
        for k, v in props.items():
            errs += check_strict(v, f"{path}.{k}")
    if "items" in schema:
        errs += check_strict(schema["items"], f"{path}[]")
    return errs
