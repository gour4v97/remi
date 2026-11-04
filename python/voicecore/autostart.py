"""HKCU Run-key autostart for the Python suite apps."""
import sys
import winreg
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _value_for(script: str) -> str:
    exe = Path(sys.executable)
    name = "pythonw.exe" if exe.name == "python.exe" else exe.name
    exe = exe.with_name(name)  # pythonw → no console flash at login
    return f'"{exe}" "{Path(script).resolve()}"'


def set_autostart(app: str, script: str, on: bool) -> None:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, app, 0, winreg.REG_SZ, _value_for(script))
        else:
            try:
                winreg.DeleteValue(k, app)
            except FileNotFoundError:
                pass


def autostart_status(app: str) -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_QUERY_VALUE) as k:
            val, _ = winreg.QueryValueEx(k, app)
            return val
    except FileNotFoundError:
        return ""


def handle_cli(app: str, script: str, value: str | None) -> int:
    """`autostart on|off|status` CLI; returns process exit code."""
    if value == "on":
        set_autostart(app, script, True)
        print(f"autostart enabled for {app}")
        return 0
    if value == "off":
        set_autostart(app, script, False)
        print(f"autostart disabled for {app}")
        return 0
    cur = autostart_status(app)
    print(f"autostart: {'on — ' + cur if cur else 'off'}")
    return 0
