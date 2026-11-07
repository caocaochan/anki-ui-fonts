# UI Fonts

Open **Tools → UI Fonts…** to configure this add-on. The Config button opens the same window.

Each area has a Latin font, a CJK fallback font, and one shared size in points.

- **Anki default** Latin font/size preserves Anki's original settings. In browser entries, this includes per-template browser fonts and sizes.
- **Automatic** CJK font chooses an installed regional Noto Sans font, then a Microsoft regional UI font.
- The initial rendering locale is **zh-Hans**. Locale changes glyph/font selection; it does not change interface translations or date/number formatting.
- Missing fonts fall back safely and appear as notices in the settings window.
- **Restore Defaults** changes the draft. Click Apply or OK to save it.
- Apply saves immediately. Cancel discards changes since the last Apply.

Font families are ordered fallbacks. If your Latin font already contains Han glyphs, those glyphs win. Choose a Latin font without Han coverage, such as Segoe UI, to make the CJK fallback effective.

Note editing, card reviewing, card preview, and template editing retain their own typography. Existing font add-ons may override these settings; disable conflicting typography add-ons if necessary.

Settings are local to this Anki installation and shared across its profiles. They do not modify cards or sync through AnkiWeb.
