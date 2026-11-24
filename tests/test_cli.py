from pathlib import Path
from shutil import copyfile
from unittest.mock import Mock
from xml.etree import ElementTree

import pytest
from rich.text import Text

from any2llm import cli, config, ocr, parsers, terminal, tokenizer
from any2llm.messages import MESSAGES, PROMPTS
from any2llm.output import write_pack


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    config.save_config(config.Settings())
    monkeypatch.setattr(cli, "_interactive", lambda: True)
    monkeypatch.setattr(cli, "copy_prompt", Mock(return_value=True))


@pytest.mark.parametrize(("lang", "pdf", "count_text"), [
    ("en", "research-designs.pdf", "Selected documents: 4"),
    ("tr", "araştırma-desenleri.pdf", "Seçilen belge sayısı: 4"),
])
def test_demo_uses_bundled_sources_and_preserves_previous_runs(tmp_path, monkeypatch, capsys, lang, pdf, count_text):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "_interactive", lambda: False)
    saved = config.Settings(lang="fr", preset="High Detail", auto_open=False)
    config.save_config(saved)

    args = ["demo", "--lang", lang, "--no-open"]
    assert cli.main(args) == 0
    first, = tmp_path.glob(f"any2llm-demo-{lang}-*")
    batch = first / "batch_01_of_1.md"
    assert pdf in batch.read_text(encoding="utf-8")
    prompt = (first / "PROMPT.txt").read_text(encoding="utf-8")
    assert PROMPTS[lang]["reply_language"] in prompt
    assert cli.demo.QUESTIONS[lang] in prompt
    logs = capsys.readouterr().out
    assert count_text in logs and str(first) in logs and batch.name in logs

    batch.write_text("User edit", encoding="utf-8")
    assert cli.main(args) == 0
    second, = set(tmp_path.glob(f"any2llm-demo-{lang}-*")) - {first}
    assert (second / batch.name).is_file()
    assert batch.read_text(encoding="utf-8") == "User edit"
    assert config.load_config() == saved


def test_dot_demo_is_a_regular_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tokenizer, "get_encoding", lambda: None)
    folder = tmp_path / "demo"
    folder.mkdir()
    (folder / "notes.txt").write_text("My own file", encoding="utf-8")
    assert cli.main(["./demo", "-y", "--no-open"]) == 0
    pack = folder / "_llm_pack" / "batch_01_of_1.md"
    assert "My own file" in pack.read_text(encoding="utf-8")


def test_checkbox_uses_file_names_and_reports_skips(tmp_path, monkeypatch, capsys):
    (tmp_path / "notes.txt").write_text("Hello!           \n\n")
    (tmp_path / "broken.xlsx").write_bytes(b"truncated")
    monkeypatch.setattr(tokenizer, "get_encoding", lambda: None)
    parse = Mock(wraps=cli.parse_selected)
    monkeypatch.setattr(cli, "parse_selected", parse)
    checkbox = Mock()

    def choose():
        parse.assert_not_called()
        return [Path("broken.xlsx"), Path("notes.txt")]

    checkbox.return_value.unsafe_ask.side_effect = choose
    monkeypatch.setattr(terminal.questionary, "checkbox", checkbox)
    for name in ("select", "text"):
        monkeypatch.setattr(terminal.questionary, name, Mock(side_effect=AssertionError))
    (tmp_path / "unused.txt").write_text("Leave this file out")

    monkeypatch.setattr(cli, "_open_folder", Mock())
    assert cli.main([str(tmp_path), "--task", "Compare examples"]) == 0
    message, choices = checkbox.call_args.args
    assert message == "Which files do you want to prepare for your chat?"
    assert [(c.title, c.value, c.checked) for c in choices] == [
        ("1. broken.xlsx", Path("broken.xlsx"), True),
        ("2. notes.txt", Path("notes.txt"), True),
        ("3. unused.txt", Path("unused.txt"), True),
    ]
    assert [entry.args[0].name for entry in parse.call_args_list] == ["broken.xlsx", "notes.txt"]
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


def test_recursive_yes_honors_sensitive_and_exclude_flags(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "_interactive", lambda: False)
    monkeypatch.setattr(tokenizer, "get_encoding", lambda: None)
    monkeypatch.setattr(cli, "select_files", Mock(side_effect=AssertionError))
    (tmp_path / ".gitignore").write_text("credentials-ignored.json\n")
    for name in (
        "notes.txt", "credentials.json", "credentials-ignored.json", "id_rsa", "nested/server.pem",
        "scratch.tmp", "nested/skip/output.txt", "venv/library.txt", "build/library.txt",
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("example data")
    args = [str(tmp_path), "-r", "-y", "--lang", "en"]
    batch = tmp_path / "_llm_pack" / "batch_01_of_1.md"

    assert cli.main(args) == 0
    packed = batch.read_text(encoding="utf-8")
    assert all(f'name="{name}"' in packed for name in ("notes.txt", "scratch.tmp", "nested/skip/output.txt"))
    assert "credentials" not in packed and "server.pem" not in packed and "id_rsa" not in packed
    assert "library.txt" not in packed
    logs = capsys.readouterr().out
    assert "credentials.json — potentially sensitive file" in logs
    assert f'{Path("nested") / "server.pem"} — potentially sensitive file' in logs
    assert "id_rsa — potentially sensitive file" in logs

    assert cli.main([*args, "--include-sensitive", "--exclude", "*.tmp", "--exclude", "nested/skip/"]) == 0
    packed = batch.read_text(encoding="utf-8")
    assert all(f'name="{name}"' in packed for name in ("notes.txt", "credentials.json", "nested/server.pem", "id_rsa"))
    assert "credentials-ignored.json" not in packed and "library.txt" not in packed
    assert "scratch.tmp" not in packed and "nested/skip/output.txt" not in packed


@pytest.mark.parametrize("args", [["--lang", "de"], ["--max-tokens", "0"], ["-o"], ["--exclude"]])
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
    (tmp_path / "notes.txt").write_text("A long line with the word ‘örnek’\n" * 40, encoding="utf-8")
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
    msg = MESSAGES["en"]
    size = terminal.display_size(sum(batch.stat().st_size for batch in batches), msg)
    summary = msg["ready"].format(selected=1, batches=len(batches), size=size, tokens=msg["tokens_estimated"])
    assert summary in handoff
    assert str(output) in handoff and batches[0].name in handoff
    assert (msg["next"] in handoff) == multiple
    assert ("Open PROMPT.txt" in handoff) == (not copied)
    assert (msg["paste"] in handoff) == copied
    status = msg["clipboard_copied" if copied else "clipboard_failed"]
    assert handoff.index(status) < handoff.index(msg["open_chat"])
    assert msg["clipboard_failed" if copied else "clipboard_copied"] not in handoff
    copy.assert_called_once_with((output / "PROMPT.txt").read_text(encoding="utf-8"))
    assert opener.call_count == int(auto_open)


@pytest.mark.parametrize("override", [False, True])
def test_handoff_shows_token_method_for_single_file_preset(tmp_path, monkeypatch, capsys, override):
    config.save_config(config.Settings(preset="Single File", auto_open=False))
    (tmp_path / "notes.txt").write_text("Example")
    get_encoding = Mock(return_value=Mock(encode_ordinary=lambda text: [1]))
    monkeypatch.setattr(tokenizer, "get_encoding", get_encoding)
    args = [str(tmp_path), "-y", "--lang", "en"]
    if override:
        args.extend(["--max-tokens", "100"])

    assert cli.main(args) == 0
    msg = MESSAGES["en"]
    key = "tokens_cl100k" if override else "tokens_unlimited"
    assert msg[key] in capsys.readouterr().out
    assert get_encoding.called is override


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

    parse_selected = cli.parse_selected
    monkeypatch.setattr(cli, "parse_selected", lambda path, **kwargs: (
        ParsedFile("PDF", "Text", (PdfPage(17, "Text", partial=True),))
        if path.suffix == ".pdf" else parse_selected(path, **kwargs)
    ))
    monkeypatch.setattr(cli.sys.stdout, "isatty", lambda: True)
    assert cli.main([str(tmp_path), "-y", "--no-open"]) == 0
    logs = Text.from_ansi(capsys.readouterr().out).plain
    assert "Files examined: 25" in logs and "26 × video" in logs
    assert "video-25.mp4" not in logs and "any2llm --details" in logs
    assert "z-workbook.xls" not in logs
    assert "file type we can’t read — Export the file to a supported format" in logs
    assert "image, video — Save the text from the media or a transcript as a .txt file" in logs
    assert "Check the original PDF (report.pdf, page(s) 17). Only part of the text could be read." in logs
    assert cli.main([str(tmp_path), "-y", "--no-open", "--details"]) == 0
    assert "video-25.mp4" in capsys.readouterr().out


@pytest.mark.parametrize(("flags", "ocr_lang", "error"), [
    ([], None, None),
    (["--ocr"], "eng", None),
    (["--ocr-lang", "tur+eng"], "tur+eng", None),
    (["--ocr"], "eng", "ocr_tools_missing"),
    (["--ocr-lang", "tur"], "tur", "ocr_languages_missing"),
])
def test_image_only_pdf_page_is_reported_and_kept_in_pack(tmp_path, monkeypatch, capsys, flags, ocr_lang, error):
    sample = Path(__file__).resolve().parents[1] / "examples/delivery-dates/supplier-offer.pdf"
    copyfile(sample, tmp_path / sample.name)
    copyfile(sample, tmp_path / "unselected.pdf")
    monkeypatch.setattr(cli, "select_files", lambda *_args, **_kwargs: [Path(sample.name)])
    monkeypatch.setattr(tokenizer, "get_encoding", lambda: None)
    monkeypatch.setattr(parsers, "_pdftotext", lambda *_: "")
    monkeypatch.setattr(cli, "parse_selected", parsers.parse_file)
    setup = Mock(return_value=error)
    recognize = Mock(return_value="Confirm freight costs separately.\n")
    monkeypatch.setattr(ocr, "setup_error", setup)
    monkeypatch.setattr(ocr, "read_page", recognize)

    assert cli.main([str(tmp_path), "--lang", "en", "--no-open", *flags]) == 0
    captured = capsys.readouterr()
    if ocr_lang is None:
        setup.assert_not_called()
    else:
        setup.assert_called_once_with(ocr_lang)
    if error:
        assert MESSAGES["en"][error].format(lang=ocr_lang) in captured.err
    assert "unselected.pdf" not in captured.out
    directory = tmp_path / "_llm_pack"
    batch = (directory / "batch_01_of_1.md").read_text(encoding="utf-8")
    prompt = (directory / "PROMPT.txt").read_text(encoding="utf-8")
    elements = ElementTree.fromstring(f"<pack>{batch}</pack>").findall("file/page")
    assert [page.get("number") for page in elements] == ["1", "2", "3"]
    assert "Pilot shipment" in elements[0].text
    assert "Main shipment" in elements[2].text
    assert all("extraction" not in elements[index].attrib for index in (0, 2))
    if ocr_lang and not error:
        assert recognize.call_count == 1
        assert all(call.args[1:] == (2, ocr_lang) for call in recognize.call_args_list)
        assert "supplier-offer.pdf — PDF pages read with OCR: 2" in captured.out
        assert elements[1].get("extraction") == "ocr"
        assert elements[1].text == "Confirm freight costs separately."
        assert PROMPTS["en"]["ocr_sources"] in prompt
    else:
        recognize.assert_not_called()
        assert "Check the original PDF (supplier-offer.pdf, page(s) 2). No text could be read." in captured.out
        assert elements[1].get("extraction") == "no-extractable-text"
        assert elements[1].text is None
        assert PROMPTS["en"]["ocr_sources"] not in prompt


def test_pdf_warning_groups_page_ranges(tmp_path, monkeypatch, capsys):
    from any2llm.parsers import ParsedFile, PdfPage

    (tmp_path / "report.pdf").touch()
    pages = (PdfPage(1, "Text"), *(PdfPage(n, "", no_text=True) for n in (2, 3, 4, 6, 8, 9)))
    monkeypatch.setattr(cli, "parse_selected", lambda _, **_kwargs: ParsedFile("PDF", "Text", pages))
    assert cli.main([str(tmp_path), "-y", "--lang", "tr", "--no-open"]) == 0
    logs = capsys.readouterr().out
    assert "Orijinal PDF’i kontrol edin (report.pdf, sayfa 2–4, 6, 8–9). Metin okunamadı." in logs


def test_only_unusable_selected_files_produce_no_pack(tmp_path, monkeypatch, capsys):
    (tmp_path / "bad.docx").write_bytes(b"truncated")
    (tmp_path / "blank.txt").write_text("   \n")
    (tmp_path / "ignored.txt").write_text("Valid but unselected")
    selected = [Path("bad.docx"), Path("blank.txt")]
    monkeypatch.setattr(cli, "select_files", lambda *_args, **_kwargs: selected)
    assert cli.main([str(tmp_path), "--no-open", "--lang", "en"]) == 0
    output = capsys.readouterr().out
    assert "bad.docx — damaged document" in output
    assert "blank.txt — no usable content" in output
    assert "No new files were prepared" in output
    assert not (tmp_path / "_llm_pack").exists()


def test_sensitive_content_warning_lists_only_name_and_types(tmp_path, capsys, caplog):
    fake_api_key = "sk-proj-" + "synthetic" * 4
    fake_private_key = "-----BEGIN OPENSSH PRIVATE KEY-----\nsynthetic sample\n-----END OPENSSH PRIVATE KEY-----"
    (tmp_path / "notes.txt").write_text(f"{fake_api_key}\n{fake_private_key}\n", encoding="utf-8")
    assert cli.main([str(tmp_path), "-y", "--no-open", "--lang", "en"]) == 0
    captured = capsys.readouterr()
    assert "notes.txt — private key" in captured.out and "notes.txt — API key or access token" in captured.out
    assert "Review the prepared files before uploading them." in captured.out
    terminal_text = captured.out + captured.err + caplog.text
    assert fake_api_key not in terminal_text and "BEGIN OPENSSH" not in terminal_text
    batch = (tmp_path / "_llm_pack/batch_01_of_1.md").read_text(encoding="utf-8")
    assert fake_api_key in batch and fake_private_key in batch
