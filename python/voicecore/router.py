"""Compatibility shim for voicecore.router."""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from remi.tools.router import (
    CLICK_JS,
    FIND_JS,
    SITES,
    TYPE_JS,
    VOLUME_JS,
    ZOOM_JS,
    Outcome,
    ensure_cdp,
    run,
)
