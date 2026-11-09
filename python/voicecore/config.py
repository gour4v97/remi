"""Compatibility shim for voicecore.config."""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from remi.core.config import (
    APPDATA,
    BIN_DIR,
    DEFAULTS,
    LOCALAPPDATA,
    VT_MODELS,
    config_path,
    ensure_dirs,
    history_path,
    load,
    model_path,
    save,
)
