"""Interactive folder scanner."""

import argparse
import sys
from pathlib import Path

import questionary

from .messages import MESSAGES
from .scanner import scan_folder
from .tokenizer import count_tokens, get_encoding


def display_path(path: Path | str) -> str:
    return "".join(c if c.isprintable() else ascii(c)[1:-1] for c in str(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False, exit_on_error=False)
    parser.add_argument("folder", nargs="?", default=".", type=Path)
    parser.add_argument("-r", "--recursive", action="store_true")
    # Accept the previous UI language option for command-line compatibility.
    parser.add_argument(
        "--ui-lang", choices=("en", "tr", "zh", "hi", "es", "ar", "fr", "bn", "pt", "id", "ur"),
        help=argparse.SUPPRESS,
    )
    parser.add_argument("-h", "--help", action="store_true")
    msg = MESSAGES
    try:
        args, unknown = parser.parse_known_args(argv)
        if unknown:
            raise ValueError
    except (ValueError, argparse.ArgumentError):
        print(msg["arguments"], "any2llm --help", file=sys.stderr)
        return 2
    if args.help:
        print(f'any2llm [{msg["folder"]}] [-r]')
        print(f'  -r, --recursive   {msg["recursive"]}')
        return 0
    try:
        result = scan_folder(args.folder, args.recursive)
    except OSError:
        print(f'{msg["unreadable"]}: {display_path(args.folder)}', file=sys.stderr)
        return 1
    if result.skipped:
        print(f'{msg["skipped"]} ({len(result.skipped)})')
        for path, reason in result.skipped.items():
            print(f"  {display_path(path)} — {msg[reason]}")
    if not result.parsed:
        print(msg["empty"])
        return 0

    prefix = "~" if get_encoding() is None else ""
    choices = []
    for path, parsed in result.parsed.items():
        count = count_tokens(parsed.text)
        unit = "token" if count == 1 else "tokens"
        label = f"{display_path(path)} [{display_path(parsed.file_type)}, {prefix}{count:,} {unit}]"
        choices.append(questionary.Choice(label, value=path, checked=True))
    try:
        selected = questionary.checkbox(
            msg["select"], choices, instruction=msg["keys"], erase_when_done=True,
        ).unsafe_ask()
    except (KeyboardInterrupt, EOFError):
        print(msg["cancelled"], file=sys.stderr)
        return 130
    print(f'{msg["selected"]}: {len(selected)}')
    return 0
