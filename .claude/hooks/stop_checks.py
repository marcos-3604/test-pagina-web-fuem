#!/usr/bin/env python3
"""Hook Stop generado por aiforge: si hay cambios de código sin commitear, ejecuta los checks rápidos del proyecto
(.aiforge/project.toml → checks.stop_hook). Si fallan, exit 2 devuelve el error a Claude para que lo corrija
(patrón oficial de Anthropic: "Enforce the check with a Stop hook")."""
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python < 3.11: no bloquear
    sys.exit(0)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        data = {}
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ".")
    cfg_path = root / ".aiforge" / "project.toml"
    if not cfg_path.is_file():
        return 0
    with cfg_path.open("rb") as fh:
        checks = tomllib.load(fh).get("checks", {})
    names = checks.get("stop_hook", [])
    if not names:
        return 0
    status = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True).stdout
    changed = [line[3:].strip('"') for line in status.splitlines() if line.strip()]
    # Solo cambios de código: la documentación y la configuración de agentes no disparan los checks
    # (p.ej. durante la entrevista del SPEC no hay nada que comprobar).
    ignored_dirs = (".aiforge/", ".claude/", ".gemini/", ".github/")
    ignored_ext = (".md", ".txt")
    code = [f for f in changed if not f.startswith(ignored_dirs) and not f.endswith(ignored_ext)]
    if not code:
        return 0
    failures = []
    for name in names:
        cmd = checks.get(name, "")
        if not cmd:
            continue
        proc = subprocess.run(cmd, shell=True, cwd=root, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            out = ((proc.stdout or "") + (proc.stderr or "")).strip().splitlines()[-60:]
            failures.append(f"`{cmd}` falló:\n" + "\n".join(out))
    if failures:
        print("Antes de terminar, corrige esto:\n\n" + "\n\n".join(failures), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
