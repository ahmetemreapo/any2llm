"""Interactive folder scanner."""

import argparse
import sys
from pathlib import Path

import questionary

from .messages import MESSAGES
from .scanner import scan_folder


def display_path(path: Path) -> str:
    return "".join(c if c.isprintable() else ascii(c)[1:-1] for c in str(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False, exit_on_error=False)
    parser.add_argument("folder", nargs="?", default=".", type=Path)
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument("--ui-lang", choices=MESSAGES, default="tr")
    parser.add_argument("-h", "--help", action="store_true")
    msg = MESSAGES["tr"]
    try:
        args, unknown = parser.parse_known_args(argv)
        msg = MESSAGES[args.ui_lang]
        if unknown:
            raise ValueError
    except (ValueError, argparse.ArgumentError):
        print(msg["arguments"], "any2llm --help", file=sys.stderr)
        return 2
    if args.help:
        print(f'any2llm [{msg["folder"]}] [-r] [--ui-lang {{{",".join(MESSAGES)}}}]')
        print(f'  -r, --recursive   {msg["recursive"]}')
        print(f'  --ui-lang         {msg["language"]}')
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
    if not result.readable:
        print(msg["empty"])
        return 0

    choices = [questionary.Choice(display_path(path), value=path, checked=True)
               for path in result.readable]
    try:
        selected = questionary.checkbox(
            msg["select"], choices, instruction=msg["keys"], erase_when_done=True,
        ).unsafe_ask()
    except (KeyboardInterrupt, EOFError):
        print(msg["cancelled"], file=sys.stderr)
        return 130
    print(f'{msg["selected"]}: {len(selected)}')
    return 0
