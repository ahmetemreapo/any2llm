from pathlib import Path
from unittest.mock import Mock

import pytest
from docx import Document
from openpyxl import Workbook
from pptx import Presentation
from pypdf import PdfWriter

from any2llm import parsers
from any2llm.parse_worker import parse_selected
from any2llm.parsers import SkippedFile
from any2llm.scanner import scan_folder


def test_scan_depth_and_ignores(tmp_path):
    for name in (
        ".git", ".venv", ".hidden", "node_modules", "__pycache__", "_llm_pack",
        "venv", "env", "build", "dist", "target", "site-packages", "__MACOSX", "vendor", "src", "src/vendor",
    ):
        (tmp_path / name).mkdir()
        (tmp_path / name / "nested.txt").write_text("Hello")
    (tmp_path / ".env").touch()
    (tmp_path / "empty").touch()
    assert scan_folder(tmp_path).candidates == [Path("empty")]
    result = scan_folder(tmp_path, recursive=True)
    assert result.candidates == [Path("empty"), Path("src/nested.txt")]
    assert not result.skipped


@pytest.mark.parametrize("name", [
    "server.pem", "server.KEY", "keystore.p12", "client.pfx", "id_rsa", "id_rsa.pub",
    "ID_ED25519.backup", "credentials.json", "Secrets.local.txt", "vault.kdbx",
])
def test_sensitive_files_are_not_parsed_without_opt_in(tmp_path, monkeypatch, name):
    relative = Path("nested") / name
    path = tmp_path / relative
    path.parent.mkdir()
    path.write_text("example data")
    opener = Mock(side_effect=AssertionError("Discovery must not open candidate content."))
    monkeypatch.setattr(parsers, "open", opener, raising=False)

    result = scan_folder(tmp_path, recursive=True)
    assert result.candidates == []
    assert result.skipped == {relative: "sensitive"}
    opener.assert_not_called()

    result = scan_folder(tmp_path, recursive=True, include_sensitive=True)
    assert result.candidates == [relative]
    assert not result.skipped
    opener.assert_not_called()


def test_root_gitignore_matches_simple_git_patterns(tmp_path):
    (tmp_path / ".gitignore").write_text(
        "# comment\n\n*.log\n!keep.log\n/root.txt\nscratch/\ndocs/*.tmp\n"
        "archives/**/draft?.txt\ndocs/out/**\n!docs/out/keep.txt\n"
        "excluded/\n!excluded/keep.txt\n\\!literal.txt\n\\#literal.txt\n",
        encoding="utf-8-sig",
    )
    excluded = [
        "debug.log", "sub/debug.log", "root.txt", "sub/scratch/cache.txt", "docs/drop.tmp",
        "archives/draft1.txt", "archives/x/y/draft2.txt", "docs/out/drop.txt",
        "excluded/keep.txt", "!literal.txt", "#literal.txt",
    ]
    kept = ["keep.log", "docs/keep.log", "docs/nested/keep.tmp", "sub/root.txt", "docs/scratch", "docs/out/keep.txt"]
    for name in [*excluded, *kept]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("example data")
    (tmp_path / "docs" / ".gitignore").write_text("keep.log\n")

    result = scan_folder(tmp_path, recursive=True)
    assert result.candidates == sorted(map(Path, kept))
    assert not result.skipped


def test_excluded_directories_do_not_count_as_subfolders(tmp_path):
    (tmp_path / "venv").mkdir()
    (tmp_path / "root-ignore").mkdir()
    (tmp_path / "cli-ignore").mkdir()
    (tmp_path / ".gitignore").write_text("/root-ignore/\n")

    result = scan_folder(tmp_path, exclude=["cli-ignore/"])
    assert not result.has_subfolders


def test_unreadable_gitignore_is_reported_before_files_are_selected(tmp_path, monkeypatch):
    (tmp_path / ".gitignore").touch()
    (tmp_path / "notes.txt").touch()
    original = Path.read_text

    def guarded_read(path, *args, **kwargs):
        if path.name == ".gitignore":
            raise PermissionError
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read)
    result = scan_folder(tmp_path)
    assert result.candidates == []
    assert result.skipped == {Path(".gitignore"): "unreadable"}


def test_content_detection(tmp_path):
    (tmp_path / "script").write_bytes(b"a" * 65535 + "你好".encode())
    (tmp_path / "notes").write_text("Merhaba dünya", encoding="utf-16")
    (tmp_path / "fake.txt").write_bytes(b"x" * 65536 + b"\x00")
    (tmp_path / "data").write_bytes(b"\xff")
    (tmp_path / "art.SVG").write_text("<svg/>")
    (tmp_path / "video.mp4").touch()
    (tmp_path / "audio.mp3").touch()
    (tmp_path / "page.html").write_text("<h1>Title</h1>")
    (tmp_path / "picture").write_bytes(b"\x89PNG\r\n\x1a\n")
    result = scan_folder(tmp_path)
    assert result.candidates == list(map(Path, ["data", "fake.txt", "notes", "page.html", "picture", "script"]))
    parsed, skipped = _parse_candidates(tmp_path, result)
    assert parsed == [Path("notes"), Path("page.html"), Path("script")]
    assert skipped == {
        Path("fake.txt"): "binary", Path("data"): "binary",
        Path("art.SVG"): "image", Path("picture"): "image",
        Path("video.mp4"): "video", Path("audio.mp3"): "audio",
    }


@pytest.mark.parametrize(("name", "create"), [
    ("a.docx", Document), ("b.pptx", Presentation), ("c.xlsx", Workbook),
])
def test_office_documents(tmp_path, name, create):
    create().save(tmp_path / name)
    damaged = tmp_path / ("broken" + Path(name).suffix)
    damaged.write_bytes(b"truncated")
    result = scan_folder(tmp_path)
    parsed, skipped = _parse_candidates(tmp_path, result)
    assert parsed == [Path(name)]
    assert skipped == {Path(damaged.name): "invalid"}


def test_pdf_and_encryption(tmp_path):
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(tmp_path / "ok.pdf")
    writer.encrypt("password")
    writer.write(tmp_path / "locked.pdf")
    (tmp_path / "broken.pdf").touch()
    result = scan_folder(tmp_path)
    parsed, skipped = _parse_candidates(tmp_path, result)
    assert parsed == []
    assert skipped == {
        Path("ok.pdf"): "no_pdf_text", Path("locked.pdf"): "encrypted", Path("broken.pdf"): "invalid",
    }


def _parse_candidates(root, result):
    parsed = []
    skipped = dict(result.skipped)
    for relative in result.candidates:
        document = parse_selected(root.resolve() / relative, ocr_lang=None)
        if isinstance(document, SkippedFile):
            skipped[relative] = document.reason
        else:
            parsed.append(relative)
    return parsed, skipped


def test_discovery_skips_symlinks_to_files_and_directories(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    source = outside / "notes.txt"
    source.write_text("Outside the scan root")
    try:
        (docs / "notes.txt").symlink_to(source)
        (docs / "nested").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Creating symlinks requires filesystem support and privileges.")
    scan = scan_folder(docs, recursive=True)
    assert scan.candidates == []
    assert scan.skipped == {Path("nested"): "special", Path("notes.txt"): "special"}
