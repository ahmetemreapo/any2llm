"""Pack selected, parsed files into token-limited Markdown documents."""

import re
from bisect import bisect_right
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import quoteattr

from .output import write_pack
from .parsers import ParsedFile
from .tokenizer import count_tokens

PRESETS = {"High Detail": 12_000, "Balanced": 25_000, "Single File": None}
_INVALID_XML = re.compile(r"[^\x09\x0a\x0d\x20-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]")
_CONTENT_END_TAG = re.compile(r"<\\*/(?:file|page|manifest)>")
_EMPTY_PAGE = "\ud800"  # Cannot occur in UTF-8 content.


def _xml_attribute(text: str) -> str:
    # Represent characters XML 1.0 cannot encode, including surrogateescaped paths.
    return _INVALID_XML.sub(lambda match: ascii(match[0])[1:-1], text)


def _utf8_text(text: str) -> str:
    # Keep lone surrogates printable when writing UTF-8 batches.
    return re.sub(r"[\ud800-\udfff]", lambda match: ascii(match[0])[1:-1], text)


@dataclass(frozen=True)
class _PageStart:
    offset: int
    number: int
    partial: bool
    no_text: bool


@dataclass(frozen=True)
class _Part:
    id: str
    name: str
    file_type: str
    text: str
    number: int = 0
    pages: tuple[_PageStart, ...] = ()
    start: int = 0
    end: int | None = None


def _raw_content(text: str) -> str:
    # Add one backslash even to already escaped spellings, so decoding is lossless.
    return _CONTENT_END_TAG.sub(lambda match: "<\\" + match[0][1:], text)


def _start_tag(name: str, attrs: dict[str, str]) -> str:
    attributes = " ".join(f"{key}={quoteattr(value)}" for key, value in attrs.items())
    return f"<{name} {attributes}>"


def _render_content(part: _Part) -> str:
    if not part.pages:
        return _raw_content(part.text[part.start:part.end])

    end = len(part.text) if part.end is None else part.end
    first = bisect_right(part.pages, part.start, key=lambda page: page.offset) - 1
    pages = []
    for index in range(first, len(part.pages)):
        page = part.pages[index]
        if page.offset >= end:
            break
        next_offset = part.pages[index + 1].offset if index + 1 < len(part.pages) else end
        attrs = {"number": str(page.number)}
        if page.partial:
            attrs["status"] = "partial"
        if page.no_text:
            attrs["extraction"] = "no-extractable-text"
        content = part.text[max(part.start, page.offset):min(end, next_offset)]
        pages.append(_start_tag("page", attrs) + _raw_content(content.removesuffix(_EMPTY_PAGE)) + "</page>")
    return "\n" + "\n".join(pages) + "\n"


def _render(parts: list[_Part], number: int, total: int, counts: Counter[str]) -> str:
    manifest = ET.Element("manifest", batch=str(number), total=str(total))
    blocks = []
    for part in parts:
        attrs = {"id": part.id, "name": part.name, "type": part.file_type}
        if part.number:
            attrs["part"] = f"{part.number}/{counts[part.id] or 1}"
        ET.SubElement(manifest, "entry", attrs)
        blocks.append(_start_tag("file", attrs) + _render_content(part) + "</file>")
    ET.indent(manifest)
    return "\n\n".join([ET.tostring(manifest, encoding="unicode"), *blocks]) + "\n"


def _split_end(text: str, start: int, limit: int, fits: Callable[[str], bool]) -> int:
    """Find a fitting prefix without repeatedly encoding the entire remaining file."""
    low = start
    high = min(len(text), start + 4 * limit)
    while fits(text[start:high]):
        if high == len(text):
            return high
        low, high = high, min(len(text), start + 2 * (high - start))
    while high - low > 1:
        mid = (low + high) // 2
        if fits(text[start:mid]):
            low = mid
        else:
            high = mid
    if low == start:
        raise ValueError("Token limit is too small for the file metadata and content.")
    for separator in ("\n", " ", "\t"):
        end = text.rfind(separator, start, low) + 1
        # BPE token counts can increase when shortening a prefix.
        if end > start and fits(text[start:end]):
            return end
    return low


def _group(files: list[_Part], limit: int, total: int, counts: Counter[str]) -> list[list[_Part]]:
    batches: list[list[_Part]] = [[]]

    def fits(part: _Part) -> bool:
        batch = [*batches[-1], part]
        return count_tokens(_render(batch, len(batches), total, counts)) <= limit

    for file in files:
        if fits(file):
            batches[-1].append(file)
            continue
        if batches[-1]:
            batches.append([])
            if fits(file):
                batches[-1].append(file)
                continue

        if not file.text:
            raise ValueError("Token limit is too small for the file metadata.")
        start = 0
        number = 1
        while start < len(file.text):
            part = replace(file, number=number, start=start)

            # _split_end calls this closure within the current iteration.
            def prefix_fits(prefix: str) -> bool:
                return fits(replace(part, end=start + len(prefix)))  # noqa: B023

            end = _split_end(file.text, start, limit, prefix_fits)
            batches[-1].append(replace(part, end=end))
            start = end
            number += 1
            if start < len(file.text):
                batches.append([])
    return batches


def _documents(files: list[_Part], limit: int | None) -> list[str]:
    if not files:
        return []
    if limit is None:
        return [_render(files, 1, 1, Counter())]

    reserved_total = 1
    reserved_counts: Counter[str] = Counter()
    while True:
        batches = _group(files, limit, reserved_total, reserved_counts)
        total = len(batches)
        counts = Counter(part.id for batch in batches for part in batch if part.number)
        docs = [_render(batch, i, total, counts) for i, batch in enumerate(batches, 1)]
        # Crossing a digit boundary in the final totals can require another pass.
        if all(count_tokens(doc) <= limit for doc in docs):
            return docs
        reserved_total = max(reserved_total, total)
        reserved_counts |= counts


def _pack_file(file_id: str, path: Path, parsed: ParsedFile) -> _Part:
    name, file_type = _xml_attribute(path.as_posix()), _xml_attribute(parsed.file_type)
    if not parsed.pages:
        return _Part(file_id, name, file_type, _utf8_text(parsed.text))

    pages = []
    texts = []
    offset = 0
    for page in parsed.pages:
        # An empty page needs one position of its own when splitting a PDF.
        text = _utf8_text(page.text) or _EMPTY_PAGE
        pages.append(_PageStart(offset, page.number, page.partial, page.no_text))
        texts.append(text)
        offset += len(text)
    return _Part(file_id, name, file_type, "".join(texts), pages=tuple(pages))


def build_batches(
    selected: Mapping[Path, ParsedFile],
    *,
    preset: str = "Balanced",
    max_tokens: int | None = None,
) -> dict[str, str]:
    """Render named batches in upload order."""
    limit = PRESETS[preset] if max_tokens is None else max_tokens
    if limit is not None and limit < 1:
        raise ValueError("Token limit must be positive.")
    files = [
        _pack_file(str(i), path, parsed)
        for i, (path, parsed) in enumerate(selected.items(), 1)
    ]
    docs = _documents(files, limit)
    return {f"batch_{i:02d}_of_{len(docs)}.md": doc for i, doc in enumerate(docs, 1)}


def write_batches(
    selected: Mapping[Path, ParsedFile],
    output_dir: Path,
    *,
    preset: str = "Balanced",
    max_tokens: int | None = None,
) -> list[Path]:
    """Write batches in selection order and return their paths in upload order."""
    return write_pack(output_dir, build_batches(selected, preset=preset, max_tokens=max_tokens))
