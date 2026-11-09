"""Compatibility shim for voicecore.browser."""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from remi.tools.browser import (
    activate_tab,
    close_tab,
    eval_js,
    find_browser_exe,
    is_cdp_up,
    launch,
    new_tab,
    tabs,
)
