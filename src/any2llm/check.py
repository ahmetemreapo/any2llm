"""any2llm check: verify the quotes an AI answer cites against the original pages."""

import argparse
import json
import os
import sys
from pathlib import Path

from . import ocr
from .citations import (
    CLOSE,
    FAILED,
    NO_QUOTE,
    OTHER_FILE,
    OTHER_PAGE,
    VERIFIED,
    Check,
    Report,
    check_answer,
    find_citations,
    resolve_source,
)
from .languages import LANGUAGE_NAMES, system_language
from .messages import MESSAGES, help_text
from .sources import load
from .terminal import display_path

_ICONS = {VERIFIED: "✓", CLOSE: "≈", NO_QUOTE: "?"}
_STYLES = {VERIFIED: "green", CLOSE: "green", NO_QUOTE: "yellow"}


def describe(check: Check, msg: dict[str, str]) -> str:
    text = msg[f"check_{check.status}"]
    if check.status == OTHER_PAGE:
        return text.format(page=check.found_page)
    if check.status == OTHER_FILE:
        where = check.found_file or ""
        if check.found_page is not None:
            where = f"{where}, p. {check.found_page}"
        return text.format(file=where)
    return text


def render(report: Report, msg: dict[str, str]) -> list[tuple[str, str]]:
    """Return (style, line) pairs that summarize a report."""
    if not report.checks:
        return [("bold yellow", f'▲  {msg["check_none"]}')]
    passed = report.count(VERIFIED, CLOSE)
    summary = msg["check_summary"].format(verified=passed, total=len(report.checks))
    failed = report.count(*FAILED)
    head_style = "bold green" if report.passed and not report.count(NO_QUOTE) else (
        "bold red" if failed else "bold yellow")
    head_icon = "✓" if head_style == "bold green" else ("✗" if failed else "▲")
    lines = [(head_style, f"{head_icon}  {summary}")]
    for check in report.checks:
        icon = _ICONS.get(check.status, "✗")
        style = _STYLES.get(check.status, "red")
        lines.append((style, f"  {icon} [{display_path(check.citation.label)}] {describe(check, msg)}"))
        if check.status in FAILED and check.citation.quote:
            quote = check.citation.quote if len(check.citation.quote) <= 120 else check.citation.quote[:117] + "…"
            lines.append(("dim", f'      "{display_path(quote)}"'))
    if failed:
        lines.append(("bold red", msg["check_failed_hint"]))
    return lines


def as_json(report: Report) -> dict:
    return {
        "passed": report.passed,
        "total": len(report.checks),
        "verified": report.count(VERIFIED, CLOSE),
        "failed": report.count(*FAILED),
        "unchecked": report.count(NO_QUOTE),
        "citations": [
            {
                "source": check.citation.source, "first_page": check.citation.first_page,
                "last_page": check.citation.last_page, "quote": check.citation.quote,
                "status": check.status, "file": check.file, "found_page": check.found_page,
                "found_file": check.found_file,
            }
            for check in report.checks
        ],
    }


def print_report(report: Report, msg: dict[str, str], *, stream=None) -> None:
    stream = stream or sys.stderr
    lines = render(report, msg)
    if stream.isatty() and not os.environ.get("NO_COLOR"):
        from rich.console import Console
        from rich.text import Text

        console = Console(file=stream, highlight=False)
        console.print()
        for style, line in lines:
            console.print(Text(line, style=style), soft_wrap=True)
        return
    print(file=stream)
    for _, line in lines:
        print(line, file=stream)


def _arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="any2llm check", add_help=False, allow_abbrev=False, exit_on_error=False)
    parser.add_argument("targets", nargs="*")
    parser.add_argument("--lang", choices=LANGUAGE_NAMES)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--ocr", action="store_true")
    parser.add_argument("--ocr-lang", metavar="LANG")
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB")
    parser.add_argument("--include-sensitive", action="store_true")
    parser.add_argument("-h", "--help", action="store_true")
    return parser.parse_args(argv)


def _read_clipboard() -> str:
    try:
        import pyperclip

        return pyperclip.paste() or ""
    except Exception:  # noqa: BLE001 - every backend failure means the same thing here.
        return ""


def main(argv: list[str]) -> int:
    lang = system_language()
    try:
        args = _arguments(argv)
    except (argparse.ArgumentError, SystemExit) as exc:
        option = getattr(exc, "argument_name", "") or ""
        print(MESSAGES[lang]["invalid_option"].format(option=option), "any2llm check --help", file=sys.stderr)
        return 2
    lang = args.lang or lang
    msg = MESSAGES[lang]
    if args.help:
        print(help_text(lang))
        return 0
    if len(args.targets) > 2:
        print(msg["unknown_option"].format(option=args.targets[2]), file=sys.stderr)
        return 2
    folder, answer_path = Path("."), None
    if len(args.targets) == 2:
        folder, answer_path = Path(args.targets[0]), args.targets[1]
    elif args.targets:
        target = Path(args.targets[0])
        if target.is_dir():
            folder = target
        else:
            answer_path = args.targets[0]

    if answer_path == "-" or (answer_path is None and not sys.stdin.isatty()):
        answer = sys.stdin.read()
    elif answer_path is not None:
        try:
            answer = Path(answer_path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            print(f'{msg["check_no_answer_file"]}: {display_path(answer_path)}', file=sys.stderr)
            return 1
    else:
        answer = _read_clipboard()
        if answer.strip():
            print(msg["check_clipboard"], file=sys.stderr)
    if not answer.strip():
        print(msg["check_input"], file=sys.stderr)
        return 2

    ocr_lang = args.ocr_lang or ("eng" if args.ocr else None)
    if ocr_lang is not None and (error := ocr.setup_error(ocr_lang)):
        print(msg[error].format(lang=display_path(ocr_lang)), file=sys.stderr)
        ocr_lang = None
    names = [citation.source for citation in find_citations(answer)]

    answer_file = Path(os.path.realpath(answer_path)) if answer_path not in (None, "-") else None

    def cited(available: list[str]) -> list[str]:
        # The answer itself is not a source, even when it is saved in the folder.
        root = Path(os.path.realpath(folder))
        available = [name for name in available if answer_file is None or root / name != answer_file]
        # In large folders, parse only the files the answer cites.
        matched = {resolve_source(name, available) for name in names}
        return available if len(available) <= 50 else [name for name in available if name in matched]

    try:
        library = load(
            folder, recursive=True, exclude=args.exclude, include_sensitive=args.include_sensitive,
            ocr_lang=ocr_lang, keep=cited,
        )
    except OSError as exc:
        key = {FileNotFoundError: "no_folder", NotADirectoryError: "not_folder"}.get(type(exc), "read_folder")
        print(f'{msg[key]}: {display_path(folder)}', file=sys.stderr)
        return 1
    report = check_answer(answer, library.by_name())
    if args.json:
        print(json.dumps(as_json(report), ensure_ascii=False, indent=2))
    else:
        print_report(report, msg, stream=sys.stdout)
    return 0 if report.passed else 1
