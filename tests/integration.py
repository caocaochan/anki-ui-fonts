"""Assumes Anki 26.09.4 packages are importable; uses ONLY project-local profiles.

Run after build.py. --inspect leaves the tested UI open until .test-output/stop
exists. This uses Anki's own installer, collection, browser, editor, and webviews.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import importlib
import json
import os
from pathlib import Path
import sys
import time
import traceback
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ADDON_VERSION = json.loads((ROOT / "ui_fonts" / "manifest.json").read_text(encoding="utf-8"))["human_version"]
ARTIFACT = ROOT / "dist" / f"anki-ui-fonts-{ADDON_VERSION}.ankiaddon"
OUTPUT = ROOT / ".test-output"
OUTPUT.mkdir(exist_ok=True)
parser = argparse.ArgumentParser()
parser.add_argument("--inspect", action="store_true")
parser.add_argument("--restart", action="store_true")
parser.add_argument("--profile", default=".test-profile")
parser.add_argument("--scale-factor", type=float)
parser.add_argument("--new-editor", action="store_true")
args = parser.parse_args()
if args.inspect:
    (OUTPUT / "stop").unlink(missing_ok=True)
os.environ["ANKI_SINGLE_INSTANCE_KEY"] = "anki-ui-font-tests-" + str(uuid.uuid4())
os.environ["ANKI_NOSYNC"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True
if args.scale_factor is not None:
    os.environ["QT_SCALE_FACTOR"] = str(args.scale_factor)

import aqt
import aqt.sound
import anki.lang
from anki.buildinfo import version
from aqt.profiles import ProfileManager
from aqt.qt import QApplication, QFont, QTimer, Qt

assert version == "26.09.4", version
# The standalone Python harness has no bundled mpv executable. Audio is outside
# typography coverage; avoid spawning/failing a player when switching profiles.
aqt.sound.setup_audio = lambda *args, **kwargs: None
aqt.sound.cleanup_audio = lambda *args, **kwargs: None
base = (ROOT / args.profile).resolve()
if base.parent != ROOT or not base.name.startswith(".test-profile"):
    raise ValueError("Test profiles must be project-local .test-profile* folders")
base.mkdir(exist_ok=True)
# Stage the current artifact before startup so iterative test runs never import
# yesterday's installed code before the installer replaces it.
if (base / "addons21" / "anki_ui_fonts").exists():
    with zipfile.ZipFile(ARTIFACT) as archive:
        archive.extractall(base / "addons21" / "anki_ui_fonts")
anki.lang.set_lang("en")
pm = ProfileManager(base)
pm.setupMeta()
pm.create("Font Tests")
pm.load("Font Tests")
pm.meta.update(defaultLang="en", firstRun=False, updates=False)
pm.profile.update(autoSync=False, syncKey=None, numBackups=0)
pm.set_check_for_addon_updates(False)
pm.save()
pm.db.close()

checks = []


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    checks.append(message)
    print("PASS", message, flush=True)


def wait_until(predicate, seconds=20):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QApplication.processEvents()
        if predicate():
            return
        time.sleep(0.01)
    raise TimeoutError("Timed out waiting for " + str(predicate))


def web_eval(web, script):
    result = []
    web.evalWithCallback(script, lambda value: result.append(value))
    wait_until(lambda: bool(result))
    return result[0]


def drain_collection_queue():
    # A collection-queue barrier plus processing its main-thread completions.
    for _ in range(2):
        done = []
        mw.taskman.run_in_background(lambda: None, lambda future: done.append(True))
        wait_until(lambda: bool(done))


app = aqt._run(["anki-ui-font-tests", "-b", str(base), "-p", "Font Tests", "-l", "en"], exec=False)
assert app is not None
mw = aqt.mw
assert Path(mw.pm.base).resolve() == base.resolve()


def tests():
    try:
        wait_until(lambda: mw.col is not None and mw.state == "deckBrowser" and mw.web._domDone)
        artifact = ARTIFACT
        if not args.restart:
            from aqt.addons import InstallOk

            installed = mw.addonManager.install(str(artifact))
            check(isinstance(installed, InstallOk) and installed.compatible, "Anki's installer accepts the .ankiaddon manifest and package")
            mw.addonManager.loadAddons()
        addon = importlib.import_module("anki_ui_fonts")
        from anki_ui_fonts.settings import AreaSettings, Settings
        from anki_ui_fonts.controller import ui_context
        from aqt.browser import Browser
        from aqt.browser.table import SearchContext
        from aqt.theme import Theme, theme_manager

        controller = mw._anki_ui_fonts_controller
        check(controller.module == "anki_ui_fonts", "Packaged add-on loads under its installed module name")
        check(addon.initialize() is controller, "Initialization is idempotent")
        check(sum(action.objectName() == "anki_ui_fonts_settings" for action in mw.form.menuTools.actions()) == 1, "Exactly one Tools → UI Fonts entry exists")
        check(mw.addonManager._configButtonActions[controller.module] == controller.show_settings, "Add-ons Config opens the same settings dialog")
        if args.restart:
            check(controller.settings.ui.size == 11.5 and controller.settings.browser.size == 18, "Saved fonts and sizes survive a complete Anki restart")

        controller.save(Settings())
        col = mw.col
        model = col.models.by_name("Basic")
        if not col.find_notes('tag:ui_font_test'):
            for number in range(120):
                note = col.new_note(model)
                note["Front"] = f"English {number:03} 简体中文 骨直令遍返 日本語 かな カナ 한국어 🙂"
                note["Back"] = '<span lang="ja" style="font-family: Times New Roman; font-size: 27px;">Card text 骨直令</span>'
                note.tags = ["ui_font_test"] + (["marked"] if number == 0 else [])
                col.add_note(note, col.decks.id("Font Tests 简体中文 骨直令"))
        # Exercise template-specific browser fonts and sizes.
        model = col.models.by_name("Basic")
        model["tmpls"][0]["bfont"] = "Times New Roman"
        model["tmpls"][0]["bsize"] = 31
        col.models.save(model)
        ids = col.find_cards("tag:ui_font_test")
        col.sched.suspend_cards([ids[-1]])
        from anki.collection import ExperimentFlag
        col._experiments[str(ExperimentFlag.SVELTE_EDITOR)] = args.new_editor
        browser = aqt.dialogs.open("Browser", mw, search=("tag:ui_font_test",))
        wait_until(lambda: browser.table._model.rowCount() == len(ids) and browser.editor.web._domDone and getattr(browser.editor, "_ready", True))
        wait_until(lambda: web_eval(browser.editor.web, "typeof saveNow === 'function'"))
        drain_collection_queue()
        view = browser.table._view
        data_model = browser.table._model
        original_delegate = view.itemDelegate()
        original_editor_font = QFont(browser.editor.web.font())
        original_main_font = QFont(mw.web.font())
        col_before = col.get_note(col.get_card(ids[0]).nid).fields[:]
        template_before = col.models.by_name("Basic")["tmpls"]
        language_before = anki.lang.current_lang
        from aqt.qt import QLocale
        qt_locale_before = QLocale().name()

        # Both modes must use configured fonts, including cells that normally have no FontRole.
        custom = Settings(locale="zh-Hans", ui=AreaSettings("Segoe UI", "auto", 11.5), browser=AreaSettings("Arial", "auto", 18))
        controller.save(custom)
        wait_until(lambda: app.font().pointSizeF() == 11.5)
        for notes_mode in (False, True):
            if browser.table.is_notes_mode() != notes_mode:
                browser.on_table_state_changed(notes_mode)
                wait_until(lambda: browser.table.is_notes_mode() == notes_mode)
                drain_collection_queue()
            for column in range(data_model.columnCount()):
                font = data_model.data(data_model.index(0, column), Qt.ItemDataRole.FontRole)
                check(font.pointSizeF() == 18 and font.families()[:2] == ["Arial", "Noto Sans SC"], f"{'Notes' if notes_mode else 'Cards'} column {column} uses the independent browser font")
        check(view.itemDelegate() is original_delegate, "Anki's original status/selection delegate is retained")
        check(view.verticalHeader().defaultSectionSize() >= 30, "Browser row height accommodates configured CJK fonts")
        check(app.font().pointSizeF() == 11.5 and app.font().families()[:2] == ["Segoe UI", "Noto Sans SC"], "General UI uses its independent font stack and size")
        check(browser.editor.web.font() == original_editor_font and mw.web.font() == original_main_font, "Native webview font metrics are unchanged")

        mw.deckBrowser.refresh()
        wait_until(lambda: mw.web._domDone)
        check(web_eval(mw.web, "document.documentElement.lang") == "zh-Hans", "Deck list receives the rendering locale")
        check("Segoe UI" in web_eval(mw.web, "getComputedStyle(document.body).fontFamily"), "Deck list receives the configured UI font")
        check(abs(float(web_eval(mw.web, "parseFloat(getComputedStyle(document.body).fontSize)")) - 11.5 * mw.web.logicalDpiX() / 72) < 0.05, "Web UI font size matches the configured point size")
        check(web_eval(browser.editor.web, "document.getElementById('anki-ui-fonts') === null"), "Note editor DOM is excluded")
        check(not controller.supported_webview(browser.editor.web), "Editor remains outside web styling coverage")
        editor_web = browser.editor.web
        field_locales = "Array.from(document.querySelectorAll('.editing-area')).map(element => element.getAttribute('lang'))"
        field_snapshot = """Array.from(document.querySelectorAll('.rich-text-editable')).map(host => {
            const field = host.shadowRoot && host.shadowRoot.querySelector('anki-editable');
            if (!field) return null;
            const style = getComputedStyle(field);
            return {html: field.innerHTML, family: style.fontFamily, size: style.fontSize};
        })"""
        wait_until(lambda: web_eval(editor_web, "document.querySelectorAll('.editing-area').length > 0"))
        check(all(value == "zh-Hans" for value in web_eval(editor_web, field_locales)), "Browser note fields inherit the rendering locale by default")
        check(web_eval(editor_web, "document.querySelector('.rich-text-editable').shadowRoot.querySelector('anki-editable').matches(':lang(zh-Hans)')"), "Rendering language reaches the real rich-text shadow DOM")
        original_fields = web_eval(editor_web, field_snapshot)
        controller.save(replace(custom, locale="ja"))
        check(all(value == "ja" for value in web_eval(editor_web, field_locales)), "Browser note fields follow live changes to the main locale")
        check(web_eval(mw.web, "document.documentElement.lang") == "ja", "Editor and UI share the same locale setting")
        check(web_eval(editor_web, field_snapshot) == original_fields, "Changing editor locale preserves field HTML, font family, and font size")
        check(web_eval(editor_web, "document.querySelectorAll('.rich-text-editable')[1].shadowRoot.querySelector('[lang=ja]').matches(':lang(ja)')"), "Explicit language tags in note content remain intact")
        controller.save(replace(custom, locale=""))
        check(all(value is None for value in web_eval(editor_web, field_locales)), "Anki default restores original field-wrapper language attributes")
        check(web_eval(editor_web, "typeof window.__ankiUiFontsEditorLocale === 'undefined'"), "Disabling the editor override disconnects its observer")
        controller.save(custom)
        web_eval(editor_web, """(() => {
            const wrapper = document.createElement('div');
            wrapper.className = 'editing-area'; wrapper.id = 'locale-test-wrapper';
            wrapper.lang = 'ko'; document.body.appendChild(wrapper);
        })()""")
        wait_until(lambda: web_eval(editor_web, "document.getElementById('locale-test-wrapper').lang") == "zh-Hans")
        check(True, "Newly mounted field wrappers receive the locale automatically")
        controller.save(replace(custom, locale=""))
        check(web_eval(editor_web, "document.getElementById('locale-test-wrapper').lang") == "ko", "Original nonempty wrapper language is restored")
        web_eval(editor_web, "document.getElementById('locale-test-wrapper').remove()")
        controller.save(replace(custom, locale="ko"))
        previous_card = browser.table.get_current_card().id
        browser.onNextCard()
        wait_until(lambda: browser.table.get_current_card().id != previous_card)
        drain_collection_queue()
        wait_until(lambda: all(value == "ko" for value in web_eval(editor_web, field_locales)))
        check(True, "Changing browser notes retains the selected editor locale")
        from aqt import gui_hooks
        controller.save(replace(custom, locale="ja"))
        add_cards = aqt.dialogs.open("AddCards", mw)
        wait_until(lambda: add_cards.editor.web._domDone and getattr(add_cards.editor, "_ready", True))
        wait_until(lambda: web_eval(add_cards.editor.web, "typeof saveNow === 'function'"))
        check(web_eval(add_cards.editor.web, "typeof window.__ankiUiFontsEditorLocale === 'undefined'"), "Add Notes editor is outside the browser-only locale override")
        add_cards.close()
        drain_collection_queue()
        controller.save(custom)
        from aqt.webview import AnkiWebView, AnkiWebViewKind
        early_web = AnkiWebView(mw, kind=AnkiWebViewKind.PREVIEWER)
        early_css = early_web.standard_css()
        check(early_web.font().pointSizeF() == controller.original_app_font.pointSizeF(), "New webview metrics are pinned before standard CSS is generated")
        early_web.cleanup()
        early_web.deleteLater()

        selected_before = list(browser.table.get_selected_card_ids())
        rows_before = data_model.rowCount()
        controller.save(replace(custom, browser=replace(custom.browser, size=48)))
        check(view.verticalHeader().defaultSectionSize() >= 65, "48 pt browser entries have a sufficiently tall row")
        check(rows_before == data_model.rowCount() and selected_before == list(browser.table.get_selected_card_ids()), "Applying fonts preserves browser results and selection")

        controller.save(replace(custom, locale="ja"))
        check(data_model.data(data_model.index(0, 0), Qt.ItemDataRole.FontRole).families()[1] == "Noto Sans JP", "Japanese locale resolves to the Japanese regional font")
        wait_until(lambda: web_eval(mw.web, "document.documentElement.lang") == "ja")
        check(web_eval(mw.web, "document.querySelectorAll('#anki-ui-fonts').length") == 1, "Live changes replace one style element rather than accumulating styles")
        controller.save(replace(custom, locale=""))
        check(web_eval(mw.web, "document.documentElement.getAttribute('lang')") is None, "Anki default restores the original missing language attribute")

        # Open a new webview after changing the application font.
        from aqt.browser.previewer import BrowserPreviewer
        browser.onTogglePreview()
        wait_until(lambda: browser._previewer is not None and browser._previewer._web is not None and browser._previewer._web._domDone)
        previewer = browser._previewer
        check(previewer._web.font().pointSizeF() == original_main_font.pointSizeF(), "New card-preview webviews retain baseline font metrics")
        check(web_eval(previewer._web, "document.getElementById('anki-ui-fonts') === null"), "Card preview DOM is excluded")
        previewer.close()

        controller.save(custom)
        controller.show_settings()
        dialog = controller.dialog
        dialog.ui.size_default.setChecked(False)
        dialog.ui.size.setValue(20)
        dialog.locale.setCurrentIndex(dialog.locale.findData("ko"))
        check(controller.settings.ui.size == 11.5 and app.font().pointSizeF() == 11.5, "Preview edits do not apply or persist until requested")
        dialog.reject()
        check(controller.settings == custom, "Cancel discards unapplied changes")
        controller.show_settings()
        dialog = controller.dialog
        dialog.ui.size.setValue(12)
        dialog.locale.setCurrentIndex(dialog.locale.findData("ja"))
        check(dialog.apply(), "Apply persists a draft without closing the settings dialog")
        check(all(value == "ja" for value in web_eval(editor_web, field_locales)), "Settings dialog Apply updates browser field locale")
        check(mw.addonManager.getConfig(controller.module)["ui"]["size"] == 12, "Settings persist through Anki's configuration API")
        dialog.ui.size.setValue(15)
        dialog.reject()
        check(controller.settings.ui.size == 12, "Cancel after Apply retains the last applied settings")
        controller.show_settings()
        dialog = controller.dialog
        dialog.set_value(Settings())
        check(controller.settings.ui.size == 12, "Restore Defaults remains a draft until applied")
        check(dialog.apply(), "Restoring defaults applies successfully")
        check(app.font().pointSizeF() == controller.original_app_font.pointSizeF(), "Anki default restores the original native UI size")
        dialog.reject()
        default_font = data_model.data(data_model.index(0, 0), Qt.ItemDataRole.FontRole)
        check(default_font.pixelSize() == 31 and default_font.families()[0] == "Times New Roman", "Browser Anki default restores per-template font and pixel size")

        controller.config_updated({"locale": "invalid", "ui": {"size": -1, "latin": "Missing Font"}})
        check(controller.settings.ui.size is None and bool(controller.config_issues), "Invalid and missing-font configuration recovers safely")
        controller.save(custom)
        mw.pm.set_theme(Theme.DARK)
        theme_manager.apply_style()
        QApplication.processEvents()
        check(app.font().pointSizeF() == 11.5, "UI typography survives a theme change")
        mw.pm.set_theme(Theme.LIGHT)
        theme_manager.apply_style()
        QApplication.processEvents()

        # The review screen reuses MAIN. Switching must not style the card DOM.
        mw.col.decks.select(col.get_card(ids[0]).did)
        mw.moveToState("review")
        wait_until(lambda: mw.web._domDone and mw.reviewer.card is not None)
        check(not controller.supported_webview(mw.web), "MAIN reviewer webview is excluded by context")
        check(web_eval(mw.web, "document.getElementById('anki-ui-fonts') === null"), "Reviewer card DOM receives no UI stylesheet")
        controller.save(replace(custom, ui=replace(custom.ui, size=14)))
        check(web_eval(mw.web, "document.getElementById('anki-ui-fonts') === null"), "Live UI Apply leaves an already-open reviewer card unchanged")
        mw.moveToState("deckBrowser")
        controller.save(custom)
        check(anki.lang.current_lang == language_before and QLocale().name() == qt_locale_before, "Rendering locale does not alter translations or Qt date/number locale")
        fields_after = col.get_note(col.get_card(ids[0]).nid).fields
        templates_after = col.models.by_name("Basic")["tmpls"]
        if fields_after != col_before or templates_after != template_before:
            print("CONTENT BEFORE/AFTER", repr(col_before), repr(fields_after), repr(template_before), repr(templates_after), flush=True)
        check(fields_after == col_before and templates_after == template_before, "Settings do not modify note fields or card templates")
        # Switch through real collections/profiles, exercising window destruction.
        def switch_profile(name):
            switched = []

            def opened():
                mw.pm.load(name)
                mw.pm.profile.update(autoSync=False, syncKey=None, numBackups=0)
                mw.pm.save()
                mw.loadProfile()
                switched.append(True)

            mw.unloadProfile(opened)
            wait_until(lambda: bool(switched) and mw.col is not None and mw.state == "deckBrowser")
            QApplication.processEvents()

        mw.pm.create("Font Tests Second")
        switch_profile("Font Tests Second")
        check(controller.settings == custom and app.font().pointSizeF() == 11.5, "Switching to another real profile preserves shared typography settings")
        switch_profile("Font Tests")
        check(controller.settings == custom and app.font().pointSizeF() == 11.5, "Returning to the original profile reapplies shared typography settings")
        mw.col._experiments[str(ExperimentFlag.SVELTE_EDITOR)] = args.new_editor
        browser = aqt.dialogs.open("Browser", mw, search=("tag:ui_font_test",))
        wait_until(lambda: getattr(browser.editor, "_ready", True) and browser.editor.web._domDone)
        wait_until(lambda: web_eval(browser.editor.web, "typeof saveNow === 'function'"))
        drain_collection_queue()
        result = {"version": version, "checks": checks, "success": True, "device_pixel_ratio": mw.devicePixelRatioF(), "logical_dpi": mw.logicalDpiX(), "editor": type(browser.editor).__name__}
        (OUTPUT / "integration.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        controller.show_settings()
        if args.inspect:
            (OUTPUT / "inspect-ready").write_text("ready", encoding="utf-8")
            timer = QTimer(mw)
            timer.timeout.connect(lambda: finish() if (OUTPUT / "stop").exists() else None)
            timer.start(300)
            mw._font_test_timer = timer
        else:
            QTimer.singleShot(250, finish)
    except BaseException:
        (OUTPUT / "integration.json").write_text(json.dumps({"version": version, "checks": checks, "success": False, "error": traceback.format_exc()}, indent=2), encoding="utf-8")
        traceback.print_exc()
        app.exit(1)


def finish():
    # Use Anki's normal ordered cleanup (webengine pages, server, collection).
    controller = getattr(mw, "_anki_ui_fonts_controller", None)
    if controller is not None:
        controller.close_dialog()
    drain_collection_queue()
    mw.unloadProfileAndExit()


QTimer.singleShot(100, tests)
QTimer.singleShot(600000 if args.inspect else 120000, lambda: app.exit(2))
sys.exit(app.exec())
