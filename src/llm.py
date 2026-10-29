"""
FAZ 5 — Tek ortak LLM çağrısı: call_llm(system_prompt, user_content, schema, tag)

- Ayarlar config.yaml'dan (model, temperature = 0, fiyatlar, zaman aşımı, tekrar).
- OpenAI Structured Outputs (strict JSON şeması) ile çağrı; dönen JSON şemaya göre
  ayrıca doğrulanır.
- Önbellek: anahtar = sha256(model + system_prompt + user_content + şema),
  dosya = outputs/cache/<hash>.json. Aynı girdi ikinci kez ödenmez.
- Her çağrı outputs/llm_log.jsonl'a yazılır: zaman, tag, model, token, maliyet,
  önbellek isabeti.
- Hata / zaman aşımında 3 kez artan beklemeyle (2, 4, 8 sn) tekrar dener.
- Güvenlik: config.yaml'da model_verified = false iken gerçek API çağrısı yapılmaz
  (önbellekten okuma serbest).

Testler gerçek API yerine `_request` fonksiyonunu sahte bir fonksiyonla değiştirir.
"""
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from schemas import response_format, validate

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"          # testler geçici bir klasöre yönlendirir
RETRY_WAIT = (2, 4, 8)

_cfg = None
_client = None


class LLMError(RuntimeError):
    pass


def cfg():
    global _cfg
    if _cfg is None:
        with open(ROOT / "config.yaml", encoding="utf-8") as f:
            _cfg = yaml.safe_load(f)
    return _cfg


def cache_key(model, system_prompt, user_content, schema):
    blob = json.dumps({"model": model, "system": system_prompt, "user": user_content, "schema": schema},
                      ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def cost_usd(usage):
    c = cfg()
    pin, pout = c.get("price_input_per_1m"), c.get("price_output_per_1m")
    if pin is None or pout is None or not usage:
        return None
    return round(usage["input_tokens"] * pin / 1e6 + usage["output_tokens"] * pout / 1e6, 8)


def _get_client():
    global _client
    if _client is None:
        from dotenv import dotenv_values
        from openai import OpenAI
        key = dotenv_values(ROOT / ".env").get("OPENAI_API_KEY")
        if not key or key == "sk-...":
            raise LLMError(".env içinde OPENAI_API_KEY yok")
        _client = OpenAI(api_key=key, max_retries=0)  # tekrar denemeyi burada kendimiz yapıyoruz
    return _client


def _request(model, system_prompt, user_content, schema, temperature, timeout):
    """Gerçek API çağrısı. (içerik metni, usage) döndürür."""
    resp = _get_client().chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
        response_format=response_format(schema),
        timeout=timeout,
    )
    msg = resp.choices[0].message
    if getattr(msg, "refusal", None):
        raise LLMError(f"Model reddetti: {msg.refusal}")
    if resp.choices[0].finish_reason == "length":
        raise LLMError("Yanıt token sınırında kesildi")
    usage = {"input_tokens": resp.usage.prompt_tokens, "output_tokens": resp.usage.completion_tokens,
             "model_returned": resp.model}
    return msg.content, usage


def _retryable(exc):
    try:
        import openai
    except ImportError:
        return False
    kinds = tuple(getattr(openai, n) for n in ("APITimeoutError", "APIConnectionError", "RateLimitError",
                                                 "InternalServerError") if hasattr(openai, n))
    return isinstance(exc, kinds) or isinstance(exc, TimeoutError)


def _log(entry):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "llm_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def call_llm(system_prompt, user_content, schema, tag):
    """Şemaya uyan JSON'u (dict) döndürür. Önbellekte varsa API çağrısı yapmaz."""
    c = cfg()
    model = c["model"]
    key = cache_key(model, system_prompt, user_content, schema)
    path = OUT_DIR / "cache" / f"{key}.json"
    entry = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tag": tag, "model": model,
             "cache_key": key}

    if path.exists():
        with open(path, encoding="utf-8") as f:
            cached = json.load(f)
        _log({**entry, "cache_hit": True, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
        return cached["response"]

    if _request is _REAL_REQUEST and not c.get("model_verified"):
        raise LLMError("config.yaml: model_verified = false. Model erişimi doğrulanmadan gerçek API çağrısı "
                       "yapılmaz.")

    last = None
    for attempt in range(c.get("llm_retries", 3) + 1):
        try:
            content, usage = _request(model, system_prompt, user_content, schema, c.get("temperature", 0),
                                      c.get("llm_timeout", 120))
            break
        except Exception as exc:  # noqa: BLE001
            last = exc
            if not _retryable(exc) or attempt >= c.get("llm_retries", 3):
                _log({**entry, "cache_hit": False, "error": f"{type(exc).__name__}: {exc}", "attempt": attempt + 1})
                raise
            time.sleep(RETRY_WAIT[min(attempt, len(RETRY_WAIT) - 1)])
    else:  # pragma: no cover
        raise LLMError(f"Çağrı başarısız: {last}")

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        _log({**entry, "cache_hit": False, "error": "JSON çözülemedi", **usage})
        raise LLMError(f"[{tag}] JSON çözülemedi: {exc}") from exc
    errs = validate(data, schema["schema"])
    if errs:
        _log({**entry, "cache_hit": False, "error": "şema ihlali", "detail": errs[:5], **usage})
        raise LLMError(f"[{tag}] yanıt şemaya uymuyor: {errs[:5]}")

    cost = cost_usd(usage)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"tag": tag, "model": model, "usage": usage, "cost_usd": cost, "created": entry["time"],
                   "request": {"system": system_prompt, "user": user_content, "schema": schema["name"]},
                   "response": data}, f, ensure_ascii=False, indent=2)
    _log({**entry, "cache_hit": False, "input_tokens": usage["input_tokens"],
          "output_tokens": usage["output_tokens"], "cost_usd": cost,
          "model_returned": usage.get("model_returned")})
    return data


_REAL_REQUEST = _request
