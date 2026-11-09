"""Remi UI subpackage (System Tray & Windows Autostart)."""
from remi.ui.autostart import (
    autostart_status,
    handle_cli,
    set_autostart,
)
from remi.ui.tray import TrayApp, make_icon, simple_menu

__all__ = [
    "TrayApp",
    "make_icon",
    "simple_menu",
    "set_autostart",
    "autostart_status",
    "handle_cli",
]
