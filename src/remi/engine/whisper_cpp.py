"""whisper.cpp engine implementation: persistent HTTP server with one-shot CLI fallback.

Preserves exact whisper-server HTTP protocol and whisper-cli invocations from Remi Suite.
"""
from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import threading
import time
import urllib.request
import uuid
import wave
import zipfile
from pathlib import Path
from typing import Any

from remi.core import config
from remi.core.constants import DEFAULT_ASR_PORT
from remi.core.registry import EngineRegistry
from remi.engine._base import BaseASREngine

logger = logging.getLogger(__name__)

WHISPER_ZIP_URL = "https://github.com/ggerganov/whisper.cpp/releases/download/b5454/whisper-bin-x64.zip"
CUDA_ZIP_URL = "https://github.com/ggerganov/whisper.cpp/releases/download/b5454/whisper-bin-win-cuda-12.4.0-x64.zip"

WHISPER_CLI = config.BIN_DIR / "whisper-cli.exe"
WHISPER_SERVER = config.BIN_DIR / "whisper-server.exe"          # CPU build
CUDA_DIR = config.LOCALAPPDATA / "bin-cuda"
WHISPER_SERVER_CUDA = CUDA_DIR / "whisper-server.exe"           # GPU build (~80x faster)

_bin_lock = threading.Lock()
_server_lock = threading.Lock()
_server_proc: subprocess.Popen | None = None
_spawned_by_us = False


def ensure_binaries() -> None:
    """Download whisper.cpp binaries (CLI + CPU server + DLLs) if not present."""
    with _bin_lock:
        if WHISPER_CLI.exists() and WHISPER_SERVER.exists():
            return
        try:
            config.ensure_dirs()
            config.BIN_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as ex:
            logger.warning(f"Could not create BIN directory ({ex})")
            return
        logger.info(f"Downloading whisper.cpp binaries (~2 MB) from {WHISPER_ZIP_URL} ...")
        zip_path = config.BIN_DIR / "whisper-bin.zip"
        urllib.request.urlretrieve(WHISPER_ZIP_URL, zip_path)
        with zipfile.ZipFile(zip_path) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                name = Path(info.filename).name  # flatten
                if name.lower().endswith((".exe", ".dll")):
                    (config.BIN_DIR / name).write_bytes(z.read(info))
        zip_path.unlink(missing_ok=True)
        if not WHISPER_CLI.exists():
            raise RuntimeError("whisper-cli.exe not found in the downloaded archive")


def has_nvidia() -> bool:
    """Check whether NVIDIA GPU is present via nvidia-smi."""
    import os
    return os.path.exists("C:/Windows/System32/nvidia-smi.exe") or shutil.which("nvidia-smi") is not None


def ensure_cuda() -> bool:
    """Download the CUDA whisper build once (NVIDIA machines only)."""
    if WHISPER_SERVER_CUDA.exists():
        return True
    if not has_nvidia():
        return False
    try:
        config.ensure_dirs()
        CUDA_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as ex:
        logger.warning(f"Could not create CUDA directory ({ex})")
        return False
    logger.info("Downloading whisper.cpp CUDA build (~250 MB) for GPU transcription ...")
    zip_path = CUDA_DIR / "cuda.zip"
    try:
        urllib.request.urlretrieve(CUDA_ZIP_URL, zip_path)
        with zipfile.ZipFile(zip_path) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                name = Path(info.filename).name
                if name.lower().endswith((".exe", ".dll")):
                    (CUDA_DIR / name).write_bytes(z.read(info))
        zip_path.unlink(missing_ok=True)
    except Exception as ex:
        logger.warning(f"CUDA download failed ({ex}) - staying on CPU")
        return False
    return WHISPER_SERVER_CUDA.exists()


def server_port(cfg: dict[str, Any]) -> int:
    return int(cfg.get("asr_port", DEFAULT_ASR_PORT))


def server_up(port: int) -> bool:
    """Check if whisper-server responds on HTTP port."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def start_server(cfg: dict[str, Any], wait_s: int = 90) -> bool:
    """Start whisper-server process with configured model."""
    global _server_proc, _spawned_by_us
    port = server_port(cfg)
    if server_up(port):
        return True
    ensure_binaries()
    model = config.model_path(cfg.get("local_model", "large-v3-turbo-q5_0"))
    if not model.exists():
        raise FileNotFoundError(f"Model '{model.name}' not found. Download it via 'remi model download'")
    lang = {"en": "en", "hi": "hi"}.get(cfg.get("language", "hinglish"), "auto")

    with _server_lock:
        if server_up(port):
            return True
        exe = WHISPER_SERVER_CUDA if ensure_cuda() else WHISPER_SERVER
        label = "GPU" if exe == WHISPER_SERVER_CUDA else "CPU"
        logger.info(f"Starting whisper server ({label}, model {model.name}, port {port}) ...")
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        _server_proc = subprocess.Popen(
            [str(exe), "--model", str(model), "-t", "8", "--port", str(port), "-l", lang],
            creationflags=creation_flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(exe.parent),
        )
        _spawned_by_us = True
        deadline = time.time() + wait_s
        while time.time() < deadline:
            if server_up(port):
                logger.info(f"Whisper server ready ({label}).")
                return True
            time.sleep(0.5)
        return False


def shutdown() -> None:
    """Explicit cleanup for tray-app quit; CLI runs intentionally leave the server warm."""
    global _server_proc
    if _spawned_by_us and _server_proc is not None:
        try:
            _server_proc.terminate()
        except Exception:
            pass


def peak_amplitude(pcm: bytes) -> int:
    """Detect peak 16-bit PCM amplitude for silence checking."""
    peak = 0
    for i in range(0, len(pcm) - 1, 2):
        s = pcm[i] | (pcm[i + 1] << 8)
        a = s if s < 0x8000 else 0x10000 - s
        peak = max(peak, a)
    return peak


@EngineRegistry.register("whisper_cpp")
@EngineRegistry.register("default")
class WhisperCppEngine(BaseASREngine):
    """Production whisper.cpp engine utilizing server and CLI fallback."""

    def __init__(self, cfg: dict[str, Any] | None = None):
        self.cfg = cfg or {}

    def is_ready(self) -> bool:
        port = server_port(self.cfg)
        return server_up(port) or WHISPER_CLI.exists()

    def prewarm(self, cfg: dict | None = None) -> None:
        c = cfg or self.cfg
        threading.Thread(target=lambda: self._safe_start(c), daemon=True).start()

    def _safe_start(self, c: dict):
        try:
            start_server(c)
        except Exception as ex:
            logger.warning(f"Whisper server prewarm failed ({ex}) - will use CLI fallback")

    def shutdown(self) -> None:
        global _server_proc
        if _spawned_by_us and _server_proc is not None:
            try:
                _server_proc.terminate()
            except Exception:
                pass

    def transcribe_pcm(
        self,
        pcm: bytes,
        model: str,
        language: str = "hinglish",
        cfg: dict | None = None,
    ) -> str:
        cfg = cfg or self.cfg or {"asr_port": DEFAULT_ASR_PORT, "local_model": model, "language": language}
        wav_path = config.LOCALAPPDATA / "utterance.wav"
        wav_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(wav_path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(pcm)

        port = server_port(cfg)
        if server_up(port) or start_server(cfg):
            try:
                return self._transcribe_server(wav_path, port, language)
            except Exception as ex:
                logger.warning(f"Server transcription failed ({ex}) - falling back to CLI")

        return self._transcribe_cli(wav_path, model, language)

    def _transcribe_server(self, wav_path: Path, port: int, language: str) -> str:
        boundary = "----remi" + uuid.uuid4().hex
        parts = []
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{wav_path.name}"\r\n'
            f'Content-Type: audio/wav\r\n\r\n'.encode() + wav_path.read_bytes() + b"\r\n"
        )
        for field, value in (
            ("response-format", "json"),
            ("temperature", "0.0"),
            ("language", {"en": "en", "hi": "hi"}.get(language, "auto")),
        ):
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"\r\n\r\n{value}\r\n'.encode())
        parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(parts)

        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/inference",
            data=body,
            method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(req, timeout=300) as r:
            data = json.loads(r.read().decode("utf-8"))
        return data.get("text", "").strip()

    def _transcribe_cli(self, wav_path: Path, model: str, language: str) -> str:
        ensure_binaries()
        model_file = config.model_path(model)
        if not model_file.exists():
            raise FileNotFoundError(f"Model '{model}' not found at {model_file}")
        lang = "en" if language == "en" else "hi" if language == "hi" else "auto"
        proc = subprocess.run(
            [
                str(WHISPER_CLI),
                "--model",
                str(model_file),
                "--file",
                str(wav_path),
                "--language",
                lang,
                "--no-gpu",
                "-t",
                "8",
            ],
            capture_output=True,
            timeout=900,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"whisper-cli failed: {proc.stderr.decode(errors='replace')[-300:]}")
        out = []
        for line in proc.stdout.decode(errors="replace").splitlines():
            m = re.match(r"^\[[^\]]+\]\s*(.*)$", line.strip())
            if m and m.group(1):
                out.append(m.group(1))
        return "".join(out)
