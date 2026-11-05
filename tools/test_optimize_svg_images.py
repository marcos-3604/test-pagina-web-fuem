import base64
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import optimize_svg_images as opt  # noqa: E402


def rgba_image(w=96, h=64):
    """Degradado RGBA con zona totalmente transparente (con color basura debajo) y borde semitransparente."""
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            if x < 10:
                px[x, y] = (255, 0, 255, 0)          # transparente: el color no se ve
            elif x < 16:
                px[x, y] = (200, 30, 30, (x - 10) * 40)  # borde semitransparente
            else:
                px[x, y] = (x * 2 % 256, y * 3 % 256, (x + y) % 256, 255)
    return img


def png_bytes(img, compress_level=9):
    buf = io.BytesIO()
    img.save(buf, "PNG", compress_level=compress_level)
    return buf.getvalue()


def svg_with(png, prefix_extra="", suffix_extra="", wrap=False):
    b64 = base64.b64encode(png).decode("ascii")
    if wrap:  # base64 partido en líneas, como hacen algunos editores
        b64 = "\n".join(b64[i:i + 76] for i in range(0, len(b64), 76))
    return ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            'viewBox="57 66 2318 738">%s<title>Logo · prueba</title>'
            '<defs><mask id="m"><rect width="10" height="10" fill="white"/></mask></defs>'
            '<image transform="translate(1 2)" mask="url(#m)" width="96" height="64" '
            'xlink:href="data:image/png;base64,%s"/>%s</svg>\n'
            % (prefix_extra, b64, suffix_extra)).encode("utf-8")


class ImageErrorTests(unittest.TestCase):
    def test_identical_is_zero(self):
        img = rgba_image()
        self.assertEqual(opt.image_error(img, img.copy()), (0.0, 0))

    def test_isolated_spike_is_tolerated(self):
        # Un píxel aislado con error grande: < 0,1 % de los valores -> se admite.
        ref = rgba_image(200, 200)
        bad = ref.copy()
        bad.putpixel((50, 30), (0, 0, 0, 255))
        stats = opt.error_stats(ref, bad)
        self.assertGreater(stats["max"], opt.MAX_PIXEL_ERROR)
        self.assertGreater(stats["mean"], 0)
        self.assertLessEqual(stats["over"], opt.MAX_OVER_FRACTION)
        self.assertTrue(opt._passes(stats))

    def test_detects_changed_region(self):
        # Una zona entera estropeada: > 0,1 % de los valores con error > 32/255 -> no se admite.
        ref = rgba_image()
        bad = ref.copy()
        bad.paste((0, 0, 0, 255), (40, 20, 50, 30))
        stats = opt.error_stats(ref, bad)
        self.assertGreater(stats["over"], opt.MAX_OVER_FRACTION)
        self.assertLessEqual(stats["mean"], opt.MAX_MEAN_ERROR * 10)
        self.assertFalse(opt._passes(stats))

    def test_detects_global_shift(self):
        ref = rgba_image()
        shifted = Image.eval(ref.convert("RGB"), lambda v: min(255, v + 5)).convert("RGBA")
        shifted.putalpha(ref.getchannel("A"))
        mean, worst = opt.image_error(ref, shifted)
        self.assertGreater(mean, opt.MAX_MEAN_ERROR)

    def test_invisible_color_ignored(self):
        ref = rgba_image()
        other = ref.copy()
        other.putpixel((0, 0), (0, 0, 0, 0))  # mismo píxel transparente con otro color
        self.assertEqual(opt.image_error(ref, other), (0.0, 0))

    def test_size_mismatch(self):
        self.assertEqual(opt.image_error(rgba_image(), rgba_image(10, 10))[0], float("inf"))


class ChooseWebpTests(unittest.TestCase):
    def test_result_passes_verification(self):
        png = png_bytes(rgba_image(), compress_level=0)
        res = opt.choose_webp(png)
        self.assertIsNotNone(res["webp"])
        self.assertLess(res["webp_size"], len(png))
        decoded = Image.open(io.BytesIO(res["webp"]))
        decoded.load()
        stats = opt.error_stats(Image.open(io.BytesIO(png)), decoded)
        self.assertLessEqual(stats["mean"], opt.MAX_MEAN_ERROR)
        self.assertLessEqual(stats["over"], opt.MAX_OVER_FRACTION)
        self.assertTrue(any(t["label"] == "WebP sin pérdida" for t in res["tried"]))

    def test_lowest_passing_quality_is_chosen(self):
        res = opt.choose_webp(png_bytes(rgba_image(), compress_level=0))
        lossy = [t for t in res["tried"] if "con pérdida" in t["label"]]
        # Se prueban de menor a mayor y se para en la primera que cumple.
        self.assertTrue(all(not t["ok"] for t in lossy[:-1]))
        if lossy[-1]["ok"] and res["label"].startswith("WebP con pérdida"):
            self.assertEqual(res["label"], lossy[-1]["label"])

    def test_strict_threshold_forces_exact_result(self):
        png = png_bytes(rgba_image(), compress_level=0)
        res = opt.choose_webp(png, max_mean=0, max_pixel=0, max_over=0)
        self.assertIsNotNone(res["webp"])
        self.assertEqual((res["mean"], res["max"]), (0.0, 0))
        self.assertEqual(res["label"], "WebP sin pérdida")

    def test_keeps_transparency(self):
        res = opt.choose_webp(png_bytes(rgba_image(), compress_level=0))
        decoded = Image.open(io.BytesIO(res["webp"])).convert("RGBA")
        self.assertEqual(decoded.getpixel((0, 0))[3], 0)
        self.assertEqual(decoded.getpixel((50, 30))[3], 255)

    def test_detects_c2pa_chunk(self):
        png = png_bytes(rgba_image())
        self.assertFalse(opt.choose_webp(png)["c2pa"])
        # Inserta un chunk 'caBX' (C2PA) antes de IEND; Pillow lo ignora al decodificar.
        import struct
        import zlib
        body = b"fake-c2pa"
        chunk = struct.pack(">I", len(body)) + b"caBX" + body + struct.pack(">I", zlib.crc32(b"caBX" + body))
        iend = png.rindex(b"IEND") - 4
        self.assertTrue(opt.choose_webp(png[:iend] + chunk + png[iend:])["c2pa"])


class ProcessFileTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def write_svg(self, name, data):
        path = os.path.join(self._tmp.name, name)
        with open(path, "wb") as fh:
            fh.write(data)
        return path

    def read(self, path):
        with open(path, "rb") as fh:
            return fh.read()

    def test_rewrites_only_data_uri(self):
        for wrap in (False, True):
            with self.subTest(wrap=wrap):
                original = svg_with(png_bytes(rgba_image(), compress_level=0), wrap=wrap)
                path = self.write_svg("logo-%d.svg" % wrap, original)
                res = opt.process_file(path)
                self.assertTrue(res["written"])
                self.assertGreaterEqual(res["saving"], opt.MIN_SAVING)
                new = self.read(path)
                self.assertEqual(len(new), res["after"])
                self.assertNotIn(b"data:image/png", new)
                self.assertIn(b'xlink:href="data:image/webp;base64,', new)
                # Todo lo que hay antes y después del data URI es idéntico byte a byte.
                head = original[:original.index(b"data:image/png;base64,")]
                tail = original[original.rindex(b'"/>'):]
                self.assertTrue(new.startswith(head + b"data:image/webp;base64,"))
                self.assertTrue(new.endswith(tail))
                b64 = new[len(head) + len(b"data:image/webp;base64,"):len(new) - len(tail)]
                webp = Image.open(io.BytesIO(base64.b64decode(b64)))
                webp.load()
                self.assertEqual(webp.format, "WEBP")
                mean, _ = opt.image_error(rgba_image(), webp)
                self.assertLessEqual(mean, opt.MAX_MEAN_ERROR)
                self.assertEqual(opt.strip_data_uris(new), opt.strip_data_uris(original))
                self.assertEqual(os.listdir(self._tmp.name).count(os.path.basename(path)), 1)

    def test_saving_below_threshold_not_rewritten(self):
        # La imagen sí mejora (PNG sin comprimir), pero es pequeña dentro de un SVG grande:
        # el ahorro total del fichero es < 20 %.
        png = png_bytes(rgba_image(16, 16), compress_level=0)
        padding = "<!-- %s -->" % ("x" * 20000)
        original = svg_with(png, prefix_extra=padding)
        path = self.write_svg("big.svg", original)
        res = opt.process_file(path)
        self.assertFalse(res["written"])
        self.assertLess(res["saving"], opt.MIN_SAVING)
        self.assertIn("no se reescribe", res["decision"])
        self.assertEqual(self.read(path), original)

    def test_dry_run_does_not_write(self):
        original = svg_with(png_bytes(rgba_image(), compress_level=0))
        path = self.write_svg("dry.svg", original)
        res = opt.process_file(path, dry_run=True)
        self.assertFalse(res["written"])
        self.assertGreaterEqual(res["saving"], opt.MIN_SAVING)
        self.assertEqual(self.read(path), original)

    def webp_svg(self, **save):
        buf = io.BytesIO()
        rgba_image().save(buf, "WEBP", **save)
        raw = buf.getvalue()
        return raw, svg_with(b"").replace(b"data:image/png;base64,",
                                          b"data:image/webp;base64," + base64.b64encode(raw))

    def test_lossless_webp_is_a_source(self):
        raw, svg = self.webp_svg(lossless=True)
        self.assertTrue(opt.is_lossless_webp(raw))
        new, images = opt.optimize_svg_bytes(svg)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["src_format"], "webp")
        self.assertFalse(images[0]["c2pa"])
        self.assertEqual(opt.strip_data_uris(new), opt.strip_data_uris(svg))
        if images[0]["webp"] is not None:
            self.assertLessEqual(images[0]["mean"], opt.MAX_MEAN_ERROR)
            self.assertLessEqual(images[0]["over"], opt.MAX_OVER_FRACTION)

    def test_lossy_webp_is_ignored(self):
        raw, svg = self.webp_svg(quality=80)
        self.assertFalse(opt.is_lossless_webp(raw))
        new, images = opt.optimize_svg_bytes(svg)
        self.assertEqual(images, [])
        self.assertEqual(new, svg)
        path = self.write_svg("lossy.svg", svg)
        self.assertEqual(opt.process_file(path)["decision"], "sin PNG ni WebP sin pérdida incrustado")

    def test_report_append(self):
        self.write_svg("a.svg", svg_with(png_bytes(rgba_image(), compress_level=0)))
        report = os.path.join(self._tmp.name, "report.txt")
        with open(report, "w", encoding="utf-8") as fh:
            fh.write("primera pasada\n")
        with redirect_stdout(io.StringIO()):
            opt.main([os.path.join(self._tmp.name, "a.svg"), "--dry-run", "--report", report, "--append"])
        with open(report, encoding="utf-8") as fh:
            text = fh.read()
        self.assertTrue(text.startswith("primera pasada\n"))
        self.assertIn("TOTAL", text)

    def test_svg_without_png_untouched(self):
        original = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1"/></svg>'
        path = self.write_svg("plain.svg", original)
        res = opt.process_file(path)
        self.assertEqual(res["decision"], "sin PNG ni WebP sin pérdida incrustado")
        self.assertEqual(self.read(path), original)

    def test_main_report_and_globs(self):
        self.write_svg("a.svg", svg_with(png_bytes(rgba_image(), compress_level=0)))
        self.write_svg("b.svg", svg_with(png_bytes(rgba_image(), compress_level=0)))
        report = os.path.join(self._tmp.name, "out", "report.txt")
        with redirect_stdout(io.StringIO()) as out:
            code = opt.main([os.path.join(self._tmp.name, "*.svg"), "--dry-run", "--report", report])
        self.assertEqual(code, 0)
        with open(report, encoding="utf-8") as fh:
            text = fh.read()
        self.assertEqual(text.strip(), out.getvalue().strip())
        self.assertIn("C2PA", text)
        self.assertIn("a.svg", text)
        self.assertIn("b.svg", text)
        self.assertIn("TOTAL", text)
        self.assertIn(b"data:image/png", self.read(os.path.join(self._tmp.name, "a.svg")))

    def test_main_missing_input_fails(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(opt.main([os.path.join(self._tmp.name, "nada-*.svg")]), 1)


if __name__ == "__main__":
    unittest.main()
