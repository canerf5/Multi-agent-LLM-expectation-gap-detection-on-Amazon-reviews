"""
FAZ 5 — API'siz testler (sahte LLM ile)

Çalıştırma:
    .venv/bin/python -m unittest tests.test_faz5 -v

Gerçek API çağrılmaz: llm._request sahte fonksiyonla değiştirilir, tüm çıktılar geçici
bir klasöre yazılır (repo içindeki outputs/ klasörüne dokunulmaz).
Gold ürünlerin içeriği ve gold etiket dosyaları okunmaz; gold izi taraması
src/audit_gold.py ile kullanıcı tarafından yapılır.
"""
import copy
import hashlib
import importlib.util
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import agents  # noqa: E402
import llm  # noqa: E402
import pipeline  # noqa: E402
import runs  # noqa: E402
import schemas  # noqa: E402


def load_module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / "src" / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def all_asins(split):
    """Yalnızca gold dışı kümeler için (gold ürünlere bakılmaz)."""
    assert split != "gold"
    with open(ROOT / "data" / "processed" / "products_200.jsonl", encoding="utf-8") as f:
        return {p["parent_asin"]: p["title"] for p in map(json.loads, f) if p["split"] == split}


VALID_RESULT = {"gap_var": True, "gap_tipleri": ["Beden/Kalıp"], "seviye": "Orta",
                "tip_gerekceleri": [{"tip": "Beden/Kalıp", "yorum_numaralari": [1, 2], "sayfa_iddiasi": "bilgi yok"}],
                "ana_risk": "Beden küçük geliyor.",
                "oneriler": [{"tip": "Beden/Kalıp", "sayfa_iddiasi": "bilgi yok",
                              "musteri_deneyimi": "Yorum 1, 2: küçük geliyor", "islem": "ekle",
                              "duzeltme": "Beden tablosu ekle"}]}
BAD_RESULT = {**VALID_RESULT, "tip_gerekceleri": [{"tip": "Beden/Kalıp", "yorum_numaralari": [1],
                                                    "sayfa_iddiasi": "bilgi yok"}]}


class FakeLLM:
    """Şema adına göre cevap veren sahte istek fonksiyonu; çağrıları kaydeder."""

    def __init__(self, agent3_answers=None):
        self.calls = []
        self.agent3_answers = list(agent3_answers or [])

    def __call__(self, model, system_prompt, user_content, schema, temperature, timeout):
        self.calls.append({"schema": schema["name"], "system": system_prompt, "user": user_content,
                           "temperature": temperature})
        tag = "id-" + hashlib.sha1(user_content.encode()).hexdigest()[:8]   # ürüne özgü, ham metin içermez
        if schema["name"] == "expectation":
            out = {"beklentiler": [{"konu": "Beden/Kalıp", "iddia": tag, "iddia_turu": "genel"}]}
        elif schema["name"] == "review_mining":
            out = {"sikayet_gruplari": [{"tip": "Beden/Kalıp", "ozet": tag, "yorum_numaralari": [1, 2],
                                         "ilgili": True, "ilgisiz_sebebi": None}]}
        else:
            out = self.agent3_answers.pop(0) if self.agent3_answers else VALID_RESULT
        return json.dumps(out, ensure_ascii=False), {"input_tokens": 1000, "output_tokens": 200,
                                                      "model_returned": model}


class TempOutputs(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._out = llm.OUT_DIR
        llm.OUT_DIR = self.tmp

    def tearDown(self):
        llm.OUT_DIR = self._out
        shutil.rmtree(self.tmp)

    def log(self):
        p = self.tmp / "llm_log.jsonl"
        return [json.loads(l) for l in open(p, encoding="utf-8")] if p.exists() else []


# ------------------------------------------------------------------ kurallar ve prompt'lar
class TestRulesAndPrompts(unittest.TestCase):
    def test_sections_read_from_rules_file(self):
        text = (ROOT / "docs" / "etiketleme_kurallari.md").read_text(encoding="utf-8")
        sec = agents.rule_sections()
        for name in agents.RULE_SECTIONS:
            self.assertIn(f"## {name}", text)
            self.assertTrue(sec[name])
            for pname in ("expectation", "review_mining", "gap_fix"):
                self.assertIn(sec[name], agents.load_prompt(pname), f"{pname}: '{name}' bölümü prompt'ta yok")
        self.assertIn(sec["Örnek"], agents.load_prompt("gap_fix"))

    def test_prompt_follows_rules_file_at_runtime(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            src = (ROOT / "docs" / "etiketleme_kurallari.md").read_text(encoding="utf-8")
            marked = src.replace("## Sayılmayanlar\n", "## Sayılmayanlar\n- TEST_ISARETI_123\n")
            (tmp / "k.md").write_text(marked, encoding="utf-8")
            self.assertIn("TEST_ISARETI_123", agents.load_prompt("review_mining", rules_path=tmp / "k.md"))
            (tmp / "eksik.md").write_text(src.replace("## Seviye kuralı", "## Baska"), encoding="utf-8")
            with self.assertRaises(ValueError):
                agents.load_prompt("gap_fix", rules_path=tmp / "eksik.md")
        finally:
            shutil.rmtree(tmp)

    def test_no_placeholders_left(self):
        for pname in ("expectation", "review_mining", "gap_fix"):
            raw = (ROOT / "prompts" / f"{pname}.md").read_text(encoding="utf-8")
            self.assertIn("{KURALLAR}", raw)
            self.assertNotRegex(agents.load_prompt(pname), r"\{[A-ZÇĞİÖŞÜ_]+\}")
            self.assertNotRegex(raw, r"\bB0[0-9A-Z]{8}\b")                   # prompt'ta hiç ASIN yok


# ------------------------------------------------------------------ şemalar
class TestSchemas(unittest.TestCase):
    def test_strict(self):
        for s in schemas.ALL_SCHEMAS:
            self.assertEqual(schemas.check_strict(s["schema"]), [], s["name"])
            rf = schemas.response_format(s)
            self.assertTrue(rf["json_schema"]["strict"])

    def test_constants_match_rules_and_gold(self):
        m02 = load_module("m02", "02_make_labeling_sheet.py")
        m03 = load_module("m03", "03_export_gold.py")
        self.assertEqual(schemas.GAP_TYPES, m02.GAP_TYPES)
        self.assertEqual(schemas.GAP_TYPES, m03.GAP_TYPES)
        self.assertEqual(schemas.LEVELS, m03.LEVELS)
        self.assertEqual(list(schemas.GOLD_COLS.values()), m03.TYPE_COLS)  # gold CSV bu sütunlarla yazılır
        rules = (ROOT / "docs" / "etiketleme_kurallari.md").read_text(encoding="utf-8")
        for t in schemas.GAP_TYPES:
            self.assertIn(f"| {t} |", rules)
        for lvl in schemas.LEVELS:
            self.assertIn(lvl, rules)

    def test_validate(self):
        self.assertEqual(schemas.validate(VALID_RESULT, schemas.RESULT_SCHEMA["schema"]), [])
        bad = {**VALID_RESULT, "seviye": "Çok"}
        self.assertTrue(schemas.validate(bad, schemas.RESULT_SCHEMA["schema"]))
        extra = {**VALID_RESULT, "fazla": 1}
        self.assertTrue(schemas.validate(extra, schemas.RESULT_SCHEMA["schema"]))


# ------------------------------------------------------------------ girdi
class TestInput(unittest.TestCase):
    def test_dev_inputs_complete(self):
        for p in pipeline.load_products("dev"):
            page, rev = agents.page_text(p), agents.reviews_text(p)
            self.assertEqual(agents.check_input(p, page, rev), [], p["parent_asin"])
            self.assertLessEqual(len(p["negative_reviews"]), 15)

    def test_truncation_detected(self):
        p = copy.deepcopy(pipeline.load_products("dev")[0])
        page, rev = agents.page_text(p), agents.reviews_text(p)
        long_review = max(p["negative_reviews"], key=lambda r: len(r["text"]))["text"]
        self.assertTrue(agents.check_input(p, page, rev.replace(long_review, long_review[:20])))
        if p.get("description"):
            self.assertTrue(agents.check_input(p, page.replace(p["description"], p["description"][:30]), rev))
        self.assertTrue(agents.check_input(p, page.replace(f"• {p['features'][0]}", ""), rev))

    def test_review_format_same_as_review_sheet(self):
        """Ajan 2 girdisi, gözden geçirme dosyasındaki (04_review_gold.py) yorum biçimiyle aynı."""
        src4 = (ROOT / "src" / "04_review_gold.py").read_text(encoding="utf-8")
        fmt = "f\"{i}) [{int(r['rating'])}★] {r['title']} — {r['text']}\""
        self.assertIn(fmt, src4)
        self.assertIn(fmt, (ROOT / "src" / "agents.py").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ tutarlılık
class TestConsistency(unittest.TestCase):
    def test_rules(self):
        rv = agents.result_violations
        self.assertEqual(rv(VALID_RESULT, 5), [])
        self.assertTrue(rv({**VALID_RESULT, "gap_var": False}, 5))
        self.assertEqual(rv({"gap_var": False, "gap_tipleri": [], "seviye": "Yok", "tip_gerekceleri": [],
                             "ana_risk": "", "oneriler": []}, 5), [])
        self.assertTrue(rv({**VALID_RESULT, "seviye": "Yok"}, 5))
        self.assertTrue(rv(BAD_RESULT, 5))                                  # tek yorum
        self.assertTrue(rv(VALID_RESULT, 1))                                # olmayan yorum no
        overlap = {**VALID_RESULT, "gap_tipleri": ["Beden/Kalıp", "Renk"], "tip_gerekceleri": [
            {"tip": "Beden/Kalıp", "yorum_numaralari": [1, 2], "sayfa_iddiasi": "bilgi yok"},
            {"tip": "Renk", "yorum_numaralari": [2, 3], "sayfa_iddiasi": "bilgi yok"}]}
        self.assertTrue(any("tek konu" in x for x in rv(overlap, 5)))
        missing = {**VALID_RESULT, "gap_tipleri": ["Beden/Kalıp", "Renk"]}
        self.assertTrue(any("Renk" in x for x in rv(missing, 5)))

    def test_level_and_quote_rules(self):
        rv = agents.result_violations
        # sayfa iddiası yokken Yüksek olamaz
        self.assertTrue(any("Yüksek" in x for x in rv({**VALID_RESULT, "seviye": "Yüksek"}, 5)))
        claim = "Runs true to size"
        high = {**VALID_RESULT, "seviye": "Yüksek",
                "tip_gerekceleri": [{"tip": "Beden/Kalıp", "yorum_numaralari": [1, 2], "sayfa_iddiasi": claim}],
                "oneriler": [{**VALID_RESULT["oneriler"][0], "sayfa_iddiasi": claim, "islem": "değiştir"}]}
        self.assertEqual(rv(high, 5, quotes=["Fit: runs  TRUE to size."]), [])     # boşluk/harf duyarsız
        self.assertEqual(rv(high, 5), [])                                          # kaynak verilmezse denetlenmez
        made_up = rv(high, 5, quotes=["100% cotton"])
        self.assertTrue(any("birebir geçmiyor" in x for x in made_up))
        self.assertTrue(any("öneri 1" in x for x in made_up))

    def test_suggestion_rules(self):
        rv = agents.result_violations
        fix = VALID_RESULT["oneriler"][0]
        self.assertTrue(any("oneriler boş" in x for x in rv({**VALID_RESULT, "oneriler": []}, 5)))
        self.assertTrue(any("gap_tipleri içinde yok" in x
                            for x in rv({**VALID_RESULT, "oneriler": [{**fix, "tip": "Renk"}]}, 5)))
        self.assertTrue(any("'ekle' olmalı" in x
                            for x in rv({**VALID_RESULT, "oneriler": [{**fix, "islem": "kaldır"}]}, 5)))
        self.assertTrue(any("duzeltme boş" in x
                            for x in rv({**VALID_RESULT, "oneriler": [{**fix, "duzeltme": " "}]}, 5)))
        no_gap = {"gap_var": False, "gap_tipleri": [], "seviye": "Yok", "tip_gerekceleri": [], "ana_risk": "",
                  "oneriler": [fix]}
        self.assertTrue(any("oneriler dolu" in x for x in rv(no_gap, 5)))

    def test_expectation_warnings_and_render(self):
        p = pipeline.load_products("dev")[0]
        page = agents.page_text(p)
        ok = {"beklentiler": [{"konu": "Diğer", "iddia": p["title"], "iddia_turu": "genel"}]}
        self.assertEqual(agents.expectation_warnings(ok, page), [])
        bad = {"beklentiler": [{"konu": "Malzeme", "iddia": "uydurma iddia xyz", "iddia_turu": "somut"}]}
        self.assertEqual(len(agents.expectation_warnings(bad, page)), 1)
        text = agents.render_text("B000TEST00", VALID_RESULT)
        for part in ("B000TEST00", "gap_var:      Evet", "Beden/Kalıp", "[Beden/Kalıp | ekle] Beden tablosu ekle"):
            self.assertIn(part, text)
        self.assertNotIn("Eksik Bilgi", schemas.EXPECTATION_TOPICS)


# ------------------------------------------------------------------ uçtan uca (sahte LLM)
class TestEndToEnd(TempOutputs):
    def test_dev_run_files_log_and_cache(self):
        fake = FakeLLM()
        with mock.patch.object(llm, "_request", fake):
            pipeline.main([])
        dev, other = all_asins("dev"), {**all_asins("rest"), **all_asins("reserve")}
        out = self.tmp / "multi_agent"
        self.assertEqual({d.name for d in out.iterdir() if d.is_dir()}, {"dev"})
        self.assertEqual({d.name for d in (out / "dev").iterdir() if d.is_dir()}, set(dev))
        for asin in dev:
            for f in ("agent1.json", "agent2.json", "agent3.json", "meta.json", "ozet.txt"):
                self.assertTrue((out / "dev" / asin / f).exists(), f"{asin}/{f}")
        self.assertEqual(len(fake.calls), 15)
        self.assertTrue(all(c["temperature"] == 0 for c in fake.calls))
        a1_users = [c["user"] for c in fake.calls if c["schema"] == "expectation"]
        self.assertEqual(sorted(u.split("\n")[0] for u in a1_users),          # yalnızca 5 dev ürün gönderildi
                         sorted(f"BAŞLIK: {t}" for t in dev.values()))
        blob = json.dumps(fake.calls, ensure_ascii=False)
        for title in other.values():
            self.assertNotIn(title[:40], blob)
        # görünürlük: Ajan 1 yorum, Ajan 2 sayfa, Ajan 3 ham metin görmez
        p = pipeline.load_products("dev")[0]
        a1 = next(c for c in fake.calls if c["schema"] == "expectation" and p["title"] in c["user"])
        self.assertNotIn(p["negative_reviews"][0]["text"], a1["user"])
        a2 = next(c for c in fake.calls if c["schema"] == "review_mining"
                  and p["negative_reviews"][0]["text"] in c["user"])
        self.assertNotIn(p["title"], a2["user"])
        for c in fake.calls:
            if c["schema"] == "gap_result":
                self.assertNotIn(p["negative_reviews"][0]["text"], c["user"])
                self.assertNotIn("BAŞLIK:", c["user"])
        log = self.log()
        self.assertEqual(len(log), 15)
        self.assertFalse(any(e["cache_hit"] for e in log))
        self.assertGreater(sum(e["cost_usd"] for e in log), 0)
        self.assertEqual(len(list((self.tmp / "cache").glob("*.json"))), 15)

        fake2 = FakeLLM()
        with mock.patch.object(llm, "_request", fake2):
            pipeline.main([])
        self.assertEqual(fake2.calls, [])                                   # ikinci koşu: hiç API yok
        second = self.log()[15:]
        self.assertEqual(len(second), 15)
        self.assertTrue(all(e["cache_hit"] and e["cost_usd"] == 0 for e in second))

    def test_run_records(self):
        """Her koşu ayrı klasöre yazılır; önbellekli koşuda ödenen 0, eşdeğer maliyet aynı kalır."""
        dev = all_asins("dev")
        with mock.patch.object(llm, "_request", FakeLLM()):
            pipeline.main(["--not", "Öneri formatı v2!"])
        with mock.patch.object(llm, "_request", FakeLLM()):
            pipeline.main([])
        run_dirs = list((self.tmp / "runs" / "dev").iterdir())
        self.assertEqual(len(run_dirs), 2)
        first = next(d for d in run_dirs if d.name.endswith("_multi_agent_oneri-formati-v2"))
        second = next(d for d in run_dirs if d != first)
        for f in ("manifest.json", "sonuclar.csv", "ozetler.txt", "llm_calls.jsonl", "olcumler.json",
                  "prompts/expectation.md", "prompts/review_mining.md", "prompts/gap_fix.md"):
            self.assertTrue((first / f).exists(), f)
        for asin in dev:
            for f in ("agent1.json", "agent2.json", "agent3.json", "meta.json", "ozet.txt"):
                self.assertTrue((first / asin / f).exists(), f"{asin}/{f}")
        self.assertEqual((first / "prompts" / "gap_fix.md").read_text(encoding="utf-8"),
                         agents.load_prompt("gap_fix"))

        import csv
        with open(first / "sonuclar.csv", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(list(rows[0]), runs.RESULT_COLS)
        self.assertEqual({r["parent_asin"] for r in rows}, set(dev))
        self.assertTrue(set(schemas.GOLD_COLS.values()) <= set(rows[0]))      # gold ile aynı tip sütunları

        man = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(man["tamamlandi"])
        self.assertEqual(man["sistem"], "multi_agent")
        self.assertEqual(sorted(man["urunler_tamamlanan"]), sorted(dev))
        self.assertEqual(set(man["hash"]["prompts"]), {"expectation", "review_mining", "gap_fix"})
        for k in ("git_commit", "kod_degisikligi_var", "model", "config"):
            self.assertIn(k, man)

        m1 = json.loads((first / "olcumler.json").read_text(encoding="utf-8"))
        m2 = json.loads((second / "olcumler.json").read_text(encoding="utf-8"))
        self.assertEqual((m1["urun"], m1["cagri"]["toplam"], m1["cagri"]["onbellekten"]), (5, 15, 0))
        self.assertGreater(m1["maliyet_usd"]["odenen"], 0)
        self.assertEqual(m2["cagri"]["onbellekten"], 15)
        self.assertEqual(m2["maliyet_usd"]["odenen"], 0)
        self.assertEqual(m2["maliyet_usd"]["esdeger"], m1["maliyet_usd"]["esdeger"])
        self.assertEqual(m2["token"]["girdi_esdeger"], m1["token"]["girdi_esdeger"])
        self.assertEqual(m1["oneriler"]["islem_dagilimi"]["ekle"], 5)

        with open(self.tmp / "runs" / "index.csv", encoding="utf-8") as f:
            index = list(csv.DictReader(f))
        self.assertEqual([r["run_id"] for r in index], [first.name, second.name])
        self.assertEqual(index[0]["prompt_hash"], index[1]["prompt_hash"])

    def test_partial_run_still_recorded(self):
        class Boom(FakeLLM):
            def __call__(self, *a, **k):
                if len(self.calls) == 3:                                        # 2. ürünün ilk çağrısı
                    raise ValueError("kalıcı hata")
                return super().__call__(*a, **k)
        with mock.patch.object(llm, "_request", Boom()):
            with self.assertRaises(ValueError):
                pipeline.main([])
        (run,) = (self.tmp / "runs" / "dev").iterdir()
        man = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(man["tamamlandi"])
        self.assertIn("kalıcı hata", man["hata"])
        self.assertEqual(len(man["urunler_tamamlanan"]), 1)
        self.assertEqual(len((run / "sonuclar.csv").read_text(encoding="utf-8").splitlines()), 2)

    def test_slug_and_violation_kind(self):
        self.assertEqual(runs.slug("Öneri formatı v2!"), "oneri-formati-v2")
        self.assertEqual(runs.slug(None), "")
        self.assertEqual(runs.violation_kind("Renk: en az 2 farklı destekleyen yorum gerekli, 1 var [1]"),
                         "2 yorum şartı")
        self.assertEqual(runs.violation_kind("bilinmeyen"), "diğer")

    def test_retry_fixes_violation(self):
        asin = next(iter(all_asins("dev")))
        fake = FakeLLM(agent3_answers=[BAD_RESULT, VALID_RESULT])
        with mock.patch.object(llm, "_request", fake):
            pipeline.main(["--asin", asin])
        d = self.tmp / "multi_agent" / "dev" / asin
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["deneme"], 2)
        self.assertFalse(meta["tutarsiz"])
        self.assertTrue(meta["ilk_ihlaller"])
        self.assertEqual(json.loads((d / "agent3.json").read_text(encoding="utf-8")), VALID_RESULT)
        retry = [c for c in fake.calls if c["schema"] == "gap_result"][1]
        self.assertIn("KURAL İHLALLERİNİ", retry["user"])
        self.assertFalse((self.tmp / "multi_agent" / "dev" / "tutarsiz.jsonl").exists())

    def test_still_inconsistent_marked_not_changed(self):
        asin = next(iter(all_asins("dev")))
        bad2 = {**BAD_RESULT, "ana_risk": "ikinci cevap"}
        fake = FakeLLM(agent3_answers=[BAD_RESULT, bad2])
        with mock.patch.object(llm, "_request", fake):
            pipeline.main(["--asin", asin])
        d = self.tmp / "multi_agent" / "dev" / asin
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        self.assertTrue(meta["tutarsiz"])
        self.assertTrue(meta["ihlaller"])
        self.assertEqual(json.loads((d / "agent3.json").read_text(encoding="utf-8")), bad2)
        lines = (self.tmp / "multi_agent" / "dev" / "tutarsiz.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(json.loads(lines[0])["parent_asin"], asin)
        self.assertEqual(len([c for c in fake.calls if c["schema"] == "gap_result"]), 2)


# ------------------------------------------------------------------ gold kilidi
class FakeGit:
    def __init__(self, dirty="", tag=True, same=True):
        self.dirty, self.tag, self.same = dirty, tag, same

    def __call__(self, cmd, **kw):
        r = mock.Mock(stderr="")
        if cmd[1] == "status":
            r.returncode, r.stdout = 0, self.dirty
        elif cmd[1] == "rev-parse":
            r.returncode, r.stdout = (0 if self.tag else 1), ""
        else:
            r.returncode, r.stdout = (0 if self.same else 1), ""
        return r


class TestGoldLock(TempOutputs):
    def test_lock_conditions(self):
        unlock = self.tmp / "kilit_acik"
        with self.assertRaisesRegex(pipeline.GoldLockError, "Kilidi kullanıcı açmalı"):
            pipeline.gold_lock(run=FakeGit(), unlock_file=unlock)             # kullanıcı kilidi yok
        unlock.touch()
        pipeline.gold_lock(run=FakeGit(), unlock_file=unlock)
        for kw in ({"dirty": " M x.csv"}, {"tag": False}, {"same": False}):
            with self.assertRaises(pipeline.GoldLockError):
                pipeline.gold_lock(run=FakeGit(**kw), unlock_file=unlock)

    def test_gold_refused_before_any_call(self):
        fake = FakeLLM()
        with mock.patch.object(llm, "_request", fake), \
                mock.patch.object(pipeline, "gold_lock", side_effect=pipeline.GoldLockError("kilit")):
            with self.assertRaises(pipeline.GoldLockError):
                pipeline.main(["--split", "gold"])
        self.assertEqual(fake.calls, [])
        self.assertFalse((self.tmp / "multi_agent").exists())

    def test_default_split_is_dev_and_asin_must_match_split(self):
        self.assertEqual(pipeline.main.__defaults__, (None,))
        fake = FakeLLM()
        rest_asin = next(iter(all_asins("rest")))
        with mock.patch.object(llm, "_request", fake):
            with self.assertRaises(SystemExit):
                pipeline.main(["--asin", rest_asin])                         # dev kümesinde değil
        self.assertEqual(fake.calls, [])

    def test_real_repo_lock_closed(self):
        """Gerçek repo: kullanıcı kilidi açmadıkça gold reddedilir (gold ÇALIŞTIRILMAZ)."""
        if pipeline.UNLOCK_FILE.exists():
            self.skipTest("kullanıcı kilidi açık")
        with self.assertRaisesRegex(pipeline.GoldLockError, "touch .gold_unlock"):
            pipeline.gold_lock()


# ------------------------------------------------------------------ llm.py
class TestLLM(TempOutputs):
    def test_real_api_blocked_until_verified(self):
        with mock.patch.dict(llm.cfg(), {"model_verified": False}):
            with self.assertRaises(llm.LLMError):
                llm.call_llm("s", "benzersiz-girdi-" + self.tmp.name, schemas.RESULT_SCHEMA, "t")

    def test_retry_with_backoff(self):
        import openai
        err = openai.APITimeoutError(request=None)
        calls = {"n": 0}

        def flaky(*a, **k):
            calls["n"] += 1
            if calls["n"] < 3:
                raise err
            return json.dumps(VALID_RESULT), {"input_tokens": 10, "output_tokens": 5}

        with mock.patch.object(llm, "_request", flaky), mock.patch.object(llm.time, "sleep") as sl:
            self.assertEqual(llm.call_llm("s", "u", schemas.RESULT_SCHEMA, "t"), VALID_RESULT)
        self.assertEqual(calls["n"], 3)
        self.assertEqual([c.args[0] for c in sl.call_args_list], [2, 4])

    def test_non_retryable_and_schema_violation(self):
        def boom(*a, **k):
            raise ValueError("kalıcı hata")
        with mock.patch.object(llm, "_request", boom), mock.patch.object(llm.time, "sleep") as sl:
            with self.assertRaises(ValueError):
                llm.call_llm("s", "u2", schemas.RESULT_SCHEMA, "t")
        sl.assert_not_called()

        def wrong(*a, **k):
            return json.dumps({"gap_var": "evet"}), {"input_tokens": 1, "output_tokens": 1}
        with mock.patch.object(llm, "_request", wrong):
            with self.assertRaises(llm.LLMError):
                llm.call_llm("s", "u3", schemas.RESULT_SCHEMA, "t")
        self.assertFalse((self.tmp / "cache").exists() and any((self.tmp / "cache").iterdir()))

    def test_cache_key_parts(self):
        k = llm.cache_key("m", "s", "u", schemas.RESULT_SCHEMA)
        self.assertNotEqual(k, llm.cache_key("m2", "s", "u", schemas.RESULT_SCHEMA))
        self.assertNotEqual(k, llm.cache_key("m", "s2", "u", schemas.RESULT_SCHEMA))
        self.assertNotEqual(k, llm.cache_key("m", "s", "u2", schemas.RESULT_SCHEMA))
        self.assertNotEqual(k, llm.cache_key("m", "s", "u", schemas.EXPECTATION_SCHEMA))


if __name__ == "__main__":
    unittest.main()
