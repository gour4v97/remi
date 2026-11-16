"""Text-to-Speech synthesis with engine caching, Kokoro neural TTS, and non-blocking background queue."""
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

    def stop(self) -> None:
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


@TTSRegistry.register("kokoro")
class KokoroTTS(BaseTTS):
    """High-quality local neural TTS with Hindi/Hinglish and English voice support.

    Zero cloud dependencies. Generates natural-sounding speech locally via kokoro-onnx.
    Falls back gracefully to SapiTTS if Kokoro or ONNX is unavailable.
    """

    def __init__(self, voice: str = "hf_beta", lang: str = "hi"):
        self.voice = voice
        self.lang = lang
        self._kokoro = None
        self._fallback = SapiTTS()
        self._lock = threading.Lock()
        self._init_kokoro()

    def _init_kokoro(self) -> None:
        try:
            import kokoro_onnx

            self._kokoro = kokoro_onnx.Kokoro("kokoro-v0_19.onnx", "voices.json")
            logger.info("Kokoro neural TTS initialized successfully.")
        except Exception as ex:
            logger.debug(f"Kokoro initialization skipped ({ex}); using SAPI fallback.")

    def _do_speak(self, text: str) -> None:
        if self._kokoro is None:
            self._fallback.speak(text, blocking=True)
            return

        with self._lock:
            try:
                import sounddevice as sd

                samples, sample_rate = self._kokoro.create(
                    text,
                    voice=self.voice,
                    speed=1.0,
                    lang=self.lang,
                )
                sd.play(samples, sample_rate)
                sd.wait()
            except Exception as ex:
                logger.debug(f"Kokoro speech synthesis failed ({ex}); falling back to SAPI.")
                self._fallback.speak(text, blocking=True)

    def speak(self, text: str, blocking: bool = False) -> None:
        if not text:
            return
        if blocking:
            self._do_speak(text)
        else:
            threading.Thread(target=self._do_speak, args=(text,), daemon=True).start()

    def stop(self) -> None:
        try:
            import sounddevice as sd

            sd.stop()
        except Exception:
            pass
        self._fallback.stop()


_default_tts: BaseTTS = SapiTTS()


def set_tts_engine(engine_name: str = "default") -> None:
    """Switch active global TTS engine between 'sapi' and 'kokoro'."""
    global _default_tts
    if engine_name.lower() == "kokoro":
        _default_tts = KokoroTTS()
    else:
        _default_tts = SapiTTS()


def say(text: str, enabled: bool = True, blocking: bool = False) -> None:
    """Spoken confirmation helper; best-effort, safe to fail, non-blocking by default."""
    if not enabled or not text:
        return
    _default_tts.speak(text, blocking=blocking)


def stop_speaking() -> None:
    """Halt any running TTS synthesis immediately."""
    _default_tts.stop()
