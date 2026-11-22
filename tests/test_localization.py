from string import Formatter
from unittest.mock import Mock

import pytest

from any2llm import cli, config, languages, terminal, tokenizer
from any2llm.messages import MESSAGES, PROMPTS
from any2llm.prompts import master_prompt

LOCALES = [
    ("en", "en_US.UTF-8", "Choose your language", "Answer in English.", "continue"),
    ("zh", "zh_CN.UTF-8", "选择语言", "请用简体中文回答。", "继续"),
    ("hi", "hi_IN.UTF-8", "भाषा चुनें", "हिन्दी में जवाब दें।", "आगे बढ़ें"),
    ("es", "es-MX", "Elige el idioma", "Responde en español.", "continuar"),
    ("fr", "fr_CA.UTF-8", "Choisissez votre langue", "Réponds en français.", "continuer"),
    ("ar", "ar_EG.UTF-8", "اختر اللغة", "أجب باللغة العربية.", "تابع"),
    ("bn", "bn_BD.UTF-8", "ভাষা বেছে নিন", "বাংলায় উত্তর দিন।", "এগিয়ে যান"),
    ("pt", "pt-BR", "Escolha seu idioma", "Responda em português.", "continuar"),
    ("ru", "ru_RU.UTF-8", "Выберите язык", "Отвечай по-русски.", "продолжай"),
    ("ur", "ur_PK.UTF-8", "زبان منتخب کریں", "اردو میں جواب دیں۔", "جاری رکھیں"),
    ("tr", "tr_TR.UTF-8", "Dilinizi seçin", "Türkçe yanıt ver.", "devam"),
]


@pytest.mark.parametrize(("code", "locale", "title", "reply", "word"), LOCALES)
def test_localized_first_run_and_daily_use(tmp_path, monkeypatch, capsys, code, locale, title, reply, word):
    monkeypatch.setenv("LC_ALL", locale)
    monkeypatch.setattr(cli, "_interactive", lambda: True)
    monkeypatch.setattr(tokenizer, "get_encoding", lambda: None)
    copy = Mock(return_value=False)
    monkeypatch.setattr(cli, "copy_prompt", copy)
    monkeypatch.setattr(cli, "_open_folder", Mock(side_effect=AssertionError))
    (tmp_path / "Notes.txt").write_text("A line from the original file.\n" * 100)
    (tmp_path / "Picture.png").touch()
    answers = iter(["", "", "2", ""])
    asked = []
    monkeypatch.setattr("builtins.input", lambda question: (asked.append(question), next(answers))[1])
    args = [str(tmp_path), "--plain", "--max-tokens", "180"]

    assert cli.main(args) == 0
    logs = capsys.readouterr().out
    msg = MESSAGES[code]
    assert f"1/3  {title}" in logs
    assert all(name in logs for name in languages.LANGUAGE_NAMES.values())
    assert asked[0] == f"[{list(languages.LANGUAGE_NAMES).index(code) + 1}] > "
    assert len(asked) == 4
    assert f'2/3  {msg["detail"]}' in logs and f'3/3  {msg["open"]}' in logs
    assert msg["select"] in logs and f'Picture.png — {msg["image"]}' in logs
    assert msg["skipped_help"] in logs and msg["media_help"] in logs
    assert msg["clipboard_failed"] in logs and msg["clipboard_copied"] not in logs
    assert msg["clipboard"] in logs and msg["next"] in logs and word in msg["next"]
    saved = config.Settings(code, "Balanced", False)
    assert config.load_config() == saved

    output = tmp_path / "_llm_pack"
    batches = sorted(output.glob("batch_*.md"))
    assert len(batches) > 1
    prompt = (output / "PROMPT.txt").read_text(encoding="utf-8")
    assert reply in prompt and word in prompt
    assert all(path.name in prompt for path in batches)
    assert "<manifest>" in prompt and "<page>" in prompt
    copy.assert_called_once_with(prompt)

    monkeypatch.setenv("LC_ALL", "de_DE.UTF-8")
    monkeypatch.setattr("builtins.input", lambda _: "")
    copy.return_value = True
    assert cli.main([str(tmp_path), "--plain"]) == 0
    daily = capsys.readouterr().out
    assert title not in daily and msg["select"] in daily and msg["paste"] in daily
    assert msg["clipboard_copied"] in daily and msg["clipboard_failed"] not in daily
    assert msg["next"] not in daily
    assert reply in (output / "PROMPT.txt").read_text(encoding="utf-8")

    assert cli.main(["--help"]) == 0
    assert msg["help"] in capsys.readouterr().out
    assert cli.main(["--max-tokens", "0"]) == 2
    assert msg["invalid_limit"] in capsys.readouterr().err

    assert cli.main([str(tmp_path), "-y", "--lang", "en"]) == 0
    assert MESSAGES["en"]["paste"] in capsys.readouterr().out
    assert config.load_config() == saved


def _fields(text):
    return {name for _, name, _, _ in Formatter().parse(text) if name}


def test_every_catalog_has_the_same_messages_and_placeholders():
    assert set(languages.LANGUAGE_NAMES) == {code for code, *_ in LOCALES}
    for catalogs in (MESSAGES, PROMPTS):
        english = catalogs["en"]
        for code, catalog in catalogs.items():
            assert set(catalog) - {"grouping"} == set(english), code
            for key, reference in english.items():
                assert _fields(catalog[key]) == _fields(reference), (code, key)
                assert catalog[key], (code, key)
    for code in languages.LANGUAGE_NAMES:
        task = "Example task"
        catalog = PROMPTS[code]
        single = master_prompt(["first.md"], code, task)
        multi = master_prompt(["first.md", "second.md"], code, task)
        assert catalog["task_single"].format(first="first.md") in single
        assert catalog["task_multi"].format(first="first.md", continue_word=catalog["continue"]) in multi
        assert catalog["task_evidence"] in single and catalog["task_evidence"] in multi
        assert catalog["task_final"] in multi


@pytest.mark.parametrize(("environment", "platform_locale", "expected"), [
    ({"LANG": "de_DE.UTF-8"}, "fr_FR", "en"),
    ({"LANG": "tr_TR.UTF-8", "LC_MESSAGES": "ar_SA"}, "en_US", "ar"),
    ({"LC_ALL": "C", "LC_MESSAGES": "ar_SA", "LANG": "tr_TR"}, "fr_FR", "en"),
    ({"LANG": "cmn-Hans-CN"}, None, "zh"),
    ({}, "Portuguese_Brazil", "pt"),
    ({}, "Chinese (Simplified)_China", "zh"),
    ({}, None, "en"),
])
def test_system_language_order_and_fallback(monkeypatch, environment, platform_locale, expected):
    for key in ("LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(key, raising=False)
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(languages, "_native_message_locale", lambda: platform_locale)
    assert languages.system_language() == expected


@pytest.mark.parametrize(("locale", "first"), [
    ("de_DE", "Choose your language"),
    ("hi_IN", "भाषा चुनें"),
])
def test_wizard_changes_language_immediately(tmp_path, monkeypatch, capsys, locale, first):
    monkeypatch.setenv("LC_ALL", locale)
    monkeypatch.setattr(cli, "_interactive", lambda: True)
    # Arabic-Indic input selects the sixth language and the second open-folder option.
    answers = iter(["٦", "", "٢"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert cli.main(["setup", "--plain"]) == 0
    screen = capsys.readouterr().out
    assert f"1/3  {first}" in screen
    assert "2/3  كيف تريد تجهيز مستنداتك؟" in screen
    assert "3/3  هل تريد فتح مجلد الملفات المجهّزة عند الانتهاء؟" in screen
    assert config.load_config() == config.Settings("ar", "Balanced", False)


@pytest.mark.parametrize(("code", "formatted"), [
    ("hi", "12,34,567"), ("bn", "12,34,567"), ("ar", "1٬234٬567"),
    ("fr", "1 234 567"), ("tr", "1.234.567"),
])
def test_locale_specific_count_format(code, formatted):
    assert terminal.display_count(1234567, MESSAGES[code]) == formatted
