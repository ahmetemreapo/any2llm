"""Extract readable contents and report file-level failures."""

import codecs
import mimetypes
import re
import subprocess
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import BinaryIO
from zipfile import ZipFile

from docx import Document
from docx.table import Table
from openpyxl import load_workbook
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pypdf import PdfReader

from .cleaner import clean_pages, clean_text

_CONTROL = re.compile(r"[\x00-\x08\x0e-\x1f\x7f-\x9f]")
_IMAGE_SIGNATURES = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"GIF87a", b"GIF89a")
# Common media extensions must also work without a system MIME database.
_MEDIA = {
    **dict.fromkeys((".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif", ".heic"), "image"),
    **dict.fromkeys((".mp4", ".m4v", ".mov", ".mkv", ".avi", ".webm"), "video"),
    **dict.fromkeys((".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg"), "audio"),
}
_SOURCE = set("""
    .c .cc .cpp .cs .css .go .h .hpp .html .java .js .jsx .kt .lua .php .pl
    .py .rb .rs .sh .sql .swift .ts .tsx .xml .yaml .yml .json .toml
""".split())


@dataclass(frozen=True)
class PdfPage:
    number: int
    text: str
    partial: bool = False
    no_text: bool = False


@dataclass(frozen=True)
class ParsedFile:
    file_type: str
    text: str
    pages: tuple[PdfPage, ...] = ()


@dataclass(frozen=True)
class SkippedFile:
    reason: str


def _decode(stream: BinaryIO, encoding: str) -> str | None:
    stream.seek(0)
    decoder = codecs.getincrementaldecoder(encoding)()
    chunks = []
    while True:
        block = stream.read(65536)
        text = decoder.decode(block, final=not block)
        if _CONTROL.search(text):
            return None
        chunks.append(text)
        if not block:
            return "".join(chunks)


def _plain(stream: BinaryIO, path: Path, mime: str) -> ParsedFile | SkippedFile:
    prefix = stream.read(8)
    if prefix.startswith(_IMAGE_SIGNATURES):
        return SkippedFile("image")
    if prefix.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
        encoding = "utf-32"
    elif prefix.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        encoding = "utf-16"
    elif prefix.startswith(codecs.BOM_UTF8):
        encoding = "utf-8-sig"
    else:
        encoding = "utf-8"

    suffix = path.suffix.lower()
    try:
        text = _decode(stream, encoding)
    except UnicodeDecodeError:
        # Limit legacy decoding to recognizable text formats, since most byte
        # sequences also have a Windows-1252 interpretation.
        if encoding != "utf-8" or not (mime.startswith("text/") or suffix in _SOURCE):
            return SkippedFile("binary")
        try:
            text = _decode(stream, "cp1252")
        except UnicodeDecodeError:
            return SkippedFile("binary")
    if text is None:
        return SkippedFile("binary")
    # Source files and Markdown can use trailing spaces and blank lines as data.
    if suffix == ".txt":
        content = clean_text(text)
    else:
        content = text.replace("\r\n", "\n").replace("\r", "\n")
    return ParsedFile(suffix[1:].upper() if suffix else "Text", content)


def _pdftotext(path: Path, number: int) -> str:
    try:
        result = subprocess.run(
            ["pdftotext", "-f", str(number), "-l", str(number),
             "-layout", "-nopgbrk", "-enc", "UTF-8", str(path.absolute()), "-"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=True, timeout=10,
        )
        return result.stdout.decode("utf-8")
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        return ""


def _damaged_pdf_text(text: str) -> bool:
    return bool(_CONTROL.search(text) or "\ufffd" in text)


def _pdf(stream: BinaryIO, path: Path) -> ParsedFile | SkippedFile:
    reader = PdfReader(stream, strict=True)
    if reader.is_encrypted:
        return SkippedFile("encrypted")
    texts = []
    partial = set()
    for number, page in enumerate(reader.pages, 1):
        try:
            text = page.extract_text() or ""
        except Exception:
            # A damaged page can fail independently of the rest of the PDF.
            text = ""
        else:
            if not _damaged_pdf_text(text):
                texts.append(text)
                continue
        recovered = _pdftotext(path, number)
        if recovered.strip() and not _damaged_pdf_text(recovered):
            texts.append(recovered)
        else:
            partial.add(number)
            texts.append(_CONTROL.sub("\ufffd", text or recovered))

    pages = tuple(
        PdfPage(number, cleaned, number in partial, not raw.replace("\ufffd", "").strip())
        for number, (raw, cleaned) in enumerate(zip(texts, clean_pages(texts)), 1)
    )
    text = "\n\n".join(page.text for page in pages if page.text)
    if not text.replace("\ufffd", "").strip():
        return SkippedFile("invalid" if partial else "no_pdf_text")
    return ParsedFile("PDF", text, pages)


def _markdown_table(rows: Iterable[Iterable[object]]) -> str:
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
    cells.insert(1, ["---"] * width)
    return "\n".join("| " + " | ".join(row + [""] * (width - len(row))) + " |" for row in cells)


def _docx(stream: BinaryIO) -> str:
    blocks = []
    for block in Document(stream).iter_inner_content():
        if isinstance(block, Table):
            blocks.append(_markdown_table([cell.text for cell in row.cells] for row in block.rows))
        else:
            blocks.append(block.text)
    return clean_text("\n\n".join(blocks))


def _shape_text(shapes) -> Iterator[str]:
    for shape in shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from _shape_text(shape.shapes)
        elif shape.has_text_frame:
            yield shape.text
        elif shape.has_table:
            yield _markdown_table([cell.text for cell in row.cells] for row in shape.table.rows)


def _pptx(stream: BinaryIO) -> str:
    slides = []
    for number, slide in enumerate(Presentation(stream).slides, 1):
        slides.append(f"## Slide {number}")
        slides.extend(_shape_text(slide.shapes))
    return clean_text("\n\n".join(slides))


def _xlsx(stream: BinaryIO) -> str:
    workbook = load_workbook(stream, read_only=True)
    try:
        sections = []
        for sheet in workbook.worksheets:
            sections.append(f"## {sheet.title}")
            sheet.reset_dimensions()  # Some exporters write inaccurate used ranges.
            table = _markdown_table(sheet.iter_rows(values_only=True))
            if table:
                sections.append(table)
        return "\n\n".join(sections)
    finally:
        workbook.close()


_OFFICE = {".docx": _docx, ".pptx": _pptx, ".xlsx": _xlsx}


def parse_file(path: Path) -> ParsedFile | SkippedFile:
    """Parse one file, isolating malformed documents and filesystem errors."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in _MEDIA:
        return SkippedFile(_MEDIA[suffix])
    mime = mimetypes.guess_type(path.name)[0] or ""
    if mime.startswith("image/"):
        return SkippedFile("image")
    if mime.startswith(("audio/", "video/")) and suffix not in _SOURCE:
        return SkippedFile(mime.partition("/")[0])
    if suffix in {".bin", ".doc", ".ppt", ".xls", ".rtf", ".zip", ".exe"}:
        return SkippedFile("unsupported")
    try:
        with path.open("rb") as stream:
            if suffix == ".pdf":
                return _pdf(stream, path)
            if suffix in _OFFICE:
                if stream.read(8) == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
                    # Password-protected Office packages use a compound file container.
                    return SkippedFile("compound")
                stream.seek(0)
                with ZipFile(stream) as archive:
                    if any(part.flag_bits & 1 for part in archive.infolist()):
                        return SkippedFile("encrypted")
                stream.seek(0)
                return ParsedFile(suffix[1:].upper(), _OFFICE[suffix](stream))
            return _plain(stream, path, mime)
    except OSError:
        return SkippedFile("unreadable")
    except Exception:
        # Format libraries surface many unrelated exceptions for damaged input.
        return SkippedFile("invalid")
