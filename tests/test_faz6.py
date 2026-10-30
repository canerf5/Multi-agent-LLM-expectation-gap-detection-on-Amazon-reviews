"""
FAZ 6 — Tek LLM baseline için API'siz testler (sahte LLM ile)

Çalıştırma:
    .venv/bin/python -m unittest tests.test_faz6 -v

Gerçek API çağrılmaz; çıktılar geçici bir klasöre yazılır. Gold içeriği okunmaz.
"""
import csv
import json
import unittest
from unittest import mock

from tests.test_faz5 import BAD_RESULT, VALID_RESULT, FakeLLM, TempOutputs, all_asins, ROOT  # noqa: F401

import agents  # noqa: E402
import baseline  # noqa: E402
import llm  # noqa: E402
import pipeline  # noqa: E402
import schemas  # noqa: E402


class TestBaselinePrompt(unittest.TestCase):
    def test_same_rules_and_example(self):
        prompt = agents.load_prompt("baseline")
        sec = agents.rule_sections()
        for name in agents.RULE_SECTIONS:
            self.assertIn(sec[name], prompt, name)
        self.assertIn(sec["Örnek"], prompt)
        self.assertNotRegex(prompt, r"\{[A-ZÇĞİÖŞÜ_]+\}")
        raw = (ROOT / "prompts" / "baseline.md").read_text(encoding="utf-8")
        self.assertNotRegex(raw, r"\bB0[0-9A-Z]{8}\b")                          # prompt'ta ASIN yok

    def test_instructions_of_three_agents_present(self):
        """Üç ajan prompt'undaki görev talimatlarının baseline'da da bulunduğunu (birebir parça) denetler."""
        base = (ROOT / "prompts" / "baseline.md").read_text(encoding="utf-8")
        must = [
            # Ajan 1
            "Sayfanın TÜM bölümlerini tara; açıklama paragrafının içindeki iddiaları da ayrı ayrı",
            "Eksik Bilgi dışındaki 6 konudan, tanımı bu ifadeye en iyi uyanı seç",
            "BİREBİR alıntısı (İngilizce, kelimesi kelimesine",
            "Tanımdaki ölçüt \"doğrulanabilir\" olmaktır",
            "Sayfada olmayan bir vaadi ekleme",
            "paket/kargo ölçüsü ve ağırlığı, sayfanın listelenme tarihi, model/ürün numarası",
            "İfade bir materyal adı içeriyorsa (ör. leather, cotton, synthetic)",
            "Sayfanın bir konuda bilgi VERMEMESİ de önemlidir",
            # Ajan 2
            "Aynı sorunu dile getiren yorumları, farklı kelimelerle anlatılsa bile TEK grupta topla",
            "Eksik Bilgi'yi yalnızca yorum, sayfada veya açıklamada bir bilginin YER ALMADIĞINI açıkça söylüyorsa",
            "Üründe bir özelliğin bulunmaması veya yetersiz olması da Eksik Bilgi değildir",
            "bir yorum ilgili gruplardan yalnızca BİRİNDE yer alır",
            "Sadece yorumlarda yazanı kullan; tahmin etme. Yorum numaraları yalnızca verilen numaralardan olmalı.",
            # Ajan 3
            "Aynı tipteki farklı sorunları birbirine ekleyerek 2'ye tamamlama.",
            "2 yorum şartını sağlamayan tipi TAMAMEN çıkar",
            "\"gap yok\" geçerli ve normal bir sonuçtur",
            "Somut iddia olsa bile şikayet onunla DOĞRUDAN çelişmiyorsa Orta'dır.",
            "sayfa_iddiasi \"bilgi yok\" olan bir tip hiçbir zaman Yüksek değildir.",
            "sayfaya iddia yükleme",
            "Eklenecek bilginin İÇERİĞİNİ yaz",
            "Yalnızca ürün sayfası değişikliği öner.",
            "Ölçü, oran veya değer uydurma",
            "SON KONTROL",
        ]
        missing = [m for m in must if m not in base]
        self.assertEqual(missing, [])
        self.assertNotIn("Ajan 1", base)                                         # ara çıktıya atıf yok
        self.assertNotIn("Ajan 2", base)

    def test_input_is_same_text_as_agents(self):
        p = pipeline.load_products("dev")[0]
        page, rev = agents.page_text(p), agents.reviews_text(p)
        text = agents.baseline_input(page, rev)
        self.assertIn(page, text)
        self.assertIn(rev, text)
        self.assertEqual(agents.check_input(p, page, rev), [])


class TestBaselineRun(TempOutputs):
    def test_run_records_and_visibility(self):
        fake = FakeLLM()
        with mock.patch.object(llm, "_request", fake):
            self.assertIsNone(baseline.main(["--not", "deneme"]))
        dev = all_asins("dev")
        self.assertEqual(len(fake.calls), 5)
        self.assertEqual({c["schema"] for c in fake.calls}, {"gap_result"})
        self.assertTrue(all(c["temperature"] == 0 for c in fake.calls))
        self.assertEqual({c["system"] for c in fake.calls}, {agents.load_prompt("baseline")})
        p = pipeline.load_products("dev")[0]
        call = next(c for c in fake.calls if p["title"] in c["user"])
        self.assertIn(p["negative_reviews"][0]["text"], call["user"])           # sayfa + yorum birlikte

        (run,) = (self.tmp / "runs" / "dev").iterdir()
        self.assertTrue(run.name.endswith("_baseline_deneme"))
        man = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(man["sistem"], "baseline")
        self.assertTrue(man["tamamlandi"])
        self.assertEqual(set(man["hash"]["prompts"]), {"baseline"})
        with open(run / "sonuclar.csv", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual({r["parent_asin"] for r in rows}, set(dev))
        for asin in dev:
            for f in ("baseline.json", "meta.json", "ozet.txt"):
                self.assertTrue((run / asin / f).exists())
                self.assertTrue((self.tmp / "baseline" / "dev" / asin / f).exists())
        self.assertFalse((self.tmp / "multi_agent").exists())
        with open(self.tmp / "runs" / "index.csv", encoding="utf-8") as f:
            self.assertEqual([r["sistem"] for r in csv.DictReader(f)], ["baseline"])

    def test_same_check_and_single_retry(self):
        asin = next(iter(all_asins("dev")))
        fake = FakeLLM(agent3_answers=[BAD_RESULT, VALID_RESULT])
        with mock.patch.object(llm, "_request", fake):
            baseline.main(["--asin", asin])
        (run,) = (self.tmp / "runs" / "dev").iterdir()
        meta = json.loads((run / asin / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual((meta["deneme"], meta["tutarsiz"]), (2, False))
        self.assertIn("KURAL İHLALLERİNİ", fake.calls[1]["user"])
        tags = [json.loads(l)["tag"] for l in (self.tmp / "llm_log.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(tags, [f"baseline:{asin}", f"baseline_retry:{asin}"])

        fake2 = FakeLLM(agent3_answers=[BAD_RESULT, BAD_RESULT])
        asin2 = sorted(all_asins("dev"))[1]
        with mock.patch.object(llm, "_request", fake2):
            baseline.main(["--asin", asin2])
        run2 = next(d for d in (self.tmp / "runs" / "dev").iterdir() if d != run)
        meta2 = json.loads((run2 / asin2 / "meta.json").read_text(encoding="utf-8"))
        self.assertTrue(meta2["tutarsiz"])
        self.assertEqual(len(fake2.calls), 2)                                    # yalnızca 1 tekrar

    def test_quote_source_is_page(self):
        p = pipeline.load_products("dev")[0]
        page = agents.page_text(p)
        claim = p["title"][:25]
        good = {**VALID_RESULT, "tip_gerekceleri": [{**VALID_RESULT["tip_gerekceleri"][0], "sayfa_iddiasi": claim}],
                "oneriler": [{**VALID_RESULT["oneriler"][0], "sayfa_iddiasi": claim, "islem": "değiştir"}]}
        self.assertEqual(agents.result_violations(good, 5, [page]), [])
        bad = {**good, "tip_gerekceleri": [{**good["tip_gerekceleri"][0], "sayfa_iddiasi": "made-up claim xyz"}]}
        self.assertTrue(any("birebir geçmiyor" in v for v in agents.result_violations(bad, 5, [page])))

    def test_gold_lock_and_options(self):
        fake = FakeLLM()
        for split in ("gold", "all"):
            with mock.patch.object(llm, "_request", fake), \
                    mock.patch.object(pipeline, "gold_lock", side_effect=pipeline.GoldLockError("kilit")):
                with self.assertRaises(pipeline.GoldLockError):
                    baseline.main(["--split", split])
        self.assertEqual(fake.calls, [])
        rest_asin = next(iter(all_asins("rest")))
        with mock.patch.object(llm, "_request", fake):
            with self.assertRaises(SystemExit):
                baseline.main(["--asin", rest_asin])
        self.assertEqual(fake.calls, [])
        e = baseline.estimate(pipeline.load_products("dev"))
        self.assertEqual((e["urun"], e["cagri"], e["cagri_tekrar_dahil_en_fazla"]), (5, 5, 10))
        self.assertFalse((self.tmp / "runs").exists())


if __name__ == "__main__":
    unittest.main()
