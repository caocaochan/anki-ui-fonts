"""Anki integration. Native fonts, browser FontRole, and scoped webview hooks."""

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
import weakref

import anki.lang
from aqt import gui_hooks
from aqt.browser.table.model import DataModel
from aqt.browser.table.table import Table
from aqt.qt import QAction, QEvent, QFont, QObject, QTimer, Qt
from aqt.qt import sip
from aqt.webview import AnkiWebView

from .settings import Settings, effective_locale, load_settings
from .editor_locale import editor_locale_script
from .typography import FontResolver, explicit_font, web_css, web_script

UI_CONTEXT_MODULES = {
    "aqt.deckbrowser", "aqt.overview", "aqt.toolbar", "aqt.deckoptions",
    "aqt.preferences", "aqt.stats", "aqt.browser.card_info", "aqt.addons",
}
UI_WEBVIEW_KINDS = {
    "TOP_TOOLBAR", "BOTTOM_TOOLBAR", "DECK_OPTIONS", "LEGACY_DECK_STATS",
    "DECK_STATS", "CHANGE_NOTETYPE", "BROWSER_CARD_INFO", "IMPORT_CSV",
    "EMPTY_CARDS", "FIND_DUPLICATES", "FIELDS", "IMPORT_LOG",
    "IMPORT_ANKI_PACKAGE", "PREFERENCES",
}


def ui_context(context: object) -> bool:
    cls = type(context)
    return cls.__module__ in UI_CONTEXT_MODULES or (
        cls.__module__ == "aqt.reviewer" and cls.__name__ == "ReviewerBottomBar"
    )


def browser_editor_context(context: object) -> bool:
    from aqt.browser import Browser

    return isinstance(getattr(context, "parentWindow", None), Browser)


@dataclass
class BrowserBaseline:
    font: QFont
    row_height: int
    minimum_height: int


class FontController(QObject):
    def __init__(self, mw, module: str) -> None:
        super().__init__(mw)
        self.mw = mw
        self.module = module
        self.original_app_font = QFont(mw.app.font())
        self.resolver = FontResolver()
        self.settings, self.config_issues = load_settings(mw.addonManager.getConfig(module))
        self.web_baselines: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
        self.browser_baselines: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
        self.model_baselines: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
        self.font_cache: dict[tuple, QFont] = {}
        self._applying = False
        self._refresh_pending = False
        self.dialog = None

        # Pin webview metrics BEFORE changing QApplication's inherited font.
        for widget in mw.app.allWidgets():
            if isinstance(widget, AnkiWebView):
                self.web_baselines[widget] = explicit_font(widget.font())
        mw.app.installEventFilter(self)
        self._patch_webview_metrics()
        self._patch_browser()
        gui_hooks.browser_will_show.append(self.browser_will_show)
        gui_hooks.webview_will_set_content.append(self.webview_will_set_content)
        gui_hooks.webview_did_inject_style_into_page.append(self.style_injected)
        gui_hooks.editor_web_view_did_init.append(self.editor_webview_initialized)
        gui_hooks.editor_did_load_note.append(self.editor_note_loaded)
        gui_hooks.theme_did_change.append(self.queue_refresh)
        gui_hooks.profile_did_open.append(self.queue_refresh)
        gui_hooks.profile_will_close.append(self.close_dialog)
        gui_hooks.main_window_did_init.append(self.queue_refresh)

        self.action = QAction("UI Fonts…", mw)
        self.action.setObjectName("anki_ui_fonts_settings")
        self.action.triggered.connect(self.show_settings)
        mw.form.menuTools.addAction(self.action)
        mw.addonManager.setConfigAction(module, self.show_settings)
        mw.addonManager.setConfigUpdatedAction(module, self.config_updated)
        self.apply()

    @property
    def locale(self) -> str:
        return effective_locale(self.settings.locale, anki.lang.current_lang)

    def eventFilter(self, obj, event) -> bool:
        if not self._applying and isinstance(obj, AnkiWebView) and event.type() in (
            QEvent.Type.Polish, QEvent.Type.Show,
        ):
            self._applying = True
            try:
                self.pin_webview(obj)
            finally:
                self._applying = False
        return False

    def pin_webview(self, web) -> None:
        if web not in self.web_baselines:
            # New webviews inherit the already-customized application font.
            baseline = QFont(self.original_app_font)
            if web.testAttribute(Qt.WidgetAttribute.WA_SetFont):
                baseline = QFont(web.font())
            self.web_baselines[web] = explicit_font(baseline)
        web.setFont(self.web_baselines[web])

    def _patch_webview_metrics(self) -> None:
        original_css = AnkiWebView.standard_css

        @wraps(original_css)
        def standard_css(web):
            # stdHtml() can generate CSS BEFORE the widget is polished or shown.
            # Pin here as well, so an unopened card/editor never sees UI metrics.
            self.pin_webview(web)
            return original_css(web)

        AnkiWebView.standard_css = standard_css

    def _patch_browser(self) -> None:
        original_data = DataModel.data

        @wraps(original_data)
        def data(model, index=None, role=0):
            # Always retain Anki's original role handling (and other add-on wrappers).
            if index is None:
                result = original_data(model, role=role)
                return result
            result = original_data(model, index, role)
            if role != Qt.ItemDataRole.FontRole or not index.isValid():
                return result
            base = result if isinstance(result, QFont) else self.model_baselines.get(model, self.original_app_font)
            key = (base.toString(), tuple(base.families()), self.settings.browser, self.locale)
            if key not in self.font_cache:
                self.font_cache[key] = self.resolver.font(base, self.settings.browser, self.locale)
            return QFont(self.font_cache[key])

        DataModel.data = data
        original_update = Table._update_font

        @wraps(original_update)
        def update_font(table):
            original_update(table)
            self.update_browser(table, fresh_baseline=True)

        Table._update_font = update_font

    def browser_will_show(self, browser) -> None:
        self.update_browser(browser.table)
        self.update_editor_locale(browser.editor.web)

    def editor_webview_initialized(self, web) -> None:
        if not browser_editor_context(getattr(web, "editor", None)):
            return
        if getattr(web, "_anki_ui_fonts_locale_connected", False):
            return
        web._anki_ui_fonts_locale_connected = True
        ref = weakref.ref(web)

        def loaded(*args):
            current = ref()
            if current is not None and not sip.isdeleted(current):
                self.update_editor_locale(current)

        web.loadFinished.connect(loaded)

    def editor_note_loaded(self, editor) -> None:
        if browser_editor_context(editor):
            self.update_editor_locale(editor.web)

    def update_editor_locale(self, web) -> None:
        if getattr(getattr(web, "kind", None), "name", "") != "EDITOR":
            return
        editor = getattr(web, "editor", getattr(web, "_bridge_context", None))
        if browser_editor_context(editor):
            web.eval(editor_locale_script(self.settings.locale))

    def update_browser(self, table, fresh_baseline: bool = False) -> None:
        view = table._view
        if view is None:
            return
        header = view.verticalHeader()
        baseline = self.browser_baselines.get(view)
        if baseline is None:
            font = QFont(self.original_app_font)
            if view.testAttribute(Qt.WidgetAttribute.WA_SetFont):
                font = QFont(view.font())
            baseline = BrowserBaseline(font, header.defaultSectionSize(), header.minimumSectionSize())
            self.browser_baselines[view] = baseline
            self.model_baselines[table._model] = QFont(font)
        elif fresh_baseline:
            baseline.row_height = header.defaultSectionSize()
        view.setFont(self.resolver.font(baseline.font, self.settings.browser, self.locale))
        # Column headings are interface text, rather than browser entries.
        view.horizontalHeader().setFont(self.mw.app.font())
        measurement_font = QFont(baseline.font)
        if self.settings.browser.size is None:
            measurement_font.setPixelSize(max(1, baseline.row_height - 6))
        height = self.resolver.row_height(measurement_font, self.settings.browser, self.locale, view)
        if self.settings.browser.size is None:
            height = max(height, baseline.row_height)
        header.setMinimumSectionSize(baseline.minimum_height if self.settings.browser.size is None else 1)
        header.setDefaultSectionSize(height)
        table._model.redraw_cells()
        view.viewport().update()

    def queue_refresh(self, *args) -> None:
        if not self._refresh_pending:
            self._refresh_pending = True
            QTimer.singleShot(0, self._queued_refresh)

    def _queued_refresh(self) -> None:
        self._refresh_pending = False
        self.apply()

    def apply(self) -> None:
        if self._applying:
            return
        self._applying = True
        try:
            self.font_cache.clear()
            # Capture newly created views before propagating a new application font.
            for widget in self.mw.app.allWidgets():
                if isinstance(widget, AnkiWebView) and widget not in self.web_baselines:
                    self.web_baselines[widget] = explicit_font(self.original_app_font)
            # Explicit fonts for webviews prevent UI settings leaking into standard_css().
            for web, baseline in list(self.web_baselines.items()):
                if not sip.isdeleted(web):
                    web.setFont(baseline)
            self.mw.app.setFont(self.resolver.font(self.original_app_font, self.settings.ui, self.locale))
            for web, baseline in list(self.web_baselines.items()):
                if not sip.isdeleted(web):
                    web.setFont(baseline)
            for view in list(self.browser_baselines):
                if sip.isdeleted(view):
                    continue
                browser = view.model().parent()
                if hasattr(browser, "table"):
                    self.update_browser(browser.table)
            for web in list(self.web_baselines):
                if not sip.isdeleted(web):
                    self.update_webview(web)
        finally:
            self._applying = False

    def _web_css(self, dpi: float = 96.0) -> str:
        area = self.settings.ui
        px = area.size * dpi / 72.0 if area.size is not None else None
        return web_css(self.resolver.families(self.original_app_font, area, self.locale), px)

    def webview_will_set_content(self, content, context) -> None:
        if not ui_context(context):
            return
        script = web_script(self._web_css(self.mw.logicalDpiX()), self.settings.locale)
        # A script in the head runs after the document element exists, before paint.
        content.head += f"<script>{script}</script>"

    def supported_webview(self, web: AnkiWebView) -> bool:
        kind = getattr(getattr(web, "kind", None), "name", "")
        if kind in {"EDITOR", "PREVIEWER", "CARD_LAYOUT"}:
            return False
        if kind in UI_WEBVIEW_KINDS:
            return True
        if ui_context(getattr(web, "_bridge_context", None)):
            return True
        # The study-finished page is UI; the MAIN view is also used for actual cards.
        return kind == "MAIN" and "/congrats" in web.url().path()

    def style_injected(self, web) -> None:
        self.update_webview(web)

    def update_webview(self, web) -> None:
        if getattr(getattr(web, "kind", None), "name", "") == "EDITOR":
            self.update_editor_locale(web)
            return
        if not self.supported_webview(web):
            return
        script = web_script(self._web_css(web.logicalDpiX()), self.settings.locale)
        ref = weakref.ref(web)

        def resized(_):
            current = ref()
            if current is not None and not sip.isdeleted(current) and getattr(current.kind, "name", "") in {"TOP_TOOLBAR", "BOTTOM_TOOLBAR"}:
                current.adjustHeightToFit()

        web.evalWithCallback(script, resized)

    def save(self, settings: Settings) -> None:
        self.mw.addonManager.writeConfig(self.module, settings.to_dict())
        self.settings = settings
        self.config_issues = []
        self.apply()

    def config_updated(self, raw) -> None:
        self.settings, self.config_issues = load_settings(raw)
        self.apply()

    def show_settings(self, *args) -> None:
        from .dialog import SettingsDialog

        if self.dialog is None:
            self.resolver.refresh()
            self.dialog = SettingsDialog(self)
            self.dialog.finished.connect(self._dialog_finished)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def _dialog_finished(self, *args) -> None:
        if self.dialog is not None:
            self.dialog.deleteLater()
            self.dialog = None

    def close_dialog(self) -> None:
        if self.dialog is not None:
            self.dialog.reject()


def install(module: str):
    import aqt

    mw = aqt.mw
    if mw is None:
        return None
    if not hasattr(mw, "_anki_ui_fonts_controller"):
        mw._anki_ui_fonts_controller = FontController(mw, module)
    return mw._anki_ui_fonts_controller
