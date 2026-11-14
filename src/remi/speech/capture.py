"""Audio capture pipeline via sounddevice → 16 kHz mono signed 16-bit PCM bytes.

Two capture strategies:
- MicCapture: opens/closes stream per recording (original, safe, compatible)
- WarmMicCapture: keeps stream open between recordings for lower latency (~150ms saved)

Both share the same interface (start / stop_and_read / is_capturing) so agents
can swap between them transparently.
"""
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


def _open_stream(callback, prefer_16k: bool = True):
    """Open a sounddevice InputStream, falling back to native rate on error.

    Returns:
        (stream, native_rate_or_None)
    """
    if sd is None:
        raise RuntimeError("sounddevice is not installed or audio backend unavailable.")
    if prefer_16k:
        try:
            stream = sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype="int16",
                blocksize=0,
                callback=callback,
            )
            stream.start()
            return stream, None
        except Exception:
            pass
    # Device rejected 16 kHz — capture at native rate and resample on read
    dev = sd.query_devices(kind="input")
    rate = int(dev["default_samplerate"])
    stream = sd.InputStream(
        samplerate=rate,
        channels=1,
        dtype="int16",
        blocksize=0,
        callback=callback,
    )
    stream.start()
    return stream, rate


@SpeechRegistry.register("microphone")
class MicCapture:
    """Thread-safe microphone capture streaming into 16 kHz PCM buffer.

    Opens and closes the sounddevice InputStream on each PTT press/release.
    Safe and compatible. For lower per-command latency use WarmMicCapture.
    """

    def __init__(self):
        self._buf = bytearray()
        self._lock = threading.Lock()
        self._stream = None
        self._native_rate: int | None = None

    def start(self) -> None:
        if sd is None:
            raise RuntimeError("sounddevice is not installed or audio backend unavailable.")
        self._stream, self._native_rate = _open_stream(self._on_data)

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


@SpeechRegistry.register("microphone_warm")
class WarmMicCapture:
    """Warm microphone capture: stream stays open between recordings.

    Eliminates ~150-200ms PortAudio device open/close latency per PTT press.

    Lifecycle:
        # At app startup:
        mic = WarmMicCapture()
        mic.open()

        # On PTT press:
        mic.start()          # begin_recording() — zero-latency, stream already open

        # On PTT release:
        pcm = mic.stop_and_read()   # end_and_read() — buffer collected

        # On app shutdown:
        mic.close()

    Compatible with MicCapture interface: start() / stop_and_read() / is_capturing.
    """

    def __init__(self):
        self._buf = bytearray()
        self._lock = threading.Lock()
        self._stream = None
        self._recording = False
        self._native_rate: int | None = None
        self._stream_lock = threading.Lock()

    def open(self) -> None:
        """Open the audio stream once — call at application startup.

        Idempotent: calling multiple times is safe.
        """
        with self._stream_lock:
            if self._stream is not None:
                return  # Already open
            self._stream, self._native_rate = _open_stream(self._on_data)

    def begin_recording(self) -> None:
        """Start accumulating audio data into buffer (PTT pressed)."""
        with self._lock:
            self._buf.clear()
            self._recording = True

    def _on_data(self, indata, frames, time_info, status) -> None:
        with self._lock:
            if self._recording:
                self._buf.extend(indata.tobytes())

    def end_and_read(self) -> bytes:
        """Stop accumulating and return captured PCM bytes (PTT released)."""
        with self._lock:
            self._recording = False
            raw = bytes(self._buf)
            self._buf.clear()
        if self._native_rate and self._native_rate != 16000:
            raw = resample_16k(raw, self._native_rate)
        return raw

    def close(self) -> None:
        """Close the persistent stream — call on application shutdown."""
        with self._stream_lock:
            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None

    @property
    def is_open(self) -> bool:
        return self._stream is not None

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._recording

    # --- MicCapture-compatible interface ---

    def start(self) -> None:
        """Compat: open stream if needed, then begin recording."""
        self.open()
        self.begin_recording()

    def stop_and_read(self) -> bytes:
        """Compat: stop recording, return PCM. Stream stays open."""
        return self.end_and_read()

    @property
    def is_capturing(self) -> bool:
        return self.is_recording
