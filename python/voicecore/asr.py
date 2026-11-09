"""Compatibility shim for voicecore.asr."""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from remi.engine.whisper_cpp import (
    CUDA_DIR,
    CUDA_ZIP_URL,
    DEFAULT_ASR_PORT,
    WHISPER_CLI,
    WHISPER_SERVER,
    WHISPER_SERVER_CUDA,
    WHISPER_ZIP_URL,
    WhisperCppEngine,
    ensure_binaries,
    ensure_cuda,
    has_nvidia,
    peak_amplitude,
    server_port,
    server_up,
    shutdown,
    start_server,
)

_default_engine = WhisperCppEngine()


def transcribe_pcm(pcm, model, language="hinglish", cfg=None):
    return _default_engine.transcribe_pcm(pcm, model, language, cfg)


def prewarm(cfg):
    _default_engine.prewarm(cfg)
