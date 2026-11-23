import subprocess
import sys

from any2llm import parse_worker
from any2llm.parsers import ParsedFile, SkippedFile


def test_worker_timeout_terminates_slow_extraction(tmp_path, monkeypatch):
    popen = subprocess.Popen
    path = tmp_path / "notes.txt"
    path.write_text("Local notes")

    def slow_worker(command, **kwargs):
        if "any2llm.parse_worker" in command:
            assert command[-2] == str(path.resolve())
            return popen([sys.executable, "-c", "from time import sleep; sleep(30)"], **kwargs)
        return popen(command, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(parse_worker, "PARSE_TIMEOUT", 0.5)
        patch.setattr(parse_worker.subprocess, "Popen", slow_worker)
        assert parse_worker.parse_selected(path.resolve(), ocr_lang=None) == SkippedFile("parse_timeout")
    assert parse_worker.parse_selected(path.resolve(), ocr_lang=None) == ParsedFile("TXT", "Local notes")


def test_worker_handles_files_removed_after_discovery(tmp_path):
    assert parse_worker.parse_selected(tmp_path.resolve() / "missing.txt", ocr_lang=None) == SkippedFile("unreadable")


def test_worker_rejects_a_candidate_replaced_by_a_symlink(tmp_path):
    import pytest

    docs = tmp_path / "docs"
    docs.mkdir()
    outside = tmp_path / "private.txt"
    outside.write_text("Outside the scan root")
    candidate = docs / "notes.txt"
    try:
        candidate.symlink_to(outside)
    except OSError:
        pytest.skip("Creating symlinks requires filesystem support and privileges.")
    assert parse_worker.parse_selected(docs.resolve() / candidate.name, ocr_lang=None) == SkippedFile("special")
