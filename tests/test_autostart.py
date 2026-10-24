import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from allinone import autostart


def test_non_windows():
    if sys.platform == "win32":
        pytest.skip("Non-Windows behavior")
    assert not autostart.enabled()
    with pytest.raises(OSError):
        autostart.set_enabled(True)


def test_command_is_quoted_and_hidden(monkeypatch):
    monkeypatch.setattr(sys, "executable", str(Path("C:/Program Files/Chatapp/chatapp.exe")))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    command = autostart.startup_command()
    assert command.startswith('"')
    assert command.endswith("--hidden")
    assert " -m " not in command


def test_development_command(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert "-m allinone --hidden" in autostart.startup_command()


def test_registry_is_per_user(monkeypatch):
    registry = MagicMock()
    monkeypatch.setitem(sys.modules, "winreg", registry)
    monkeypatch.setattr(sys, "platform", "win32")
    autostart.set_enabled(True)
    registry.CreateKey.assert_called_with(registry.HKEY_CURRENT_USER, autostart.RUN_KEY)
    registry.SetValueEx.assert_called_once()
    registry.OpenKey.return_value.__enter__.return_value = "key"
    registry.QueryValueEx.return_value = (autostart.startup_command(), 1)
    assert autostart.enabled()
    autostart.set_enabled(False)
    registry.DeleteValue.assert_called_once()
    registry.DeleteValue.side_effect = FileNotFoundError
    autostart.set_enabled(False)
    registry.OpenKey.side_effect = FileNotFoundError
    assert not autostart.enabled()
