"""Microphone capture via sounddevice → 16 kHz mono s16le bytes."""
import threading

import numpy as np
import sounddevice as sd

from .asr import peak_amplitude  # re-export convenience


class MicCapture:
    def __init__(self):
        self._buf = bytearray()
        self._lock = threading.Lock()
        self._stream = None
        self._native_rate = None

    def start(self):
        try:
            self._stream = sd.InputStream(samplerate=16000, channels=1, dtype="int16",
                                          blocksize=0, callback=self._on_data)
            self._stream.start()
        except Exception:
            # device refused 16 kHz — record native rate and resample on stop
            dev = sd.query_devices(kind="input")
            rate = int(dev["default_samplerate"])
            self._native_rate = rate
            self._stream = sd.InputStream(samplerate=rate, channels=1, dtype="int16",
                                          blocksize=0, callback=self._on_data)
            self._stream.start()

    def _on_data(self, indata, frames, time_info, status):
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
            raw = _resample_16k(raw, self._native_rate)
        return raw


def _resample_16k(pcm: bytes, src_rate: int) -> bytes:
    """Simple linear-interpolation resample (speech-quality MVP)."""
    samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
    if len(samples) == 0:
        return pcm
    duration = len(samples) / src_rate
    target_len = int(duration * 16000)
    x_src = np.linspace(0.0, len(samples) - 1, num=len(samples))
    x_dst = np.linspace(0.0, len(samples) - 1, num=target_len)
    out = np.interp(x_dst, x_src, samples).astype(np.int16)
    return out.tobytes()
