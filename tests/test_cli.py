from pathlib import Path
from unittest.mock import Mock

from any2llm import cli, tokenizer


def test_checkbox_uses_cleaned_token_counts_and_reports_skips(tmp_path, monkeypatch, capsys):
    (tmp_path / "notes.txt").write_text("Hello!           \n\n")
    (tmp_path / "broken.xlsx").write_bytes(b"truncated")
    monkeypatch.setattr(cli, "get_encoding", lambda: None)
    monkeypatch.setattr(tokenizer, "get_encoding", lambda: None)
    checkbox = Mock()
    checkbox.return_value.unsafe_ask.return_value = [Path("notes.txt")]
    monkeypatch.setattr(cli.questionary, "checkbox", checkbox)
    preset = Mock()
    preset.return_value.unsafe_ask.return_value = "Single File"
    monkeypatch.setattr(cli.questionary, "select", preset)
    (tmp_path / "unused.txt").write_text("Leave this file out")

    assert cli.main([str(tmp_path)]) == 0
    message, choices = checkbox.call_args.args
    assert message == "Select files"
    assert [(c.title, c.value, c.checked) for c in choices] == [
        ("notes.txt [TXT, ~2 tokens]", Path("notes.txt"), True),
        ("unused.txt [TXT, ~5 tokens]", Path("unused.txt"), True),
    ]
    output = capsys.readouterr().out
    assert "broken.xlsx — invalid document" in output
    assert "Files selected: 1" in output
    batch = (tmp_path / "_llm_pack" / "batch_01_of_1.md").read_text()
    assert "Hello!" in batch
    assert "unused.txt" not in batch


def test_noninteractive_token_override(tmp_path, monkeypatch):
    monkeypatch.setattr(tokenizer, "get_encoding", lambda: None)
    (tmp_path / "notes.md").write_text("Example line\n" * 100)
    assert cli.main([str(tmp_path), "-y", "--max-tokens", "100"]) == 0
    batches = list((tmp_path / "_llm_pack").glob("batch_*.md"))
    assert len(batches) > 1
    assert all(tokenizer.count_tokens(path.read_text()) <= 100 for path in batches)
