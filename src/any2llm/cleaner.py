"""Normalize prose and remove repeated PDF page margins."""

import re
from collections import Counter

_PAGE_NUMBER = re.compile(r"page\s+\d+(?:\s*(?:of|/)\s*\d+)?", re.IGNORECASE)


def clean_text(text: str) -> str:
    """Trim trailing whitespace and collapse blank lines, preserving indentation."""
    lines = [line.rstrip() for line in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip("\n")


def clean_pages(pages: list[str]) -> str:
    """Remove page numbers and recurring first/last lines from PDF pages."""
    bodies = []
    for number, page in enumerate(pages, 1):
        lines = clean_text(page).splitlines()
        for edge in (-1, 0):
            if lines:
                margin = lines[edge].strip()
                if margin == str(number) or _PAGE_NUMBER.fullmatch(margin):
                    lines.pop(edge)
        lines = "\n".join(lines).strip("\n").splitlines()
        if lines:
            bodies.append(lines)

    headers = Counter(lines[0] for lines in bodies if len(lines) > 1)
    footers = Counter(lines[-1] for lines in bodies if len(lines) > 1)
    threshold = max(2, len(bodies) // 2 + 1)
    cleaned = []
    for lines in bodies:
        if len(lines) > 1 and headers[lines[0]] >= threshold:
            lines = lines[1:]
        if len(lines) > 1 and footers[lines[-1]] >= threshold:
            lines = lines[:-1]
        cleaned.append("\n".join(lines))
    return clean_text("\n\n".join(cleaned))
