"""Compatibility shim for voicecore.app."""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from remi.core.constants import COLORS
from remi.ui.tray import TrayApp, make_icon, simple_menu
