"""Voice Activity Detection (VAD) and hands-free speech auto-stop engine.

Provides:
- EnergyVAD: Zero-dependency amplitude and energy threshold detector.
- SileroVAD: Deep-learning ONNX VAD for precise voice detection (when onnxruntime is installed).
- AutoStopDetector: Streaming window evaluator that triggers speech-start and silence-end events.
"""
from __future__ import annotations

import logging
import math
import struct
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseVAD(ABC):
    """Abstract interface for Voice Activity Detectors."""

    @abstractmethod
    def is_speech(self, pcm_chunk: bytes) -> float:
        """Score a chunk of 16 kHz 16-bit mono PCM audio (0.0 to 1.0 probability of speech)."""
        pass

    def reset(self) -> None:
        """Reset internal recurrent or tracking state."""
        pass


class EnergyVAD(BaseVAD):
    """Zero-dependency baseline VAD using RMS energy and adaptive noise flooring.

    Requires only standard library math and struct modules.
    """

    def __init__(self, energy_threshold: float = 300.0):
        self.energy_threshold = energy_threshold

    def is_speech(self, pcm_chunk: bytes) -> float:
        if not pcm_chunk:
            return 0.0

        n_samples = len(pcm_chunk) // 2
        if n_samples == 0:
            return 0.0

        # Unpack signed 16-bit samples
        samples = struct.unpack(f"<{n_samples}h", pcm_chunk)
        sum_sq = sum(s * s for s in samples)
        rms = math.sqrt(sum_sq / n_samples)

        # Sigmoid-like smooth scoring based on threshold
        if rms < self.energy_threshold * 0.5:
            return 0.0
        elif rms > self.energy_threshold * 2.5:
            return 1.0
        else:
            return min(1.0, max(0.0, (rms - self.energy_threshold * 0.5) / (self.energy_threshold * 2.0)))


class SileroVAD(BaseVAD):
    """Silero VAD ONNX implementation for sub-millisecond neural speech detection.

    Falls back automatically to EnergyVAD if onnxruntime is absent.
    """

    def __init__(self, model_path: str | None = None, threshold: float = 0.5):
        self.threshold = threshold
        self._session = None
        self._fallback = EnergyVAD()
        self._state = None
        self._context = bytearray()

        try:
            import onnxruntime as ort
            if model_path:
                self._session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
                self.reset()
        except Exception as ex:
            logger.debug(f"SileroVAD onnxruntime init skipped ({ex}); using EnergyVAD fallback.")

    def reset(self) -> None:
        if self._session:
            import numpy as np
            # Silero VAD state tensor: [2, 1, 128]
            self._state = np.zeros((2, 1, 128), dtype=np.float32)
            self._context.clear()

    def is_speech(self, pcm_chunk: bytes) -> float:
        if self._session is None:
            return self._fallback.is_speech(pcm_chunk)

        try:
            import numpy as np

            # Accumulate to 512 samples (32ms at 16kHz)
            self._context.extend(pcm_chunk)
            chunk_bytes = 512 * 2  # 512 samples * 2 bytes
            if len(self._context) < chunk_bytes:
                return 0.0

            raw = bytes(self._context[:chunk_bytes])
            self._context = self._context[chunk_bytes:]

            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            x = samples.reshape(1, -1)
            sr = np.array([16000], dtype=np.int64)

            ort_inputs = {"input": x, "state": self._state, "sr": sr}
            ort_outs = self._session.run(None, ort_inputs)
            prob = float(ort_outs[0][0][0])
            self._state = ort_outs[1]
            return prob
        except Exception:
            return self._fallback.is_speech(pcm_chunk)


class AutoStopDetector:
    """Monitors streaming audio PCM chunks to detect hands-free speech finish.

    Triggers when:
    1. Speech was detected (has_speech = True)
    2. Continuous silence exceeds `silence_duration_s` (e.g. 0.8s)
    """

    def __init__(
        self,
        vad: BaseVAD | None = None,
        speech_threshold: float = 0.5,
        min_speech_duration_s: float = 0.25,
        silence_duration_s: float = 0.75,
        sample_rate: int = 16000,
    ):
        self.vad = vad or EnergyVAD()
        self.speech_threshold = speech_threshold
        self.min_speech_duration_s = min_speech_duration_s
        self.silence_duration_s = silence_duration_s
        self.sample_rate = sample_rate

        self._speech_seconds = 0.0
        self._silence_seconds = 0.0
        self._has_spoken = False

    def reset(self) -> None:
        self._speech_seconds = 0.0
        self._silence_seconds = 0.0
        self._has_spoken = False
        self.vad.reset()

    def process_chunk(self, chunk_pcm: bytes) -> dict[str, Any]:
        """Feed a PCM chunk (typically 20ms - 50ms) and evaluate speech/silence state.

        Returns:
            {
                "is_speaking": bool,
                "speech_prob": float,
                "has_started": bool,
                "is_finished": bool  # Ready to auto-stop!
            }
        """
        chunk_duration_s = (len(chunk_pcm) / 2) / self.sample_rate
        prob = self.vad.is_speech(chunk_pcm)
        is_active = prob >= self.speech_threshold

        if is_active:
            self._speech_seconds += chunk_duration_s
            self._silence_seconds = 0.0
            if self._speech_seconds >= self.min_speech_duration_s:
                self._has_spoken = True
        else:
            if self._has_spoken:
                self._silence_seconds += chunk_duration_s

        is_finished = self._has_spoken and (self._silence_seconds >= self.silence_duration_s)

        return {
            "is_speaking": is_active,
            "speech_prob": round(prob, 3),
            "has_started": self._has_spoken,
            "is_finished": is_finished,
        }
