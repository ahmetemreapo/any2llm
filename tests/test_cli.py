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

    assert cli.main([str(tmp_path)]) == 0
    message, choices = checkbox.call_args.args
    assert message == "Select files"
    assert [(c.title, c.value, c.checked) for c in choices] == [
        ("notes.txt [TXT, ~2 tokens]", Path("notes.txt"), True)
    ]
    output = capsys.readouterr().out
    assert "broken.xlsx — invalid document" in output
    assert "Files selected: 1" in output
