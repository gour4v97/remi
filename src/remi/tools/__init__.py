"""Remi Tools subpackage (Browser automation, Command router, Text delivery, History)."""
from remi.tools.browser import (
    BrowserClient,
    activate_tab,
    close_tab,
    eval_js,
    find_browser_exe,
    is_cdp_up,
    launch,
    new_tab,
    tabs,
)
from remi.tools.delivery import (
    DeliveryService,
    foreground_hwnd,
    set_clipboard,
    type_text,
)
from remi.tools.history import HistoryStore, append, load
from remi.tools.router import CommandRouter, Outcome, ensure_cdp, run

__all__ = [
    "BrowserClient",
    "is_cdp_up",
    "find_browser_exe",
    "launch",
    "tabs",
    "new_tab",
    "activate_tab",
    "close_tab",
    "eval_js",
    "CommandRouter",
    "Outcome",
    "run",
    "ensure_cdp",
    "DeliveryService",
    "type_text",
    "set_clipboard",
    "foreground_hwnd",
    "HistoryStore",
    "append",
    "load",
]
