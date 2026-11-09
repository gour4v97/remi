"""Hardware and ASR engine auto-discovery (GPU, CPU, whisper binaries)."""
from dataclasses import dataclass
import shutil

from remi.core import config
from remi.core.constants import MODEL_CATALOG
from remi.engine.whisper_cpp import (
    CUDA_DIR,
    WHISPER_CLI,
    WHISPER_SERVER,
    WHISPER_SERVER_CUDA,
    has_nvidia,
    server_port,
    server_up,
)


@dataclass
class HardwareSpec:
    has_nvidia_gpu: bool
    cuda_build_installed: bool
    whisper_cli_installed: bool
    whisper_server_installed: bool
    installed_models: list[str]
    active_server: bool


def detect_environment(cfg: dict | None = None) -> HardwareSpec:
    """Scan local host environment and return detected hardware capabilities."""
    c = cfg or config.load()
    port = server_port(c)

    installed = []
    for m in MODEL_CATALOG:
        if config.model_path(m).exists():
            installed.append(m)

    return HardwareSpec(
        has_nvidia_gpu=has_nvidia(),
        cuda_build_installed=WHISPER_SERVER_CUDA.exists(),
        whisper_cli_installed=WHISPER_CLI.exists(),
        whisper_server_installed=WHISPER_SERVER.exists(),
        installed_models=installed,
        active_server=server_up(port),
    )
