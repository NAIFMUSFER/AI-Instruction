"""Verify the Apple Quick Look launch markup, first-party files and hosting contract."""
from html.parser import HTMLParser
from pathlib import Path
import re
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "public"
MODEL = "/guest-plans/apartment-20x25.usdz"
THUMB = "/guest-plans/apartment-20x25-preview.jpg"


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            self.active = (attrs, [], [])
            self.links.append(self.active)
        elif self.active:
            self.active[1].append((tag, attrs))

    def handle_endtag(self, tag):
        if tag == "a":
            self.active = None

    def handle_data(self, data):
        if self.active and data.strip():
            self.active[2].append(data.strip())


class QuickLook(unittest.TestCase):
    def check_launch(self, markup):
        parser = Links()
        parser.feed(markup)
        native, = [item for item in parser.links if item[0].get("rel") == "ar"]
        anchor, children, text = native
        self.assertEqual(anchor["href"], MODEL)
        self.assertNotIn("download", anchor)
        self.assertIn("الآيفون", anchor["aria-label"])
        self.assertEqual([tag for tag, _ in children], ["img"])
        self.assertEqual(children[0][1]["src"], THUMB)
        self.assertEqual(text, [], "iOS Quick Look requires the image as the sole child")
        return {item[0]["href"] for item in parser.links}

    def test_standalone_page(self):
        page = (PUBLIC / "guest-plans/apartment-iphone.html").read_text()
        routes = self.check_launch(page)
        self.assertIn("/?guest=1&example=apartment-20x25", routes)
        self.assertIn("/guest-plans/apartment-floor-0.svg", routes)
        self.assertNotIn("<script", page)
        self.assertIn("Safari", page)
        self.assertIn("الأصلي", page)
        self.assertTrue((PUBLIC / THUMB[1:]).read_bytes().startswith(b"\xff\xd8\xff"))
        self.assertTrue((PUBLIC / "guest-plans/apartment-floor-0.svg").is_file())

    def test_studio_and_fallback(self):
        for relative, link in [("ui/guest-workspace.js", "guestNativeSample"),
                               ("boot/engine-guard.js", "guestFallbackNative")]:
            source = (PUBLIC / "app" / relative).read_text()
            fragment = re.search(r'<a id="' + link + r'".*?</a>', source).group()
            self.check_launch(fragment)

    def test_usdz_served_inline(self):
        with (ROOT / "netlify.toml").open("rb") as stream:
            rules = tomllib.load(stream)["headers"]
        mime, = [rule["values"]
                 for rule in rules if rule["for"] == "/guest-plans/*.usdz"]
        self.assertEqual(mime["Content-Type"], "model/vnd.usdz+zip")
        self.assertEqual(mime["Content-Disposition"], "inline")


if __name__ == "__main__":
    unittest.main()
