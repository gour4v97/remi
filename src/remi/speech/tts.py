"""Text-to-Speech synthesis with engine caching."""
from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod

from remi.core.registry import TTSRegistry

logger = logging.getLogger(__name__)


class BaseTTS(ABC):
    """Abstract interface for TTS synthesis."""

    @abstractmethod
    def speak(self, text: str) -> None:
        pass


@TTSRegistry.register("sapi")
@TTSRegistry.register("default")
class SapiTTS(BaseTTS):
    """Windows SAPI TTS implementation via pyttsx3 with single-instance caching."""

    _lock = threading.Lock()
    _engine = None

    def speak(self, text: str) -> None:
        if not text:
            return
        with self._lock:
            try:
                if self._engine is None:
                    import pyttsx3
                    self._engine = pyttsx3.init()
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception as ex:
                logger.debug(f"TTS synthesis warning: {ex}")
                self._engine = None  # Re-initialize next time


_default_tts = SapiTTS()


def say(text: str, enabled: bool = True) -> None:
    """Spoken confirmation helper; best-effort, safe to fail."""
    if not enabled or not text:
        return
    _default_tts.speak(text)
