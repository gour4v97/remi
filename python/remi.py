"""Remi (Python port) - backward compatibility shim.

Redirects to the new openjarvis-style `remi` package at src/remi.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on the search path
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from remi.agents.browser_agent import (
    BrowserVoiceAgent,
    say_audio,
    say_text,
)
from remi.cli.main import cmd_model, main
from remi.core.constants import MODEL_CATALOG as CATALOG

# Re-exports for backward compatibility
APP = "remi-py"
HOTKEY_DEFAULT = "ctrl+alt+b"


def model_cmd(args) -> int:
    action = getattr(args, "payload", None) or "list"
    parts = action.split()
    cmd = parts[0]
    target = parts[1] if len(parts) > 1 else None
    ctx = cmd_model.make_context("model", [cmd] + ([target] if target else []))
    try:
        cmd_model.invoke(ctx)
        return 0
    except SystemExit as e:
        return e.code or 0


if __name__ == "__main__":
    sys.exit(main())
