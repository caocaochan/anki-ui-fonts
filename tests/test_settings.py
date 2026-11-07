import json
from pathlib import Path
import unittest

from ui_fonts.settings import AreaSettings, Settings, effective_locale, load_settings, resolve_cjk


class SettingsTests(unittest.TestCase):
    def test_shipped_defaults_match_code(self):
        shipped = json.loads((Path(__file__).parents[1] / "ui_fonts" / "config.json").read_text())
        settings, issues = load_settings(shipped)
        self.assertEqual(settings.to_dict(), shipped)
        self.assertEqual(issues, [])

    def test_valid_configuration_roundtrips(self):
        value = Settings(locale="ja", ui=AreaSettings("Segoe UI", "Noto Sans JP", 10.5), browser=AreaSettings("Arial", "auto", 48))
        self.assertEqual(load_settings(value.to_dict()), (value, []))

    def test_invalid_values_recover_without_dropping_valid_neighbors(self):
        value, issues = load_settings({"locale": [], "ui": {"latin": "Arial", "cjk": "bad\nfont", "size": float("nan")}, "browser": {"size": True}})
        self.assertEqual(value.locale, "zh-Hans")
        self.assertEqual(value.ui.latin, "Arial")
        self.assertEqual(value.ui.cjk, "auto")
        self.assertIsNone(value.ui.size)
        self.assertIsNone(value.browser.size)
        self.assertEqual(len(issues), 4)

    def test_invalid_configuration_shapes(self):
        for raw in (None, [], 5, "wrong"):
            with self.subTest(raw=raw):
                settings, issues = load_settings(raw)
                self.assertEqual(settings, Settings())
                self.assertTrue(issues)
        settings, issues = load_settings({"ui": [], "browser": "wrong"})
        self.assertEqual(settings, Settings())
        self.assertEqual(len(issues), 2)

    def test_size_bounds(self):
        for size in (0, 5.9, 48.1, float("inf"), "12", False):
            with self.subTest(size=size):
                self.assertIsNone(load_settings({"ui": {"size": size}})[0].ui.size)
        for size in (6, 48, 12.5):
            self.assertEqual(load_settings({"ui": {"size": size}})[0].ui.size, size)

    def test_anki_language_mapping(self):
        for tag, expected in (("zh_CN", "zh-Hans"), ("zh-TW", "zh-Hant-TW"), ("zh-HK", "zh-Hant-HK"), ("ja-JP", "ja"), ("ko", "ko"), ("en-US", "")):
            self.assertEqual(effective_locale("", tag), expected)
        self.assertEqual(effective_locale("zh-Hans", "ja"), "zh-Hans")

    def test_regional_font_order_and_missing_fonts(self):
        self.assertEqual(resolve_cjk("auto", "zh-Hans", ["Microsoft YaHei UI", "Noto Sans SC"]), ("Noto Sans SC", None))
        self.assertEqual(resolve_cjk("auto", "zh-Hans", ["Microsoft YaHei UI"]), ("Microsoft YaHei UI", None))
        self.assertEqual(resolve_cjk("noto sans sc", "ja", ["Noto Sans SC"]), ("Noto Sans SC", None))
        self.assertTrue(resolve_cjk("Missing Font", "ja", [])[1])
        self.assertTrue(resolve_cjk("auto", "ja", [])[1])
        self.assertEqual(resolve_cjk("auto", "", []), ("", None))


if __name__ == "__main__":
    unittest.main()
