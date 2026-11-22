"""Persistent preferences and first-run setup."""

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import questionary

from .languages import LANGUAGE_NAMES
from .messages import MESSAGES
from .packer import PRESETS
from .terminal import Terminal, select


@dataclass(frozen=True)
class Settings:
    lang: str = "en"
    preset: str = "Balanced"
    auto_open: bool = True


def config_path() -> Path:
    return Path.home() / ".config" / "any2llm" / "config.json"


def load_config() -> Settings | None:
    try:
        data = json.loads(config_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    if not isinstance(data, dict):
        raise ValueError("Invalid configuration")
    lang, preset, auto_open = (data.get(key) for key in ("lang", "preset", "auto_open"))
    if not isinstance(lang, str) or lang not in LANGUAGE_NAMES:
        raise ValueError("Invalid configuration language")
    if preset not in tuple(PRESETS) or not isinstance(auto_open, bool):
        raise ValueError("Invalid configuration")
    return Settings(lang, preset, auto_open)


def save_config(settings: Settings) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=path.parent) as staging:
        temporary = Path(staging) / path.name
        temporary.write_text(json.dumps(asdict(settings), indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)


def setup(initial: Settings, *, menu_language: str, plain: bool = False) -> Settings | None:
    lang = menu_language
    msg = MESSAGES[lang]
    screen = Terminal(plain=plain)
    try:
        print()
        screen.line(msg["welcome"])
        print()
        screen.controls(msg["plain_keys" if plain else "arrows"])
        print()
        lang = select(
            f'1/3  {msg["language"]}',
            [questionary.Choice(name, code) for code, name in LANGUAGE_NAMES.items()],
            initial.lang, msg["invalid_choice"], plain=plain, accent="brightcyan",
        )
        return _preferences(lang, initial, screen, plain=plain)
    except KeyboardInterrupt:
        print(MESSAGES[lang]["cancelled"], file=sys.stderr)
        return None
    except EOFError:
        raise EOFError(lang) from None


def _preferences(lang: str, initial: Settings, screen: Terminal, *, plain: bool) -> Settings:
    msg = MESSAGES[lang]
    screen.section(msg["hint"])
    preset = select(
        f'2/3  {msg["detail"]}', [questionary.Choice(msg[key], key) for key in PRESETS],
        initial.preset, msg["invalid_choice"], plain=plain, accent="brightmagenta",
    )
    print()
    auto_open = select(
        f'3/3  {msg["open"]}', [questionary.Choice(msg["yes"], True), questionary.Choice(msg["no"], False)],
        initial.auto_open, msg["invalid_choice"], plain=plain, accent="brightblue",
    )
    return Settings(lang, preset, auto_open)
