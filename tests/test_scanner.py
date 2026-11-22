from pathlib import Path

import pytest
from docx import Document
from openpyxl import Workbook
from pptx import Presentation
from pypdf import PdfWriter

from any2llm.scanner import scan_folder


def test_scan_depth_and_ignores(tmp_path):
    for name in (".git", ".venv", ".hidden", "node_modules", "__pycache__", "_llm_pack", "src"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "nested.txt").write_text("Hello")
    (tmp_path / ".env").touch()
    (tmp_path / "empty").touch()
    assert scan_folder(tmp_path).readable == [Path("empty")]
    result = scan_folder(tmp_path, recursive=True)
    assert result.readable == [Path("empty"), Path("src/nested.txt")]
    assert not result.skipped


def test_content_detection(tmp_path):
    (tmp_path / "script").write_bytes(b"a" * 65535 + "你好".encode())
    (tmp_path / "notes").write_text("Merhaba dünya", encoding="utf-16")
    (tmp_path / "fake.txt").write_bytes(b"x" * 65536 + b"\x00")
    (tmp_path / "data").write_bytes(b"\xff")
    (tmp_path / "art.SVG").write_text("<svg/>")
    (tmp_path / "picture").write_bytes(b"\x89PNG\r\n\x1a\n")
    result = scan_folder(tmp_path)
    assert result.readable == [Path("notes"), Path("script")]
    assert result.skipped == {
        Path("fake.txt"): "binary", Path("data"): "binary",
        Path("art.SVG"): "image", Path("picture"): "image",
    }


@pytest.mark.parametrize(("name", "create"), [
    ("a.docx", Document), ("b.pptx", Presentation), ("c.xlsx", Workbook),
])
def test_office_documents(tmp_path, name, create):
    create().save(tmp_path / name)
    damaged = tmp_path / ("broken" + Path(name).suffix)
    damaged.write_bytes(b"truncated")
    result = scan_folder(tmp_path)
    assert result.readable == [Path(name)]
    assert result.skipped == {Path(damaged.name): "invalid"}


def test_pdf_and_encryption(tmp_path):
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(tmp_path / "ok.pdf")
    writer.encrypt("password")
    writer.write(tmp_path / "locked.pdf")
    (tmp_path / "broken.pdf").touch()
    result = scan_folder(tmp_path)
    assert result.readable == [Path("ok.pdf")]
    assert result.skipped == {Path("locked.pdf"): "encrypted", Path("broken.pdf"): "invalid"}


def test_read_error_does_not_stop_scan(tmp_path, monkeypatch):
    (tmp_path / "locked").touch()
    (tmp_path / "ok").touch()
    original = Path.open

    def guarded_open(path, *args, **kwargs):
        if path.name == "locked":
            raise PermissionError
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    result = scan_folder(tmp_path)
    assert result.readable == [Path("ok")]
    assert result.skipped == {Path("locked"): "unreadable"}
