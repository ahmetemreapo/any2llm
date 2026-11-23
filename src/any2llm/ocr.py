"""Read scanned PDF pages using optional local command-line tools."""

import subprocess
from pathlib import Path

from .tools import resolve_tool


def setup_error(language: str) -> str | None:
    """Check the tools and requested language models once per CLI run."""
    tesseract = resolve_tool("tesseract")
    if not tesseract or not resolve_tool("pdftoppm"):
        return "ocr_tools_missing"
    try:
        result = subprocess.run(
            [tesseract, "--list-langs"], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True, timeout=10,
        )
        available = result.stdout.decode("utf-8", errors="replace").splitlines()[1:]
    except (OSError, subprocess.SubprocessError):
        return "ocr_tools_missing"
    if not set(language.split("+")).issubset(available):
        return "ocr_languages_missing"
    return None


def read_page(path: Path, number: int, language: str) -> str:
    """Render one physical page and pass its PNG to Tesseract in memory."""
    pdftoppm = resolve_tool("pdftoppm")
    tesseract = resolve_tool("tesseract")
    if not pdftoppm or not tesseract:
        return ""
    page = str(number)
    try:
        rendered = subprocess.run(
            [pdftoppm, "-f", page, "-l", page, "-singlefile", "-scale-to", "3300", "-gray", "-png",
             str(path.absolute())],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=True, timeout=30,
        )
        result = subprocess.run(
            [tesseract, "stdin", "stdout", "-l", language], input=rendered.stdout,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True, timeout=30,
        )
        return result.stdout.decode("utf-8")
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        return ""
