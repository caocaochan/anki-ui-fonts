# Changelog

## 1.0.1

First public release, targeting Anki 26.09.4 on Windows 11.

- Independent general UI and browser-entry Latin/CJK fonts, with one size per area.
- Rendering-locale presets, including zh-Hans, and automatic regional CJK fallback selection.
- Tools → UI Fonts settings with searchable font pickers, live previews, Apply/Cancel, and Restore Defaults.
- Preserved note-field, reviewer-card, preview-card, and template typography.
- Compact previews at half the original height.
- GitHub repository metadata and reproducible installable package.

Validation: 16 unit/Qt tests pass. The original 1.0.0 implementation passed 48 integration checks at both 150% and 200% scaling; the preview-only 1.0.1 change received a rendered Qt layout check. See [VALIDATION.md](VALIDATION.md).
