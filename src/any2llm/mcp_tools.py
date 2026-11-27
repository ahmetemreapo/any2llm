"""Read-only document tools exposed by the MCP server."""

import os
from dataclasses import dataclass
from pathlib import Path

from .check import render
from .citations import check_answer, find_citations, resolve_source
from .messages import MESSAGES
from .packer import build_batches
from .parsers import ParsedFile, SkippedFile
from .pipeline import parse_paths
from .scanner import scan_folder
from .secrets import finding_types
from .terminal import display_page_ranges, display_path

DEFAULT_TOKENS = 25_000
MIN_TOKENS = 1_000
MAX_TOKENS = 200_000
MAX_FILES = 100
MAX_LISTED = 1_000

_FOLDER = {"type": "string", "description": "Folder to read, relative to the server root or absolute inside it.",
           "default": "."}
_RECURSIVE = {"type": "boolean", "description": "Include subfolders.", "default": False}

TOOLS = [
    {
        "name": "list_documents",
        "title": "List documents",
        "description": (
            "List the files any2llm can read in a folder: PDF, Word, PowerPoint, Excel, EPUB, HTML, CSV, "
            "Markdown, text, and source code. Also lists files it will skip and why (for example encrypted, "
            "image-only, or sensitive). Call this before read_documents to choose paths."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"folder": _FOLDER, "recursive": _RECURSIVE},
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "read_documents",
        "title": "Read documents",
        "description": (
            "Extract text from local documents as Markdown inside <file> blocks. PDF text is wrapped in "
            "<page number=\"N\"> tags with the physical page number, so cite answers as (file name, page N) and "
            "tell the user which pages had no extractable text. Excel sheets become tables with values and "
            "formulas. Large results are split into batches; the reply says when to call again with the next "
            "batch number."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "folder": _FOLDER,
                "paths": {
                    "type": "array", "items": {"type": "string"},
                    "description": "File paths relative to folder, as list_documents prints them. "
                                   "Omit to read every readable file.",
                },
                "recursive": _RECURSIVE,
                "batch": {"type": "integer", "minimum": 1, "default": 1,
                          "description": "Batch number to return when the content spans several batches."},
                "max_tokens": {"type": "integer", "minimum": MIN_TOKENS, "maximum": MAX_TOKENS,
                               "default": DEFAULT_TOKENS, "description": "Token budget per batch."},
            },
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "check_citations",
        "title": "Check citations",
        "description": (
            "Check an answer's citations against the original documents before you show it to the user. Write each "
            "citation as a short quote copied word for word, followed by its source: \"exact words\" [filename, p. N] "
            "(omit \", p. N\" for files without pages). The result marks each citation as found on the cited page, "
            "found elsewhere (with the right page or file), or not found. Fix or remove failed citations."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "answer": {"type": "string", "description": "The answer text with its citations."},
                "folder": _FOLDER,
            },
            "required": ["answer"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
]


class ToolError(Exception):
    """A problem the model can fix by changing its arguments."""


@dataclass(frozen=True)
class _CacheKey:
    path: str
    size: int
    modified: int
    ocr_lang: str | None


class Library:
    """Serve documents below one root folder."""

    def __init__(self, root: Path, *, lang: str = "en", ocr_lang: str | None = None):
        self.root = Path(os.path.realpath(root))
        self.msg = MESSAGES[lang]
        self.ocr_lang = ocr_lang
        self._cache: dict[_CacheKey, ParsedFile | SkippedFile] = {}

    def call(self, name: str, arguments: dict) -> str:
        if name == "list_documents":
            return self.list_documents(**_options(arguments, {"folder": str, "recursive": bool}))
        if name == "read_documents":
            return self.read_documents(**_options(
                arguments, {"folder": str, "paths": list, "recursive": bool, "batch": int, "max_tokens": int},
            ))
        if name == "check_citations":
            return self.check_citations(**_options(arguments, {"answer": str, "folder": str}))
        raise KeyError(name)

    def _folder(self, folder: str) -> Path:
        candidate = Path(folder).expanduser()
        resolved = Path(os.path.realpath(candidate if candidate.is_absolute() else self.root / candidate))
        if resolved != self.root and self.root not in resolved.parents:
            raise ToolError(f"{folder} is outside the server root {self.root}.")
        if not resolved.is_dir():
            raise ToolError(f'{self.msg["not_folder"]}: {display_path(folder)}')
        return resolved

    def _scan(self, folder: Path, recursive: bool):
        try:
            return scan_folder(folder, recursive)
        except OSError as exc:
            raise ToolError(f'{self.msg["read_folder"]}: {display_path(folder)}') from exc

    def list_documents(self, folder: str = ".", recursive: bool = False) -> str:
        directory = self._folder(folder)
        result = self._scan(directory, recursive)
        lines = [f"Folder: {directory}", f"Readable files ({len(result.candidates)}):"]
        lines += [f"- {display_path(path.as_posix())}" for path in result.candidates[:MAX_LISTED]]
        if len(result.candidates) > MAX_LISTED:
            lines.append(f"… {len(result.candidates) - MAX_LISTED} more. List a subfolder to see them.")
        if result.skipped:
            lines.append(f"Skipped ({len(result.skipped)}):")
            lines += [f"- {display_path(path.as_posix())} — {self.msg[reason]}"
                      for path, reason in list(result.skipped.items())[:MAX_LISTED]]
        if not recursive and result.has_subfolders:
            lines.append("This folder has subfolders. Call again with recursive=true to include them.")
        return "\n".join(lines)

    def read_documents(
        self, folder: str = ".", paths: list | None = None, recursive: bool = False,
        batch: int = 1, max_tokens: int = DEFAULT_TOKENS,
    ) -> str:
        if not MIN_TOKENS <= max_tokens <= MAX_TOKENS:
            raise ToolError(f"max_tokens must be between {MIN_TOKENS} and {MAX_TOKENS}.")
        if batch < 1:
            raise ToolError("batch must be 1 or greater.")
        directory = self._folder(folder)
        notes = []
        if paths:
            if not all(isinstance(path, str) for path in paths):
                raise ToolError("paths must be a list of strings.")
            result = self._scan(directory, True)
            available = set(result.candidates)
            selected = []
            for path in dict.fromkeys(Path(path) for path in paths):
                if path in available:
                    selected.append(path)
                else:
                    reason = result.skipped.get(path)
                    label = self.msg[reason] if reason else "not found or not readable here"
                    notes.append(f"Skipped {display_path(path.as_posix())} — {label}")
        else:
            result = self._scan(directory, recursive)
            selected = result.candidates
            notes += [f"Skipped {display_path(path.as_posix())} — {self.msg[reason]}"
                      for path, reason in result.skipped.items()]
        if len(selected) > MAX_FILES:
            raise ToolError(
                f"{len(selected)} files match. Read at most {MAX_FILES} at a time by passing paths from "
                "list_documents.",
            )
        documents, skipped = self._parse(directory, selected)
        notes += [f"Skipped {display_path(path.as_posix())} — {self.msg[reason]}" for path, reason in skipped.items()]
        if not documents:
            return "\n".join([self.msg["empty"], *notes])

        batches = list(build_batches(documents, max_tokens=max_tokens).values())
        if batch > len(batches):
            raise ToolError(f"batch {batch} does not exist. This content has {len(batches)} batch(es).")
        header = [f"any2llm batch {batch} of {len(batches)} · {len(documents)} file(s) from {directory}"]
        for path, document in documents.items():
            name = display_path(path.as_posix())
            missing = [page.number for page in document.pages if page.no_text]
            if missing:
                header.append(f"{name}: no extractable text on page(s) {display_page_ranges(missing, self.msg)}.")
            recognized = [page.number for page in document.pages if page.ocr]
            if recognized:
                header.append(f"{name}: page(s) {display_page_ranges(recognized, self.msg)} were read with OCR; "
                              "flag uncertain readings.")
            header += [f"{name}: may contain a {self.msg[kind]}; do not repeat it." for kind in finding_types(
                document.text)]
        footer = []
        if batch < len(batches):
            footer.append(f"More content remains. Call read_documents again with the same arguments and "
                          f"batch={batch + 1}.")
        return "\n".join([*header, *notes, "", batches[batch - 1], *footer])

    def check_citations(self, answer: str, folder: str = ".") -> str:
        directory = self._folder(folder)
        result = self._scan(directory, True)
        available = [path.as_posix() for path in result.candidates]
        wanted = {resolve_source(citation.source, available) for citation in find_citations(answer)}
        paths = result.candidates if len(available) <= 50 else [
            path for path in result.candidates if path.as_posix() in wanted]
        documents, _ = self._parse(directory, paths[:MAX_FILES])
        report = check_answer(answer, {path.as_posix(): parsed for path, parsed in documents.items()})
        return "\n".join(line for _, line in render(report, self.msg))

    def _parse(self, directory: Path, paths: list[Path]):
        cached, pending = {}, []
        for path in paths:
            key = self._key(directory / path)
            if key is not None and key in self._cache:
                cached[path] = self._cache[key]
            else:
                pending.append(path)
        documents, skipped = parse_paths(directory, pending, ocr_lang=self.ocr_lang)
        for path in pending:
            key = self._key(directory / path)
            if key is not None:
                if len(self._cache) >= 256:
                    self._cache.pop(next(iter(self._cache)))
                self._cache[key] = documents.get(path) or SkippedFile(skipped[path])
        for path, value in cached.items():
            if isinstance(value, SkippedFile):
                skipped[path] = value.reason
            else:
                documents[path] = value
        # Keep the caller's order, which decides batch contents.
        order = {path: index for index, path in enumerate(paths)}
        return dict(sorted(documents.items(), key=lambda item: order[item[0]])), skipped

    def _key(self, path: Path) -> _CacheKey | None:
        try:
            info = path.stat()
        except OSError:
            return None
        return _CacheKey(str(path), info.st_size, info.st_mtime_ns, self.ocr_lang)


def _options(arguments: dict, types: dict[str, type]) -> dict:
    if not isinstance(arguments, dict):
        raise ToolError("arguments must be an object.")
    options = {}
    for name, value in arguments.items():
        expected = types.get(name)
        if expected is None:
            raise ToolError(f"Unknown argument: {name}")
        # JSON booleans are not integers here.
        if not isinstance(value, expected) or (expected is int and isinstance(value, bool)):
            raise ToolError(f"{name} must be of type {expected.__name__}.")
        options[name] = value
    return options
