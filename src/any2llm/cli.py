"""Select files and write token-balanced Markdown batches."""

import argparse
import sys
from pathlib import Path

import questionary

from .messages import MESSAGES
from .packer import PRESETS, build_batches, write_pack
from .parsers import ParsedFile
from .prompts import clipboard_walkthrough, generate_prompts
from .scanner import scan_folder
from .tokenizer import count_tokens, get_encoding


def display_path(path: Path | str) -> str:
    return "".join(c if c.isprintable() else ascii(c)[1:-1] for c in str(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="any2llm", add_help=False, allow_abbrev=False, exit_on_error=False,
        description="Pack files into Markdown batches with one prompt per turn.",
    )
    parser.add_argument("folder", nargs="?", default=".", type=Path, help="Folder to scan (default: .)")
    parser.add_argument("-r", "--recursive", action="store_true", help=MESSAGES["recursive"])
    parser.add_argument("--max-tokens", type=int, metavar="INT", help="Override the token limit per batch")
    parser.add_argument("--lang", choices=("en", "tr"), default="en", help="Prompt language (default: en)")
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("_llm_pack"), metavar="DIR",
        help="Output directory, relative to the scanned folder unless absolute (default: _llm_pack)",
    )
    parser.add_argument("-y", "--yes", action="store_true", help="Pack all files without interaction")
    # Accept the previous UI language option for command-line compatibility.
    parser.add_argument(
        "--ui-lang", choices=("en", "tr", "zh", "hi", "es", "ar", "fr", "bn", "pt", "id", "ur"),
        help=argparse.SUPPRESS,
    )
    parser.add_argument("-h", "--help", action="store_true", help="Show this help message and exit")
    msg = MESSAGES
    try:
        args, unknown = parser.parse_known_args(argv)
        if unknown or (args.max_tokens is not None and args.max_tokens < 1):
            raise ValueError
    except (ValueError, argparse.ArgumentError):
        print(msg["arguments"], "any2llm --help", file=sys.stderr)
        return 2
    if args.help:
        parser.print_help()
        return 0
    output_dir = args.folder / args.output
    try:
        result = scan_folder(args.folder, args.recursive, output_dir=output_dir)
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
    task = ""
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
            if selected:
                task = questionary.text(
                    "Optional task (press Enter for a detailed analysis)"
                ).unsafe_ask()
    except (KeyboardInterrupt, EOFError):
        print(msg["cancelled"], file=sys.stderr)
        return 130
    print(f'{msg["selected"]}: {len(selected)}')
    if not selected:
        return 0
    try:
        documents = build_batches(
            {path: result.parsed[path] for path in selected},
            preset=preset, max_tokens=args.max_tokens,
        )
        batch_names = list(documents)
        prompts = generate_prompts(batch_names, args.lang, task)
        documents["PROMPTS.md"] = "\n\n".join(prompts) + "\n"
        paths = write_pack(output_dir, documents)
    except (OSError, ValueError) as exc:
        print(f"Cannot write pack: {display_path(str(exc))}", file=sys.stderr)
        return 1
    for path in paths:
        print(f"Written: {display_path(path)}")
    if not args.yes:
        try:
            clipboard_walkthrough(batch_names, prompts)
        except (KeyboardInterrupt, EOFError):
            print("Walkthrough stopped. All turns are saved in PROMPTS.md.", file=sys.stderr)
            return 130
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
