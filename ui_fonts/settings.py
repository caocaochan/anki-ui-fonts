"""Qt-independent validation for persisted settings."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
from typing import Any

LOCALES = (
    ("", "Anki default"),
    ("zh-Hans", "Simplified Chinese — zh-Hans"),
    ("zh-Hant-TW", "Traditional Chinese (Taiwan) — zh-Hant-TW"),
    ("zh-Hant-HK", "Traditional Chinese (Hong Kong) — zh-Hant-HK"),
    ("ja", "Japanese — ja"),
    ("ko", "Korean — ko"),
)

REGIONAL_FONTS = {
    "zh-Hans": ("Noto Sans SC", "Noto Sans CJK SC", "Microsoft YaHei UI", "Microsoft YaHei"),
    "zh-Hant-TW": ("Noto Sans TC", "Noto Sans CJK TC", "Microsoft JhengHei UI", "Microsoft JhengHei"),
    "zh-Hant-HK": ("Noto Sans HK", "Noto Sans CJK HK", "Microsoft JhengHei UI", "Microsoft JhengHei"),
    "ja": ("Noto Sans JP", "Noto Sans CJK JP", "Yu Gothic UI", "Meiryo", "MS UI Gothic"),
    "ko": ("Noto Sans KR", "Noto Sans CJK KR", "Malgun Gothic"),
}


@dataclass(frozen=True)
class AreaSettings:
    latin: str = ""  # Anki's original family
    cjk: str = "auto"  # regional font, or "" for Anki's original fallback
    size: float | None = None  # points, or Anki default


@dataclass(frozen=True)
class Settings:
    version: int = 1
    locale: str = "zh-Hans"
    ui: AreaSettings = field(default_factory=AreaSettings)
    browser: AreaSettings = field(default_factory=AreaSettings)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_settings(raw: Any) -> tuple[Settings, list[str]]:
    """Recover individual invalid values; never discard a valid neighboring value."""
    issues: list[str] = []
    if not isinstance(raw, dict):
        return Settings(), ["Invalid configuration; using defaults."]
    if raw.get("version", 1) != 1:
        issues.append("Unrecognized configuration version; reading supported settings.")
    locale = raw.get("locale", "zh-Hans")
    if not isinstance(locale, str) or locale not in dict(LOCALES):
        locale = "zh-Hans"
        issues.append("Invalid rendering locale; using zh-Hans.")

    def area(key: str) -> AreaSettings:
        values = raw.get(key, {})
        if not isinstance(values, dict):
            issues.append(f"Invalid {key} settings; using defaults.")
            return AreaSettings()
        fonts: dict[str, str] = {}
        for name, default in (("latin", ""), ("cjk", "auto")):
            value = values.get(name, default)
            if not isinstance(value, str) or len(value) > 256 or any(ord(c) < 32 for c in value):
                value = default
                issues.append(f"Invalid {key} {name} font; using default.")
            fonts[name] = value.strip()
        size = values.get("size")
        if size is not None:
            if isinstance(size, bool) or not isinstance(size, (int, float)) or not math.isfinite(size) or not 6 <= size <= 48:
                issues.append(f"Invalid {key} size; using Anki default.")
                size = None
            else:
                size = float(size)
        return AreaSettings(**fonts, size=size)

    return Settings(locale=locale, ui=area("ui"), browser=area("browser")), issues


def effective_locale(preference: str, anki_language: str) -> str:
    if preference:
        return preference
    tag = anki_language.replace("_", "-").lower()
    if tag.startswith("zh"):
        if "hk" in tag:
            return "zh-Hant-HK"
        if "hant" in tag or "tw" in tag:
            return "zh-Hant-TW"
        return "zh-Hans"
    if tag.startswith("ja"):
        return "ja"
    if tag.startswith("ko"):
        return "ko"
    return ""


def resolve_cjk(choice: str, locale: str, installed: list[str]) -> tuple[str, str | None]:
    families = {name.casefold(): name for name in installed}
    if not choice:
        return "", None
    if choice != "auto":
        if choice.casefold() in families:
            return families[choice.casefold()], None
        return "", f'CJK font "{choice}" is not installed; using Anki fallback.'
    if not locale:
        return "", None
    for candidate in REGIONAL_FONTS.get(locale, ()):
        if candidate.casefold() in families:
            return families[candidate.casefold()], None
    return "", f"No recommended {locale} font is installed; select an installed CJK font."
