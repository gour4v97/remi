"""Streaming transcription worker for real-time partial transcript generation.

Periodically peeks at the live recording buffer (e.g. every 500ms) and transcribes
intermediate audio with whisper.cpp, streaming partial text to the floating HUD
so the user sees their words appearing live on screen while speaking.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable

from remi.engine import whisper_cpp
from remi.speech.capture import WarmMicCapture
from remi.speech.translit import to_roman
from remi.ui.overlay import StatusOverlay

logger = logging.getLogger(__name__)


class StreamingASRWorker:
    """Background worker generating live partial transcripts during active speech."""

    def __init__(
        self,
        mic: WarmMicCapture,
        cfg: dict,
        interval_s: float = 0.6,
        on_partial: Callable[[str], None] | None = None,
    ):
        self.mic = mic
        self.cfg = cfg
        self.interval_s = interval_s
        self.on_partial = on_partial
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        engine = whisper_cpp.WhisperCppEngine(self.cfg)
        model = self.cfg.get("local_model", "large-v3-turbo-q5_0")
        lang = self.cfg.get("language", "hinglish")

        while self._running and self.mic.is_recording:
            time.sleep(self.interval_s)
            if not self._running or not self.mic.is_recording:
                break

            # Need at least ~0.8s of audio (12,800 bytes) for a meaningful partial decode
            pcm = self.mic.peek_buffer()
            if len(pcm) < 25600:
                continue

            try:
                # Transcribe current partial audio snapshot
                text = engine.transcribe_pcm(pcm, model, lang, self.cfg)
                text = to_roman(text).strip()
                if text:
                    # Update live desktop HUD with streaming partial text
                    StatusOverlay.get_instance().set_state("listening", text)
                    if self.on_partial:
                        self.on_partial(text)
            except Exception as ex:
                logger.debug(f"Partial streaming decode warning: {ex}")
