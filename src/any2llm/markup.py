"""Render HTML and tabular data as compact Markdown."""

import re
from collections.abc import Iterable
from html import escape
from html.parser import HTMLParser

from .cleaner import clean_text

_SKIPPED = {"script", "style", "noscript", "template", "svg", "head", "iframe", "object", "canvas"}
_BLOCKS = {
    "address", "article", "aside", "blockquote", "body", "dd", "details", "dialog", "div", "dl", "dt",
    "fieldset", "figcaption", "figure", "footer", "form", "header", "hr", "html", "li", "main", "nav", "ol",
    "p", "section", "summary", "ul",
}
_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
_TEMPLATE_MARKERS = ("{{", "{%", "<%", "<?php", "{#")
_INDENT = "\ue000"  # Marks list indentation that survives whitespace trimming.
_DOCUMENT = re.compile(r"<!doctype\s+html|<html[\s>]|<body[\s>]", re.IGNORECASE)


def markdown_table(rows: Iterable[Iterable[object]]) -> str:
    cells = []
    for row in rows:
        values = []
        for value in row:
            text = "" if value is None else str(value)
            text = escape(text, quote=False).replace("\\", "\\\\").replace("|", r"\|")
            values.append("<br>".join(text.strip().splitlines()))
        while values and not values[-1]:
            values.pop()
        if values:
            cells.append(values)
    if not cells:
        return ""
    width = max(map(len, cells))
    # Use the first non-empty row as the table header.
    cells.insert(1, ["---"] * width)
    return "\n".join("| " + " | ".join(row + [""] * (width - len(row))) + " |" for row in cells)


def is_html_document(text: str) -> bool:
    """Tell saved pages and exports apart from templates that belong in a code pack."""
    return bool(_DOCUMENT.search(text[:4096])) and not any(marker in text for marker in _TEMPLATE_MARKERS)


class _Renderer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip_depth = 0
        self.pre_depth = 0
        self.lists: list[list] = []  # [tag, item count] per open list
        self.tables: list[list[list[str]]] = []
        self.cell: list[str] | None = None

    def _write(self, text: str) -> None:
        if self.cell is not None:
            self.cell.append(text)
        else:
            self.out.append(text)

    def _break(self, count: int = 2) -> None:
        if self.cell is not None:
            self.cell.append(" ")
        else:
            # Count existing trailing line breaks so nested blocks don't stack blank lines.
            tail = "".join(self.out[-4:]).rstrip(" ")
            self.out.append("\n" * max(0, count - (len(tail) - len(tail.rstrip("\n")))))

    def handle_starttag(self, tag, attrs):
        if tag in _SKIPPED:
            self.skip_depth += tag not in _VOID
            return
        if self.skip_depth:
            return
        if re.fullmatch(r"h[1-6]", tag):
            self._break()
            self._write("#" * int(tag[1]) + " ")
        elif tag in ("ul", "ol"):
            self.lists.append([tag, 0])
            self._break(1)
        elif tag == "li":
            self._break(1)
            marker = "- "
            if self.lists:
                self.lists[-1][1] += 1
                if self.lists[-1][0] == "ol":
                    marker = f"{self.lists[-1][1]}. "
            self._write(_INDENT * max(0, len(self.lists) - 1) + marker)
        elif tag == "br":
            self._break(1)
        elif tag == "pre":
            self.pre_depth += 1
            self._break()
            self._write("```\n")
        elif tag == "table":
            self.tables.append([])
        elif tag == "tr" and self.tables:
            self.tables[-1].append([])
        elif tag in ("td", "th") and self.tables:
            if not self.tables[-1]:
                self.tables[-1].append([])
            self.cell = []
        elif tag == "img":
            alt = dict(attrs).get("alt")
            if alt:
                self._write(f"[Image: {alt}]")
        elif tag in _BLOCKS:
            self._break()

    def handle_endtag(self, tag):
        if tag in _SKIPPED:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth:
            return
        if re.fullmatch(r"h[1-6]", tag) or tag in _BLOCKS:
            if tag in ("ul", "ol") and self.lists:
                self.lists.pop()
            self._break(1 if tag in ("li", "ul", "ol") and self.lists else 2)
        elif tag == "pre" and self.pre_depth:
            self.pre_depth -= 1
            self._write("\n```")
            self._break()
        elif tag in ("td", "th") and self.cell is not None and self.tables:
            self.tables[-1][-1].append(re.sub(r"\s+", " ", "".join(self.cell)).strip())
            self.cell = None
        elif tag == "table" and self.tables:
            table = self.tables.pop()
            self._break()
            self._write(markdown_table(table))
            self._break()

    def handle_data(self, data):
        if self.skip_depth:
            return
        if self.pre_depth:
            self._write(data)
        else:
            self._write(re.sub(r"\s+", " ", data))


def html_to_text(html: str) -> str:
    """Return readable Markdown-like text without scripts, styles, or markup."""
    renderer = _Renderer()
    renderer.feed(html)
    renderer.close()
    lines = []
    in_pre = False
    for line in "".join(renderer.out).split("\n"):
        fence = line.strip() == "```"
        if not in_pre or fence:
            line = line.strip()
        lines.append(line.replace(_INDENT, "  "))
        in_pre ^= fence
    return clean_text("\n".join(lines))
