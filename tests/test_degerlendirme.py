"""
FAZ 8 — Değerlendirme script'i testleri (SAHTE altın standart ve sahte koşularla; gerçek gold okunmaz)

Çalıştırma:
    .venv/bin/python -m unittest tests.test_degerlendirme -v

İki örneğin beklenen değerleri elle hesaplanmıştır (açıklamalar test içinde).
"""
import csv
import json
import math
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import evaluate as ev  # noqa: E402
import runs  # noqa: E402
from schemas import GOLD_COLS  # noqa: E402

COLS = list(GOLD_COLS.values())   # beden_kalip, renk, gorsel, kalite, malzeme, dayaniklilik, eksik_bilgi


def row(asin, gap, types, seviye, **extra):
    r = {"parent_asin": asin, "gap_var": gap, **{c: int(c in types) for c in COLS}, "seviye": seviye}
    r.update(extra)
    return r


def rec(gap, types, seviye):
    return ev.to_record({k: str(v) for k, v in row("x", gap, types, seviye).items()})


# Örnek 1 (4 ürün)
#   gold:  P1 beden+malzeme Yüksek | P2 beden Orta | P3 dayaniklilik Orta | P4 gap yok, Yok
#   tahmin: P1 beden Orta          | P2 beden+renk Orta | P3 gap yok, Yok | P4 gap yok, Yok
GOLD1 = [rec(1, {"beden_kalip", "malzeme"}, "Yüksek"), rec(1, {"beden_kalip"}, "Orta"),
         rec(1, {"dayaniklilik"}, "Orta"), rec(0, set(), "Yok")]
PRED1 = [rec(1, {"beden_kalip"}, "Orta"), rec(1, {"beden_kalip", "renk"}, "Orta"),
         rec(0, set(), "Yok"), rec(0, set(), "Yok")]

# Örnek 2 (3 ürün; Eksik Bilgi yanlış pozitifi, tanımsız sınıflar)
#   gold:  P1 kalite Orta | P2 kalite+gorsel Yüksek | P3 renk Orta
#   tahmin: P1 kalite+eksik_bilgi Orta | P2 gorsel Yüksek | P3 renk+kalite Yüksek
GOLD2 = [rec(1, {"kalite"}, "Orta"), rec(1, {"kalite", "gorsel"}, "Yüksek"), rec(1, {"renk"}, "Orta")]
PRED2 = [rec(1, {"kalite", "eksik_bilgi"}, "Orta"), rec(1, {"gorsel"}, "Yüksek"), rec(1, {"renk", "kalite"}, "Yüksek")]


class TestHandComputed(unittest.TestCase):
    def test_example1(self):
        m = ev.metrics(GOLD1, PRED1)
        # tipler: beden TP2 -> F1 1; renk FP1 -> F1 0; malzeme FN1 -> 0; dayaniklilik FN1 -> 0;
        # gorsel, kalite: TP+FP+FN = 0 -> tanımsız, macro'ya katılmaz. micro: TP2 FP1 FN2
        self.assertAlmostEqual(m["tip_micro_precision"], 2 / 3)
        self.assertAlmostEqual(m["tip_micro_recall"], 2 / 4)
        self.assertAlmostEqual(m["tip_micro_f1"], 4 / 7)                     # 2·(2/3·1/2)/(2/3+1/2)
        self.assertAlmostEqual(m["tip_macro_f1"], (1 + 0 + 0 + 0) / 4)
        # gap var/yok: gold [1,1,1,0], tahmin [1,1,0,0]
        self.assertAlmostEqual(m["gapvar_evet_f1"], 0.8)                     # P 1, R 2/3
        self.assertAlmostEqual(m["gapvar_hayir_f1"], 2 / 3)                  # P 1/2, R 1
        self.assertAlmostEqual(m["gapvar_macro_f1"], (0.8 + 2 / 3) / 2)
        self.assertAlmostEqual(m["gapvar_accuracy"], 0.75)
        # seviye: gold [Y,O,O,Yok], tahmin [O,O,Yok,Yok] -> doğru P2, P4
        self.assertAlmostEqual(m["seviye_isabet"], 0.5)
        self.assertAlmostEqual(m["seviye_macro_f1"], (0 + 0.5 + 2 / 3) / 3)  # Yüksek 0, Orta .5, Yok 2/3
        maj = ev.majority_reference(GOLD1)
        self.assertEqual(maj["seviye"], "Orta")
        self.assertAlmostEqual(maj["gapvar_accuracy"], 0.75)
        self.assertAlmostEqual(maj["gapvar_macro_f1"], (6 / 7 + 0) / 2)     # Evet: P .75 R 1; Hayır: FN1 -> 0
        self.assertAlmostEqual(maj["seviye_isabet"], 0.5)
        self.assertAlmostEqual(maj["seviye_macro_f1"], (0 + 2 / 3 + 0) / 3)
        renk = next(r for r in ev.type_table(GOLD1, PRED1) if r["tip"] == "Renk")
        self.assertEqual((renk["TP"], renk["FP"], renk["FN"], renk["F1"], renk["support"]), (0, 1, 0, 0.0, 0))

    def test_example2(self):
        m = ev.metrics(GOLD2, PRED2)
        # kalite TP1 FP1 FN1 -> .5; gorsel TP1 -> 1; renk TP1 -> 1; eksik_bilgi hesaplama dışı
        self.assertAlmostEqual(m["tip_micro_f1"], 0.75)                      # TP3 FP1 FN1
        self.assertAlmostEqual(m["tip_macro_f1"], (0.5 + 1 + 1) / 3)
        tt = {r["tip"]: r for r in ev.type_table(GOLD2, PRED2)}
        self.assertEqual((tt["Eksik Bilgi"]["FP"], tt["Eksik Bilgi"]["support"],
                          tt["Eksik Bilgi"]["hesaplamaya_dahil"]), (1, 0, 0))
        self.assertTrue(math.isnan(tt["Beden/Kalıp"]["F1"]))
        # gap var/yok: hepsi 1/1 -> Evet F1 1, Hayır tanımsız -> macro 1
        self.assertAlmostEqual(m["gapvar_evet_f1"], 1.0)
        self.assertTrue(math.isnan(m["gapvar_hayir_f1"]))
        self.assertAlmostEqual(m["gapvar_macro_f1"], 1.0)
        # seviye: gold [O,Y,O], tahmin [O,Y,Y]; Orta P1 R.5, Yüksek P.5 R1, Yok tanımsız
        self.assertAlmostEqual(m["seviye_isabet"], 2 / 3)
        self.assertAlmostEqual(m["seviye_macro_f1"], 2 / 3)


class TestEvaluateFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write_gold(self, gold):
        path = self.tmp / "sahte_altin.csv"
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["parent_asin", "gap_var", *COLS, "seviye", "not", "kaynak"])
            w.writeheader()
            for i, g in enumerate(gold):
                w.writerow({**row(f"T{i}", g["gap_var"], {GOLD_COLS[t] for t, v in g["types"].items() if v},
                                  g["seviye"]), "not": "sahte", "kaynak": "gold"})
        return path

    def write_run(self, system, preds, name, tutarsiz=()):
        d = self.tmp / "runs" / "gold" / name
        d.mkdir(parents=True)
        (d / "manifest.json").write_text(json.dumps({"run_id": name, "sistem": system, "split": "gold",
                                                     "model": "m", "tamamlandi": True}), encoding="utf-8")
        with open(d / "sonuclar.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=runs.RESULT_COLS)
            w.writeheader()
            for i, p in enumerate(preds):
                w.writerow(row(f"T{i}", p["gap_var"], {GOLD_COLS[t] for t, v in p["types"].items() if v},
                               p["seviye"], tutarsiz=int(i in tutarsiz), deneme=1, n_oneri=1,
                               maliyet_esdeger_usd=0.001, sure_esdeger_sn=2.0))
        return d

    def test_files_and_paired_bootstrap(self):
        gold = self.write_gold(GOLD1)
        multi = self.write_run("multi_agent", PRED1, "m1", tutarsiz=(2,))
        base = self.write_run("baseline", GOLD1, "b1")                       # baseline = mükemmel
        out = self.tmp / "rapor"
        point, comp = ev.evaluate(gold, multi, base, out, n=200, seed=42)
        for f in ("girdi.json", "metrikler.csv", "tip_bazinda.csv", "karsilastirma.csv", "urun_bazinda.csv",
                  "rapor.md"):
            self.assertTrue((out / f).exists(), f)
        c = {r["metrik"]: r for r in comp}
        self.assertAlmostEqual(c["tip_micro_f1"]["fark"], 4 / 7 - 1)
        self.assertEqual(c["tip_micro_f1"]["oran_fark_le_0"], 1.0)           # mükemmel sisteme karşı hep ≤ 0
        self.assertLessEqual(c["tip_micro_f1"]["ci_ust"], 0)
        girdi = json.loads((out / "girdi.json").read_text(encoding="utf-8"))
        self.assertEqual(girdi["bootstrap"]["tekrar"], 200)
        self.assertEqual(girdi["altin_standart"]["urun"], 4)
        with open(out / "urun_bazinda.csv", encoding="utf-8") as f:
            pr = list(csv.DictReader(f))
        self.assertEqual(pr[0]["gold_tipler"], "Beden/Kalıp;Malzeme")
        self.assertEqual(pr[2]["multi_agent_tutarsiz"], "1")
        self.assertIn("Tutarsız karar | 1 | 0", (out / "rapor.md").read_text(encoding="utf-8"))

        # aynı tohum -> aynı aralıklar (tekrarlanabilir)
        _, comp2 = ev.evaluate(gold, multi, base, self.tmp / "rapor2", n=200, seed=42)
        self.assertEqual([r["ci_alt"] for r in comp], [r["ci_alt"] for r in comp2])

    def test_identical_systems_zero_difference(self):
        gold = self.write_gold(GOLD2)
        multi = self.write_run("multi_agent", PRED2, "m")
        base = self.write_run("baseline", PRED2, "b")
        _, comp = ev.evaluate(gold, multi, base, self.tmp / "r", n=100, seed=1)
        for c in comp:
            if c["gecerli_tekrar"]:
                self.assertEqual((c["fark"], c["ci_alt"], c["ci_ust"], c["oran_fark_le_0"], c["anlamli"]),
                                 (0, 0, 0, 1.0, "hayır"), c["metrik"])

    def test_input_checks(self):
        gold = self.write_gold(GOLD1)
        multi = self.write_run("multi_agent", PRED1, "m")
        short = self.write_run("baseline", PRED1[:3], "kisa")                 # bir ürün eksik
        with self.assertRaisesRegex(ValueError, "1 tanesi yok"):
            ev.evaluate(gold, multi, short, self.tmp / "r")
        wrong = self.write_run("multi_agent", PRED1, "yanlis_sistem")
        with self.assertRaisesRegex(ValueError, "beklenen 'baseline'"):
            ev.evaluate(gold, multi, wrong, self.tmp / "r")

    def test_real_gold_requires_lock(self):
        real = ev.GOLD_DIR / "herhangi.csv"                                   # dosya açılmaz
        self.assertTrue(ev.is_real_gold(real))
        self.assertFalse(ev.is_real_gold(self.tmp / "sahte_altin.csv"))
        import pipeline
        with mock.patch.object(pipeline, "gold_lock", side_effect=pipeline.GoldLockError("kilit")), \
                mock.patch.object(ev, "evaluate") as e:
            with self.assertRaises(pipeline.GoldLockError):
                ev.main(["--gold", str(real), "--multi", "m", "--baseline", "b"])
        e.assert_not_called()


if __name__ == "__main__":
    unittest.main()
