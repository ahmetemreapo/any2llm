from pathlib import Path
from shutil import copyfile
from unittest.mock import Mock
from xml.etree import ElementTree

import pytest

from any2llm import cli, config, terminal, tokenizer
from any2llm.messages import MESSAGES
from any2llm.output import write_pack


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    config.save_config(config.Settings())
    monkeypatch.setattr(cli, "_interactive", lambda: True)
    monkeypatch.setattr(cli, "copy_prompt", Mock(return_value=True))


def test_checkbox_uses_file_names_and_reports_skips(tmp_path, monkeypatch, capsys):
    (tmp_path / "notes.txt").write_text("Hello!           \n\n")
    (tmp_path / "broken.xlsx").write_bytes(b"truncated")
    monkeypatch.setattr(tokenizer, "get_encoding", lambda: None)
    checkbox = Mock()
    checkbox.return_value.unsafe_ask.return_value = [Path("notes.txt")]
    monkeypatch.setattr(terminal.questionary, "checkbox", checkbox)
    for name in ("select", "text"):
        monkeypatch.setattr(terminal.questionary, name, Mock(side_effect=AssertionError))
    (tmp_path / "unused.txt").write_text("Leave this file out")

    monkeypatch.setattr(cli, "_open_folder", Mock())
    assert cli.main([str(tmp_path), "--task", "Compare examples"]) == 0
    message, choices = checkbox.call_args.args
    assert message == "Which files do you want to prepare for your chat?"
    assert [(c.title, c.value, c.checked) for c in choices] == [
        ("1. notes.txt", Path("notes.txt"), True),
        ("2. unused.txt", Path("unused.txt"), True),
    ]
    output = capsys.readouterr().out
    assert "broken.xlsx — damaged document" in output
    assert "What to do about files left out" in output
    assert "damaged document — Try a fresh copy of the document" in output
    assert "Selected documents: 1" in output
    batch = (tmp_path / "_llm_pack" / "batch_01_of_1.md").read_text(encoding="utf-8")
    assert "Hello!" in batch
    assert "unused.txt" not in batch
    prompt = (tmp_path / "_llm_pack" / "PROMPT.txt").read_text(encoding="utf-8")
    assert "Compare examples" in prompt
    cli.copy_prompt.assert_called_once_with(prompt)
    cli._open_folder.assert_called_once_with(tmp_path / "_llm_pack")


def test_noninteractive_token_override(tmp_path, monkeypatch):
    monkeypatch.setattr(tokenizer, "get_encoding", lambda: None)
    (tmp_path / "notes.md").write_text("Example line\n" * 100)
    assert cli.main([str(tmp_path), "-y", "--no-open", "--max-tokens", "100"]) == 0
    batches = list((tmp_path / "_llm_pack").glob("batch_*.md"))
    assert len(batches) > 1
    assert all(tokenizer.count_tokens(path.read_text(encoding="utf-8")) <= 100 for path in batches)
    prompts = (tmp_path / "_llm_pack" / "PROMPT.txt").read_text(encoding="utf-8")
    assert "batch_01" in prompts and '"continue"' in prompts
    cli.copy_prompt.assert_called_once_with(prompts)


def test_recursive_custom_output_rerun_with_turkish_prompts(tmp_path, monkeypatch, capsys):
    for name in ("checkbox", "select", "text"):
        monkeypatch.setattr(terminal.questionary, name, Mock(side_effect=AssertionError))
    monkeypatch.setattr(tokenizer, "get_encoding", lambda: None)
    source = tmp_path / "src"
    source.mkdir()
    (source / "notes.md").write_text("A nested file.")
    output = tmp_path / "packs" / "result"
    monkeypatch.setattr(cli, "_open_folder", Mock())
    args = [str(tmp_path), "--recursive", "--yes", "--lang", "tr", "--no-open"]
    assert cli.main([*args, "-o", "packs/result"]) == 0
    batch = output / "batch_01_of_1.md"
    first_pack = batch.read_bytes()
    assert b"src/notes.md" in first_pack
    assert cli.main([*args, "--output", str(output)]) == 0
    assert batch.read_bytes() == first_pack
    assert (output / "PROMPT.txt").read_text(encoding="utf-8").startswith("Ekteki")
    logs = capsys.readouterr().out
    assert "Seçilen belge sayısı: 1" in logs
    cli._open_folder.assert_not_called()
    assert config.load_config() == config.Settings()
    assert "## Tur" not in logs


@pytest.mark.parametrize("args", [["--lang", "de"], ["--max-tokens", "0"], ["-o"]])
def test_invalid_flags(args, capsys):
    assert cli.main(args) == 2
    assert f"{args[0]}" in capsys.readouterr().err


def test_unwritable_prompts_destination_preserves_existing_batches(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(tokenizer, "get_encoding", lambda: None)
    output = tmp_path / "_llm_pack"
    (output / "PROMPT.txt").mkdir(parents=True)
    batch = output / "batch_01_of_1.md"
    write_pack(output, {batch.name: "Previous batch"})
    (tmp_path / "notes.md").write_text("New content")
    assert cli.main([str(tmp_path), "-y"]) == 1
    assert "PROMPT.txt" in capsys.readouterr().err
    assert batch.read_text(encoding="utf-8") == "Previous batch"


@pytest.mark.parametrize(("platform", "command"), [("linux", "xdg-open"), ("darwin", "open")])
def test_folder_launcher_is_quiet_and_handles_missing_command(tmp_path, monkeypatch, platform, command):
    monkeypatch.setattr(cli.sys, "platform", platform)
    launch = Mock(side_effect=FileNotFoundError)
    monkeypatch.setattr(cli.subprocess, "Popen", launch)
    cli._open_folder(tmp_path)
    assert launch.call_args.args == ([command, str(tmp_path)],)
    assert launch.call_args.kwargs["stdout"] == cli.subprocess.DEVNULL
    assert launch.call_args.kwargs["stderr"] == cli.subprocess.DEVNULL


@pytest.mark.parametrize("multiple", [False, True])
@pytest.mark.parametrize("copied", [False, True])
@pytest.mark.parametrize("auto_open", [False, True])
def test_handoff(tmp_path, monkeypatch, capsys, multiple, copied, auto_open):
    config.save_config(config.Settings(auto_open=auto_open))
    monkeypatch.setattr(tokenizer, "get_encoding", lambda: None)
    (tmp_path / "notes.txt").write_text("A long line with a few words\n" * 40)
    copy = Mock(return_value=copied)
    opener = Mock()
    monkeypatch.setattr(cli, "copy_prompt", copy)
    monkeypatch.setattr(cli, "_open_folder", opener)
    output = tmp_path / "Chat Files"
    args = [str(tmp_path), "-y", "-o", output.name]
    if multiple:
        args.extend(["--max-tokens", "100"])
    assert cli.main(args) == 0
    handoff = capsys.readouterr().out
    batches = sorted(output.glob("batch*.md"))
    assert (len(batches) > 1) == multiple
    assert f"Files to attach: {len(batches)}" in handoff
    assert str(output) in handoff and batches[0].name in handoff
    msg = MESSAGES["en"]
    assert (msg["next"] in handoff) == multiple
    assert ("Open PROMPT.txt" in handoff) == (not copied)
    assert (msg["paste"] in handoff) == copied
    status = msg["clipboard_copied" if copied else "clipboard_failed"]
    assert handoff.index(status) < handoff.index(msg["open_chat"])
    assert msg["clipboard_failed" if copied else "clipboard_copied"] not in handoff
    copy.assert_called_once_with((output / "PROMPT.txt").read_text(encoding="utf-8"))
    assert opener.call_count == int(auto_open)


def test_noninteractive_selection_and_setup_need_a_terminal(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "_interactive", lambda: False)
    config.config_path().unlink()
    monkeypatch.setattr(config, "setup", Mock(side_effect=AssertionError))
    monkeypatch.setattr(cli, "setup", config.setup)
    (tmp_path / "notes.txt").write_text("Hello")
    assert cli.main(["--lang=tr", str(tmp_path)]) == 2
    assert "any2llm -y" in capsys.readouterr().err
    assert cli.main(["setup", "-y"]) == 2
    assert "interactive terminal" in capsys.readouterr().err
    assert cli.main(["--ui-lang", "tr", str(tmp_path), "-y"]) == 0
    assert "Yapay zekâ sohbetinizi açın" in capsys.readouterr().out
    assert not config.config_path().exists()
    config.save_config(config.Settings("tr"))
    assert cli.main([str(tmp_path)]) == 2
    assert "any2llm -y" in capsys.readouterr().err


def test_plain_menu_excludes_numbered_files(tmp_path, monkeypatch, capsys):
    for name in ("a.txt", "b.txt"):
        (tmp_path / name).write_text(name)
    answers = iter(["3", "2"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(cli, "_open_folder", Mock())
    assert cli.main([str(tmp_path), "--plain"]) == 0
    logs = capsys.readouterr().out
    assert "1. a.txt" in logs and "2. b.txt" in logs
    assert "Enter a number from the list" in logs
    batch = (tmp_path / "_llm_pack/batch_01_of_1.md").read_text(encoding="utf-8")
    assert "a.txt" in batch and "b.txt" not in batch


def test_empty_subfolder_and_no_selection(tmp_path, monkeypatch, capsys):
    child = tmp_path / "sub"
    child.mkdir()
    (child / "notes.txt").write_text("Read this")
    assert cli.main([str(tmp_path), "-y", "--no-open"]) == 0
    assert "any2llm -r" in capsys.readouterr().out
    monkeypatch.setattr(cli, "select_files", lambda *args, **kwargs: [])
    assert cli.main([str(tmp_path), "-r"]) == 0
    assert "No files selected" in capsys.readouterr().out
    assert not (tmp_path / "_llm_pack").exists()


@pytest.mark.parametrize(("folder", "message"), [
    ("missing", "Klasör bulunamadı"), ("file.txt", "Bu yol bir dosyaya ait"),
])
def test_folder_errors_and_argument_language(tmp_path, capsys, folder, message):
    (tmp_path / "file.txt").touch()
    assert cli.main([str(tmp_path / folder), "-y", "--lang", "tr"]) == 1
    assert message in capsys.readouterr().err
    assert cli.main(["--lang", "tr", "--max-tokens", "0"]) == 2
    assert "pozitif bir tam sayı" in capsys.readouterr().err


def test_in_place_output_does_not_scan_its_previous_files(tmp_path, monkeypatch):
    (tmp_path / "original.txt").write_text("Source")
    monkeypatch.setattr(cli, "_open_folder", Mock())
    args = [str(tmp_path), "-y", "-o", "."]
    assert cli.main(args) == 0
    first_batch = tmp_path / "batch_01_of_1.md"
    before = first_batch.read_bytes()
    assert cli.main(args) == 0
    assert first_batch.read_bytes() == before


def test_windows_folder_launcher(tmp_path, monkeypatch):
    startfile = Mock(side_effect=OSError)
    monkeypatch.setattr(cli.sys, "platform", "win32")
    monkeypatch.setattr(cli.os, "startfile", startfile, raising=False)
    cli._open_folder(tmp_path)
    startfile.assert_called_once_with(tmp_path)


def test_skip_details_progress_and_partial_pdf(tmp_path, monkeypatch, capsys):
    from any2llm.parsers import ParsedFile, PdfPage

    for number in range(26):
        (tmp_path / f"video-{number:02}.mp4").touch()
    (tmp_path / "photo.png").touch()
    (tmp_path / "z-workbook.xls").touch()
    (tmp_path / "report.pdf").touch()
    from any2llm import scanner

    parse_file = scanner.parse_file
    monkeypatch.setattr(scanner, "parse_file", lambda path: (
        ParsedFile("PDF", "Text", (PdfPage(17, "Text", partial=True),))
        if path.suffix == ".pdf" else parse_file(path)
    ))
    monkeypatch.setattr(cli.sys.stdout, "isatty", lambda: True)
    assert cli.main([str(tmp_path), "-y", "--no-open"]) == 0
    logs = capsys.readouterr().out
    assert "Files examined: 25" in logs and "26 × video" in logs
    assert "video-25.mp4" not in logs and "any2llm --details" in logs
    assert "z-workbook.xls" not in logs
    assert "file type we can’t read — Export the file to a supported format" in logs
    assert "image, video — Save the text from the media or a transcript as a .txt file" in logs
    assert "report.pdf — 1 PDF page" in logs
    assert cli.main([str(tmp_path), "-y", "--no-open", "--details"]) == 0
    assert "video-25.mp4" in capsys.readouterr().out


def test_image_only_pdf_page_is_reported_and_kept_in_pack(tmp_path, monkeypatch, capsys):
    sample = Path(__file__).resolve().parents[1] / "examples/delivery-dates/supplier-offer.pdf"
    copyfile(sample, tmp_path / sample.name)
    copyfile(sample, tmp_path / "unselected.pdf")
    monkeypatch.setattr(cli, "select_files", lambda *_args, **_kwargs: [Path(sample.name)])
    monkeypatch.setattr(tokenizer, "get_encoding", lambda: None)

    assert cli.main([str(tmp_path), "--lang", "en", "--no-open"]) == 0
    logs = capsys.readouterr().out
    assert "supplier-offer.pdf — PDF pages with no extractable text: 2" in logs
    assert "unselected.pdf" not in logs
    batch = (tmp_path / "_llm_pack/batch_01_of_1.md").read_text(encoding="utf-8")
    elements = ElementTree.fromstring(f"<pack>{batch}</pack>").findall("file/page")
    assert [page.get("number") for page in elements] == ["1", "2", "3"]
    assert elements[1].get("extraction") == "no-extractable-text"
    assert elements[1].text is None
    assert "Pilot shipment" in elements[0].text
    assert "Main shipment" in elements[2].text


def test_pdf_warning_groups_page_ranges(tmp_path, monkeypatch, capsys):
    from any2llm import scanner
    from any2llm.parsers import ParsedFile, PdfPage

    (tmp_path / "report.pdf").touch()
    pages = (PdfPage(1, "Text"), *(PdfPage(n, "", no_text=True) for n in (2, 3, 4, 6, 8, 9)))
    monkeypatch.setattr(scanner, "parse_file", lambda _: ParsedFile("PDF", "Text", pages))
    assert cli.main([str(tmp_path), "-y", "--lang", "tr", "--no-open"]) == 0
    logs = capsys.readouterr().out
    assert "report.pdf — Şu PDF sayfalarından metin alınamadı: 2–4, 6, 8–9" in logs
