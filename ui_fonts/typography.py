"""Font stacks shared by native Qt rendering and webview styles."""

from __future__ import annotations

import json
import math

from aqt.qt import QFont, QFontDatabase, QFontMetricsF, QRawFont

from .settings import AreaSettings, resolve_cjk

SAMPLE = "English ABC abc 0123 — 简体中文 骨直令遍 — 繁體中文 — 日本語 かな カナ — 한국어 — ، العربية 🙂"


def explicit_font(base: QFont) -> QFont:
    """QWidget.setFont resolves unset attributes against its parent/application.

    A copied default QFont has no size/family resolve bits. Set those attributes
    explicitly so a later QApplication.setFont cannot change a pinned webview.
    """
    font = QFont(base)
    font.setFamilies(base.families())
    if base.pixelSize() > 0:
        font.setPixelSize(base.pixelSize())
    else:
        font.setPointSizeF(base.pointSizeF())
    # Empty axes must also be explicit, rather than inherited from app.font().
    axes = [(tag, base.variableAxisValue(tag)) for tag in base.variableAxisTags()]
    font.clearVariableAxes()
    for tag, value in axes:
        font.setVariableAxis(tag, value)
    return font


class FontResolver:
    def __init__(self) -> None:
        self._stack_ids: dict[tuple[str, ...], int] = {}
        self.refresh()

    def refresh(self) -> None:
        self.installed = list(QFontDatabase.families())
        self._names = {name.casefold(): name for name in self.installed}

    def families(self, base: QFont, area: AreaSettings, locale: str) -> list[str]:
        latin = self._names.get(area.latin.casefold(), "") if area.latin else ""
        families = [latin] if latin else base.families()
        cjk, _ = resolve_cjk(area.cjk, locale, self.installed)
        if cjk:
            families.append(cjk)
        return list(dict.fromkeys(families))

    def font(self, base: QFont, area: AreaSettings, locale: str) -> QFont:
        font = explicit_font(base)
        families = self.families(base, area, locale)
        font.setFamilies(families)
        if len(families) > 1:
            # Qt 6.11.2's font-engine cache omits fallback families at one cache
            # level. Two stacks with the same Latin font/size can therefore draw
            # with the FIRST stack's CJK font, even in separate widgets.
            # An unsupported custom variable axis is visually inert, but is part
            # of the engine cache key. Salt per stack, without changing metrics,
            # style names, or the application's global fallback configuration.
            key = tuple(families)
            if key not in self._stack_ids:
                self._stack_ids[key] = len(self._stack_ids) + 1
            font.setVariableAxis(QFont.Tag.fromString("UIFN"), float(self._stack_ids[key]))
        if area.size is not None:
            font.setPointSizeF(area.size)
        return font

    def notices(self, base: QFont, area: AreaSettings, locale: str) -> list[str]:
        notices: list[str] = []
        if area.latin and area.latin.casefold() not in self._names:
            notices.append(f'Latin font "{area.latin}" is not installed; using Anki default.')
        cjk, notice = resolve_cjk(area.cjk, locale, self.installed)
        if notice:
            notices.append(notice)
        if cjk:
            latin = QFont(base)
            latin.setFamilies([self.families(base, area, locale)[0]])
            raw = QRawFont.fromFont(latin)
            if raw.isValid() and any(raw.supportsCharacter(ord(c)) for c in "骨直汉漢"):
                notices.append("The Latin font contains Han glyphs. Those glyphs take priority over the CJK fallback; choose a Latin font without Han coverage for a reliable split.")
        return notices

    def row_height(self, base: QFont, area: AreaSettings, locale: str, device=None) -> int:
        font = self.font(base, area, locale)
        metrics = QFontMetricsF(font, device)
        heights = [metrics.height(), metrics.boundingRect(SAMPLE).height()]
        for family in self.families(base, area, locale):
            candidate = QFont(font)
            candidate.setFamilies([family])
            heights.append(QFontMetricsF(candidate, device).height())
        return math.ceil(max(heights)) + 6


def css_quote(value: str) -> str:
    """A CSS string, including protection against closing an HTML style tag."""
    return '"' + "".join(f"\\{ord(c):x} " if c in '\\"<>\n\r\f' else c for c in value) + '"'


def web_css(families: list[str], size_px: float | None) -> str:
    stack = ", ".join(css_quote(name) for name in families) + ", sans-serif"
    css = f"""
html, body {{ font-family: {stack} !important; }}
:root {{ --bs-body-font-family: {stack}; --font-family: {stack}; }}
button, input, select, textarea {{ font-family: {stack} !important; }}
"""
    if size_px is not None:
        size = f"{size_px:.4f}px"
        css += f"""
html, body {{ font-size: {size} !important; }}
:root, :root.system-font-size, :root.night-mode.system-font-size {{
  --bs-body-font-size: {size}; --font-size: {size}; font-size: {size} !important;
}}
button, input, select, textarea {{ font-size: inherit; }}
"""
    return css


def web_script(css: str, locale: str) -> str:
    # JSON escapes prevent font names and config values becoming executable code.
    payload = json.dumps({"css": css, "locale": locale}, ensure_ascii=True).replace("<", "\\u003c")
    return """(() => {
const value = PAYLOAD;
const root = document.documentElement;
if (!root || !document.head) return;
let style = document.getElementById('anki-ui-fonts');
if (!style) {
    style = document.createElement('style');
    style.id = 'anki-ui-fonts';
    document.head.appendChild(style);
}
style.textContent = value.css;
if (!Object.prototype.hasOwnProperty.call(window, '__ankiUiFontsOriginalLang'))
    window.__ankiUiFontsOriginalLang = root.getAttribute('lang');
if (value.locale) root.setAttribute('lang', value.locale);
else if (window.__ankiUiFontsOriginalLang === null) root.removeAttribute('lang');
else root.setAttribute('lang', window.__ankiUiFontsOriginalLang);
})();""".replace("PAYLOAD", payload)
