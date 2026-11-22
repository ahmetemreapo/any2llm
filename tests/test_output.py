from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import pytest

from any2llm.output import OutputBusy, OutputConflict, owned_outputs, write_pack


def test_existing_user_prompt_and_numbered_file_are_never_replaced(tmp_path):
    numbered = tmp_path / "batch_09_of_9.md"
    prompt = tmp_path / "PROMPT.txt"
    numbered.write_text("User notes")
    prompt.write_text("User prompt")
    with pytest.raises(OutputConflict):
        write_pack(tmp_path, {"batch_01_of_1.md": "Batch", prompt.name: "Instructions"})
    with pytest.raises(OutputConflict):
        write_pack(tmp_path, {numbered.name: "Batch"})
    assert numbered.read_text() == "User notes" and prompt.read_text() == "User prompt"
    assert len(list(tmp_path.iterdir())) == 2


def test_modified_old_batch_is_retained(tmp_path):
    first, stale = "batch_01_of_2.md", "batch_02_of_2.md"
    write_pack(tmp_path, {first: "Generated", stale: "Generated", "PROMPT.txt": "Old"})
    (tmp_path / stale).write_text("My additions")
    write_pack(tmp_path, {"batch_01_of_1.md": "New", "PROMPT.txt": "New"})
    assert not (tmp_path / first).exists()
    assert (tmp_path / stale).read_text() == "My additions"
    assert owned_outputs(tmp_path) == {"batch_01_of_1.md", "PROMPT.txt"}


def test_failure_mid_update_restores_previous_pack(tmp_path, monkeypatch):
    batch, prompt = "batch_01_of_1.md", "PROMPT.txt"
    write_pack(tmp_path, {batch: "Old batch", prompt: "Old prompt"})
    replace = Path.replace

    def fail_prompt(self, destination):
        if destination == tmp_path / prompt:
            raise PermissionError("Injected write failure")
        return replace(self, destination)

    monkeypatch.setattr(Path, "replace", fail_prompt)
    with pytest.raises(PermissionError):
        write_pack(tmp_path, {batch: "New batch", prompt: "New prompt"})
    assert (tmp_path / batch).read_text() == "Old batch"
    assert (tmp_path / prompt).read_text() == "Old prompt"
    assert owned_outputs(tmp_path) == {batch, prompt}
    assert not (tmp_path / ".any2llm-writing").exists()


def test_concurrent_writer_cannot_change_active_pack(tmp_path, monkeypatch):
    active, release = Event(), Event()
    write_text = Path.write_text

    def pause_writer(self, text, *args, **kwargs):
        if self.name == "PROMPT.txt":
            active.set()
            assert release.wait(timeout=5)
        return write_text(self, text, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", pause_writer)
    pack = {"batch_01_of_1.md": "First batch", "PROMPT.txt": "First prompt"}
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(write_pack, tmp_path, pack)
        try:
            assert active.wait(timeout=5)
            with pytest.raises(OutputBusy):
                write_pack(tmp_path, {name: "Second" for name in pack})
        finally:
            release.set()
        assert len(first.result(timeout=5)) == 2
    assert {name: (tmp_path / name).read_text() for name in pack} == pack
