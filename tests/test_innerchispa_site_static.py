import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_ROOT = REPO_ROOT / "site"


class InnerChispaStaticSiteTest(unittest.TestCase):
    def test_required_pages_exist(self):
        required_pages = [
            "index.html",
            "ralphiia/index.html",
            "infrastructure/index.html",
            "solutions/index.html",
            "case-studies/pc-doctor/index.html",
            "investors/index.html",
            "investors/deck/index.html",
            "impact/index.html",
        ]
        for page in required_pages:
            with self.subTest(page=page):
                self.assertTrue((SITE_ROOT / page).is_file())

    def test_core_positioning_is_present(self):
        home = (SITE_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("Sovereign AI operations", home)
        self.assertIn("InnerChispa LLC builds sovereign", home)
        self.assertIn("RalphiIA", home)
        self.assertIn("PC Doctor", home)
        self.assertIn("lab.innerchispa.us", home)

    def test_investor_narrative_and_deck_route_exist(self):
        investors = (SITE_ROOT / "investors" / "index.html").read_text(encoding="utf-8")
        deck = SITE_ROOT / "investors" / "deck" / "index.html"
        self.assertTrue(deck.is_file())
        self.assertIn("US$250K", investors)
        self.assertIn("paid design partnerships", investors)
        self.assertIn("/investors/deck/", investors)

    def test_language_switcher_is_not_google_translate_dependent(self):
        script = (SITE_ROOT / "assets" / "site.js").read_text(encoding="utf-8")
        self.assertIn("data-lang-switch", script)
        self.assertIn("innerchispa-language", script)
        all_site_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in SITE_ROOT.rglob("*")
            if path.is_file() and path.suffix in {".html", ".css", ".js", ".md"}
        )
        self.assertNotIn("translate.google", all_site_text.lower())
        self.assertNotIn("goog-te", all_site_text.lower())

    def test_public_site_does_not_expose_sensitive_infrastructure_details(self):
        forbidden_patterns = [
            r"192\.168\.",
            r"localhost:\d+",
            r"127\.0\.0\.1:\d+",
            r"\bapi[_ -]?key\b",
            r"\bsecret\b",
            r"\btoken\b",
            r"ngrok",
            r"raw logs?",
        ]
        for path in SITE_ROOT.rglob("*"):
            if path.is_file() and path.suffix in {".html", ".css", ".js", ".md"}:
                text = path.read_text(encoding="utf-8")
                for pattern in forbidden_patterns:
                    with self.subTest(path=path.relative_to(REPO_ROOT), pattern=pattern):
                        self.assertIsNone(re.search(pattern, text, flags=re.IGNORECASE))

    def test_home_json_ld_is_parseable(self):
        home = (SITE_ROOT / "index.html").read_text(encoding="utf-8")
        match = re.search(
            r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
            home,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match)
        data = json.loads(match.group(1))
        self.assertEqual(data["@type"], "Organization")
        self.assertEqual(data["name"], "InnerChispa LLC")


if __name__ == "__main__":
    unittest.main()
