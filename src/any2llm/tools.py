"""Resolve optional native tools without implicit executable searches."""

import os
from pathlib import Path


def resolve_tool(name: str) -> str | None:
    """Search absolute PATH entries outside the current working directory."""
    # These Windows tools ship as executables. Ignore PATHEXT and scripts.
    filename = f"{name}.exe" if os.name == "nt" else name
    try:
        cwd = Path.cwd().resolve()
    except OSError:
        return None
    for entry in os.get_exec_path():
        directory = Path(entry)
        if not directory.is_absolute():
            continue
        try:
            directory = directory.resolve(strict=True)
            if directory == cwd:
                continue
            candidate = (directory / filename).resolve(strict=True)
            if candidate.parent == cwd or not candidate.is_file():
                continue
            if os.name == "nt" and candidate.suffix.lower() != ".exe":
                continue
            if os.access(candidate, os.X_OK):
                return str(candidate)
        except (OSError, RuntimeError, ValueError):
            continue
    return None
