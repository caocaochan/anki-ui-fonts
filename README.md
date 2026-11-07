# Anki UI Fonts

Assumes **Windows 11 and Anki 26.09.4**, with its bundled Qt 6.11.2 runtime.

Set fonts for the interface and browser entries independently, with separate Latin/CJK font choices and one shared size per area. The default rendering locale is **zh-Hans**.

## Install

1. In Anki, open **Tools → Add-ons → Get Add-ons…** and enter **`1031646718`** ([AnkiWeb listing](https://ankiweb.net/shared/info/1031646718)).
2. Restart Anki.
3. Open **Tools → UI Fonts…**. The add-on's **Config** button opens the same dialog.

Alternatively, download `anki-ui-fonts-1.0.1.ankiaddon` from the [latest GitHub release](https://github.com/caocaochan/anki-ui-fonts/releases/latest) and use **Install from file…**.

If switching from the GitHub package to AnkiWeb, disable the existing GitHub-installed copy before enabling the AnkiWeb copy. AnkiWeb uses a different add-on folder ID, so the copies can coexist and their settings are not migrated automatically.

The package has no dependencies beyond Anki and does not include fonts. Development testing uses isolated profiles.

## Settings

Each area has searchable installed-font pickers and a size in points (6–48 pt):

| Setting | Meaning |
|---|---|
| Latin: Anki default | Preserve Anki's existing family, including template-specific browser fonts. |
| CJK: Automatic | Prefer an installed regional Noto Sans family, then Microsoft's regional UI font. |
| CJK: Anki default | Keep ordinary system fallback rather than selecting a regional CJK family. |
| Size: Anki default | Preserve the native UI size or template-specific browser pixel size. |
| Rendering locale | Anki default, zh-Hans, zh-Hant-TW, zh-Hant-HK, ja, or ko. |

For Simplified Chinese, **Segoe UI + Automatic CJK + zh-Hans** is the recommended starting point. Automatic prefers **Noto Sans SC**, then **Microsoft YaHei UI** if Noto Sans SC is unavailable. Browser entries can use their own Latin font and size.

**Apply** saves and updates supported open windows. **Cancel** discards changes since the last Apply. **Restore Defaults** changes the draft; Apply or OK saves it. Previews do not change the application until applied.

Configuration is local to the add-on installation, shared across Anki profiles, and not synced through AnkiWeb. Missing fonts or invalid values recover to defaults and produce notices in the settings dialog.

## Coverage and limits

- Native menus, dialogs, controls, browser sidebar, and browser headings use general UI settings. Browser entry settings cover all table columns in Cards and Notes modes.
- Supported interface webviews include deck lists, overview, toolbars, preferences, deck options, statistics, and selected import/utility dialogs. Unknown third-party webviews are left alone.
- Note editor webviews, reviewer card content, card previews, and template editing retain their own typography. The editor's embedded toolbar is also left alone, since it shares the note-field webview.
- Font families are ordered fallbacks, not strict Unicode-script assignments. If the Latin font contains Han characters, those glyphs take priority. The dialog detects representative Han coverage and explains this limitation.
- Shared Han characters do not reveal whether a passage is Chinese or Japanese. One regional preference applies to untagged Han text. An explicitly chosen CJK font takes priority over the automatic locale preset.
- The rendering locale does not change Anki's translations, Qt's date/number locale, system locale, note data, or templates. Fonts with a fixed regional design retain that design even if another locale is selected.

Initial defaults retain Anki's Latin fonts and sizes, and add an automatic Simplified Chinese fallback. Other typography add-ons can override these settings; compatibility with individual third-party add-ons has not been tested. Other Anki versions and operating systems are not claimed as tested.

## Build and test

From this directory in PowerShell, with Python 3.10+:

```powershell
python build.py
python -m unittest discover -s tests -p test_settings.py -v
```

`build.py` produces a deterministic ZIP-format `.ankiaddon`, with `__init__.py` and the manifest at its root. It excludes tests, reference sources, local configuration, and the test runtime.

Qt and full integration tests require **Python 3.13** with Anki 26.09.4 packages. In an active Python 3.13 environment, install the pinned Anki/Qt dependencies and run:

```powershell
python -m pip install "aqt[qt]==26.9.4"
python -m unittest discover -s tests -v
python tests/integration.py
python tests/integration.py --restart
```

The Qt/regional-font tests assume Windows with Segoe UI, Arial, Noto Sans SC, and Noto Sans JP installed. The integration harness uses Anki's own installer, two real project-local profiles, a sample collection, browser/editor/reviewer webviews, and normal shutdown. It uses a unique single-instance key so it cannot attach to your normal Anki process. The standalone harness disables audio players; multimedia behavior is outside these typography checks. Integration tests need permission to bind a localhost socket for Anki's webviews.

See [VALIDATION.md](VALIDATION.md) for the verified runtime and coverage.

## Integration notes

The add-on retains Anki's browser delegate and wraps only `DataModel.data()` for FontRole and `Table._update_font()` for row height. `AnkiWebView.standard_css()` is wrapped to pin original metrics before CSS generation. Public GUI hooks handle web content, theme/profile changes, and browser initialization. All wrappers are installed once per main window.

Qt 6.11.2 can reuse a font engine's original fallback when only secondary font families change. This was reproduced using `QTextLayout.glyphRuns()`. A distinct, unsupported `UIFN` variable-axis value separates each font stack's engine cache entry without changing glyph metrics, named styles, global substitutions, or application-wide script fallback lists. The regression test checks the actual rendered font families, not only `QFont.families()`. This workaround is covered on the bundled Windows DirectWrite backend; custom GDI configurations are not validated.

Reference integration points: [Anki 26.09.4 browser model](https://github.com/ankitects/anki/blob/26.09.4/qt/aqt/browser/table/model.py), [browser table](https://github.com/ankitects/anki/blob/26.09.4/qt/aqt/browser/table/table.py), [webview](https://github.com/ankitects/anki/blob/26.09.4/qt/aqt/webview.py), and [Qt 6.11.2 font database](https://github.com/qt/qtbase/blob/v6.11.2/src/gui/text/qfontdatabase.cpp).

MIT licensed; see [LICENSE](LICENSE).
