#!/usr/bin/env python3
"""Comprobador del sitio FUEM (Python estándar).

Falla (código de salida != 0) si:
  1. alguna referencia local de un HTML/CSS/JS no existe;
  2. un .svg de assets/ incrusta un PNG base64 de más de 400 KB;
  3. una página .html referencia más de 6 MB de imágenes (sin vídeos).

Uso: python3 tools/check_site.py [RAIZ] [--json]
"""
import argparse
import base64
import json
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import unquote

EXCLUDED_DIRS = {".git", ".github", ".claude", ".codex", ".gemini", "tools", "docs", "node_modules"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif", ".avif"}
MAX_SVG_PNG_BYTES = 400 * 1024
MAX_PAGE_IMAGE_BYTES = 6 * 1024 * 1024

CSS_URL_RE = re.compile(r"url\(\s*(?:\"([^\"]*)\"|'([^']*)'|([^)\"'\s][^)]*?))\s*\)", re.I)
CSS_IMPORT_RE = re.compile(r"@import\s+(?:\"([^\"]*)\"|'([^']*)')", re.I)
JS_ASSET_RE = re.compile(r"[\"'`]((?:\.{1,2}/)*assets/[^\"'`\s]*)[\"'`]")
SVG_PNG_RE = re.compile(r"data:image/png;base64,([A-Za-z0-9+/=\s]+)")
IGNORED_PREFIXES = ("http:", "https:", "//", "data:", "mailto:", "tel:", "#", "javascript:", "blob:")


def css_refs(text):
    out = []
    for m in CSS_URL_RE.finditer(text):
        out.append(next(g for g in m.groups() if g is not None))
    for m in CSS_IMPORT_RE.finditer(text):
        out.append(m.group(1) or m.group(2))
    return out


def js_refs(text):
    return [m.group(1) for m in JS_ASSET_RE.finditer(text)
            if "${" not in m.group(1) and not m.group(1).endswith("/")]


class _HTMLRefs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs = []      # referencias de atributos y de CSS/JS en línea
        self.assets = []    # recursos que se cargan (CSS/JS) se resuelven igual que refs
        self._tag = None

    def handle_starttag(self, tag, attrs):
        self._tag = tag
        for name, value in attrs:
            if not value:
                continue
            if name in ("src", "href", "poster"):
                self.refs.append(value)
            elif name == "srcset":
                for cand in value.split(","):
                    parts = cand.strip().split()
                    if parts:
                        self.refs.append(parts[0])
            elif name == "style":
                self.refs.extend(css_refs(value))

    def handle_endtag(self, tag):
        self._tag = None

    def handle_data(self, data):
        if self._tag == "style":
            self.refs.extend(css_refs(data))
        elif self._tag == "script":
            self.refs.extend(js_refs(data))


def html_refs(text):
    p = _HTMLRefs()
    p.feed(text)
    return p.refs


def clean_ref(ref):
    ref = ref.strip()
    # Las rutas absolutas ("/x") dependen del prefijo de despliegue (p. ej. /repo/ en
    # GitHub Pages) y no se pueden resolver contra el disco: se ignoran.
    if not ref or ref.startswith("/") or ref.lower().startswith(IGNORED_PREFIXES):
        return None
    ref = ref.split("#", 1)[0].split("?", 1)[0]
    return unquote(ref) or None


def resolve(root, source_rel, ref):
    """Devuelve ruta relativa a root (con /) o None si la ref sale de la raíz."""
    if ref.startswith("/"):
        target = os.path.normpath(os.path.join(root, ref.lstrip("/")))
    else:
        target = os.path.normpath(os.path.join(root, os.path.dirname(source_rel), ref))
    rel = os.path.relpath(target, root)
    return rel.replace(os.sep, "/"), target


def walk_files(root):
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir == ".":
            dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for f in filenames:
            rel = os.path.relpath(os.path.join(dirpath, f), root).replace(os.sep, "/")
            found.append(rel)
    return sorted(found)


def check_site(root):
    root = os.path.abspath(root)
    files = walk_files(root)
    sources = [f for f in files if f.endswith((".html", ".css", ".js"))]
    problems = []
    seen = set()

    def problem(file, reason, detail=""):
        key = (file, reason, detail)
        if key not in seen:
            seen.add(key)
            problems.append({"file": file, "reason": reason, "detail": detail})

    # 1) Referencias locales
    refs_of = {}  # fichero -> lista de rutas existentes (relativas a root)
    for src in sources:
        with open(os.path.join(root, src), encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        if src.endswith(".html"):
            raw = html_refs(text)
        elif src.endswith(".css"):
            raw = css_refs(text)
        else:
            raw = js_refs(text)
        resolved = []
        for r in raw:
            ref = clean_ref(r)
            if ref is None:
                continue
            rel, target = resolve(root, src, ref)
            if rel.startswith("..") or not os.path.exists(target):
                problem(src, "referencia local inexistente", r)
            else:
                resolved.append(rel)
        refs_of[src] = resolved

    # 2) PNG incrustados en SVG de assets/
    for f in files:
        if f.startswith("assets/") and f.endswith(".svg"):
            with open(os.path.join(root, f), encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            for m in SVG_PNG_RE.finditer(text):
                try:
                    data = re.sub(r"\s+", "", m.group(1))
                    size = len(base64.b64decode(data + "=" * (-len(data) % 4)))
                except Exception:
                    size = len(m.group(1)) * 3 // 4
                if size > MAX_SVG_PNG_BYTES:
                    problem(f, "PNG incrustado > 400 KB", "%d KB" % (size // 1024))

    # 3) Peso de imágenes por página
    pages = {}
    for page in (f for f in sources if f.endswith(".html")):
        stack, visited = [page], set()
        images = set()
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            for rel in refs_of.get(cur, []):
                ext = os.path.splitext(rel)[1].lower()
                if ext in IMAGE_EXTS:
                    images.add(rel)
                elif ext in (".css", ".js") and rel in refs_of:
                    stack.append(rel)
        total = sum(os.path.getsize(os.path.join(root, i)) for i in images
                    if os.path.isfile(os.path.join(root, i)))
        pages[page] = {"image_bytes": total, "images": len(images)}
        if total > MAX_PAGE_IMAGE_BYTES:
            problem(page, "imágenes > 6 MB", "%.2f MB" % (total / 1048576))

    return {"root": root, "pages": pages, "problems": problems, "ok": not problems}


def format_report(result):
    lines = ["Peso de imágenes por página:"]
    for page, info in sorted(result["pages"].items()):
        lines.append("  %-28s %8.2f MB  (%d imágenes)" % (page, info["image_bytes"] / 1048576, info["images"]))
    if result["problems"]:
        lines.append("")
        lines.append("Ficheros problemáticos (%d):" % len(result["problems"]))
        for p in result["problems"]:
            lines.append("  %s: %s%s" % (p["file"], p["reason"], " [%s]" % p["detail"] if p["detail"] else ""))
        lines.append("")
        lines.append("FALLO")
    else:
        lines.append("")
        lines.append("OK")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    default_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("root", nargs="?", default=default_root, help="raíz del sitio")
    ap.add_argument("--json", action="store_true", help="salida en JSON")
    args = ap.parse_args(argv)
    result = check_site(args.root)
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else format_report(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
