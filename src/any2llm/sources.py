"""Scan and parse a folder for the ask and check commands."""

import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from .parsers import ParsedFile
from .pipeline import parse_paths
from .scanner import scan_folder


@dataclass
class Library:
    root: Path
    documents: dict[Path, ParsedFile]
    skipped: dict[Path, str]

    def by_name(self) -> dict[str, ParsedFile]:
        return {path.as_posix(): parsed for path, parsed in self.documents.items()}


def load(
    folder: Path, *, recursive: bool, exclude: Iterable[str] = (), include_sensitive: bool = False,
    ocr_lang: str | None = None, keep: Callable[[list[str]], list[str]] | None = None,
) -> Library:
    """Parse readable files below folder. ``keep`` may narrow the candidate names before parsing.

    Raises OSError when the folder cannot be listed.
    """
    root = Path(os.path.realpath(folder))
    result = scan_folder(root, recursive, include_sensitive=include_sensitive, exclude=exclude)
    candidates = result.candidates
    if keep is not None:
        wanted = set(keep([path.as_posix() for path in candidates]))
        candidates = [path for path in candidates if path.as_posix() in wanted]
    documents, skipped = parse_paths(root, candidates, ocr_lang=ocr_lang)
    return Library(root, documents, {**result.skipped, **skipped})
