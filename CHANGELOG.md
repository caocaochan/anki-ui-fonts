# Changelog

## 1.1.0

- Apply the existing rendering locale to note fields in the browser, including rich-text fields in both editor implementations. No new setting is added.
- Preserve field fonts, sizes, inline formatting, and saved HTML. Explicit content language tags remain intact.
- Restore original wrapper language metadata when Anki default is selected; keep the locale across note changes and newly mounted fields.
- Leave Add Notes, reviewer cards, previews, and template editing unchanged.

Validation: 16 unit/Qt tests and 61 integration checks pass with both the legacy editor at 200% scaling and the newer Svelte editor at 150% scaling.

## 1.0.1

First public release, targeting Anki 26.09.4 on Windows 11.

- Independent general UI and browser-entry Latin/CJK fonts, with one size per area.
- Rendering-locale presets, including zh-Hans, and automatic regional CJK fallback selection.
- Tools → UI Fonts settings with searchable font pickers, live previews, Apply/Cancel, and Restore Defaults.
- Preserved note-field, reviewer-card, preview-card, and template typography.
- Compact previews at half the original height.
- GitHub repository metadata and reproducible installable package.

Validation: 16 unit/Qt tests pass. The original 1.0.0 implementation passed 48 integration checks at both 150% and 200% scaling; the preview-only 1.0.1 change received a rendered Qt layout check. See [VALIDATION.md](VALIDATION.md).
