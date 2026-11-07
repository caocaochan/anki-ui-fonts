"""Settings UI. Previews never change the saved/application settings."""

from __future__ import annotations

from aqt.qt import (
    QAbstractItemView, QCheckBox, QComboBox, QCompleter, QDialog,
    QDialogButtonBox, QDoubleSpinBox, QFont, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QScrollArea,
    QTableWidget, QTableWidgetItem, Qt, QVBoxLayout, QWidget,
)

from .settings import AreaSettings, LOCALES, Settings, effective_locale
from .typography import SAMPLE


class FontPicker(QComboBox):
    def __init__(self, families: list[str], cjk: bool, parent=None) -> None:
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setMinimumContentsLength(22)
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.addItem("Anki default", "")
        if cjk:
            self.addItem("Automatic (from rendering locale)", "auto")
        for family in families:
            self.addItem(family, family)
        self.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def set_value(self, value: str) -> None:
        index = self.findData(value)
        if index >= 0:
            self.setCurrentIndex(index)
        else:
            self.setEditText(value)

    def value(self) -> str:
        text = self.currentText().strip()
        index = self.findText(text, Qt.MatchFlag.MatchFixedString)
        return str(self.itemData(index)) if index >= 0 else text


class AreaPanel(QGroupBox):
    def __init__(self, title: str, resolver, base: QFont, browser: bool, parent=None) -> None:
        super().__init__(title, parent)
        self.resolver = resolver
        self.base = QFont(base)
        self.browser = browser
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.latin = FontPicker(resolver.installed, False, self)
        self.cjk = FontPicker(resolver.installed, True, self)
        self.size_default = QCheckBox("Anki default", self)
        self.size = QDoubleSpinBox(self)
        self.size.setRange(6, 48)
        self.size.setDecimals(1)
        self.size.setSingleStep(0.5)
        self.size.setSuffix(" pt")
        sizes = QHBoxLayout()
        sizes.addWidget(self.size_default)
        sizes.addWidget(self.size)
        sizes.addStretch()
        form.addRow("&Latin font:", self.latin)
        form.addRow("&CJK font:", self.cjk)
        form.addRow("Size (both fonts):", sizes)
        layout.addLayout(form)
        self.notice = QLabel(self)
        self.notice.setWordWrap(True)
        self.notice.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.notice)
        if browser:
            self.preview = QTableWidget(2, 2, self)
            self.preview.setHorizontalHeaderLabels(["Browser entries preview", "Example"])
            self.preview.setItem(0, 0, QTableWidgetItem(SAMPLE))
            self.preview.setItem(0, 1, QTableWidgetItem("2026-11-07"))
            self.preview.setItem(1, 0, QTableWidgetItem("骨 直 令 遍 返 — 汉字 / 漢字 — English"))
            self.preview.setItem(1, 1, QTableWidgetItem("12345"))
            self.preview.setColumnWidth(0, 565)
            self.preview.setColumnWidth(1, 120)
            self.preview.setWordWrap(False)
            self.preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            self.preview.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            self.preview.verticalHeader().hide()
            self.preview.setMinimumHeight(65)
            self.preview.setMaximumHeight(90)
        else:
            self.preview = QPlainTextEdit(SAMPLE, self)
            self.preview.setReadOnly(True)
            self.preview.setMinimumHeight(50)
            self.preview.setMaximumHeight(80)
        layout.addWidget(self.preview)
        self.size_default.toggled.connect(lambda checked: self.size.setEnabled(not checked))

    def set_value(self, value: AreaSettings) -> None:
        self.latin.set_value(value.latin)
        self.cjk.set_value(value.cjk)
        default_size = self.base.pointSizeF()
        if default_size <= 0:
            default_size = self.base.pixelSize() * 72 / 96
        self.size.setValue(value.size if value.size is not None else max(6, default_size))
        self.size_default.setChecked(value.size is None)
        self.size.setEnabled(value.size is not None)

    def value(self) -> AreaSettings:
        return AreaSettings(self.latin.value(), self.cjk.value(), None if self.size_default.isChecked() else self.size.value())

    def refresh_preview(self, locale: str) -> None:
        value = self.value()
        font = self.resolver.font(self.base, value, locale)
        self.preview.setFont(font)
        if self.browser:
            self.preview.verticalHeader().setMinimumSectionSize(1)
            self.preview.verticalHeader().setDefaultSectionSize(self.resolver.row_height(self.base, value, locale, self.preview))
        notices = self.resolver.notices(self.base, value, locale)
        cjk = self.resolver.families(self.base, value, locale)
        self.notice.setText("Font stack: " + " → ".join(cjk) + ("\n" + "\n".join(notices) if notices else ""))


class SettingsDialog(QDialog):
    silentlyClose = True

    def __init__(self, controller) -> None:
        super().__init__(controller.mw)
        self.controller = controller
        self.setWindowTitle("UI Fonts")
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.resize(850, 850)
        outer = QVBoxLayout(self)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content = QWidget(scroll)
        layout = QVBoxLayout(content)
        intro = QLabel("Set interface and browser-entry fonts independently. Card content and note fields keep their existing formatting.", content)
        intro.setWordWrap(True)
        layout.addWidget(intro)
        locale_form = QFormLayout()
        self.locale = QComboBox(content)
        for tag, label in LOCALES:
            self.locale.addItem(label, tag)
        locale_form.addRow("&Rendering locale:", self.locale)
        layout.addLayout(locale_form)
        hint = QLabel("The locale selects regional Han glyphs and the automatic CJK font. It does not translate Anki. Untagged Chinese and Japanese Han characters share this one regional preference.", content)
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.issues = QLabel("\n".join(controller.config_issues), content)
        self.issues.setWordWrap(True)
        self.issues.setTextFormat(Qt.TextFormat.PlainText)
        self.issues.setVisible(bool(controller.config_issues))
        layout.addWidget(self.issues)
        self.ui = AreaPanel("General UI", controller.resolver, controller.original_app_font, False, content)
        browser_base = QFont(controller.original_app_font)
        browser_base.setFamily("Arial")
        browser_base.setPixelSize(12)
        self.browser = AreaPanel("Browser entries", controller.resolver, browser_base, True, content)
        layout.addWidget(self.ui)
        layout.addWidget(self.browser)
        note = QLabel("Fonts use Latin-first fallback. A Latin font that already contains CJK glyphs takes priority. “Anki default” size in the browser preserves per-template browser sizes; the preview uses a 12 px sample.", content)
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.RestoreDefaults,
            parent=self,
        )
        outer.addWidget(self.buttons)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply)
        self.buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(lambda: self.set_value(Settings()))
        self._loading = False
        self.locale.currentIndexChanged.connect(self.refresh_previews)
        for panel in (self.ui, self.browser):
            panel.latin.currentTextChanged.connect(self.refresh_previews)
            panel.cjk.currentTextChanged.connect(self.refresh_previews)
            panel.size.valueChanged.connect(self.refresh_previews)
            panel.size_default.toggled.connect(self.refresh_previews)
        self.set_value(controller.settings)
        # Avoid opening partly off-screen on a scaled or small display.
        if self.screen() is not None:
            available = self.screen().availableGeometry()
            self.resize(min(850, available.width() - 60), min(850, available.height() - 80))

    def set_value(self, value: Settings) -> None:
        self._loading = True
        self.locale.setCurrentIndex(self.locale.findData(value.locale))
        self.ui.set_value(value.ui)
        self.browser.set_value(value.browser)
        self._loading = False
        self.refresh_previews()

    def value(self) -> Settings:
        return Settings(locale=str(self.locale.currentData()), ui=self.ui.value(), browser=self.browser.value())

    def refresh_previews(self, *args) -> None:
        if self._loading:
            return
        import anki.lang

        locale = effective_locale(str(self.locale.currentData()), anki.lang.current_lang)
        self.ui.refresh_preview(locale)
        self.browser.refresh_preview(locale)

    def apply(self) -> bool:
        # A searchable picker may contain a name that isn't installed. Reject only
        # newly entered invalid names; persisted missing fonts can be kept/replaced.
        values = self.value()
        old = self.controller.settings
        available = {name.casefold() for name in self.controller.resolver.installed}
        for area_name in ("ui", "browser"):
            area, previous = getattr(values, area_name), getattr(old, area_name)
            for name in ("latin", "cjk"):
                value = getattr(area, name)
                if value not in ("", "auto") and value.casefold() not in available and value != getattr(previous, name):
                    QMessageBox.warning(self, "Font not installed", f'Choose an installed font instead of "{value}".')
                    return False
        try:
            self.controller.save(values)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Could not save UI Fonts", str(error))
            return False
        self.issues.hide()
        return True

    def accept(self) -> None:
        if self.apply():
            super().accept()
