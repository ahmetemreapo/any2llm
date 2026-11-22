"""Discover and parse selectable files in a folder."""

import os
import stat
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .output import owned_outputs
from .parsers import ParsedFile, SkippedFile, parse_file

IGNORED_DIRS = {"node_modules", "__pycache__", "_llm_pack"}


@dataclass
class ScanResult:
    """All paths are relative to the scanned directory."""

    parsed: dict[Path, ParsedFile] = field(default_factory=dict)
    skipped: dict[Path, str] = field(default_factory=dict)

    has_subfolders: bool = False

    @property
    def readable(self) -> list[Path]:
        return list(self.parsed)


def _windows_entry(entry: os.DirEntry) -> str | None:
    """Handle native hidden files and junctions on Python 3.10 and newer."""
    info = entry.stat(follow_symlinks=False)
    if info.st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN:
        return "hidden"
    if info.st_reparse_tag == stat.IO_REPARSE_TAG_MOUNT_POINT:
        return "special"
    return None


def scan_folder(
    root: Path, recursive: bool = False, *,
    output_dir: Path | None = None, on_file: Callable[[], None] | None = None,
) -> ScanResult:
    """Scan regular files. Raise OSError if the root cannot be listed."""
    root = Path(os.path.realpath(root))
    if output_dir is not None:
        output_dir = Path(os.path.realpath(output_dir))
    generated = owned_outputs(root) if root == output_dir else set()
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
                    if directory == output_dir and entry.name in generated:
                        continue
                    relative = path.relative_to(root)
                    try:
                        if os.name == "nt":
                            kind = _windows_entry(entry)
                            if kind == "hidden":
                                continue
                            if kind == "special":
                                result.skipped[relative] = kind
                                continue
                        if entry.is_dir(follow_symlinks=False):
                            if path != output_dir and entry.name not in IGNORED_DIRS:
                                result.has_subfolders = True
                                if recursive:
                                    pending.append(path)
                            continue
                        if not entry.is_file(follow_symlinks=False):
                            result.skipped[relative] = "special"
                            continue
                        parsed = parse_file(path)
                        if on_file is not None:
                            on_file()
                        if isinstance(parsed, SkippedFile):
                            result.skipped[relative] = parsed.reason
                        else:
                            result.parsed[relative] = parsed
                    except OSError:
                        result.skipped[relative] = "unreadable"
        except OSError:
            if directory == root:
                raise
            result.skipped[directory.relative_to(root)] = "unreadable"
    result.parsed = dict(sorted(result.parsed.items()))
    result.skipped = dict(sorted(result.skipped.items()))
    return result
