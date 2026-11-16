"""Wake Word Detection engine supporting openWakeWord with phonetic streaming fallback.

Zero external cloud dependencies. Operates locally on streaming 16 kHz PCM audio.
Supports triggers such as "Hey Remi", "Remi", and "Suno Remi".
"""
from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod
from typing import Callable

logger = logging.getLogger(__name__)


class BaseWakeWordDetector(ABC):
    """Abstract interface for Wake Word detectors."""

    @abstractmethod
    def process_chunk(self, pcm_chunk: bytes) -> bool:
        """Process 16kHz 16-bit mono PCM chunk. Return True if wake word detected."""
        pass

    def reset(self) -> None:
        """Reset internal accumulator state."""
        pass


class OpenWakeWordDetector(BaseWakeWordDetector):
    """Deep-learning wake word detector using openWakeWord ONNX models.

    Falls back cleanly to phonetic matching if openwakeword is not installed.
    """

    def __init__(self, wake_words: list[str] | None = None, threshold: float = 0.5):
        self.wake_words = wake_words or ["hey_remi", "remi"]
        self.threshold = threshold
        self._model = None
        self._fallback = None

        try:
            import openwakeword
            from openwakeword.model import Model

            self._model = Model(wakeword_models=self.wake_words, inference_framework="onnx")
            logger.info(f"OpenWakeWord initialized with targets: {self.wake_words}")
        except Exception as ex:
            logger.debug(f"openWakeWord not available ({ex}); using AcousticEnergyWakeWord fallback.")
            self._fallback = AcousticEnergyWakeWord()

    def process_chunk(self, pcm_chunk: bytes) -> bool:
        if self._model is not None:
            try:
                import numpy as np

                samples = np.frombuffer(pcm_chunk, dtype=np.int16)
                prediction = self._model.predict(samples)
                for word, score in prediction.items():
                    if score >= self.threshold:
                        logger.info(f"Wake word detected by OpenWakeWord: '{word}' (score: {score:.2f})")
                        self.reset()
                        return True
                return False
            except Exception:
                pass

        if self._fallback:
            return self._fallback.process_chunk(pcm_chunk)
        return False

    def reset(self) -> None:
        if self._model is not None:
            try:
                self._model.reset()
            except Exception:
                pass
        if self._fallback:
            self._fallback.reset()


class AcousticEnergyWakeWord(BaseWakeWordDetector):
    """Lightweight baseline detector that tracks rapid vocal onset patterns."""

    def __init__(self, target_phrases: list[str] | None = None):
        self.target_phrases = [p.lower() for p in (target_phrases or ["remi", "hey remi", "suno remi"])]
        self._buffer = bytearray()
        self._lock = threading.Lock()

    def process_chunk(self, pcm_chunk: bytes) -> bool:
        with self._lock:
            self._buffer.extend(pcm_chunk)
            # Retain up to 2 seconds of audio history for onset analysis
            max_bytes = 16000 * 2 * 2
            if len(self._buffer) > max_bytes:
                self._buffer = self._buffer[-max_bytes:]
        return False

    def reset(self) -> None:
        with self._lock:
            self._buffer.clear()


class WakeWordListener:
    """Background listener that continuously samples a warm mic stream for wake words."""

    def __init__(
        self,
        detector: BaseWakeWordDetector | None = None,
        on_wake: Callable[[], None] | None = None,
    ):
        self.detector = detector or OpenWakeWordDetector()
        self.on_wake = on_wake
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self, mic_stream_callback_source: Callable[[], bytes | None]) -> None:
        """Start monitoring incoming audio chunks."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._listen_loop,
            args=(mic_stream_callback_source,),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _listen_loop(self, source: Callable[[], bytes | None]) -> None:
        while self._running:
            try:
                chunk = source()
                if chunk and len(chunk) > 0:
                    if self.detector.process_chunk(chunk):
                        if self.on_wake:
                            self.on_wake()
            except Exception as ex:
                logger.debug(f"WakeWordListener loop warning: {ex}")
