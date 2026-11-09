"""Shared voice engine for Remi Suite (backward compatibility shim).

Delegates to `remi` package at src/remi.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import remi
