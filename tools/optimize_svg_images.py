#!/usr/bin/env python3
"""Re-codifica como WebP los PNG incrustados (data:image/png;base64,...) en ficheros SVG.

Para cada data URI PNG del SVG:
  1. decodifica el PNG;
  2. lo codifica como WebP con pérdida de alta calidad (escalera de calidades
     LOSSY_QUALITIES, alfa sin pérdida) y como WebP sin pérdida;
  3. decodifica cada candidato y lo compara con el PNG original en RGBA
     (ver error_stats): se acepta si el error medio por canal es <= MAX_MEAN_ERROR
     y como mucho una fracción MAX_OVER_FRACTION (0,1 %) de los valores de canal
     tiene un error > MAX_PIXEL_ERROR (32/255); se prueban las calidades con
     pérdida de menor a mayor y se queda la más baja que cumple, y el WebP sin
     pérdida siempre se prueba;
  4. elige el candidato válido más pequeño (si ninguno es más pequeño que el
     PNG, deja el PNG).

También acepta como fuente un WebP *sin pérdida* ya incrustado (p. ej. de una
pasada anterior con un criterio más estricto): sus píxeles visibles son idénticos
a los del PNG original, así que la verificación sigue midiéndose contra el
original. Los WebP con pérdida no se tocan (no hay original con el que comparar).

Solo se sustituye el contenido del data URI (por data:image/webp;base64,...): el
resto del SVG se conserva byte a byte y el fichero mantiene su nombre. Si el
ahorro total del fichero es menor que MIN_SAVING, el fichero no se reescribe.

La re-codificación descarta los metadatos del PNG, incluidos los C2PA (Content
Credentials, chunk caBX). El perfil ICC, si lo hay, se conserva.

Uso:
  python3 tools/optimize_svg_images.py FICHERO_O_GLOB [...] [--dry-run] [--report RUTA]
Ejemplo:
  python3 tools/optimize_svg_images.py assets/v3/car-cutout.svg 'assets/v3/part-*.svg' \\
      'assets/partners/*.svg' --report docs/svg-optimizacion.txt
"""
import argparse
import base64
import glob
import hashlib
import io
import os
import re
import sys

from PIL import Image, ImageChops

# Umbrales de la verificación visual, en unidades de 1/255 por canal.
# Error medio por canal RGBA (requisito del proyecto: <= 2/255).
MAX_MEAN_ERROR = 2.0
# Error "grande" en un canal de un píxel: 32/255 (~12,5 %).
MAX_PIXEL_ERROR = 32
# Fracción máxima de valores de canal (píxeles x 4 canales RGBA) con error >
# MAX_PIXEL_ERROR. El WebP con pérdida (YUV 4:2:0) produce picos aislados en bordes
# de color saturado aunque suba la calidad; se admiten mientras sean como mucho el
# 0,1 % de los valores (decisión del proyecto). Si no se cumple, se sube la calidad
# o se pasa a WebP sin pérdida.
MAX_OVER_FRACTION = 0.001
# Calidades WebP con pérdida que se prueban, de menor a mayor.
LOSSY_QUALITIES = (90, 95, 100)
# Ahorro mínimo (sobre el tamaño total del fichero) para reescribirlo.
MIN_SAVING = 0.20

IMAGE_URI_RE = re.compile(rb"data:image/(png|webp);base64,([A-Za-z0-9+/=]+(?:\s+[A-Za-z0-9+/=]+)*)")
WEBP_PREFIX = b"data:image/webp;base64,"
C2PA_CHUNK = b"caBX"

C2PA_NOTE = ("AVISO: la re-codificación a WebP descarta los metadatos del PNG original, "
             "incluidos los metadatos C2PA (Content Credentials, chunk PNG 'caBX'). "
             "El perfil de color ICC, si existe, se conserva.")


def is_lossless_webp(data):
    """True si `data` es un WebP estático codificado sin pérdida (chunk VP8L, sin VP8 ni ANIM)."""
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return False
    chunks = set()
    pos = 12
    while pos + 8 <= len(data):
        size = int.from_bytes(data[pos + 4:pos + 8], "little")
        chunks.add(data[pos:pos + 4])
        pos += 8 + size + (size & 1)
    return b"VP8L" in chunks and b"VP8 " not in chunks and b"ANIM" not in chunks


def find_source_images(data):
    """Devuelve [(inicio, fin, bytes, formato)] de cada data URI optimizable de `data` (bytes).

    formato es "png" o "webp" (solo WebP sin pérdida; los WebP con pérdida se ignoran).
    """
    out = []
    for m in IMAGE_URI_RE.finditer(data):
        b64 = re.sub(rb"\s+", b"", m.group(2))
        raw = base64.b64decode(b64 + b"=" * (-len(b64) % 4))
        fmt = m.group(1).decode("ascii")
        if fmt == "webp" and not is_lossless_webp(raw):
            continue
        out.append((m.start(), m.end(), raw, fmt))
    return out


def _premultiplied_rgba(img):
    """RGBA con el color premultiplicado por el alfa (lo que realmente se compone en pantalla).

    Así el color de los píxeles totalmente transparentes (invisible y que el
    codificador WebP puede alterar) no cuenta como error, y en los
    semitransparentes cuenta en proporción a su opacidad.
    """
    pm = img.convert("RGBA").convert("RGBa")
    return Image.merge("RGBA", pm.split())


def image_error(reference, candidate):
    """(error medio, error máximo) por canal RGBA entre dos imágenes, en unidades de 1/255.

    La comparación se hace sobre RGBA con el color premultiplicado por el alfa.
    Si los tamaños no coinciden devuelve (inf, inf).
    """
    stats = error_stats(reference, candidate)
    return stats["mean"], stats["max"]


def error_stats(reference, candidate, threshold=MAX_PIXEL_ERROR):
    """Como image_error, y además `over`: fracción de valores de canal con error > threshold."""
    if reference.size != candidate.size:
        return {"mean": float("inf"), "max": float("inf"), "over": 1.0}
    a = _premultiplied_rgba(reference)
    b = _premultiplied_rgba(candidate)
    hist = ImageChops.difference(a, b).histogram()  # 4 canales x 256 valores
    total = 0
    worst = 0
    over = 0
    for band in range(4):
        for value, count in enumerate(hist[band * 256:(band + 1) * 256]):
            if count:
                total += value * count
                worst = max(worst, value)
                if value > threshold:
                    over += count
    n = reference.size[0] * reference.size[1] * 4
    return {"mean": total / n if n else 0.0, "max": worst, "over": over / n if n else 0.0}


def _passes(stats, max_mean=MAX_MEAN_ERROR, max_over=MAX_OVER_FRACTION):
    """`stats` es el dict de error_stats (con `over` calculado para el umbral de píxel)."""
    return stats["mean"] <= max_mean and stats["over"] <= max_over


def _encode_webp(img, icc, **params):
    buf = io.BytesIO()
    if icc:
        params["icc_profile"] = icc
    img.save(buf, "WEBP", method=6, **params)
    return buf.getvalue()


def choose_webp(src_bytes, max_mean=MAX_MEAN_ERROR, max_pixel=MAX_PIXEL_ERROR,
                max_over=MAX_OVER_FRACTION, qualities=LOSSY_QUALITIES, src_format="png"):
    """Elige la mejor codificación WebP de una imagen sin pérdida (PNG o WebP sin pérdida).

    Devuelve un dict con: webp (bytes o None si no conviene sustituir), label,
    mean, max, over, src_format, src_size, webp_size, c2pa (bool) y tried
    (lista de candidatos).
    """
    base = {"src_format": src_format, "src_size": len(src_bytes),
            "c2pa": src_format == "png" and C2PA_CHUNK in src_bytes}
    src = Image.open(io.BytesIO(src_bytes))
    if getattr(src, "n_frames", 1) > 1:
        return dict(base, webp=None, label="imagen animada: se deja igual", mean=None, max=None,
                    over=None, webp_size=None, tried=[])
    src.load()
    icc = src.info.get("icc_profile")
    reference = src.convert("RGBA")
    has_alpha = reference.getextrema()[3][0] < 255
    to_encode = reference if has_alpha else reference.convert("RGB")

    tried = []

    def attempt(label, **params):
        webp = _encode_webp(to_encode, icc, **params)
        decoded = Image.open(io.BytesIO(webp))
        decoded.load()
        stats = error_stats(reference, decoded, max_pixel)
        ok = _passes(stats, max_mean, max_over)
        tried.append({"label": label, "size": len(webp), "mean": stats["mean"], "max": stats["max"],
                      "over": stats["over"], "ok": ok})
        return (webp, stats) if ok else (None, stats)

    valid = []
    for q in qualities:
        label = "WebP con pérdida q%d" % q
        webp, stats = attempt(label, quality=q, alpha_quality=100)
        if webp is not None:
            valid.append((len(webp), label, webp, stats))
            break  # la calidad más baja que cumple (la más pequeña de la escalera)
    webp, stats = attempt("WebP sin pérdida", lossless=True, quality=100)
    if webp is not None:
        valid.append((len(webp), "WebP sin pérdida", webp, stats))

    result = dict(base, tried=tried)
    if not valid:
        result.update(webp=None, label="ningún WebP cumple la verificación: se deja la imagen original",
                      mean=None, max=None, over=None, webp_size=None)
        return result
    valid.sort(key=lambda v: v[0])
    size, label, webp, stats = valid[0]
    result.update(mean=stats["mean"], max=stats["max"], over=stats["over"], webp_size=size)
    if size >= len(src_bytes):
        result.update(webp=None, label="%s no es más pequeño que la imagen actual: se deja igual" % label)
        return result
    result.update(webp=webp, label=label)
    return result


def strip_data_uris(data):
    """El SVG sin el contenido de sus data URI de imagen (para comprobar que el resto es idéntico)."""
    return re.sub(rb"data:image/(?:png|webp);base64,[A-Za-z0-9+/=\s]*", b"data:", data)


def optimize_svg_bytes(data, cache=None, **choose_kwargs):
    """Devuelve (nuevo_contenido, [resultado por imagen]). Solo cambian los data URI."""
    if cache is None:
        cache = {}
    parts = []
    images = []
    pos = 0
    for start, end, raw, fmt in find_source_images(data):
        key = hashlib.sha256(raw).hexdigest()
        if key not in cache:
            cache[key] = choose_webp(raw, src_format=fmt, **choose_kwargs)
        res = cache[key]
        images.append(res)
        parts.append(data[pos:start])
        if res["webp"] is not None:
            parts.append(WEBP_PREFIX + base64.b64encode(res["webp"]))
        else:
            parts.append(data[start:end])
        pos = end
    parts.append(data[pos:])
    new = b"".join(parts)
    if strip_data_uris(new) != strip_data_uris(data):
        raise RuntimeError("el resto del SVG ha cambiado: no se escribe nada")
    return new, images


def process_file(path, dry_run=False, min_saving=MIN_SAVING, cache=None, **choose_kwargs):
    """Optimiza un SVG y devuelve un dict con before, after, saving, decision, written, images."""
    with open(path, "rb") as fh:
        data = fh.read()
    new, images = optimize_svg_bytes(data, cache=cache, **choose_kwargs)
    before, after = len(data), len(new)
    saving = (before - after) / before if before else 0.0
    written = False
    if not images:
        decision = "sin PNG ni WebP sin pérdida incrustado"
        after, saving = before, 0.0
    elif new == data:
        decision = "sin cambios (ninguna imagen mejora)"
    elif saving < min_saving:
        decision = "no se reescribe: ahorro %.1f %% < %d %%" % (saving * 100, round(min_saving * 100))
    elif dry_run:
        decision = "se reescribiría (--dry-run)"
    else:
        with open(path, "wb") as fh:
            fh.write(new)
        written = True
        decision = "reescrito"
    return {"path": path, "before": before, "after": after, "saving": saving,
            "decision": decision, "written": written, "images": images}


def expand_inputs(patterns):
    files, missing = [], []
    for pat in patterns:
        matches = sorted(glob.glob(pat)) if glob.has_magic(pat) else ([pat] if os.path.isfile(pat) else [])
        if not matches:
            missing.append(pat)
        for m in matches:
            if m not in files:
                files.append(m)
    return files, missing


def _kb(n):
    return "%.1f KB" % (n / 1024)


def describe_image(i, res):
    source = "PNG" if res["src_format"] == "png" else "WebP sin pérdida"
    line = "    imagen %d: %s %s -> " % (i, source, _kb(res["src_size"]))
    if res["webp"] is not None:
        line += "%s %s (error medio %.2f/255, máx %d/255, %.4f %% de valores > %d/255)" % (
            res["label"], _kb(res["webp_size"]), res["mean"], res["max"], res["over"] * 100,
            MAX_PIXEL_ERROR)
    else:
        line += res["label"]
    if res["c2pa"]:
        line += " [tenía C2PA]"
    return line


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", help="ficheros SVG o globs (entre comillas)")
    ap.add_argument("--dry-run", action="store_true", help="calcula y muestra, pero no escribe nada")
    ap.add_argument("--report", help="guarda también la salida en este fichero de texto")
    ap.add_argument("--append", action="store_true",
                    help="añade la salida al final de --report en vez de sobrescribirlo (p. ej. segunda pasada)")
    ap.add_argument("-v", "--verbose", action="store_true", help="muestra todos los candidatos probados")
    ap.add_argument("--min-saving", type=float, default=MIN_SAVING,
                    help="ahorro mínimo para reescribir un fichero (fracción, por defecto %(default)s)")
    args = ap.parse_args(argv)

    lines = []

    def emit(text=""):
        print(text, flush=True)
        lines.append(text)

    files, missing = expand_inputs(args.inputs)
    emit("Optimización de PNG incrustados en SVG (tools/optimize_svg_images.py%s)"
         % (", --dry-run" if args.dry_run else ""))
    emit("Criterio: WebP con pérdida (calidades %s, alfa sin pérdida; se queda la más baja que cumple)"
         % "/".join(str(q) for q in LOSSY_QUALITIES))
    emit("o WebP sin pérdida, el más pequeño que cumpla, comparando con el PNG en RGBA (color premultiplicado")
    emit("por alfa): error medio por canal <= %g/255 y como mucho el %g %% de los valores de canal con error > %d/255."
         % (MAX_MEAN_ERROR, MAX_OVER_FRACTION * 100, MAX_PIXEL_ERROR))
    emit("Decisión del proyecto: se admiten picos aislados > %d/255 (hasta el %g %%) porque el WebP con pérdida"
         % (MAX_PIXEL_ERROR, MAX_OVER_FRACTION * 100))
    emit("(YUV 4:2:0) los produce en bordes de color saturado a cualquier calidad; el error máximo de cada")
    emit("imagen se indica abajo.")
    emit("Fuentes: PNG incrustados y WebP sin pérdida incrustados (sus píxeles visibles son los del PNG")
    emit("original); los WebP con pérdida no se tocan.")
    emit("Un fichero no se reescribe si ahorra menos del %d %%." % round(args.min_saving * 100))
    emit(C2PA_NOTE)
    emit()

    results = []
    cache = {}
    for path in files:
        res = process_file(path, dry_run=args.dry_run, min_saving=args.min_saving, cache=cache)
        results.append(res)
        emit(path)
        for i, img in enumerate(res["images"], 1):
            emit(describe_image(i, img))
            if args.verbose:
                for t in img["tried"]:
                    emit("        probado %s: %s, error medio %.2f/255, máx %d/255, %.4f %% de valores > %d/255"
                         " -> %s" % (t["label"], _kb(t["size"]), t["mean"], t["max"], t["over"] * 100,
                                     MAX_PIXEL_ERROR, "cumple" if t["ok"] else "no cumple"))
        emit("    %s -> %s (%.1f %%): %s" % (_kb(res["before"]), _kb(res["after"]),
                                            -res["saving"] * 100, res["decision"]))

    emit()
    width = max([len("fichero")] + [len(r["path"]) for r in results])
    header = "%-*s  %12s  %12s  %7s  %s" % (width, "fichero", "antes", "después", "ahorro", "decisión")
    emit(header)
    emit("-" * len(header))
    total_before = total_after = 0
    for r in results:
        final = r["after"] if (r["written"] or args.dry_run and r["decision"].startswith("se reescribiría")) \
            else r["before"]
        total_before += r["before"]
        total_after += final
        emit("%-*s  %12s  %12s  %6.1f%%  %s" % (width, r["path"], _kb(r["before"]), _kb(final),
                                             (r["before"] - final) / r["before"] * 100 if r["before"] else 0.0,
                                             r["decision"]))
    emit("-" * len(header))
    emit("%-*s  %12s  %12s  %6.1f%%" % (width, "TOTAL", _kb(total_before), _kb(total_after),
                                        (total_before - total_after) / total_before * 100 if total_before else 0.0))
    if any(img["c2pa"] for r in results for img in r["images"]):
        emit()
        emit("Nota: algunos PNG originales tenían metadatos C2PA ([tenía C2PA]); el WebP ya no los incluye.")
    for pat in missing:
        emit("ERROR: no existe ningún fichero para %r" % pat)

    if args.report:
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        append = args.append and os.path.isfile(args.report)
        with open(args.report, "a" if append else "w", encoding="utf-8") as fh:
            if append:
                fh.write("\n" + "=" * 95 + "\n\n")
            fh.write("\n".join(lines) + "\n")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
