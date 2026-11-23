from subprocess import CalledProcessError, CompletedProcess, TimeoutExpired
from unittest.mock import Mock

import pytest

from any2llm import ocr


def test_renders_only_requested_page_and_passes_image_in_memory(tmp_path, monkeypatch):
    pdf = tmp_path / "my notes.pdf"
    run = Mock(side_effect=[
        CompletedProcess("pdftoppm", 0, stdout=b"png data"),
        CompletedProcess("tesseract", 0, stdout="Ders notları\n\f".encode()),
    ])
    monkeypatch.setattr(ocr.subprocess, "run", run)

    assert ocr.read_page(pdf, 17, "tur+eng") == "Ders notları\n\f"
    render, recognize = run.call_args_list
    assert render.args[0][:6] == ["pdftoppm", "-f", "17", "-l", "17", "-singlefile"]
    assert render.args[0][-1] == str(pdf)
    assert recognize.args[0] == ["tesseract", "stdin", "stdout", "-l", "tur+eng"]
    assert recognize.kwargs["input"] == b"png data"


@pytest.mark.parametrize("failure", [
    FileNotFoundError(), CalledProcessError(1, "tesseract"), TimeoutExpired("tesseract", 30),
    CompletedProcess("tesseract", 0, stdout=b"\xff"),
])
def test_failed_recognition_returns_no_text(tmp_path, monkeypatch, failure):
    run = Mock(side_effect=[CompletedProcess("pdftoppm", 0, stdout=b"png data"), failure])
    monkeypatch.setattr(ocr.subprocess, "run", run)
    assert ocr.read_page(tmp_path / "scan.pdf", 1, "eng") == ""


def test_setup_reports_missing_tools_and_languages(monkeypatch):
    run = Mock(return_value=CompletedProcess("tesseract", 0, stdout=b"List of available languages (2):\neng\ntur\n"))
    monkeypatch.setattr(ocr.subprocess, "run", run)
    monkeypatch.setattr(ocr, "which", lambda _: None)
    assert ocr.setup_error("eng") == "ocr_tools_missing"
    run.assert_not_called()

    monkeypatch.setattr(ocr, "which", lambda name: name)
    assert ocr.setup_error("eng+tur") is None
    assert ocr.setup_error("eng+fra") == "ocr_languages_missing"
