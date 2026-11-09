"""Compatibility shim for voicecore.capture."""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from remi.speech.capture import MicCapture, resample_16k as _resample_16k
from remi.engine.whisper_cpp import peak_amplitude
