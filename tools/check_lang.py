#!/usr/bin/env python3
"""Every message key used in the code exists in every language file, and vice versa.

Run: python3 tools/check_lang.py   (exits non-zero on a mismatch)

Messages are assembled server-side, so a key without a translation reaches players
as a raw "msg.something" — this catches that before they do.
"""
import json
import pathlib
import re
import sys

root = pathlib.Path(__file__).resolve().parent.parent
langs = {p.stem: json.loads(p.read_text(encoding="utf-8"))
         for p in (root / "src/main/resources/assets/skinlibrary/lang").glob("*.json")}
used = set()
for java in (root / "src/main/java").rglob("*.java"):
    used |= set(re.findall(r'"(msg\.[a-z_]+)"', java.read_text(encoding="utf-8")))

problems = []
for code, keys in sorted(langs.items()):
    for missing in sorted(used - set(keys)):
        problems.append(f"{code}: missing {missing}")
    for extra in sorted(set(keys) - used):
        problems.append(f"{code}: unused {extra}")

print("\n".join(problems) if problems
      else f"OK — {len(used)} keys, languages: {', '.join(sorted(langs))}")
sys.exit(1 if problems else 0)
