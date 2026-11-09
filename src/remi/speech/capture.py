"""Audio capture pipeline via sounddevice -> 16 kHz mono signed 16-bit PCM bytes."""
from __future__ import annotations

import threading
try:
    import numpy as np
except ImportError:
    np = None

try:
    import sounddevice as sd
except (ImportError, OSError):
    sd = None  # Graceful fallback when portaudio is absent (e.g. headless CI)

from remi.core.registry import SpeechRegistry
from remi.engine.whisper_cpp import peak_amplitude


def resample_16k(pcm: bytes, src_rate: int) -> bytes:
    """Linear-interpolation resampler for converting arbitrary samplerate to 16 kHz."""
    if np is None:
        return pcm
    samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
    if len(samples) == 0:
        return pcm
    duration = len(samples) / src_rate
    target_len = int(duration * 16000)
    x_src = np.linspace(0.0, len(samples) - 1, num=len(samples))
    x_dst = np.linspace(0.0, len(samples) - 1, num=target_len)
    out = np.interp(x_dst, x_src, samples).astype(np.int16)
    return out.tobytes()


@SpeechRegistry.register("microphone")
class MicCapture:
    """Thread-safe microphone capture streaming into 16 kHz PCM buffer."""

    def __init__(self):
        self._buf = bytearray()
        self._lock = threading.Lock()
        self._stream = None
        self._native_rate: int | None = None

    def start(self) -> None:
        if sd is None:
            raise RuntimeError("sounddevice is not installed or audio backend unavailable.")
        try:
            self._stream = sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype="int16",
                blocksize=0,
                callback=self._on_data,
            )
            self._stream.start()
        except Exception:
            # Device rejected 16 kHz - capture at native rate and resample upon stop
            dev = sd.query_devices(kind="input")
            rate = int(dev["default_samplerate"])
            self._native_rate = rate
            self._stream = sd.InputStream(
                samplerate=rate,
                channels=1,
                dtype="int16",
                blocksize=0,
                callback=self._on_data,
            )
            self._stream.start()

    def _on_data(self, indata, frames, time_info, status) -> None:
        with self._lock:
            self._buf.extend(indata.tobytes())

    def stop_and_read(self) -> bytes:
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            raw = bytes(self._buf)
            self._buf.clear()
        if self._native_rate and self._native_rate != 16000:
            raw = resample_16k(raw, self._native_rate)
        return raw

    @property
    def is_capturing(self) -> bool:
        return self._stream is not None
