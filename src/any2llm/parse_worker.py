"""Run a single extraction in a process the CLI can terminate."""

import json
import os
import signal
import subprocess
import sys
from contextlib import suppress
from dataclasses import asdict
from pathlib import Path

from .parsers import ParsedFile, PdfPage, SkippedFile, parse_file

PARSE_TIMEOUT = 120


def parse_selected(path: Path, *, ocr_lang: str | None) -> ParsedFile | SkippedFile:
    """Read a selected candidate with a wall-clock deadline."""
    try:
        with subprocess.Popen(
            [sys.executable, "-E", "-P", "-m", "any2llm.parse_worker", str(path), ocr_lang or ""],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env={**os.environ, "OPENPYXL_DEFUSEDXML": "True"},
            start_new_session=os.name == "posix",
        ) as process:
            try:
                stdout, _ = process.communicate(timeout=PARSE_TIMEOUT)
            except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
                _stop_worker(process)
                if isinstance(exc, KeyboardInterrupt):
                    raise
                return SkippedFile("parse_timeout")
        if process.returncode:
            return SkippedFile("invalid")
        payload = json.loads(stdout)
    except (OSError, ValueError):
        return SkippedFile("invalid")
    if "reason" in payload:
        return SkippedFile(payload["reason"])
    pages = tuple(PdfPage(**page) for page in payload["pages"])
    return ParsedFile(payload["file_type"], payload["text"], pages)


def _stop_worker(process: subprocess.Popen) -> None:
    # Stop native PDF tools running under the worker as well.
    if os.name == "posix":
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        return
    if os.name == "nt":
        import ctypes

        directory = ctypes.create_unicode_buffer(32768)
        length = ctypes.windll.kernel32.GetSystemDirectoryW(directory, len(directory))
        if 0 < length < len(directory):
            with suppress(OSError, subprocess.SubprocessError):
                subprocess.run(
                    [str(Path(directory.value) / "taskkill.exe"), "/F", "/T", "/PID", str(process.pid)],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5,
                )
    process.kill()


def _extract(path: Path, ocr_lang: str | None) -> ParsedFile | SkippedFile:
    try:
        if path.resolve(strict=True) != path:
            return SkippedFile("special")
    except (OSError, RuntimeError):
        return SkippedFile("unreadable")
    return parse_file(path, ocr_lang=ocr_lang)


if __name__ == "__main__":
    parsed = _extract(Path(sys.argv[1]), sys.argv[2] or None)
    sys.stdout.buffer.write(json.dumps(asdict(parsed)).encode("ascii"))
