import base64
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_site  # noqa: E402


class SiteCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def write(self, rel, content="", binary=False):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb" if binary else "w") as fh:
            fh.write(content if binary else content)

    def blob(self, rel, size):
        self.write(rel, b"\0" * size, binary=True)

    def reasons(self, result):
        return [(p["file"], p["reason"]) for p in result["problems"]]


class CheckSiteTests(SiteCase):
    def test_ok_site(self):
        self.blob("assets/a.webp", 1000)
        self.blob("assets/b.jpg", 500)
        self.blob("assets/v.mp4", 10 * 1024 * 1024)
        self.write("styles.css", "body{background:url('assets/b.jpg')}")
        self.write("app.js", "var x='./assets/a.webp';")
        self.write("index.html", '<link href="styles.css" rel="stylesheet"><script src="app.js"></script>'
                   '<video poster="assets/a.webp"><source src="assets/v.mp4"></video>'
                   '<a href="en/index.html#x">en</a><a href="https://x.org/y.png">e</a>')
        self.write("en/index.html", '<img src="../assets/a.webp" srcset="../assets/a.webp 1x, ../assets/b.jpg 2x">')
        r = check_site.check_site(self.root)
        self.assertTrue(r["ok"], r["problems"])
        self.assertEqual(r["pages"]["index.html"]["image_bytes"], 1500)  # sin vídeo
        self.assertEqual(r["pages"]["en/index.html"]["image_bytes"], 1500)
        self.assertEqual(check_site.main([self.root]), 0)

    def test_broken_html_reference(self):
        self.write("index.html", '<img src="assets/nope.png">')
        r = check_site.check_site(self.root)
        self.assertIn(("index.html", "referencia local inexistente"), self.reasons(r))
        self.assertNotEqual(check_site.main([self.root]), 0)

    def test_broken_srcset_candidate(self):
        self.blob("assets/a.webp", 10)
        self.write("index.html", '<img srcset="assets/a.webp 1x, assets/b.webp 2x">')
        self.assertFalse(check_site.check_site(self.root)["ok"])

    def test_en_resolves_relative_to_en(self):
        self.blob("assets/a.webp", 10)
        self.write("en/index.html", '<img src="assets/a.webp">')  # sin ../ => roto
        self.assertFalse(check_site.check_site(self.root)["ok"])
        self.write("en/index.html", '<img src="../assets/a.webp">')
        self.assertTrue(check_site.check_site(self.root)["ok"])

    def test_broken_css_and_js_references(self):
        self.write("s.css", "a{background:url(assets/x.png)}")
        self.write("a.js", "const p = 'assets/missing.webp';")
        r = check_site.check_site(self.root)
        reasons = self.reasons(r)
        self.assertIn(("s.css", "referencia local inexistente"), reasons)
        self.assertIn(("a.js", "referencia local inexistente"), reasons)

    def test_svg_with_large_png(self):
        big = base64.b64encode(os.urandom(500 * 1024)).decode()
        small = base64.b64encode(os.urandom(1024)).decode()
        self.write("assets/big.svg", '<svg><image href="data:image/png;base64,%s"/></svg>' % big)
        self.write("assets/small.svg", '<svg><image href="data:image/png;base64,%s"/></svg>' % small)
        r = check_site.check_site(self.root)
        self.assertEqual(self.reasons(r), [("assets/big.svg", "PNG incrustado > 400 KB")])

    def test_page_over_6mb(self):
        self.blob("assets/huge.png", 7 * 1024 * 1024)
        self.write("index.html", '<img src="assets/huge.png">')
        r = check_site.check_site(self.root)
        self.assertIn(("index.html", "imágenes > 6 MB"), self.reasons(r))

    def test_images_via_css_counted_once(self):
        self.blob("assets/h.jpg", 4 * 1024 * 1024)
        self.write("s.css", "a{background:url(assets/h.jpg)}")
        self.write("index.html", '<link rel="stylesheet" href="s.css"><img src="assets/h.jpg">')
        r = check_site.check_site(self.root)
        self.assertEqual(r["pages"]["index.html"]["image_bytes"], 4 * 1024 * 1024)
        self.assertTrue(r["ok"])
        self.blob("assets/h2.jpg", 3 * 1024 * 1024)
        self.write("s.css", "a{background:url(assets/h.jpg)} b{background:url(assets/h2.jpg)}")
        self.assertFalse(check_site.check_site(self.root)["ok"])

    def test_root_absolute_paths_ignored(self):
        self.write("404.html", '<a href="/proyecto/index.html">inicio</a>')
        self.assertTrue(check_site.check_site(self.root)["ok"])

    def test_excluded_dirs_ignored(self):
        self.write("tools/x.html", '<img src="nope.png">')
        self.write("docs/x.html", '<img src="nope.png">')
        self.assertTrue(check_site.check_site(self.root)["ok"])


if __name__ == "__main__":
    unittest.main()
