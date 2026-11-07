# Validation

## Version 1.1.0 browser note-field locale

The existing main locale now also applies to browser note-field wrappers, outside the saved editable HTML. No configuration keys or controls were added. All 16 unit/Qt tests passed. The expanded integration suite passed 61 checks with the legacy editor at 200% scaling and 61 with the newer Svelte editor at 150% scaling on Anki 26.09.4 / Qt 6.11.2.

New checks verify language inheritance through the real rich-text shadow DOM, live locale changes, unchanged field HTML/font families/sizes, preserved explicit content-language tags, restoration of absent/nonempty wrapper attributes, observer cleanup, newly mounted fields, note switching, and exclusion of Add Notes. Existing reviewer/preview/template and collection-content checks still pass. Runs exited successfully; the legacy harness also emitted a late Anki collection-operation callback warning during shutdown, while the Svelte run emitted an aborted-render warning during a mode switch. These are recorded separately from the successful typography assertions.

Current artifact: `dist/anki-ui-fonts-1.1.0.ankiaddon`. SHA-256 is recorded in the GitHub release's `SHA256SUMS` asset.

## Version 1.0.1 preview-height update

Both preview height ranges were halved: general UI 50–80 logical pixels and browser entries 65–90. Unused dialog space is allocated below the sections so they do not expand to fill it. All 16 unit/Qt tests passed again. A rendered Qt layout check confirmed actual heights of 80 and 90 logical pixels. The full integration/visual results below describe the 1.0.0 baseline; they were not repeated for this layout-only update.

Current artifact: `dist/anki-ui-fonts-1.0.1.ankiaddon`.

SHA-256: `2ed1b2deac5857bf297e50b2912d959ab7638d49b0ab9c3f1ed0a52e1a98d025`.

The first public package also includes GitHub author/homepage metadata. All 16 unit/Qt tests passed again before publication.

## Version 1.0.0 baseline

**High confidence — observed in the installed runtime, not inferred from version metadata alone.**

Validated on 2026-11-07 with:

| Component | Observed version |
|---|---|
| Anki | 26.09.4 |
| Python | 3.13.17, x64 |
| PyQt | 6.11.0 |
| Runtime Qt | 6.11.2 |
| Platform | Windows 11, native Qt/DirectWrite |
| Display scaling | 150% and 200% (Qt device pixel ratios 1.5 and 2.0) |

## Automated checks

**16 unit/Qt tests passed**, covering configuration recovery, shipped defaults, regional font selection, font style preservation, point/pixel sizing, missing fonts, searchable selectors, preview size bounds, CSS/script escaping, webview font pinning, and actual `QTextLayout.glyphRuns()` font selection when alternating between Simplified Chinese and Japanese.

**48 integration checks passed at each display scale.** The 150% run included package installation using Anki's installer. The 200% run included a full process restart and configuration recovery from disk. Both used the final packaged artifact and Anki's installed packages, with project-local sample data and a unique single-instance key.

Integration coverage includes:

- Installed module loading, idempotent initialization, one Tools entry, and the Config action registration.
- Independent general/browser fonts and sizes in every displayed column, in Cards and Notes modes.
- Retention of Anki's original browser delegate, results, selection, and sufficiently tall rows at 48 pt.
- Deck-list computed font family/size and language attribute, live locale changes, one replaceable stylesheet, and restoration of the original language attribute.
- Original webview font metrics for existing editor/main views and newly constructed views before their standard CSS is generated.
- Exclusion of note editor, preview card, and reviewer card DOMs, including applying UI settings while a reviewer card is open.
- Preview drafts, Apply, Cancel, Cancel after Apply, Restore Defaults, saved configuration, and restored template-specific browser fonts/sizes.
- Invalid configuration recovery, theme changes, unchanged translation/date-number locale, unchanged sample note fields/templates, and real switches between two profiles.

Final runs used Anki's normal shutdown sequence and exited successfully. The standalone harness disables audio player initialization because it runs from a separate Python directory; audio playback is outside these checks. Anki emitted MathJax component-version and media-server shutdown warnings during the harness; typography assertions passed.

## Visual checks

Inspected the live settings window at 150% and 200%, plus the native browser at 200%, using the computer-use plugin. Font pickers, size controls, previews, and action buttons rendered correctly. Browser rows retained alternating/status styling and selection; the editor retained the sample note's explicit Times New Roman formatting. Preview text demonstrated the selected Simplified Chinese font.

Unmodified delegate behavior preserves Anki's RTL, status-color, and elision code paths; these were source-checked, but exhaustive visual testing of every RTL language/status combination was not performed. Other add-ons, operating systems, Anki releases, and custom GDI font backends are not certified.

## Artifact

`dist/anki-ui-fonts-1.0.0.ankiaddon`

SHA-256:

```text
7806004135d183d9253bf5c4e038ae971f69a5266c705bce4630ef0c86f4c005
```

The installed test profiles and runtime are excluded from the artifact. The user's normal Anki profile and add-on directory were not modified.
