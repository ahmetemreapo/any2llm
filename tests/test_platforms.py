"""Exercise native filesystem behavior and both installed entry points."""

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from any2llm import languages
from any2llm.scanner import scan_folder


def test_windows_language_uses_display_language(monkeypatch):
    import ctypes
    from unittest.mock import Mock

    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(name, raising=False)
    native = Mock()
    native.kernel32.GetUserDefaultUILanguage.return_value = 0x041F
    monkeypatch.setattr(ctypes, "windll", native, raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    assert languages.system_language() == "tr"


def test_redirected_cli_with_legacy_encoding(tmp_path):
    from sysconfig import get_path

    command = shutil.which("any2llm", path=get_path("scripts"))
    assert command, "Install the project before running the tests."
    env = {
        **os.environ, "HOME": str(tmp_path), "USERPROFILE": str(tmp_path),
        "PYTHONIOENCODING": "cp1252:strict",
    }
    for entry in ([command], [sys.executable, "-m", "any2llm"]):
        help_result = subprocess.run(
            [*entry, "--help", "--lang", "tr"], env=env, cwd=tmp_path,
            stdin=subprocess.DEVNULL, capture_output=True, timeout=20, check=True,
        )
        assert "Kullanım:" in help_result.stdout.decode("utf-8")
        error = subprocess.run(
            [*entry, "--lang", "zh", "--max-tokens", "0"], env=env, cwd=tmp_path,
            stdin=subprocess.DEVNULL, capture_output=True, timeout=20,
        )
        assert error.returncode == 2
        assert "正整数" in error.stderr.decode("utf-8")


def test_installed_command_packs_unicode_paths(tmp_path):
    docs = tmp_path / "Ders notları"
    nested = docs / "資料"
    nested.mkdir(parents=True)
    (nested / "örnek.txt").write_bytes("İlk satır\r\nİkinci satır".encode())
    output = tmp_path / "Sohbet dosyaları"
    env = {
        **os.environ, "HOME": str(tmp_path), "USERPROFILE": str(tmp_path),
        "PYTHONIOENCODING": "ascii:strict",
    }
    result = subprocess.run(
        [sys.executable, "-m", "any2llm", str(docs), "-r", "-y", "--no-open",
         "-o", str(output), "--lang", "tr"],
        cwd=tmp_path, env=env, stdin=subprocess.DEVNULL, capture_output=True,
        timeout=30, check=True,
    )
    assert str(output.resolve()) in result.stdout.decode("utf-8")
    root = ET.fromstring("<root>" + (output / "batch_01_of_1.md").read_text(encoding="utf-8") + "</root>")
    assert root.find("file").get("name") == (next(nested.iterdir()).relative_to(docs)).as_posix()
    assert root.find("file").text == "İlk satır\nİkinci satır"
    assert "Türkçe" in (output / "PROMPT.txt").read_text(encoding="utf-8")


@pytest.mark.skipif(os.name != "nt", reason="Uses native Windows filesystem attributes and junctions.")
def test_windows_hidden_files_and_junctions(tmp_path):
    folder = tmp_path / "Documents"
    folder.mkdir()
    hidden = folder / "Hidden notes.txt"
    hidden.touch()
    subprocess.run(["attrib", "+h", str(hidden)], check=True)
    other = tmp_path / "Other"
    other.mkdir()
    (other / "private.txt").touch()
    link = folder / "Linked directory"
    subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", link.name, str(other)], cwd=folder, check=True)
    assert hidden.stat().st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN
    result = scan_folder(folder, recursive=True)
    assert result.readable == []
    assert result.skipped == {Path(link.name): "special"}
