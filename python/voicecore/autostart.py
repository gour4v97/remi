"""Compatibility shim for voicecore.autostart."""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from remi.ui.autostart import (
    autostart_status,
    handle_cli,
    set_autostart,
)
