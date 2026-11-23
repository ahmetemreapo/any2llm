import os

import pytest

from any2llm.tools import resolve_tool


@pytest.mark.parametrize("name", ["pdftotext", "pdftoppm", "tesseract"])
def test_resolution_uses_only_absolute_path_entries_outside_cwd(tmp_path, monkeypatch, name):
    cwd = tmp_path / "docs"
    cwd.mkdir()
    relative = cwd / "relative"
    relative.mkdir()
    tools = tmp_path / "tools"
    tools.mkdir()
    filename = f"{name}.exe" if os.name == "nt" else name
    for entry in (cwd, relative, tools):
        candidate = entry / filename
        candidate.touch()
        candidate.chmod(0o755)
    monkeypatch.chdir(cwd)
    untrusted = os.pathsep.join(("", ".", "relative", str(cwd)))
    monkeypatch.setenv("PATH", untrusted)
    assert resolve_tool(name) is None
    monkeypatch.setenv("PATH", os.pathsep.join((untrusted, str(tools))))
    assert resolve_tool(name) == str((tools / filename).resolve())
