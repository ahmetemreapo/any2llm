from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    home = tmp_path / ".home"
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
