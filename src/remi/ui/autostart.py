"""Windows HKCU Run-key autostart manager for Remi Suite."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

try:
    import winreg
    IS_WINDOWS = True
except ImportError:
    winreg = None
    IS_WINDOWS = False

logger = logging.getLogger(__name__)

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _value_for(script: str) -> str:
    exe = Path(sys.executable)
    name = "pythonw.exe" if exe.name == "python.exe" else exe.name
    exe = exe.with_name(name)  # pythonw prevents console window flash at login
    return f'"{exe}" "{Path(script).resolve()}"'


def set_autostart(app: str, script: str, on: bool) -> None:
    """Enable or disable Windows autostart at user login."""
    if not IS_WINDOWS or winreg is None:
        logger.info(f"Autostart is Windows-only (requested {app}: {on})")
        return

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, app, 0, winreg.REG_SZ, _value_for(script))
        else:
            try:
                winreg.DeleteValue(k, app)
            except FileNotFoundError:
                pass


def autostart_status(app: str) -> str:
    """Query current autostart registry command, or empty string if disabled."""
    if not IS_WINDOWS or winreg is None:
        return ""

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_QUERY_VALUE) as k:
            val, _ = winreg.QueryValueEx(k, app)
            return val
    except FileNotFoundError:
        return ""


def handle_cli(app: str, script: str, value: str | None) -> int:
    """CLI handler for `autostart on|off|status` command."""
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
