"""Match scan exclusions and simple root .gitignore rules."""

import stat
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path


@dataclass(frozen=True)
class PathPattern:
    parts: tuple[str, ...]
    match_basename: bool
    directories_only: bool

    @classmethod
    def parse(cls, pattern: str) -> "PathPattern":
        parts = tuple(pattern.strip("/").split("/"))
        return cls(parts, len(parts) == 1 and not pattern.startswith("/"), pattern.endswith("/"))

    def matches(self, path: Path, *, is_dir: bool) -> bool:
        if self.directories_only and not is_dir:
            return False
        if self.match_basename:
            return fnmatchcase(path.name, self.parts[0])

        parts = path.parts
        positions: set[int] | range = {0}
        for index, pattern in enumerate(self.parts):
            if pattern == "**":
                # A trailing /** matches entries inside a directory.
                start = min(positions)
                if index == len(self.parts) - 1:
                    start += 1
                positions = range(start, len(parts) + 1)
            else:
                positions = {i + 1 for i in positions if i < len(parts) and fnmatchcase(parts[i], pattern)}
            if not positions:
                return False
        return len(parts) in positions


@dataclass(frozen=True)
class IgnoreRule:
    pattern: PathPattern
    ignored: bool


def read_gitignore(path: Path) -> list[IgnoreRule]:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return []
    if not stat.S_ISREG(mode):
        return []

    rules = []
    for line in path.read_text(encoding="utf-8-sig", errors="surrogateescape").split("\n"):
        line = line.rstrip(" ")
        if not line or line.startswith("#"):
            continue
        ignored = not line.startswith("!")
        if not ignored or line.startswith(("\\!", "\\#")):
            line = line[1:]
        if line:
            rules.append(IgnoreRule(PathPattern.parse(line), ignored))
    return rules
