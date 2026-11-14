"""Browser Voice Assistant Agent (Remi).

Listens for hotkey, captures audio, transcribes with whisper.cpp, transliterates Hinglish,
and dispatches browser actions via Chrome DevTools Protocol.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

try:
    import pystray
except Exception:
    pystray = None

from remi.agents._base import BaseAgent
from remi.core import config
from remi.core.constants import (
    APP_BROWSER_ID,
    COLORS,
    DEFAULT_HOTKEY_BROWSER,
    MODEL_CATALOG,
)
from remi.core.events import EventBus
from remi.core.registry import AgentRegistry
from remi.engine import whisper_cpp
from remi.speech import capture, tts
from remi.speech.translit import to_roman
from remi.tools import browser, history, router
from remi.ui.tray import TrayApp

logger = logging.getLogger(__name__)

LETTER = "R"
IDLE_COLOR = COLORS["violet"]


@AgentRegistry.register("browser")
@AgentRegistry.register("remi")
class BrowserVoiceAgent(BaseAgent):
    """Voice-controlled browser agent executing natural language and Hinglish commands."""

    def __init__(self, cfg: dict[str, Any] | None = None):
        self.app = APP_BROWSER_ID
        self.cfg = cfg or config.load(self.app)
        self.cfg.setdefault("hotkey", DEFAULT_HOTKEY_BROWSER)
        self._state = {"capturing": None, "busy": False}
        self._lock = threading.Lock()
        self.tray: TrayApp | None = None
        self.events = EventBus.get_instance()

    def process_audio(self, pcm: bytes) -> router.Outcome:
        from remi.core.perf import PipelineTimer
        timer = PipelineTimer()
        started = time.time()
        try:
            timer.mark("key_up")

            if len(pcm) < 9600:
                raise RuntimeError("Recording too short.")
            if whisper_cpp.peak_amplitude(pcm) <= 32:
                raise RuntimeError("Silent recording - check microphone selection.")
            timer.mark("audio_ready")

            engine = whisper_cpp.WhisperCppEngine(self.cfg)
            raw_text = engine.transcribe_pcm(pcm, self.cfg["local_model"], "hinglish", self.cfg)
            text = to_roman(raw_text).strip()
            if not text:
                raise RuntimeError("Empty transcript.")
            timer.mark("transcribed")

            self.events.publish("voice:transcribed", {"text": text, "agent": self.app})

            if self.tray:
                self.tray.set_state("thinking", self.cfg.get("hotkey", DEFAULT_HOTKEY_BROWSER))

            outcome = router.run(text, self.cfg)
            timer.mark("parsed")

            if self.tray:
                self.tray.set_state("idle", self.cfg.get("hotkey", DEFAULT_HOTKEY_BROWSER))

            duration_ms = int((time.time() - started) * 1000)
            timer.mark("action_done")

            history.append(
                self.app,
                {
                    "transcript": text,
                    "detail": outcome.detail,
                    "ok": outcome.ok,
                    "ms": duration_ms,
                },
            )

            feedback_enabled = self.cfg.get("voice_feedback", True)
            timer.mark("tts_start")
            tts.say(outcome.spoken if outcome.ok else f"Sorry. {outcome.spoken}", feedback_enabled)

            if not outcome.ok and self.tray:
                self.tray.notify("Remi", outcome.spoken, error=True)

            self.events.publish("command:executed", {"text": text, "outcome": outcome})

            # Log timing — always to file; print table in bench_mode
            timer.log_to_file()
            if self.cfg.get("bench_mode", False):
                timer.print_table()

            return outcome

        except Exception as ex:
            duration_ms = int((time.time() - started) * 1000)
            history.append(
                self.app,
                {
                    "transcript": "",
                    "detail": "error",
                    "ok": False,
                    "error": str(ex),
                    "ms": duration_ms,
                },
            )
            tts.say("Sorry, that failed.", self.cfg.get("voice_feedback", True))
            if self.tray:
                self.tray.notify("Remi failed", str(ex), error=True)
            logger.error(f"Error processing audio in {self.app}: {ex}")
            return router.Outcome(False, "failed", str(ex))

    def toggle(self) -> None:
        with self._lock:
            if self._state["busy"]:
                return
            if self._state["capturing"] is None:
                try:
                    cap = capture.MicCapture()
                    cap.start()
                except Exception as ex:
                    if self.tray:
                        self.tray.notify("Microphone", str(ex), error=True)
                    return
                self._state["capturing"] = cap
                if self.tray:
                    self.tray.set_state("recording", self.cfg.get("hotkey", DEFAULT_HOTKEY_BROWSER))
                return

            cap = self._state["capturing"]
            self._state["capturing"] = None
            self._state["busy"] = True

        pcm = cap.stop_and_read()
        self._state["busy"] = False
        if self.tray:
            self.tray.set_state("idle", self.cfg.get("hotkey", DEFAULT_HOTKEY_BROWSER))

        threading.Thread(target=self.process_audio, args=(pcm,), daemon=True).start()

    def build_tray(self) -> TrayApp:
        hotkey = self.cfg.get("hotkey") or DEFAULT_HOTKEY_BROWSER

        def toggle_action(icon, item):
            self.toggle()

        def start_browser_action(icon, item):
            exe = browser.find_browser_exe()
            if not exe:
                if self.tray:
                    self.tray.notify("Remi", "No Edge/Chrome found", error=True)
                return
            profile = (
                None
                if self.cfg.get("browser_profile", "remi") == "default"
                else str(config.LOCALAPPDATA / "browser-profile")
            )
            ok = browser.launch(exe, self.cfg["cdp_port"], profile)
            if self.tray:
                self.tray.notify(
                    "Remi",
                    "Browser started with voice control." if ok else "Debug port did not respond.",
                    not ok,
                )

        def toggle_feedback(icon, item):
            self.cfg["voice_feedback"] = not self.cfg.get("voice_feedback", True)
            config.save(self.app, self.cfg)

        menu = [
            pystray.MenuItem("Speak a command", toggle_action, default=True),
            pystray.MenuItem("Start browser (voice control)", start_browser_action),
            pystray.MenuItem(
                lambda item: f"Voice feedback  {'✓' if self.cfg.get('voice_feedback', True) else ''}",
                toggle_feedback,
            ),
        ] if pystray is not None else []

        tray = TrayApp(self.app, hotkey, LETTER, IDLE_COLOR, menu)
        tray.on_toggle = self.toggle
        self.tray = tray
        return tray

    def start(self) -> None:
        whisper_cpp.start_server(self.cfg)
        tray = self.build_tray()
        tray.run()


def say_text(text: str, cfg: dict | None = None) -> int:
    """Execute command directly from text string without microphone capture."""
    c = cfg or config.load(APP_BROWSER_ID)
    outcome = router.run(text, c)
    history.append(
        APP_BROWSER_ID,
        {"transcript": text, "detail": outcome.detail, "ok": outcome.ok, "ms": 0},
    )
    print(f"command : {outcome.ok}")
    print(f"result  : {outcome.spoken}")
    print(f"detail  : {outcome.detail}")
    return 0 if outcome.ok else 2


def say_audio(path: str, cfg: dict | None = None) -> int:
    """Execute command from WAV audio file."""
    import wave
    import numpy as np

    c = cfg or config.load(APP_BROWSER_ID)
    with wave.open(path, "rb") as w:
        rate, ch, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if width != 2:
        raise RuntimeError("Only 16-bit WAV supported.")
    samples = np.frombuffer(raw, dtype=np.int16)
    if ch > 1:
        samples = samples.reshape(-1, ch).mean(axis=1).astype(np.int16)
    if rate != 16000:
        pcm = capture.resample_16k(samples.tobytes(), rate)
    else:
        pcm = samples.tobytes()

    engine = whisper_cpp.WhisperCppEngine(c)
    text = engine.transcribe_pcm(pcm, c["local_model"], "hinglish", c)
    text = to_roman(text).strip()
    print(f"heard    : {text}")
    outcome = router.run(text, c)
    history.append(
        APP_BROWSER_ID,
        {"transcript": text, "detail": outcome.detail, "ok": outcome.ok, "ms": 0},
    )
    print(f"command  : {outcome.ok}")
    print(f"result   : {outcome.spoken}")
    print(f"detail   : {outcome.detail}")
    return 0 if outcome.ok else 2
