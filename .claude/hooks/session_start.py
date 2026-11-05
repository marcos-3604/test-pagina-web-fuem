#!/usr/bin/env python3
"""Hook SessionStart generado por aiforge: si otra IA dejó una nota de traspaso, la añade al contexto inicial
(lo que este hook imprime en stdout entra en el contexto de la sesión)."""
import json
import os
import sys
from pathlib import Path


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        data = {}
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ".")
    parts = []
    handoff = root / ".aiforge" / "handoff.md"
    if handoff.is_file() and handoff.stat().st_size > 0:
        parts.append("Nota de traspaso pendiente (.aiforge/handoff.md):\n" + handoff.read_text(encoding="utf-8")[:6000])
    questions = root / ".aiforge" / "questions.json"
    if questions.is_file():
        try:
            pending = [q for q in json.loads(questions.read_text(encoding="utf-8")) if not q.get("answered")]
        except json.JSONDecodeError:
            pending = []
        if pending:
            parts.append(f"Hay {len(pending)} decisión(es) pendiente(s) del usuario en .aiforge/questions.json "
                         "(se responden con `aiforge answer`). No las decidas tú.")
    if parts:
        print("\n\n".join(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
