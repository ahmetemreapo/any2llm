from unittest.mock import Mock

import pytest

from any2llm import prompts


@pytest.mark.parametrize(("lang", "heading", "first", "middle", "last", "synthesis"), [
    ("en", "Turn ", "Start the analysis now", "earlier findings", "Analyze this last batch", "all turns"),
    ("tr", "Tur ", "Analize bu turda başla", "önceki bulgularla", "Bu son paketi", "tüm turları"),
])
def test_multiturn_roles_and_custom_task(lang, heading, first, middle, last, synthesis):
    names = [f"batch_{i:02d}_of_4.md" for i in range(1, 5)]
    task = "Compare {A} and {B}.\nInclude café costs in ₺."
    turns = prompts.generate_prompts(names, lang, task)
    assert len(turns) == len(names)
    for i, (name, turn) in enumerate(zip(names, turns), 1):
        assert turn.startswith(f"## {heading}{i}")
        assert name in turn.splitlines()[0]
        assert task in turn
    assert first in turns[0]
    assert all(middle in turn for turn in turns[1:-1])
    assert last in turns[-1] and synthesis in turns[-1]


@pytest.mark.parametrize(("lang", "default", "single", "synthesis"), [
    ("en", "Explain the material in depth", "entire pack", "standalone synthesis"),
    ("tr", "İçeriği", "Tüm içerik bu pakette", "tek başına okunabilen bir sentez"),
])
def test_single_batch_with_blank_task(lang, default, single, synthesis):
    turn, = prompts.generate_prompts(["batch_01_of_1.md"], lang, "  ")
    assert default in turn and single in turn and synthesis in turn


def test_walkthrough_waits_only_between_uploads(monkeypatch, capsys):
    events = []
    monkeypatch.setattr(prompts.pyperclip, "copy", lambda prompt: events.append(prompt))
    monkeypatch.setattr("builtins.input", lambda _: events.append("Enter"))
    names = ["batch_01_of_2.md", "batch_02_of_2.md"]
    turns = prompts.generate_prompts(names)
    prompts.clipboard_walkthrough(names, turns)
    assert events == [turns[0], "Enter", turns[1]]
    lines = capsys.readouterr().out.splitlines()
    assert all(name in line for name, line in zip(names, lines, strict=True))


def test_walkthrough_switches_to_saved_prompts_on_clipboard_failure(monkeypatch, capsys):
    copy = Mock(side_effect=prompts.pyperclip.PyperclipException("No clipboard"))
    monkeypatch.setattr(prompts.pyperclip, "copy", copy)
    monkeypatch.setattr("builtins.input", lambda _: "")
    names = ["batch_01_of_2.md", "batch_02_of_2.md"]
    turns = prompts.generate_prompts(names, "tr")
    prompts.clipboard_walkthrough(names, turns)
    copy.assert_called_once_with(turns[0])
    output = capsys.readouterr().out
    assert "Clipboard unavailable" in output
    for number, name in enumerate(names, 1):
        assert f"Copy turn {number} from PROMPTS.md and attach {name}" in output
