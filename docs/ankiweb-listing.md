# AnkiWeb listing

- **Title:** Anki UI Fonts — Separate UI/Browser Fonts and CJK Locale
- **Listing / install code:** [1031646718](https://ankiweb.net/shared/info/1031646718)
- **Tags:** `fonts browser chinese japanese cjk ui`
- **Support:** https://github.com/caocaochan/anki-ui-fonts/issues
- **Package:** `anki-ui-fonts-1.0.1.ankiaddon` from the v1.0.1 GitHub release
- **Branch:** minimum `26.09.4`, maximum `-26.09.4` (restrict downloading to the tested Anki version)

## Published description

Customize Anki’s interface and browser-entry fonts independently, with regional CJK rendering for Simplified Chinese, Traditional Chinese, Japanese, and Korean.

### Features

- Separate font settings for the general UI and browser entries.
- A Latin font and CJK fallback font for each area, with one shared font size per area (6–48 pt).
- Rendering-locale presets: zh-Hans, zh-Hant-TW, zh-Hant-HK, ja, ko, or Anki default.
- Automatic selection of an installed regional Noto Sans or Microsoft CJK font.
- Searchable font pickers, compact previews, Apply/Cancel, and Restore Defaults.
- Settings shared across profiles on the same Anki installation.

### Usage

After installing, restart Anki and open **Tools → UI Fonts…**. The add-on’s **Config** button opens the same settings window.

For Simplified Chinese, use **Segoe UI + Automatic CJK + zh-Hans**. Automatic prefers Noto Sans SC, then Microsoft YaHei UI when available. No fonts are bundled.

### Compatibility and limits

**Tested with Anki 26.09.4 on Windows 11 (Qt 6.11.2).** Other Anki versions and operating systems are not validated. This is an Anki desktop add-on; it does not run in AnkiWeb, AnkiMobile, or AnkiDroid.

Note editor webviews, reviewer cards, card previews, and template editing keep their existing typography. The rendering locale does not change Anki’s translations, number/date formatting, note data, or templates.

Fonts use ordered fallback: if your Latin font already contains Han glyphs, those glyphs take priority over the CJK fallback. Untagged Han characters share one regional preference; Chinese and Japanese are not detected automatically.

If you previously installed the GitHub .ankiaddon version, disable or remove that copy before enabling the AnkiWeb copy, to avoid duplicate installations. Other font add-ons may conflict.

### Source and support

[Source code, documentation, and releases](https://github.com/caocaochan/anki-ui-fonts) · [Report a bug](https://github.com/caocaochan/anki-ui-fonts/issues)

Version 1.0.1 · MIT license.
