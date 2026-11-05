#!/usr/bin/env python3
"""Hook PreToolUse (Bash) generado por aiforge: bloquea comandos peligrosos que las reglas por prefijo no captan.

Exit 2 = bloquear (stderr es el motivo que ve Claude). Reglas en guard_rules.json (regenerable con `aiforge configure`).
"""
import json
import re
import sys
from pathlib import Path


def main() -> int:
    rules = json.loads(Path(__file__).with_name("guard_rules.json").read_text(encoding="utf-8"))
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    command = (data.get("tool_input") or {}).get("command", "")
    for pattern in rules.get("block_regex", []):
        if re.search(pattern, command):
            print(f"{rules.get('block_reason', 'Bloqueado')} (regla: {pattern})", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
