import unittest
from bridge.i18n import LANGUAGES, KEYS, ROWS, TRANSLATIONS, translate

class TranslationTests(unittest.TestCase):
    def test_catalogs_complete(self):
        for code, _ in LANGUAGES:
            self.assertEqual(len(ROWS[code]), len(KEYS), code)
            self.assertEqual(set(TRANSLATIONS[code]), set(KEYS), code)
            self.assertTrue(all(TRANSLATIONS[code].values()))

    def test_unknown_language_falls_back(self):
        self.assertEqual(translate("unknown", "import"), "Import tree")
