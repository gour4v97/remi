"""Voice Trans (Python port) - backward compatibility shim.

Redirects to the new openjarvis-style `remi` package at src/remi.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on the search path
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from remi.agents.dictation_agent import (
    DictationAgent,
    apply_dictionary,
    load_dictionary,
)
from remi.cli.main import cmd_dictation

APP = "voice-trans-py"
HOTKEY_DEFAULT = "ctrl+alt+space"


if __name__ == "__main__":
    cmd_dictation()
