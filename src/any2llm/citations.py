"""Find citations in an AI answer and check them against the extracted sources.

A checkable citation is a short verbatim quote followed by a source reference:

    "Delivery: 14 March 2026" [supplier-offer.pdf, p. 2]

The reference may use square brackets or parentheses, list several sources separated by
semicolons, use a page range, or omit the page for files without pages.
"""

import re
import unicodedata
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import PurePosixPath

from .parsers import ParsedFile

VERIFIED = "verified"
CLOSE = "close"
OTHER_PAGE = "other_page"
OTHER_FILE = "other_file"
NOT_FOUND = "not_found"
PAGE_MISSING = "page_missing"
UNKNOWN_SOURCE = "unknown_source"
NO_QUOTE = "no_quote"

PASSED = (VERIFIED, CLOSE)
FAILED = (OTHER_PAGE, OTHER_FILE, NOT_FOUND, PAGE_MISSING, UNKNOWN_SOURCE)

_GROUP = re.compile(r"\[([^\[\]\n]{3,400})\]|\(([^()\n]{3,400})\)")
# Commas and semicolons include their Arabic and full-width forms.
_REFERENCE = re.compile(
    r"^\s*(?P<source>[^\n;,،，؛；]*?[^\s\n;,،，؛；]\.[A-Za-z0-9]{1,6})\s*(?:[,:،，、]\s*(?P<locator>[^\n;؛；]*))?$",
)
_SEPARATOR = re.compile(r"[;؛；]")
_PAGES = re.compile(r"^[^\d\n]{0,16}?(?P<first>\d{1,5})(?:\s*[-–—]\s*(?P<last>\d{1,5}))?")
_QUOTE = re.compile(r"\"([^\"\n]{3,600})\"|“([^”\n]{3,600})”|«([^»\n]{3,600})»|„([^“”\n]{3,600})[“”]|"
                    r"「([^」\n]{3,600})」|『([^』\n]{3,600})』")
_ELLIPSIS = re.compile(r"\s*(?:\.\.\.|…|\[\.\.\.\]|\[…\])\s*")
_FOLD = str.maketrans({
    "‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'", "`": "'",
    "“": '"', "”": '"', "„": '"', "«": '"', "»": '"',
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-",
    "|": " ", "*": " ", "_": " ", "#": " ", " ": " ", " ": " ",
})
_CLOSE_RATIO = 0.86
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


@dataclass(frozen=True)
class Citation:
    source: str
    first_page: int | None
    last_page: int | None
    quote: str | None
    start: int
    end: int

    @property
    def label(self) -> str:
        if self.first_page is None:
            return self.source
        pages = str(self.first_page) if self.last_page in (None, self.first_page) else (
            f"{self.first_page}-{self.last_page}")
        return f"{self.source}, p. {pages}"


@dataclass(frozen=True)
class Check:
    citation: Citation
    status: str
    file: str | None = None
    found_page: int | None = None
    found_file: str | None = None


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)

    def count(self, *statuses: str) -> int:
        return sum(check.status in statuses for check in self.checks)

    @property
    def passed(self) -> bool:
        return bool(self.count(*PASSED)) and not self.count(*FAILED)


def find_citations(answer: str) -> list[Citation]:
    """Return citations in reading order, pairing each with the quote just before it."""
    citations: list[Citation] = []
    boundary = 0
    for match in _GROUP.finditer(answer):
        inner = match[1] if match[1] is not None else match[2]
        # Some models put the quote inside the brackets: ("exact words" from file.pdf, p. 2).
        inside = _quotes(inner) if _QUOTE.match(inner.lstrip()) else []
        if inside:
            inner = _QUOTE.sub(" ", inner)
        references = [_REFERENCE.match(piece) for piece in _SEPARATOR.split(inner)]
        references = [reference for reference in references if reference and _looks_like_file(reference["source"])]
        if not references:
            continue
        window_start = max(boundary, answer.rfind("\n\n", 0, match.start()) + 1)
        quotes = inside or _quotes(answer[window_start:match.start()]) or [None]
        for reference in references:
            pages = _PAGES.match(reference["locator"] or "")
            first = int(pages["first"]) if pages else None
            last = int(pages["last"]) if pages and pages["last"] else first
            if first is not None and last is not None and last < first:
                first, last = last, first
            for quote in quotes:
                citations.append(Citation(
                    source=_clean_source(reference["source"]), first_page=first, last_page=last,
                    quote=quote, start=match.start(), end=match.end(),
                ))
        boundary = match.end()
    return citations


def _clean_source(source: str) -> str:
    return source.strip().strip("`'\"*").lstrip("-–—:, ").strip()


def _looks_like_file(source: str) -> bool:
    name = source.strip().strip("`'\"*")
    # Reject things like "e.g" or a version number that only resemble a filename.
    stem, _, extension = name.rpartition(".")
    return bool(stem.strip()) and any(char.isalpha() for char in extension) and "://" not in name


def _quotes(text: str) -> list[str]:
    """Every quote since the previous citation; one source often backs several quoted phrases."""
    quotes = [next(group for group in match.groups() if group is not None) for match in _QUOTE.finditer(text)]
    return [quote.strip() for quote in quotes if len(_normalize(quote)) >= 3]


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("­", "")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = text.translate(_FOLD).casefold()
    text = re.sub(r"[\"']", "", text)
    return re.sub(r"\s+", " ", text).strip(" .,;:")


def _contains(haystack: str, quote: str) -> bool:
    """Match a normalized quote, allowing ellipses to skip text in between."""
    position = 0
    for segment in (part for part in _ELLIPSIS.split(quote) if part):
        found = haystack.find(_normalize(segment), position)
        if found < 0:
            return False
        position = found + len(_normalize(segment))
    return True


def _close(haystack: str, quote: str) -> bool:
    """Accept small differences such as a changed word or punctuation in a longer quote."""
    needle = _normalize(_ELLIPSIS.sub(" ", quote))
    if len(needle) < 16:
        return False
    words = haystack.split(" ")
    size = max(1, len(needle.split(" ")))
    numbers = Counter(_NUMBER.findall(needle))
    for index in range(len(words)):
        window = " ".join(words[index:index + size + 1])
        matcher = SequenceMatcher(None, needle, window, autojunk=False)
        if matcher.real_quick_ratio() >= _CLOSE_RATIO and matcher.quick_ratio() >= _CLOSE_RATIO and (
            matcher.ratio() >= _CLOSE_RATIO
        ) and not numbers - Counter(_NUMBER.findall(window)):
            # A changed number, date, or amount is never a small difference.
            return True
    return False


class _Source:
    def __init__(self, name: str, parsed: ParsedFile):
        self.name = name
        self.pages = {page.number: _normalize(page.text) for page in parsed.pages}
        self.text = _normalize(parsed.text)

    def locate(self, quote: str) -> tuple[bool, int | None]:
        """Return whether the quote occurs and, for paged files, on which page."""
        if self.pages:
            for number, text in self.pages.items():
                if _contains(text, quote):
                    return True, number
            return False, None
        return _contains(self.text, quote), None


def resolve_source(name: str, available: list[str]) -> str | None:
    """Match a cited name to an extracted path the way a reader would."""
    wanted = name.strip().replace("\\", "/").removeprefix("./")
    for candidate in available:
        if candidate == wanted:
            return candidate
    folded = wanted.casefold()
    for candidate in available:
        if candidate.casefold() == folded:
            return candidate
    base = PurePosixPath(folded).name
    matches = [candidate for candidate in available if PurePosixPath(candidate.casefold()).name == base]
    if len(matches) == 1:
        return matches[0]
    suffixed = [candidate for candidate in available if candidate.casefold().endswith("/" + folded)]
    if len(suffixed) == 1:
        return suffixed[0]
    # Prose before the name, as in "(see notes.txt)", is not part of it.
    words = wanted.split(" ")
    return resolve_source(" ".join(words[1:]), available) if len(words) > 1 else None


def check_answer(answer: str, documents: Mapping[str, ParsedFile]) -> Report:
    """Check every citation in an answer against extracted documents keyed by relative path."""
    sources = {name: _Source(name, parsed) for name, parsed in documents.items()}
    available = list(sources)
    report = Report()
    for citation in find_citations(answer):
        report.checks.append(_check(citation, sources, available))
    return report


def _check(citation: Citation, sources: dict[str, _Source], available: list[str]) -> Check:
    name = resolve_source(citation.source, available)
    if name is None:
        return Check(citation, UNKNOWN_SOURCE)
    source = sources[name]
    cited = None
    if source.pages and citation.first_page is not None:
        last = citation.last_page or citation.first_page
        cited = [number for number in range(citation.first_page, last + 1) if number in source.pages]
        if not cited:
            return Check(citation, PAGE_MISSING, name)
    if not citation.quote:
        return Check(citation, NO_QUOTE, name)

    quote = citation.quote
    if cited is not None:
        if any(_contains(source.pages[number], quote) for number in cited):
            return Check(citation, VERIFIED, name, cited[0])
        if any(_close(source.pages[number], quote) for number in cited):
            return Check(citation, CLOSE, name, cited[0])
    else:
        if _contains(source.text, quote):
            return Check(citation, VERIFIED, name)
        if _close(source.text, quote):
            return Check(citation, CLOSE, name)

    found, page = source.locate(quote)
    if found and page is not None:
        return Check(citation, OTHER_PAGE, name, page)
    for other_name, other in sources.items():
        if other_name != name:
            found, page = other.locate(quote)
            if found:
                return Check(citation, OTHER_FILE, name, page, other_name)
    return Check(citation, NOT_FOUND, name)


def cited_sources(answer: str) -> list[str]:
    """Names cited in an answer, in first-mention order."""
    return list(dict.fromkeys(citation.source for citation in find_citations(answer)))


_SENTENCE_END = re.compile(r"(?<=[.!?。！？])\s+")
_HEADING_BREAK = re.compile(r"(?m)^([^\n]{1,60}[^\s.!?:;,。！？])\n(?=[A-ZÀ-ÞĀ-ſА-Я0-9])")
_GROUND_RATIO = 0.6


def _sentences(text: str) -> list[str]:
    """Split on sentence ends and blank lines. Single line breaks are often PDF wrapping, not boundaries."""
    sentences = []
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # A short line without closing punctuation before a capitalized line is a heading, not wrapping.
    text = _HEADING_BREAK.sub(r"\1\n\n", text)
    for paragraph in re.split(r"\n\s*\n", text):
        flat = re.sub(r"\s+", " ", paragraph).strip()
        sentences += [sentence for sentence in _SENTENCE_END.split(flat) if sentence]
    return sentences


def ground_quotes(notes: str, documents: Mapping[str, ParsedFile]) -> str:
    """Rewrite each note quote as the full source sentence it comes from.

    Small models copy sentence fragments, or copy sentences imperfectly. Notes only feed the final
    answer, so a fragment becomes its whole sentence (which still contains it), and a misquote becomes
    the most similar sentence in the cited file. Quotes with no similar sentence are left as they are.
    """
    sources = {name: _Source(name, parsed) for name, parsed in documents.items()}
    available = list(sources)
    replacements: list[tuple[str, str, str, str]] = []
    for citation in find_citations(notes):
        name = resolve_source(citation.source, available)
        if not citation.quote or name is None:
            continue
        result = _check(citation, sources, available)
        parsed = documents[name]
        pages = [(page.number, page.text) for page in parsed.pages] or [(None, parsed.text)]
        if result.status == VERIFIED:
            pages = [(number, text) for number, text in pages if number in (None, result.found_page)]
        needle = _normalize(citation.quote)
        best: tuple[float, str, int | None] = (0.0, "", None)
        for number, text in pages:
            for sentence in _sentences(text):
                normalized = _normalize(sentence)
                if result.status == VERIFIED:
                    ratio = 1.0 if _contains(normalized, citation.quote) else 0.0
                else:
                    ratio = SequenceMatcher(None, needle, normalized, autojunk=False).ratio()
                if ratio > best[0]:
                    best = (ratio, sentence, number)
        ratio, sentence, number = best
        if ratio >= _GROUND_RATIO and _normalize(sentence) != needle:
            reference = f"[{name}, p. {number}]" if number is not None else f"[{name}]"
            replacements.append((citation.quote, sentence, notes[citation.start:citation.end], reference))
    for quote, sentence, old_reference, new_reference in replacements:
        notes = notes.replace(quote, sentence, 1).replace(old_reference, new_reference, 1)
    return notes
