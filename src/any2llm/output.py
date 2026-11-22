"""Publish packs without replacing files that belong to the user."""

import hashlib
import json
import re
import shutil
from collections.abc import Mapping
from pathlib import Path

_BATCH_NAME = re.compile(r"batch_[0-9]{2,}_of_[0-9]+\.md")
_DIGEST = re.compile(r"[0-9a-f]{64}")
_INDEX = ".any2llm-pack.json"
_LOCK = ".any2llm-writing"


class OutputConflict(OSError):
    def __init__(self, path: Path):
        super().__init__(f"Unowned output: {path}")
        self.filename = path


class OutputBusy(OutputConflict):
    pass


def _output_name(name: str) -> bool:
    return name == "PROMPT.txt" or _BATCH_NAME.fullmatch(name) is not None


def _index(folder: Path) -> dict[str, str]:
    path = folder / _INDEX
    if path.is_symlink():
        raise OutputConflict(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (ValueError, IsADirectoryError) as exc:
        raise OutputConflict(path) from exc
    if not isinstance(data, dict) or not all(
        _output_name(name) and isinstance(digest, str) and _DIGEST.fullmatch(digest)
        for name, digest in data.items()
    ):
        raise OutputConflict(path)
    return data


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def _matches(path: Path, digest: str) -> bool:
    return not path.is_symlink() and path.is_file() and _digest(path) == digest


def owned_outputs(folder: Path) -> set[str]:
    try:
        return {name for name, digest in _index(folder).items() if _matches(folder / name, digest)}
    except OSError:
        return set()


def write_pack(output_dir: Path, documents: Mapping[str, str]) -> list[Path]:
    """Serialize writers and restore the previous pack on a failed update."""
    if not documents:
        return []
    if not all(_output_name(name) for name in documents):
        raise ValueError("Unexpected pack filename.")

    output_dir.mkdir(parents=True, exist_ok=True)
    lock = output_dir / _LOCK
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise OutputBusy(lock) from exc

    keep_backup = False
    try:
        previous = _index(output_dir)
        owned = {name for name, digest in previous.items() if _matches(output_dir / name, digest)}
        for name in documents:
            target = output_dir / name
            if name not in owned and (target.exists() or target.is_symlink()):
                raise OutputConflict(target)

        staged = lock / "new"
        backup = lock / "previous"
        staged.mkdir()
        backup.mkdir()
        for name, text in documents.items():
            (staged / name).write_text(text, encoding="utf-8", newline="\n")
        index = {name: _digest(staged / name) for name in documents}
        (staged / _INDEX).write_text(json.dumps(index), encoding="utf-8")
        for name in owned | {_INDEX}:
            source = output_dir / name
            if source.is_file():
                shutil.copyfile(source, backup / name)

        obsolete = owned.difference(documents)
        changed = []
        try:
            for name in documents:
                changed.append(name)
                (staged / name).replace(output_dir / name)
            for name in sorted(obsolete):
                changed.append(name)
                (output_dir / name).unlink()
            changed.append(_INDEX)
            (staged / _INDEX).replace(output_dir / _INDEX)
        except BaseException:
            keep_backup = True
            for name in reversed(changed):
                # A failed replace leaves its staged file in place. In particular,
                # Windows may still have the untouched destination locked.
                if (staged / name).exists() or (name in obsolete and (output_dir / name).exists()):
                    continue
                original = backup / name
                if original.is_file():
                    original.replace(output_dir / name)
                else:
                    (output_dir / name).unlink(missing_ok=True)
            keep_backup = False
            raise
    finally:
        if not keep_backup:
            shutil.rmtree(lock)
    return [output_dir / name for name in documents]
