"""Discover selectable paths without opening candidate files."""

import os
import stat
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path

from .ignore import PathPattern, read_gitignore
from .output import owned_outputs
from .parsers import metadata_skip

IGNORED_DIRS = {
    ".venv", "__MACOSX", "__pycache__", "_llm_pack", "build", "dist", "env",
    "node_modules", "site-packages", "target", "vendor", "venv",
}
_SENSITIVE_PATTERNS = (
    "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa*", "id_ed25519*", "credentials*", "secrets*", "*.kdbx",
)


@dataclass
class ScanResult:
    """All paths are relative to the scanned directory."""

    candidates: list[Path] = field(default_factory=list)
    skipped: dict[Path, str] = field(default_factory=dict)

    has_subfolders: bool = False

def _windows_entry(entry: os.DirEntry) -> str | None:
    """Handle native hidden files and junctions."""
    info = entry.stat(follow_symlinks=False)
    if info.st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN:
        return "hidden"
    if info.st_reparse_tag == stat.IO_REPARSE_TAG_MOUNT_POINT:
        return "special"
    return None


def scan_folder(
    root: Path, recursive: bool = False, *,
    output_dir: Path | None = None, on_file: Callable[[], None] | None = None,
    include_sensitive: bool = False, exclude: Iterable[str] = (),
) -> ScanResult:
    """Scan regular files. Raise OSError if the root cannot be listed."""
    root = Path(os.path.realpath(root))
    if output_dir is not None:
        output_dir = Path(os.path.realpath(output_dir))
    generated = owned_outputs(root) if root == output_dir else set()
    result = ScanResult()
    exclusions = [PathPattern.parse(pattern) for pattern in exclude]
    gitignore = []

    def is_excluded(relative: Path, *, is_dir: bool) -> bool:
        if any(pattern.matches(relative, is_dir=is_dir) for pattern in exclusions):
            return True
        for rule in reversed(gitignore):
            if rule.pattern.matches(relative, is_dir=is_dir):
                return rule.ignored
        return False

    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as entries:
                if directory == root:
                    try:
                        gitignore = read_gitignore(root / ".gitignore")
                    except OSError:
                        result.skipped[Path(".gitignore")] = "unreadable"
                        return result
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
                        is_dir = entry.is_dir(follow_symlinks=False)
                        if is_dir and (path == output_dir or entry.name in IGNORED_DIRS):
                            continue
                        if is_excluded(relative, is_dir=is_dir):
                            continue
                        if is_dir:
                            result.has_subfolders = True
                            if recursive:
                                pending.append(path)
                            continue
                        if not entry.is_file(follow_symlinks=False):
                            result.skipped[relative] = "special"
                            continue
                        if not include_sensitive and any(
                            fnmatchcase(entry.name.lower(), pattern) for pattern in _SENSITIVE_PATTERNS
                        ):
                            result.skipped[relative] = "sensitive"
                            continue
                        if on_file is not None:
                            on_file()
                        if reason := metadata_skip(path):
                            result.skipped[relative] = reason
                        else:
                            result.candidates.append(relative)
                    except OSError:
                        result.skipped[relative] = "unreadable"
        except OSError:
            if directory == root:
                raise
            result.skipped[directory.relative_to(root)] = "unreadable"
    result.candidates.sort()
    result.skipped = dict(sorted(result.skipped.items()))
    return result
