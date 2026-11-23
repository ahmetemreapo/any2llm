"""Select files and write a pack with one master prompt."""

import argparse
import io
import logging
import os
import subprocess
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path

from .clipboard import copy_prompt
from .config import Settings, load_config, save_config, setup
from .languages import LANGUAGE_NAMES, system_language
from .messages import MESSAGES, help_text
from .output import OutputBusy, OutputConflict, write_pack
from .packer import build_batches
from .prompts import master_prompt
from .scanner import scan_folder
from .terminal import Terminal, display_count, display_page_ranges, display_path, select_files

# Older --ui-lang values remain accepted for command-line compatibility.
_LEGACY_LANGUAGES = (*LANGUAGE_NAMES, "id")


class ArgumentError(ValueError):
    def __init__(self, key: str, option: str = ""):
        self.key = key
        self.option = option


def _arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="any2llm", add_help=False, allow_abbrev=False, exit_on_error=False,
    )
    parser.add_argument("folder", nargs="?", default=".")
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--lang", choices=LANGUAGE_NAMES)
    parser.add_argument("--task", default="")
    parser.add_argument("--config", action="store_true")
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--plain", action="store_true")
    parser.add_argument("--details", action="store_true")
    parser.add_argument("--include-sensitive", action="store_true")
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB")
    parser.add_argument("-o", "--output", type=Path, default=Path("_llm_pack"))
    parser.add_argument("-y", "--yes", action="store_true")
    parser.add_argument("--ui-lang", choices=_LEGACY_LANGUAGES)
    parser.add_argument("-h", "--help", action="store_true")
    try:
        args, unknown = parser.parse_known_args(argv)
    except argparse.ArgumentError as exc:
        key = "invalid_limit" if exc.argument_name == "--max-tokens" else "invalid_option"
        raise ArgumentError(key, exc.argument_name or "") from exc
    if unknown:
        raise ArgumentError("unknown_option", unknown[0])
    if args.max_tokens is not None and args.max_tokens < 1:
        raise ArgumentError("invalid_limit")
    return args


def _error_language(argv: list[str], default: str) -> str:
    # Parse only the language flags to report errors in the requested language.
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False, exit_on_error=False)
    parser.add_argument("--lang", nargs="?")
    parser.add_argument("--ui-lang", nargs="?")
    args, _ = parser.parse_known_args(argv)
    if args.lang in LANGUAGE_NAMES:
        return args.lang
    return args.ui_lang if args.ui_lang in LANGUAGE_NAMES else default


def _interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _configure_output() -> None:
    """Configure process streams for the installed CLI and module entry points."""
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            if stream.isatty():
                stream.reconfigure(errors="backslashreplace")
            else:
                # Files and pipelines carry UTF-8 on all supported systems.
                stream.reconfigure(encoding="utf-8", errors="backslashreplace")


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        _configure_output()
        argv = sys.argv[1:]
    try:
        saved = load_config()
        invalid_config = False
    except (OSError, ValueError, RuntimeError):
        saved = None
        invalid_config = True
    detected_language = system_language()
    defaults = saved or Settings(lang=detected_language)
    try:
        args = _arguments(argv)
    except ArgumentError as exc:
        msg = MESSAGES[_error_language(argv, defaults.lang)]
        print(msg[exc.key].format(option=display_path(exc.option)), "any2llm --help", file=sys.stderr)
        return 2

    override = args.lang or (args.ui_lang if args.ui_lang in LANGUAGE_NAMES else None)
    msg = MESSAGES[override or defaults.lang]
    if args.help:
        print(help_text(override or defaults.lang))
        return 0
    configure = args.config or args.folder == "setup"
    if invalid_config and not configure:
        print(msg["config_error"], file=sys.stderr)
        return 1

    interactive = _interactive()
    if not interactive and (configure or not args.yes):
        print(msg["no_setup_terminal" if configure else "no_terminal"], file=sys.stderr)
        return 2
    plain = args.plain or os.environ.get("TERM") == "dumb"
    screen = Terminal(plain=plain)
    try:
        if interactive:
            screen.logo()
        if configure or (saved is None and interactive):
            saved = setup(defaults, menu_language=detected_language, plain=plain)
            if saved is None:
                return 130
            msg = MESSAGES[saved.lang]
            try:
                save_config(saved)
            except (OSError, RuntimeError):
                print(msg["save_error"], file=sys.stderr)
                print(msg["save_fix"], file=sys.stderr)
                return 1
            screen.section(msg["saved"], "bold green", icon="✓")
            screen.line(msg["setup_again"])
            if configure:
                return 0
        settings = saved or defaults
        lang = override or settings.lang
        msg = MESSAGES[lang]
        return _pack(args, settings, lang, screen, plain=plain)
    except KeyboardInterrupt:
        print(msg["cancelled"], file=sys.stderr)
        return 130
    except EOFError as exc:
        language = exc.args[0] if exc.args and exc.args[0] in LANGUAGE_NAMES else None
        print((MESSAGES[language] if language else msg)["input_closed"], file=sys.stderr)
        return 2


def _pack(args: argparse.Namespace, settings: Settings, lang: str, screen: Terminal, *, plain: bool) -> int:
    msg = MESSAGES[lang]
    folder = Path(args.folder).absolute()
    output_dir = folder / args.output
    screen.section(f'{msg["scanning"]}…', "bold cyan", icon="⌕")
    screen.line(f'{msg["folder"]}: {display_path(folder)}', flush=True)
    logging.getLogger("pypdf").setLevel(logging.CRITICAL)
    examined = 0

    def on_file() -> None:
        nonlocal examined
        examined += 1
        if examined % 25 == 0:
            screen.line(f'{msg["progress"]}: {display_count(examined, msg)}', flush=True)

    try:
        result = scan_folder(
            folder, args.recursive, output_dir=output_dir,
            on_file=on_file if screen.is_terminal else None,
            include_sensitive=args.include_sensitive, exclude=args.exclude,
        )
    except OSError as exc:
        key = {
            FileNotFoundError: "no_folder", NotADirectoryError: "not_folder",
        }.get(type(exc), "read_folder")
        print(f'{msg[key]}: {display_path(folder)}', file=sys.stderr)
        return 1
    if result.skipped:
        _report_skipped(result.skipped, msg, screen, details=args.details)
    if not result.parsed:
        screen.section(msg["empty"])
        if not args.recursive and result.has_subfolders:
            print(msg["nested"])
        return 0

    selected = result.readable if args.yes else select_files(result.readable, msg, plain=plain)
    if not selected:
        screen.section(msg["none_selected"])
        return 0
    documents_to_pack = {path: result.parsed[path] for path in selected}
    screen.section(msg["packing"], "bold bright_blue", icon="▤", flush=True)
    try:
        documents = build_batches(
            documents_to_pack, preset=settings.preset, max_tokens=args.max_tokens,
        )
    except ValueError:
        print(msg["limit_error"], file=sys.stderr)
        return 1
    batches = list(documents)
    prompt = master_prompt(batches, lang, args.task)
    documents["PROMPT.txt"] = prompt
    try:
        write_pack(output_dir, documents)
    except OSError as exc:
        key = "write_error"
        if isinstance(exc, OutputBusy):
            key = "busy"
        elif isinstance(exc, OutputConflict):
            key = "collision"
        problem_path = exc.filename if key == "collision" else output_dir
        print(f'{msg[key]}: {display_path(problem_path)}', file=sys.stderr)
        print(msg["busy_fix" if key == "busy" else "write_fix"], file=sys.stderr)
        return 1
    for path, document in documents_to_pack.items():
        partial = sum(page.partial for page in document.pages)
        if partial:
            warning = msg["partial"].format(count=display_count(partial, msg))
            print(f"  {display_path(path)} — {warning}")
        missing = [page.number for page in document.pages if page.no_text]
        if missing:
            warning = msg["no_page_text"].format(pages=display_page_ranges(missing, msg))
            print(f"  {display_path(path)} — {warning}")
    copied = copy_prompt(prompt)
    _handoff(msg, output_dir, len(selected), batches, copied, screen)
    if settings.auto_open and not args.no_open and _interactive():
        _open_folder(output_dir)
    return 0


def _report_skipped(
    skipped: Mapping[Path, str], msg: dict[str, str], screen: Terminal, *, details: bool,
) -> None:
    reasons = sorted(Counter(skipped.values()).items())
    summary = ", ".join(f"{display_count(count, msg)} × {msg[reason]}" for reason, count in reasons)
    screen.section(f'{msg["skipped"]} ({display_count(len(skipped), msg)})', "bold yellow", icon="▲")
    screen.line(f"  {summary}")
    for number, (path, reason) in enumerate(skipped.items(), 1):
        if number > 8 and not details:
            screen.line(msg["more_skipped"].format(count=display_count(len(skipped) - 8, msg)))
            break
        screen.line(f"  {display_path(path)} — {msg[reason]}")

    guidance: dict[str, list[str]] = {}
    for reason, _ in reasons:
        action = "media_help" if reason in {"image", "audio", "video"} else f"{reason}_help"
        guidance.setdefault(action, []).append(msg[reason])
    screen.section(msg["skipped_help"], "bold yellow", icon="▲")
    for action, labels in guidance.items():
        screen.line(f"  {', '.join(labels)} — {msg[action]}", "bold yellow")


def _handoff(
    msg: dict[str, str], folder: Path, selected: int, batches: list[str], copied: bool, screen: Terminal,
) -> None:
    count = len(batches)
    label_count = display_count(count, msg)
    screen.section(
        msg["ready"].format(selected=display_count(selected, msg), batches=label_count), "bold green", icon="✓",
    )
    screen.line(f'{msg["folder"]}: {display_path(folder.resolve())}')
    if copied:
        screen.section(msg["clipboard_copied"], "bold bright_green", icon="✓")
    else:
        screen.section(msg["clipboard_failed"], "bold yellow", icon="▲")
    screen.section(msg["open_chat"], "bold bright_magenta", icon="↗")
    if count == 1:
        print(msg["attach_one"].format(name=batches[0]))
    else:
        first, last = batches[0], batches[-1]
        screen.line(msg["attach_many"].format(first=first, last=last), "bright_white", filenames=(first, last))
    print(msg["paste" if copied else "clipboard"])
    if count > 1:
        print(msg["next"])


def _open_folder(path: Path) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(path.resolve())
        else:
            command = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.Popen(
                [command, str(path.resolve())], stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
            )
    except (OSError, NotImplementedError):
        pass
