"""Per-user Windows startup; never modifies machine-wide registry."""

import subprocess
import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "AllInOneChatapp"


def startup_command() -> str:
    executable = Path(sys.executable)
    if getattr(sys, "frozen", False):
        args = [str(executable), "--hidden"]
    else:
        pythonw = executable.with_name("pythonw.exe")
        args = [str(pythonw if pythonw.exists() else executable), "-m", "allinone", "--hidden"]
    return subprocess.list2cmdline(args)


def enabled() -> bool:
    if sys.platform != "win32":
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            command, _ = winreg.QueryValueEx(key, VALUE_NAME)
            return command == startup_command()
    except FileNotFoundError:
        return False


def set_enabled(value: bool) -> None:
    if sys.platform != "win32":
        raise OSError("Start with Windows is only available on Windows.")
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if value:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, startup_command())
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass
