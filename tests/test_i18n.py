import unittest

from mathfixer.i18n import TRANSLATIONS, tr


class TranslationTests(unittest.TestCase):
    def test_english_and_persian_catalogs_have_identical_keys(self):
        self.assertEqual(set(TRANSLATIONS["en"]), set(TRANSLATIONS["fa"]))

    def test_dynamic_messages_format_in_both_languages(self):
        for language in ("en", "fa"):
            self.assertIn("12", tr(language, "scan_complete", total=12, repairs=2))
            self.assertIn("7", tr(language, "processing", value=7))

    def test_desktop_options_have_explicit_off_labels_and_one_action(self):
        for language in ("en", "fa"):
            self.assertTrue(tr(language, "ai_off"))
            self.assertTrue(tr(language, "thesis_none"))
            self.assertTrue(tr(language, "scan_and_repair"))


if __name__ == "__main__":
    unittest.main()
