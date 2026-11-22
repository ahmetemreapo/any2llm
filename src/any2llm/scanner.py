"""Discover selectable files without extracting their contents."""

import codecs
import mimetypes
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO
from xml.etree import ElementTree
from zipfile import ZipFile

from pypdf import PdfReader

IGNORED_DIRS = {"node_modules", "__pycache__", "_llm_pack"}
OFFICE_PARTS = {
    ".docx": "word/document.xml",
    ".pptx": "ppt/presentation.xml",
    ".xlsx": "xl/workbook.xml",
}
CONTROL = re.compile(r"[\x00-\x08\x0e-\x1f\x7f-\x9f]")
CHUNK = 65536


@dataclass
class ScanResult:
    """All paths are relative to the scanned directory."""

    readable: list[Path] = field(default_factory=list)
    skipped: dict[Path, str] = field(default_factory=dict)


def _document_reason(stream: BinaryIO, suffix: str) -> str | None:
    try:
        if suffix == ".pdf":
            reader = PdfReader(stream, strict=True)
            if reader.is_encrypted:
                return "encrypted"
            len(reader.pages)  # Verify that the page tree is accessible.
        else:
            with ZipFile(stream) as archive:
                if any(item.flag_bits & 1 for item in archive.infolist()):
                    return "encrypted"
                for name in ("[Content_Types].xml", OFFICE_PARTS[suffix]):
                    with archive.open(name) as part:
                        ElementTree.parse(part)
    except OSError:
        return "unreadable"
    except Exception:
        # Document readers expose several exception types for malformed input.
        return "invalid"
    return None


def _skip_reason(path: Path) -> str | None:
    suffix = path.suffix.lower()
    mime = mimetypes.guess_type(path.name)[0] or ""
    if mime.startswith("image/"):
        return "image"
    with path.open("rb") as stream:
        if suffix == ".pdf" or suffix in OFFICE_PARTS:
            return _document_reason(stream, suffix)
        block = stream.read(CHUNK)
        if block.startswith((b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"GIF87a", b"GIF89a")):
            return "image"
        encoding = "utf-8"
        for bom, name in ((codecs.BOM_UTF32_LE, "utf-32"), (codecs.BOM_UTF32_BE, "utf-32"),
                          (codecs.BOM_UTF16_LE, "utf-16"), (codecs.BOM_UTF16_BE, "utf-16")):
            if block.startswith(bom):
                encoding = name
                break
        decoder = codecs.getincrementaldecoder(encoding)()
        try:
            while block:
                if CONTROL.search(decoder.decode(block)):
                    return "binary"
                block = stream.read(CHUNK)
            decoder.decode(b"", final=True)
        except UnicodeError:
            return "binary"
    return None


def scan_folder(root: Path, recursive: bool = False) -> ScanResult:
    """Scan regular files. Raise OSError if the root cannot be listed."""
    root = Path(root)
    result = ScanResult()
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if entry.name.startswith("."):
                        continue
                    path = Path(entry.path)
                    relative = path.relative_to(root)
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            if recursive and entry.name not in IGNORED_DIRS:
                                pending.append(path)
                            continue
                        if not entry.is_file(follow_symlinks=False):
                            result.skipped[relative] = "special"
                            continue
                        reason = _skip_reason(path)
                    except OSError:
                        reason = "unreadable"
                    if reason:
                        result.skipped[relative] = reason
                    else:
                        result.readable.append(relative)
        except OSError:
            if directory == root:
                raise
            result.skipped[directory.relative_to(root)] = "unreadable"
    result.readable.sort()
    result.skipped = dict(sorted(result.skipped.items()))
    return result
