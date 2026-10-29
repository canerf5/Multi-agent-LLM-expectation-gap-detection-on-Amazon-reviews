#!/usr/bin/env python3
"""
Gold bariyeri — Claude Code PreToolUse hook'u (tüm araçlar).

Araç girdisinde (tool_input) aşağıdakilerden biri geçerse çağrıyı ENGELLER
(çıkış kodu 2; stderr'deki Türkçe açıklama Claude'a gösterilir):

  A) Gold verisi (repo kökünde .gold_unlock VARSA serbest):
     - "data/gold" yolu, "gold_40", "etiketleme.xlsx", "gozden_gecirme"
     - "--split gold" / "--split=gold"
     - Bash/PowerShell'de gold dosyalarına erişen script'lerin ÇALIŞTIRILMASI:
       audit_gold, 02_make_labeling_sheet, 03_export_gold, 04_review_gold
  B) Kilit dosyası (HER ZAMAN): ".gold_unlock" (oluşturma, silme, okuma dahil)
  C) Bariyerin kendisi (HER ZAMAN): .claude/settings*.json ve .claude/hooks/
     dosyalarını değiştirme girişimi; Bash'te bu yollar, "gold_guard" veya
     "disableAllHooks" geçmesi. (Read/Grep/Glob ile okumak serbest.)

Girdi okunamazsa da engeller (fail-closed).
Kilidi yalnızca kullanıcı kendi terminalinde açar:  touch .gold_unlock
İş bitince kapatır:                                 rm .gold_unlock
"""
import json
import os
import re
import sys
from pathlib import Path

GOLD = [
    (re.compile(r"data[\\/]+gold", re.I), "data/gold yolu"),
    (re.compile(r"gold_40", re.I), "gold_40"),
    (re.compile(r"etiketleme\.xlsx", re.I), "etiketleme.xlsx"),
    (re.compile(r"gozden_gecirme", re.I), "gozden_gecirme"),
    (re.compile(r"--split(?:\s+|\s*=\s*)[\"']?gold\b", re.I), "--split gold"),
]
GOLD_SCRIPTS = (re.compile(r"audit_gold|02_make_labeling_sheet|03_export_gold|04_review_gold", re.I),
                "gold dosyalarına erişen script'in çalıştırılması")
UNLOCK = (re.compile(r"\.?gold_unlock", re.I), ".gold_unlock kilit dosyası")
CONFIG_PATH = re.compile(r"\.claude[\\/]+(?:settings[^\\/\"']*\.json|hooks(?:[\\/]|\b))", re.I)
CONFIG_WORDS = re.compile(r"gold_guard|disableAllHooks", re.I)

SHELL_TOOLS = {"Bash", "PowerShell"}
READ_TOOLS = {"Read", "Grep", "Glob"}
WRITE_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}


def block(reason):
    print(
        f"GOLD BARİYERİ: Bu çağrı engellendi ({reason}).\n"
        "Altın standart veriye erişim, sistem geliştirme sürecinde teknik olarak kapalıdır. "
        "Bu işi kullanıcı kendi terminalinde yapmalıdır; gold için kilidi yalnızca kullanıcı açar "
        "(kilit dosyasını kullanıcı oluşturur ve iş bitince siler). Bariyeri devre dışı bırakmaya "
        "veya dolanmaya çalışma; kullanıcıya ne yapılması gerektiğini söyle.",
        file=sys.stderr,
    )
    sys.exit(2)


def main():
    try:
        data = json.load(sys.stdin)
        tool = data.get("tool_name") or ""
        tool_input = data.get("tool_input") or {}
        text = json.dumps(tool_input, ensure_ascii=False)
    except Exception as exc:  # noqa: BLE001
        block(f"hook girdisi okunamadı: {type(exc).__name__}")
        return

    project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ".")
    unlocked = (project / ".gold_unlock").is_file()

    # B) kilit dosyası — her zaman
    if UNLOCK[0].search(text):
        block(UNLOCK[1])

    # C) bariyerin kendisi — her zaman
    if tool in WRITE_TOOLS and CONFIG_PATH.search(str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")):
        block(".claude ayar/hook dosyasını değiştirme")
    if tool not in READ_TOOLS and (CONFIG_WORDS.search(text) or (tool not in WRITE_TOOLS and CONFIG_PATH.search(text))):
        block("gold bariyerini (hook/ayar) değiştirme veya devre dışı bırakma girişimi")

    # A) gold verisi — kullanıcı kilidi açmadıysa
    if not unlocked:
        for pattern, name in GOLD:
            if pattern.search(text):
                block(name)
        if tool in SHELL_TOOLS and GOLD_SCRIPTS[0].search(text):
            block(GOLD_SCRIPTS[1])

    sys.exit(0)


if __name__ == "__main__":
    main()
