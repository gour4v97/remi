"""Remi Engine subpackage (ASR & Hardware detection)."""
from remi.engine._base import BaseASREngine
from remi.engine._discovery import HardwareSpec, detect_environment
from remi.engine.whisper_cpp import (
    CUDA_DIR,
    CUDA_ZIP_URL,
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

__all__ = [
    "BaseASREngine",
    "WhisperCppEngine",
    "HardwareSpec",
    "detect_environment",
    "ensure_binaries",
    "ensure_cuda",
    "has_nvidia",
    "start_server",
    "server_up",
    "server_port",
    "shutdown",
    "peak_amplitude",
    "WHISPER_CLI",
    "WHISPER_SERVER",
    "WHISPER_SERVER_CUDA",
    "WHISPER_ZIP_URL",
    "CUDA_ZIP_URL",
    "CUDA_DIR",
]
