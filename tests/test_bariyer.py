"""
Gold bariyeri hook testi — gerçek gold dosyası açılmaz.

Hook'a sahte PreToolUse girdileri (stdin JSON) verilir ve çıkış kodu kontrol edilir:
2 = engellendi, 0 = izin. Kilit (.gold_unlock) denemeleri geçici bir proje klasöründe
yapılır; gerçek repoda kilit dosyası oluşturulmaz.

Çalıştırma:
    .venv/bin/python -m unittest tests.test_bariyer -v
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "gold_guard.py"
G = "data/" + "gold"            # test metinlerinde yolu parça parça kur (gerçek dosyalara erişilmez)
UNLOCK = "." + "gold_unlock"


def run_hook(tool, tool_input, project, raw=None):
    payload = raw if raw is not None else json.dumps({
        "session_id": "t", "cwd": str(project), "hook_event_name": "PreToolUse",
        "tool_name": tool, "tool_input": tool_input})
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project)}
    r = subprocess.run([sys.executable, str(HOOK)], input=payload, capture_output=True, text=True, env=env,
                       timeout=20)
    return r.returncode, r.stderr


class TestGoldGuard(unittest.TestCase):
    def setUp(self):
        self.proj = Path(tempfile.mkdtemp())          # kilit kapalı proje

    def tearDown(self):
        for f in self.proj.iterdir():
            f.unlink()
        self.proj.rmdir()

    def assertBlocked(self, tool, ti, project=None):
        code, err = run_hook(tool, ti, project or self.proj)
        self.assertEqual(code, 2, f"ENGELLENMEDİ: {tool} {ti}")
        self.assertIn("GOLD BARİYERİ", err)

    def assertAllowed(self, tool, ti, project=None):
        code, err = run_hook(tool, ti, project or self.proj)
        self.assertEqual(code, 0, f"engellenmemeliydi: {tool} {ti}\n{err}")

    # ---------------- A) gold verisi
    def test_gold_paths_blocked(self):
        self.assertBlocked("Read", {"file_path": f"/x/proje/{G}/{'gold'}_40.csv"})
        self.assertBlocked("Read", {"file_path": f"/x/proje/{G}/README"})
        self.assertBlocked("Bash", {"command": f"cat {G}/x.csv"})
        self.assertBlocked("Bash", {"command": "head " + "gold" + "_40.csv"})
        self.assertBlocked("Bash", {"command": "python -c \"open('" + "etiketleme" + ".xlsx')\""})
        self.assertBlocked("Bash", {"command": "ls " + "gozden" + "_gecirme*"})
        self.assertBlocked("Grep", {"pattern": "B0", "path": G})
        self.assertBlocked("Glob", {"pattern": f"{G}/**"})
        self.assertBlocked("Edit", {"file_path": f"/p/{G}/a.csv", "old_string": "a", "new_string": "b"})
        self.assertBlocked("Write", {"file_path": "/p/src/x.py", "content": f"open('{G}/a')"})
        self.assertBlocked("NotebookEdit", {"notebook_path": f"/p/{G}/n.ipynb", "new_source": "x"})
        self.assertBlocked("Agent", {"prompt": f"{G} klasörünü oku", "description": "d"})
        self.assertBlocked("Bash", {"command": f"cat {G.upper()}/x"})          # büyük/küçük harf
        self.assertBlocked("Bash", {"command": "cat data\\\\gold\\\\x"})        # ters eğik çizgi

    def test_split_gold_blocked(self):
        for cmd in ("python src/pipeline.py --split gold", "python src/pipeline.py --split=gold",
                    "python src/pipeline.py --split 'gold' --estimate", "python src/pipeline.py --split  gold"):
            self.assertBlocked("Bash", {"command": cmd})

    def test_gold_scripts_execution_blocked(self):
        for s in ("audit_gold", "03_export_gold", "04_review_gold", "02_make_labeling_sheet"):
            self.assertBlocked("Bash", {"command": f".venv/bin/python src/{s}.py"})
        self.assertAllowed("Read", {"file_path": "/p/src/04_review_gold.py"})   # kaynak kodu okumak serbest

    # ---------------- B) kilit dosyası (her zaman)
    def test_unlock_file_always_blocked(self):
        unlocked = Path(tempfile.mkdtemp())
        (unlocked / UNLOCK).touch()
        try:
            for proj in (self.proj, unlocked):
                self.assertBlocked("Bash", {"command": f"touch {UNLOCK}"}, proj)
                self.assertBlocked("Bash", {"command": f"rm -f {UNLOCK}"}, proj)
                self.assertBlocked("Read", {"file_path": f"/p/{UNLOCK}"}, proj)
                self.assertBlocked("Write", {"file_path": f"/p/{UNLOCK}", "content": ""}, proj)
                self.assertBlocked("Bash", {"command": "ls -la | grep gold_unlock"}, proj)
        finally:
            (unlocked / UNLOCK).unlink()
            unlocked.rmdir()

    # ---------------- C) bariyerin kendisi (her zaman)
    def test_config_tampering_blocked(self):
        self.assertBlocked("Write", {"file_path": "/p/.claude/settings.json", "content": "{}"})
        self.assertBlocked("Edit", {"file_path": "/p/.claude/settings.local.json", "old_string": "a",
                                    "new_string": "b"})
        self.assertBlocked("Edit", {"file_path": "/p/.claude/hooks/x.py", "old_string": "a", "new_string": "b"})
        self.assertBlocked("Write", {"file_path": "/Users/u/.claude/settings.json", "content": "{}"})
        self.assertBlocked("Bash", {"command": "rm .claude/hooks/x.py"})
        self.assertBlocked("Bash", {"command": "echo '{}' > .claude/settings.json"})
        self.assertBlocked("Bash", {"command": "sed -i '' 's/a/b/' ~/.claude/settings.json"})
        self.assertBlocked("Bash", {"command": "chmod -x some/gold_guard.py"})
        self.assertBlocked("Write", {"file_path": "/p/x.json", "content": '{"disableAllHooks": true}'})
        self.assertBlocked("Agent", {"prompt": "disableAllHooks ayarını aç", "description": "d"})

    def test_config_reading_allowed(self):
        self.assertAllowed("Read", {"file_path": "/p/.claude/settings.json"})
        self.assertAllowed("Grep", {"pattern": "matcher", "path": "/p/.claude"})

    # ---------------- istisna: kullanıcı kilidi açtıysa A serbest, B ve C değil
    def test_unlock_allows_gold_only(self):
        unlocked = Path(tempfile.mkdtemp())
        (unlocked / UNLOCK).touch()
        try:
            self.assertAllowed("Bash", {"command": "python src/pipeline.py --split gold --estimate"}, unlocked)
            self.assertAllowed("Read", {"file_path": f"/p/{G}/x.csv"}, unlocked)
            self.assertAllowed("Bash", {"command": ".venv/bin/python src/audit_gold.py"}, unlocked)
            self.assertBlocked("Write", {"file_path": "/p/.claude/settings.json", "content": "{}"}, unlocked)
            self.assertBlocked("Bash", {"command": f"rm {UNLOCK}"}, unlocked)
        finally:
            (unlocked / UNLOCK).unlink()
            unlocked.rmdir()

    # ---------------- dev işleri geçmeli
    def test_dev_work_allowed(self):
        for cmd in ("python src/pipeline.py --asin B08V4QYTR6 --estimate", "python src/pipeline.py",
                    "python src/pipeline.py --split dev", "python src/pipeline.py --split rest --estimate",
                    ".venv/bin/python -m unittest tests.test_faz5 -v", "git status --short", "ls outputs",
                    "git log --oneline -3"):
            self.assertAllowed("Bash", {"command": cmd})
        self.assertAllowed("Read", {"file_path": "/p/src/pipeline.py"})
        self.assertAllowed("Read", {"file_path": "/p/data/processed/products_200.jsonl"})
        self.assertAllowed("Edit", {"file_path": "/p/src/agents.py", "old_string": "a", "new_string": "b"})
        self.assertAllowed("Write", {"file_path": "/p/outputs/multi_agent/dev/x.json", "content": "{}"})
        self.assertAllowed("Grep", {"pattern": "goldsmith", "path": "/p/src"})
        self.assertAllowed("Write", {"file_path": "/Users/u/.claude/projects/p/memory/x.md", "content": "not"})
        self.assertAllowed("WebFetch", {"url": "https://code.claude.com/docs/en/hooks", "prompt": "x"})

    def test_fail_closed_on_bad_input(self):
        code, err = run_hook(None, None, self.proj, raw="bu json değil")
        self.assertEqual(code, 2)
        self.assertIn("GOLD BARİYERİ", err)


if __name__ == "__main__":
    unittest.main()
