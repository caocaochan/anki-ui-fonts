"""Run with Anki 26.09.4's Python/Qt packages importable (no collection needed)."""

import unittest

import aqt
from aqt.qt import QApplication, QFont
from aqt.qt import QWidget, QTextLayout

from ui_fonts.dialog import AreaPanel, FontPicker
from ui_fonts.settings import AreaSettings
from ui_fonts.typography import FontResolver, explicit_font, web_css, web_script

app = QApplication.instance() or QApplication([])


class FontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resolver = FontResolver()

    def test_font_overrides_preserve_style_and_source(self):
        base = QFont("Segoe UI", 9)
        base.setBold(True)
        base.setItalic(True)
        result = self.resolver.font(base, AreaSettings("Arial", "auto", 17.5), "zh-Hans")
        self.assertEqual(result.families()[:2], ["Arial", "Noto Sans SC"])
        self.assertEqual(result.pointSizeF(), 17.5)
        self.assertTrue(result.bold())
        self.assertTrue(result.italic())
        self.assertEqual(base.families(), ["Segoe UI"])
        self.assertEqual(base.pointSize(), 9)

    def test_default_retains_pixel_size_and_template_family(self):
        base = QFont("Arial")
        base.setPixelSize(27)
        result = self.resolver.font(base, AreaSettings(), "zh-Hans")
        self.assertEqual(result.pixelSize(), 27)
        self.assertEqual(result.families()[0], "Arial")

    def test_pinned_default_font_does_not_inherit_later_application_size(self):
        original = QFont(app.font())
        widget = QWidget()
        widget.setFont(explicit_font(original))
        changed = QFont(original)
        changed.setPointSizeF(27)
        app.setFont(changed)
        try:
            self.assertEqual(widget.font().pointSizeF(), original.pointSizeF())
        finally:
            app.setFont(original)
            widget.deleteLater()

    def test_missing_fonts_and_broad_latin_coverage(self):
        self.assertIn("not installed", self.resolver.notices(QFont("Arial"), AreaSettings("Not A Real Font", "", None), "zh-Hans")[0])
        notices = self.resolver.notices(QFont("Arial"), AreaSettings("Noto Sans SC", "Noto Sans JP"), "zh-Hans")
        self.assertTrue(any("contains Han" in notice for notice in notices))

    def test_row_height_accommodates_large_fonts(self):
        small = self.resolver.row_height(QFont("Arial", 9), AreaSettings(size=6), "zh-Hans")
        large = self.resolver.row_height(QFont("Arial", 9), AreaSettings(size=48), "zh-Hans")
        self.assertGreater(large, small * 3)

    def test_qt_shapes_han_with_the_selected_regional_fallback(self):
        for locale, family in (("zh-Hans", "Noto Sans SC"), ("ja", "Noto Sans JP")):
            font = self.resolver.font(QFont("Segoe UI", 12), AreaSettings("Segoe UI", "auto"), locale)
            layout = QTextLayout("ABC 骨直令", font)
            layout.beginLayout()
            line = layout.createLine()
            line.setLineWidth(500)
            layout.endLayout()
            actual_fonts = {run.rawFont().familyName() for run in layout.glyphRuns()}
            self.assertIn(family, actual_fonts)
            self.assertIn("Segoe UI", actual_fonts)

    def test_picker_search_and_missing_persisted_font(self):
        picker = FontPicker(self.resolver.installed, True)
        for value in ("", "auto", "Noto Sans SC", "Missing Font"):
            picker.set_value(value)
            self.assertEqual(picker.value(), value)
        self.assertTrue(picker.isEditable())
        picker.deleteLater()

    def test_previews_default_and_maximum(self):
        for browser in (True, False):
            panel = AreaPanel("Test", self.resolver, QFont("Arial", 9), browser)
            for size in (None, 6, 48):
                panel.set_value(AreaSettings("Arial", "auto", size))
                panel.refresh_preview("zh-Hans")
                self.assertEqual(panel.value().size, size)
            panel.deleteLater()

    def test_css_and_script_escape_configuration_strings(self):
        hostile = 'font";}</style><script>alert(1)</script>\\'
        css = web_css([hostile], 16)
        script = web_script(css, "zh-Hans")
        self.assertNotIn("</style>", css)
        self.assertNotIn("</script>", script)
        self.assertIn("16.0000px", css)
        self.assertNotIn("font-size", web_css(["Segoe UI"], None))


if __name__ == "__main__":
    unittest.main()
