"""Terminal presentation, accessible choices and safe path labels."""

import os
import shutil
import sys
from collections import Counter
from pathlib import Path
from unicodedata import decimal

import questionary
from prompt_toolkit.output import ColorDepth
from prompt_toolkit.utils import get_cwidth
from rich.console import Console
from rich.text import Text
from rich.theme import Theme

_LOGO = (
    ("╭───╮", "", "╭─────────────╮"),
    ("│   ╰─────╮", "·  ·  ▸", "│   any2llm   │"),
    ("│  ▤   ▤  │", "", "╰───┬─────────╯"),
    ("╰─────────╯", "", "    ╰╴"),
)
_KEY_THEME = Theme(dict.fromkeys(
    ("key.move", "key.toggle", "key.all", "key.confirm", "key.cancel"),
    "bold bright_white on blue",
))


def _menu_style(accent: str) -> questionary.Style:
    focus = "bold fg:ansiwhite bg:ansiblue"
    heading = f"bold fg:ansi{accent}"
    return questionary.Style([
        ("qmark", heading),
        ("question", heading),
        ("pointer", focus),
        ("highlighted", focus),
        ("answer", "noinherit bold"),
    ])


class Terminal:
    """Style sections on a terminal while keeping redirected output readable."""

    def __init__(self, *, plain: bool):
        self.is_terminal = sys.stdout.isatty()
        color_system = None if os.environ.get("NO_COLOR") else "auto"
        self._console = Console(color_system=color_system, theme=_KEY_THEME) if self.is_terminal and not plain else None

    def logo(self) -> None:
        if self._console is None:
            self.section("any2llm")
            return
        if self._console.width < 39:
            self.section("▤  ▸  any2llm", "bold bright_cyan")
            return
        print()
        logo = Text("\n").join(
            Text.assemble(
                "  ", (f"{folder:<11}", "bright_cyan"),
                (f"{trail:^11}", "bold bright_yellow"), (chat, "bright_magenta"),
            )
            for folder, trail, chat in _LOGO
        )
        logo.highlight_words(["any2llm"], "bold bright_cyan")
        self._console.print(logo, soft_wrap=True)

    def controls(self, message: str) -> None:
        keys = Text.from_markup(message, emoji=False)
        if self._console is None:
            print(keys.plain)
        else:
            self._console.print(keys)

    def line(
        self, message: str, style: str = "", *, filenames: tuple[str, ...] = (), flush: bool = False,
    ) -> None:
        if self._console is not None and (style or filenames):
            text = Text(message, style=style)
            if filenames:
                text.highlight_words(filenames, "bright_green")
            self._console.print(text, soft_wrap=True)
        else:
            print(message, flush=flush)

    def section(self, message: str, style: str = "", *, icon: str = "", flush: bool = False) -> None:
        if self.is_terminal:
            print()
        if icon and self._console is not None:
            message = f"{icon}  {message}"
        self.line(message, style, flush=flush)


def display_path(path: Path | str) -> str:
    return "".join(c if c.isprintable() else ascii(c)[1:-1] for c in str(path))


def display_count(count: int, msg: dict[str, str]) -> str:
    if msg.get("grouping") == "indic" and count >= 1000:
        head, tail = divmod(count, 1000)
        groups = [f"{tail:03d}"]
        while head >= 100:
            head, pair = divmod(head, 100)
            groups.append(f"{pair:02d}")
        groups.append(str(head))
        return msg["thousands"].join(reversed(groups))
    return f"{count:,}".replace(",", msg["thousands"])


def display_size(byte_count: int, msg: dict[str, str]) -> str:
    amount = float(byte_count)
    unit = "B"
    for larger_unit in ("KB", "MB", "GB", "TB"):
        if round(amount, 1) < 1000:
            break
        amount /= 1000
        unit = larger_unit
    size = f"{amount:.1f}".removesuffix(".0").replace(".", msg["decimal"])
    return f"{size} {unit}"


def display_page_ranges(numbers: list[int], msg: dict[str, str]) -> str:
    ranges: list[tuple[int, int]] = []
    for number in numbers:
        if ranges and ranges[-1][1] + 1 == number:
            ranges[-1] = (ranges[-1][0], number)
        else:
            ranges.append((number, number))
    return ", ".join(
        display_count(first, msg) if first == last
        else f"{display_count(first, msg)}–{display_count(last, msg)}"
        for first, last in ranges
    )


def _normalize_digits(value: str) -> str:
    return "".join(str(decimal(char, char)) for char in value)


def _color_depth() -> ColorDepth | None:
    return ColorDepth.DEPTH_1_BIT if os.environ.get("NO_COLOR") else None


def select(
    message: str, choices: list[questionary.Choice], default: str | bool,
    invalid: str, *, plain: bool, accent: str,
) -> str | bool:
    if not plain:
        return questionary.select(
            message, choices=choices, default=default, instruction=" ",
            qmark="◇", pointer="▸", style=_menu_style(accent), color_depth=_color_depth(),
        ).unsafe_ask()

    print(message)
    default_number = next(i for i, choice in enumerate(choices, 1) if choice.value == default)
    options = {str(number): choice.value for number, choice in enumerate(choices, 1)}
    for number, choice in enumerate(choices, 1):
        print(f"  {number}. {choice.title}")
    while True:
        answer = _normalize_digits(input(f"[{default_number}] > ").strip())
        if not answer:
            return default
        if answer in options:
            return options[answer]
        print(invalid)


def select_files(paths: list[Path], msg: dict[str, str], *, plain: bool) -> list[Path]:
    screen = Terminal(plain=plain)
    screen.section(msg["local"])
    screen.line(msg["all_selected"].format(count=display_count(len(paths), msg)), "bold")
    if plain:
        screen.section(msg["select"])
        for number, path in enumerate(paths, 1):
            print(f"  {number}. {display_path(path)}")
        by_number = {str(number): path for number, path in enumerate(paths, 1)}
        while True:
            answer = _normalize_digits(input(msg["plain_files"] + "\n> ").strip())
            if not answer:
                return paths
            if answer == "0":
                return []
            excluded = answer.replace(",", " ").split()
            if excluded and all(number in by_number for number in excluded):
                omitted = {by_number[number] for number in excluded}
                return [path for path in paths if path not in omitted]
            print(msg["invalid_choice"])

    print()
    screen.controls(msg["keys"])
    # Numbered rows keep truncated paths distinguishable, including duplicate names.
    columns = shutil.get_terminal_size().columns
    width = max(12, columns - len(str(len(paths))) - 10)
    labels = [_short_label(path, width) for path in paths]
    occurrences = Counter(labels)
    choices = [
        questionary.Choice(
            f"{number}. {display_path(path) if occurrences[label] > 1 else label}",
            value=path, checked=True,
        )
        for number, (path, label) in enumerate(zip(paths, labels, strict=False), 1)
    ]
    if any(label != display_path(path) for path, label in zip(paths, labels, strict=False)):
        screen.line(msg["full_paths"])
    print()
    return questionary.checkbox(
        msg["select"], choices, instruction=" ", qmark="▦", pointer="▸", style=_menu_style("brightmagenta"),
        erase_when_done=True, color_depth=_color_depth(),
    ).unsafe_ask()


def _short_label(path: Path, width: int) -> str:
    text = display_path(path)
    if get_cwidth(text) <= width:
        return text
    left, right = [], []
    prefix_width = width // 3
    for char in text:
        prefix_width -= get_cwidth(char)
        if prefix_width < 0:
            break
        left.append(char)
    suffix_width = width - get_cwidth("".join(left)) - 1
    for char in reversed(text):
        suffix_width -= get_cwidth(char)
        if suffix_width < 0:
            break
        right.append(char)
    return "".join(left) + "…" + "".join(reversed(right))
