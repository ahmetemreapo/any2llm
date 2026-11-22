"""Discover and parse selectable files in a folder."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from .packer import is_batch_name
from .parsers import ParsedFile, SkippedFile, parse_file

IGNORED_DIRS = {"node_modules", "__pycache__", "_llm_pack"}


@dataclass
class ScanResult:
    """All paths are relative to the scanned directory."""

    parsed: dict[Path, ParsedFile] = field(default_factory=dict)
    skipped: dict[Path, str] = field(default_factory=dict)

    @property
    def readable(self) -> list[Path]:
        return list(self.parsed)


def scan_folder(root: Path, recursive: bool = False, *, output_dir: Path | None = None) -> ScanResult:
    """Scan regular files. Raise OSError if the root cannot be listed."""
    root = Path(os.path.realpath(root))
    if output_dir is not None:
        output_dir = Path(os.path.realpath(output_dir))
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
                    if directory == output_dir and (entry.name == "PROMPTS.md" or is_batch_name(entry.name)):
                        continue
                    relative = path.relative_to(root)
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            if recursive and path != output_dir and entry.name not in IGNORED_DIRS:
                                pending.append(path)
                            continue
                        if not entry.is_file(follow_symlinks=False):
                            result.skipped[relative] = "special"
                            continue
                        parsed = parse_file(path)
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
