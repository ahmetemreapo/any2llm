"""Localized terminal copy and analysis instructions."""

import json
from importlib.resources import files

from .languages import LANGUAGE_NAMES

_directory = files(__package__).joinpath("locales")
_catalogs = {
    code: json.loads(_directory.joinpath(f"{code}.json").read_text(encoding="utf-8"))
    for code in LANGUAGE_NAMES
}

PROMPTS = {code: catalog["prompt"] for code, catalog in _catalogs.items()}
MESSAGES = {code: catalog["messages"] for code, catalog in _catalogs.items()}
for code, messages in MESSAGES.items():
    messages["next"] = messages["next"].format(continue_word=PROMPTS[code]["continue"])


def help_text(lang: str) -> str:
    codes = [f"{code}  {name}" for code, name in LANGUAGE_NAMES.items()]
    rows = ["  " + "    ".join(codes[i:i + 3]) for i in range(0, len(codes), 3)]
    return MESSAGES[lang]["help"] + "\n\n--lang\n" + "\n".join(rows)
