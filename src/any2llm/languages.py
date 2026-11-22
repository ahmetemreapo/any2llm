"""Supported languages and the terminal's preferred locale."""

import locale
import os
import re
import sys

LANGUAGE_NAMES = {
    "en": "English",
    "zh": "简体中文",
    "hi": "हिन्दी",
    "es": "Español",
    "fr": "Français",
    "ar": "العربية",
    "bn": "বাংলা",
    "pt": "Português",
    "ru": "Русский",
    "ur": "اردو",
    "tr": "Türkçe",
}
_WINDOWS_NAMES = {
    "english": "en", "chinese": "zh", "hindi": "hi", "spanish": "es",
    "french": "fr", "arabic": "ar", "bengali": "bn", "bangla": "bn",
    "portuguese": "pt", "russian": "ru", "urdu": "ur", "turkish": "tr",
}


def _native_message_locale() -> str | None:
    if sys.platform == "win32":
        # The Windows display language can differ from regional number formats.
        import ctypes

        language_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        return locale.windows_locale.get(language_id)
    try:
        return locale.getlocale()[0]
    except ValueError:
        return None


def system_language() -> str:
    """Use the message locale, with English as the fallback."""
    name = os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG")
    if not name:
        name = _native_message_locale()
    language = re.split(r"[-_.@ (]", (name or "").strip().lower(), maxsplit=1)[0]
    if language == "cmn":
        return "zh"
    return language if language in LANGUAGE_NAMES else _WINDOWS_NAMES.get(language, "en")
