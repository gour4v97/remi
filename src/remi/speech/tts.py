"""Text-to-Speech synthesis with engine caching and non-blocking background queue."""
from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod

from remi.core.registry import TTSRegistry

logger = logging.getLogger(__name__)


class BaseTTS(ABC):
    """Abstract interface for TTS synthesis."""

    @abstractmethod
    def speak(self, text: str, blocking: bool = False) -> None:
        pass


@TTSRegistry.register("sapi")
@TTSRegistry.register("default")
class SapiTTS(BaseTTS):
    """Windows SAPI TTS implementation via pyttsx3 with single-instance caching.
    
    Defaults to non-blocking speech on a background worker thread so command execution
    and pipeline response are never blocked by audio playback. Pass blocking=True
    only when sequential speech is strictly necessary.
    """

    _engine_lock = threading.Lock()
    _engine = None
    _speak_lock = threading.Lock()

    def _do_speak(self, text: str) -> None:
        # Avoid overlapping or queued stale confirmations
        acquired = self._speak_lock.acquire(blocking=False)
        if not acquired:
            logger.debug(f"TTS skipped (previous speech still active): '{text[:30]}...'")
            return
        try:
            with self._engine_lock:
                try:
                    if self._engine is None:
                        import pyttsx3
                        self.__class__._engine = pyttsx3.init()
                    self._engine.say(text)
                    self._engine.runAndWait()
                except Exception as ex:
                    logger.debug(f"TTS synthesis warning: {ex}")
                    self.__class__._engine = None  # Re-initialize on next call
        finally:
            self._speak_lock.release()

    def speak(self, text: str, blocking: bool = False) -> None:
        if not text:
            return
        if blocking:
            self._do_speak(text)
        else:
            threading.Thread(target=self._do_speak, args=(text,), daemon=True).start()

    def stop(self) -> None:
        """Interrupt ongoing speech immediately."""
        with self._engine_lock:
            if self._engine is not None:
                try:
                    self._engine.stop()
                except Exception:
                    pass


_default_tts = SapiTTS()


def say(text: str, enabled: bool = True, blocking: bool = False) -> None:
    """Spoken confirmation helper; best-effort, safe to fail, non-blocking by default."""
    if not enabled or not text:
        return
    _default_tts.speak(text, blocking=blocking)


def stop_speaking() -> None:
    """Halt any running TTS synthesis immediately."""
    _default_tts.stop()
