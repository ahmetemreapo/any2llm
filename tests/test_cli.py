from pathlib import Path
from unittest.mock import Mock

import pytest

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
    task = Mock()
    task.return_value.unsafe_ask.return_value = "Explain the examples for my exam."
    monkeypatch.setattr(cli.questionary, "text", task)
    walkthrough = Mock()
    monkeypatch.setattr(cli, "clipboard_walkthrough", walkthrough)
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
    names, turns = walkthrough.call_args.args
    assert names == ["batch_01_of_1.md"]
    assert task.return_value.unsafe_ask.return_value in turns[0]
    assert (tmp_path / "_llm_pack" / "PROMPTS.md").read_text() == turns[0] + "\n"


def test_noninteractive_token_override(tmp_path, monkeypatch):
    monkeypatch.setattr(tokenizer, "get_encoding", lambda: None)
    (tmp_path / "notes.md").write_text("Example line\n" * 100)
    assert cli.main([str(tmp_path), "-y", "--max-tokens", "100"]) == 0
    batches = list((tmp_path / "_llm_pack").glob("batch_*.md"))
    assert len(batches) > 1
    assert all(tokenizer.count_tokens(path.read_text()) <= 100 for path in batches)
    prompts = (tmp_path / "_llm_pack" / "PROMPTS.md").read_text()
    assert prompts.count("## Turn ") == len(batches)
    assert "Analyze this last batch" in prompts


def test_recursive_custom_output_rerun_with_turkish_prompts(tmp_path, monkeypatch, capsys):
    for name in ("checkbox", "select", "text"):
        monkeypatch.setattr(cli.questionary, name, Mock(side_effect=AssertionError))
    monkeypatch.setattr(cli, "clipboard_walkthrough", Mock(side_effect=AssertionError))
    monkeypatch.setattr(tokenizer, "get_encoding", lambda: None)
    source = tmp_path / "src"
    source.mkdir()
    (source / "notes.md").write_text("A nested file.")
    output = tmp_path / "packs" / "result"
    args = [str(tmp_path), "--recursive", "--yes", "--lang", "tr"]
    assert cli.main([*args, "-o", "packs/result"]) == 0
    batch = output / "batch_01_of_1.md"
    first_pack = batch.read_bytes()
    assert b"src/notes.md" in first_pack
    assert cli.main([*args, "--output", str(output)]) == 0
    assert batch.read_bytes() == first_pack
    assert (output / "PROMPTS.md").read_text().startswith("## Tur 1/1")
    logs = capsys.readouterr().out
    assert "Files selected: 1" in logs
    assert "## Tur" not in logs


@pytest.mark.parametrize("args", [["--lang", "de"], ["--max-tokens", "0"], ["-o"]])
def test_invalid_flags(args, capsys):
    assert cli.main(args) == 2
    assert "Invalid command arguments" in capsys.readouterr().err


def test_unwritable_prompts_destination_preserves_existing_batches(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(tokenizer, "get_encoding", lambda: None)
    output = tmp_path / "_llm_pack"
    (output / "PROMPTS.md").mkdir(parents=True)
    batch = output / "batch_01_of_1.md"
    batch.write_text("Previous batch")
    (tmp_path / "notes.md").write_text("New content")
    assert cli.main([str(tmp_path), "-y"]) == 1
    assert "PROMPTS.md" in capsys.readouterr().err
    assert batch.read_text() == "Previous batch"
