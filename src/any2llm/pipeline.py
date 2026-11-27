"""Parse selected files for packing, shared by the CLI and the MCP server."""

from collections.abc import Iterable
from pathlib import Path

from .parse_worker import parse_selected
from .parsers import ParsedFile, SkippedFile


def parse_paths(
    root: Path, paths: Iterable[Path], *, ocr_lang: str | None,
) -> tuple[dict[Path, ParsedFile], dict[Path, str]]:
    """Return readable documents and skip reasons, both keyed by relative path."""
    documents: dict[Path, ParsedFile] = {}
    skipped: dict[Path, str] = {}
    for path in paths:
        parsed = parse_selected(root / path, ocr_lang=ocr_lang)
        if isinstance(parsed, SkippedFile):
            skipped[path] = parsed.reason
        elif not parsed.text.strip():
            skipped[path] = "empty_file"
        else:
            documents[path] = parsed
    return documents, skipped
