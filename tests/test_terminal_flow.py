"""Exercise the real terminal menus with keyboard input."""

import errno
import json
import os
import re
import select
import signal
import struct
import subprocess
import sys
from pathlib import Path
from time import monotonic

import pytest

from any2llm.config import Settings, save_config
from any2llm.languages import LANGUAGE_NAMES
from any2llm.messages import MESSAGES, PROMPTS

if os.name != "posix":
    pytest.skip("Pseudo-terminal tests require POSIX.", allow_module_level=True)

import fcntl
import pty
import termios

_ANSI = re.compile(rb"\x1b\[[0-?]*[ -/]*[@-~]")


@pytest.fixture(params=[False, True], ids=["clipboard-unavailable", "clipboard-available"])
def clipboard_available(request):
    return request.param


def _run_menu(executable, folder, home, columns, steps, *, plain=False, color=False, locale="C"):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 32, columns, 0, 0))
    args = ["--plain"] if plain else []
    env = {
        **os.environ, "HOME": str(home), "TERM": "xterm", "PROMPT_TOOLKIT_NO_CPR": "1",
        "NO_COLOR": "1", "PYTHONIOENCODING": "utf-8", "TIKTOKEN_CACHE_DIR": "",
        "LC_ALL": locale,
    }
    for key in ("WAYLAND_DISPLAY", "DISPLAY"):
        env.pop(key, None)
    if color:
        env.pop("NO_COLOR")

    with subprocess.Popen(
        [*executable, *args], cwd=folder, env=env, stdin=slave, stdout=slave, stderr=slave,
    ) as process:
        os.close(slave)
        transcript = b""

        def read():
            if select.select([master], [], [], 0.1)[0]:
                try:
                    return os.read(master, 65536)
                except OSError as exc:
                    if exc.errno != errno.EIO:
                        raise
            return b""

        try:
            for expected, keys in steps:
                deadline = monotonic() + 8
                seen = b""
                while expected.encode("utf-8") not in _ANSI.sub(b"", seen):
                    seen += read()
                    assert monotonic() < deadline and process.poll() is None, (expected, seen)
                transcript += seen
                if keys == b"\x03" and plain:
                    process.send_signal(signal.SIGINT)
                else:
                    os.write(master, keys)
            deadline = monotonic() + 12
            while process.poll() is None:
                transcript += read()
                assert monotonic() < deadline, transcript
            while extra := read():
                transcript += extra
            return process.returncode, _ANSI.sub(b"", transcript).decode(), transcript
        finally:
            if process.poll() is None:
                process.kill()
            os.close(master)


@pytest.mark.parametrize(("columns", "language", "mode"), [
    (40, "tr", "monochrome"), (68, "en", "color"), (80, "tr", "plain"),
])
def test_first_run_and_daily_keyboard_flow(tmp_path, columns, language, mode, clipboard_available):
    folder = tmp_path / "Test Documents"
    folder.mkdir()
    (folder / "A Notes.txt").write_text("Keep this")
    other = "Z " + "Uzun çalışma adı " * 4 + "照片.txt"
    (folder / other).write_text("Leave this out")
    (folder / "Video.mp4").write_bytes(b"video")
    executable = [
        sys.executable, "-c",
        f"from any2llm import cli; cli.copy_prompt = lambda _: {clipboard_available!r}; "
        "raise SystemExit(cli.main())",
    ]
    turkish = language == "tr"
    plain = mode == "plain"
    setup = [
        ("Choose your language", b"11\r" if plain else (b"\x1b[A\r" if turkish else b"\r")),
        ("Belgelerinizi" if turkish else "How should we", b"\r"),
        ("Hayır" if turkish else "No", b"2\r" if plain else b"\x1b[B\r"),
    ]
    select_title = "Sohbete hazırlamak" if turkish else "Which files"
    selection = b"2\r" if plain else b"\x1b[B \r"
    code, text, raw = _run_menu(
        executable, folder, tmp_path, columns, [*setup, (select_title, selection)],
        plain=plain, color=mode == "color",
    )
    assert code == 0 and "Video.mp4" in text and "batch_01_of_1.md" in text
    assert str((folder / "_llm_pack").resolve()) in text
    lines = text.replace("\r", "")
    banner = "\nany2llm\n" if plain else "│   any2llm   │"
    assert lines.count(banner) == 1
    assert f"\n\n{MESSAGES['en']['welcome']}\n\n" in lines
    if not plain:
        assert "╰─────────╯" in lines and "╰───┬─────────╯" in lines
        assert "▸" in lines and "‹↑↓›" in lines and "‹Enter›" in lines
        assert ("‹Boşluk›" if turkish else "‹Space›") in lines
        assert "[key." not in lines
    msg = MESSAGES[language]
    saved_icon, scan_icon, chat_icon = ("", "", "") if plain else ("✓  ", "⌕  ", "↗  ")
    assert f'\n\n{saved_icon}{msg["saved"]}\n{msg["setup_again"]}\n\n{scan_icon}{msg["scanning"]}' in lines
    assert f'\n\n{chat_icon}{msg["open_chat"]}\n' in lines
    clipboard_status = msg["clipboard_copied" if clipboard_available else "clipboard_failed"]
    assert clipboard_status in lines
    assert msg["paste" if clipboard_available else "clipboard"] in lines
    attachment = msg["attach_one"].format(name="batch_01_of_1.md")
    assert f"\r\n{attachment}\r\n".encode() in raw
    styles = [set(map(int, sgr.split(b";"))) for sgr in re.findall(rb"\x1b\[([\d;]+)m", raw)]
    colors = set().union(*styles)
    background_codes = {*range(40, 48), *range(100, 108)}
    if mode == "color":
        assert {32, 33, 36, 94, 95, 96} <= colors
        assert colors & background_codes == {44}
        assert all(97 in style for style in styles if 44 in style)
        icon, color = ("✓", 92) if clipboard_available else ("▲", 33)
        assert f"\r\n\x1b[1;{color}m{icon}  {clipboard_status}\x1b[0m\r\n".encode() in raw
    else:
        assert colors.isdisjoint(background_codes | set(range(30, 38)) | set(range(90, 98)))
    assert json.loads((tmp_path / ".config/any2llm/config.json").read_text(encoding="utf-8")) == {
        "lang": language, "preset": "Balanced", "auto_open": False,
    }
    batch = (folder / "_llm_pack/batch_01_of_1.md").read_text(encoding="utf-8")
    assert "Keep this" in batch and "Leave this out" not in batch

    code, text, _ = _run_menu(
        executable, folder, tmp_path, columns, [(("> " if plain else select_title), b"\x03")],
        plain=plain, color=mode == "color",
    )
    lines = text.replace("\r", "")
    assert code == 130 and lines.count(banner) == 1
    assert lines.index(banner) < lines.index(msg["scanning"])
    assert MESSAGES["en"]["language"] not in lines and msg["saved"] not in lines
    assert ("İptal edildi." if turkish else "Cancelled.") in text


@pytest.mark.parametrize("mode", ["color", "monochrome", "plain"])
def test_attachment_instruction_colors_only_the_filenames_green(tmp_path, mode):
    save_config(Settings(auto_open=False))
    (tmp_path / "notes.txt").write_text("A long line with a few words\n" * 40)
    executable = [sys.executable, "-m", "any2llm", "-y", "--max-tokens", "100"]
    code, _, raw = _run_menu(
        executable, tmp_path, Path.home(), 120, [], plain=mode == "plain", color=mode == "color",
    )
    assert code == 0
    batches = sorted((tmp_path / "_llm_pack").glob("batch_*.md"))
    assert len(batches) > 1
    first, last = batches[0].name, batches[-1].name
    instruction = MESSAGES["en"]["attach_many"].format(first=first, last=last)
    if mode == "color":
        white, green, reset = "\x1b[97m", "\x1b[92m", "\x1b[0m"
        for filename in (first, last):
            instruction = instruction.replace(filename, f"{reset}{green}{filename}{reset}{white}")
        instruction = f"{white}{instruction}{reset}"
    assert instruction.encode() + b"\r\n" in raw


@pytest.mark.parametrize("lang", LANGUAGE_NAMES)
def test_system_language_in_real_arrow_key_wizard(tmp_path, lang):
    (tmp_path / "notes.txt").write_text("Example")
    executable = [
        sys.executable, "-c", "from any2llm.cli import main; raise SystemExit(main())",
    ]
    msg = MESSAGES[lang]
    steps = [
        (LANGUAGE_NAMES["tr"], b"\r"),
        (msg["detail"], b"\r"),
        (msg["no"], b"\x1b[B\r"),
        (msg["select"], b"\r"),
    ]
    code, text, _ = _run_menu(executable, tmp_path, tmp_path, 120, steps, locale=f"{lang}.UTF-8")
    assert code == 0, text
    assert f'1/3  {msg["language"]}' in text
    assert f'2/3  {msg["detail"]}' in text
    assert f'3/3  {msg["open"]}' in text
    assert msg["saved"] in text
    assert json.loads((tmp_path / ".config/any2llm/config.json").read_text(encoding="utf-8"))["lang"] == lang
    prompt = (tmp_path / "_llm_pack/PROMPT.txt").read_text(encoding="utf-8")
    assert PROMPTS[lang]["reply_language"] in prompt
