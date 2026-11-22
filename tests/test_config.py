from pathlib import Path
from unittest.mock import Mock

import pytest

from any2llm import cli, config, terminal
from any2llm.languages import LANGUAGE_NAMES


@pytest.fixture(autouse=True)
def interactive_terminal(monkeypatch):
    monkeypatch.setattr(cli, "_interactive", lambda: True)
    monkeypatch.setenv("LC_ALL", "C")


def test_round_trip():
    assert config.config_path() == Path.home() / ".config/any2llm/config.json"
    assert config.load_config() is None
    for settings in (config.Settings(), config.Settings("tr", "Single File", False)):
        config.save_config(settings)
        assert config.load_config() == settings


def wizard(monkeypatch, answers):
    select = Mock(side_effect=[Mock(unsafe_ask=Mock(return_value=value)) for value in answers])
    monkeypatch.setattr(config.questionary, "select", select)
    return select


def test_first_run_switches_language_and_continues(tmp_path, monkeypatch, capsys):
    (tmp_path / "input.txt").write_text("Hello")
    select = wizard(monkeypatch, ("tr", "Single File", False))
    checkbox = Mock(return_value=Mock(unsafe_ask=Mock(return_value=[Path("input.txt")])))
    monkeypatch.setattr(terminal.questionary, "checkbox", checkbox)
    monkeypatch.setattr(cli, "copy_prompt", lambda text: False)
    monkeypatch.setattr(cli, "_open_folder", Mock(side_effect=AssertionError))
    assert cli.main([str(tmp_path)]) == 0
    language, detail, folder = select.call_args_list
    assert [c.title for c in language.kwargs["choices"]] == list(LANGUAGE_NAMES.values())
    assert "Belgelerinizi nasıl hazırlayalım?" in detail.args[0]
    assert detail.kwargs["default"] == "Balanced"
    assert [c.title.split()[0] for c in detail.kwargs["choices"]] == ["Ayrıntılı", "Dengeli", "Tek"]
    assert [c.title for c in folder.kwargs["choices"]] == ["Evet", "Hayır"]
    assert folder.kwargs["default"] is True
    assert checkbox.call_args.args[0] == "Sohbete hazırlamak istediğiniz dosyalar"
    assert checkbox.call_args.args[1][0].checked
    assert config.load_config() == config.Settings("tr", "Single File", False)
    assert "derinlemesine" in (tmp_path / "_llm_pack/PROMPT.txt").read_text(encoding="utf-8")
    logs = capsys.readouterr().out
    assert config.MESSAGES["tr"]["hint"] in logs and "PROMPT.txt dosyasını açın" in logs
    assert cli.main(["--help"]) == 0
    assert "Kullanım:" in capsys.readouterr().out


@pytest.mark.parametrize("command", ["setup", "--config"])
def test_explicit_setup_saves_and_exits(monkeypatch, command, capsys):
    config.save_config(config.Settings("tr", "Single File", False))
    wizard(monkeypatch, ("en", "High Detail", True))
    monkeypatch.setattr(cli, "scan_folder", Mock(side_effect=AssertionError))
    assert cli.main([command]) == 0
    assert config.load_config() == config.Settings("en", "High Detail", True)
    logs = capsys.readouterr().out
    assert config.MESSAGES["en"]["hint"] in logs and "Settings saved." in logs


def test_cancelled_setup_after_language_switch_preserves_settings(monkeypatch, capsys):
    config.save_config(config.Settings())
    select = wizard(monkeypatch, ("tr",))
    select.side_effect = [Mock(unsafe_ask=lambda: "tr"), KeyboardInterrupt]
    assert cli.main(["setup"]) == 130
    assert "İptal edildi" in capsys.readouterr().err
    assert config.load_config() == config.Settings()


@pytest.mark.parametrize("command", ["setup", "--config"])
def test_choose_only_language_preserves_previous_defaults(monkeypatch, command):
    config.save_config(config.Settings("en", "Single File", False))
    select = Mock(side_effect=lambda *args, **kwargs: Mock(unsafe_ask=Mock(
        return_value="tr" if args[0].startswith("1/3") else kwargs["default"],
    )))
    monkeypatch.setattr(config.questionary, "select", select)
    assert cli.main([command]) == 0
    assert config.load_config() == config.Settings("tr", "Single File", False)


@pytest.mark.parametrize("step", range(3))
def test_cancel_any_setup_step_keeps_existing_config(monkeypatch, step):
    old = config.Settings("en", "Single File", False)
    config.save_config(old)
    select = wizard(monkeypatch, ["tr", "Balanced", True][:step])
    select.side_effect = [Mock(unsafe_ask=Mock(return_value=value))
                          for value in ["tr", "Balanced"][:step]] + [KeyboardInterrupt]
    assert cli.main(["setup"]) == 130
    assert config.load_config() == old


def test_bad_config_can_be_replaced_and_failed_write_preserves_it(monkeypatch, capsys):
    config.config_path().parent.mkdir(parents=True)
    config.config_path().write_text("{bad json")
    assert cli.main(["-y"]) == 1
    assert "any2llm setup" in capsys.readouterr().err
    wizard(monkeypatch, ["en", "Balanced", True])
    with monkeypatch.context() as patch:
        patch.setattr(cli, "save_config", Mock(side_effect=PermissionError))
        assert cli.main(["setup"]) == 1
        assert "Cannot save settings" in capsys.readouterr().err
        assert config.config_path().read_text(encoding="utf-8") == "{bad json"
    wizard(monkeypatch, ["en", "Balanced", True])
    assert cli.main(["setup"]) == 0
    assert config.load_config() == config.Settings()
