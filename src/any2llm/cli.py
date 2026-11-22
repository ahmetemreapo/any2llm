"""Select files and write token-balanced Markdown batches."""

import argparse
import sys
from pathlib import Path

import questionary

from .messages import MESSAGES
from .packer import PRESETS, write_batches
from .parsers import ParsedFile
from .scanner import scan_folder
from .tokenizer import count_tokens, get_encoding


def display_path(path: Path | str) -> str:
    return "".join(c if c.isprintable() else ascii(c)[1:-1] for c in str(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False, exit_on_error=False)
    parser.add_argument("folder", nargs="?", default=".", type=Path)
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("-y", "--yes", action="store_true")
    # Accept the previous UI language option for command-line compatibility.
    parser.add_argument(
        "--ui-lang", choices=("en", "tr", "zh", "hi", "es", "ar", "fr", "bn", "pt", "id", "ur"),
        help=argparse.SUPPRESS,
    )
    parser.add_argument("-h", "--help", action="store_true")
    msg = MESSAGES
    try:
        args, unknown = parser.parse_known_args(argv)
        if unknown or (args.max_tokens is not None and args.max_tokens < 1):
            raise ValueError
    except (ValueError, argparse.ArgumentError):
        print(msg["arguments"], "any2llm --help", file=sys.stderr)
        return 2
    if args.help:
        print(f'any2llm [{msg["folder"]}] [-r] [-y] [--max-tokens INT]')
        print(f'  -r, --recursive   {msg["recursive"]}')
        print("  -y, --yes         Pack all files using the Balanced preset")
        print("  --max-tokens INT  Override the token limit per batch")
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

    selected = result.readable
    preset = "Balanced"
    try:
        if not args.yes:
            selected = _select_files(result.parsed)
            if selected and args.max_tokens is None:
                preset = questionary.select(
                    "Select a detail preset",
                    choices=[
                        questionary.Choice(f"{name} ({limit:,} tokens)" if limit else name, value=name)
                        for name, limit in PRESETS.items()
                    ],
                    default="Balanced",
                ).unsafe_ask()
    except (KeyboardInterrupt, EOFError):
        print(msg["cancelled"], file=sys.stderr)
        return 130
    print(f'{msg["selected"]}: {len(selected)}')
    try:
        paths = write_batches(
            {path: result.parsed[path] for path in selected}, args.folder / "_llm_pack",
            preset=preset, max_tokens=args.max_tokens,
        )
    except (OSError, ValueError) as exc:
        print(f"Cannot write batches: {display_path(str(exc))}", file=sys.stderr)
        return 1
    for path in paths:
        print(f"Written: {display_path(path)}")
    return 0


def _select_files(parsed_files: dict[Path, ParsedFile]) -> list[Path]:
    prefix = "~" if get_encoding() is None else ""
    choices = []
    for path, parsed in parsed_files.items():
        count = count_tokens(parsed.text)
        unit = "token" if count == 1 else "tokens"
        label = f"{display_path(path)} [{display_path(parsed.file_type)}, {prefix}{count:,} {unit}]"
        choices.append(questionary.Choice(label, value=path, checked=True))
    return questionary.checkbox(
        MESSAGES["select"], choices, instruction=MESSAGES["keys"], erase_when_done=True,
    ).unsafe_ask()
