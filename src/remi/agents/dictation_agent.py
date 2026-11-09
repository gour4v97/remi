"""Voice Trans push-to-talk dictation agent for typing into focused applications."""
from __future__ import annotations

import logging
import re
import threading
import time
from pathlib import Path
from typing import Any

try:
    import pystray
except Exception:
    pystray = None

from remi.agents._base import BaseAgent
from remi.core import config
from remi.core.constants import (
    APP_DICTATION_ID,
    COLORS,
    DEFAULT_HOTKEY_DICTATION,
)
from remi.core.events import EventBus
from remi.core.registry import AgentRegistry
from remi.engine import whisper_cpp
from remi.speech import capture
from remi.speech.translit import smart_writing, to_roman
from remi.tools import delivery, history
from remi.ui.tray import TrayApp

logger = logging.getLogger(__name__)

LETTER = "V"
IDLE_COLOR = COLORS["idle"]


def load_dictionary() -> list[str]:
    """Load custom replacement terms from dictionary.txt."""
    p = config.APPDATA.parent / "voice-trans" / "dictionary.txt"
    if not p.exists():
        p = config.APPDATA / "dictionary.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text("# one term per line; '#' starts a comment\nNamaste\n", encoding="utf-8")
    terms: list[str] = []
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            s = s.split(" #")[0].strip()
            if s:
                terms.append(s)
    return sorted(set(terms), key=len, reverse=True)


def apply_dictionary(text: str, terms: list[str]) -> str:
    """Rewrite any-case matches to the canonical term using word boundaries."""
    for term in terms:
        text = re.sub(
            r"(?<![\w\u0900-\u097F])" + re.escape(term) + r"(?![\w\u0900-\u097F])",
            term,
            text,
            flags=re.IGNORECASE,
        )
    return text


@AgentRegistry.register("dictation")
@AgentRegistry.register("voice-trans")
class DictationAgent(BaseAgent):
    """Push-to-talk dictation assistant typing directly into focused Windows applications."""

    def __init__(self, cfg: dict[str, Any] | None = None):
        self.app = APP_DICTATION_ID
        self.cfg = cfg or config.load(self.app)
        self.cfg.setdefault("hotkey", DEFAULT_HOTKEY_DICTATION)
        self._state = {"capturing": None, "start": 0.0, "busy": False, "hwnd": 0}
        self._lock = threading.Lock()
        self.tray: TrayApp | None = None
        self.events = EventBus.get_instance()

    def process_audio(self, pcm: bytes, start_hwnd: int = 0) -> str:
        started = time.time()
        try:
            if len(pcm) < 9600:
                raise RuntimeError("Recording too short.")
            if whisper_cpp.peak_amplitude(pcm) <= 32:
                raise RuntimeError("Silent recording - check microphone selection.")

            engine = whisper_cpp.WhisperCppEngine(self.cfg)
            lang = self.cfg.get("language", "hinglish")
            text = engine.transcribe_pcm(pcm, self.cfg["local_model"], lang, self.cfg)

            if lang == "hinglish":
                text = to_roman(text)
            text = smart_writing(text, self.cfg.get("writing_mode", "smart"))
            text = apply_dictionary(text, load_dictionary())

            if not text.strip():
                raise RuntimeError("Empty transcript.")

            mode = self.cfg.get("delivery_mode", "type")
            if mode == "clipboard":
                delivery.set_clipboard(text)
                detail = "clipboard"
            elif mode == "guarded" and delivery.foreground_hwnd() != start_hwnd:
                delivery.set_clipboard(text)
                detail = "clipboard (guarded fallback)"
                if self.tray:
                    self.tray.notify("Voice Trans", "Focused window changed - copied to clipboard.")
            else:
                delivery.set_clipboard(text)
                delivery.type_text(text)
                detail = "type"

            duration_ms = int((time.time() - started) * 1000)
            history.append(
                self.app,
                {"transcript": text, "detail": detail, "ok": True, "ms": duration_ms},
            )
            self.events.publish("dictation:delivered", {"text": text, "mode": detail})
            return text

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
            if self.tray:
                self.tray.notify("Voice Trans failed", str(ex), error=True)
            logger.error(f"Dictation processing error: {ex}")
            return ""

    def toggle(self) -> None:
        with self._lock:
            if self._state["busy"]:
                return
            if self._state["capturing"] is None:
                cap = self._start_recording()
                if cap:
                    self._state["capturing"] = cap
                return
            cap = self._state["capturing"]
            self._state["capturing"] = None
            self._state["busy"] = True

        if self._state["busy"]:
            pcm = cap.stop_and_read()
            start_hwnd = self._state["hwnd"]
            self._state["busy"] = False
            if self.tray:
                self.tray.set_state("idle", self.cfg.get("hotkey", DEFAULT_HOTKEY_DICTATION))
            threading.Thread(
                target=self.process_audio,
                args=(pcm, start_hwnd),
                daemon=True,
            ).start()

    def _start_recording(self) -> capture.MicCapture | None:
        try:
            cap = capture.MicCapture()
            cap.start()
            self._state["hwnd"] = delivery.foreground_hwnd()
            if self.tray:
                self.tray.set_state("recording", self.cfg.get("hotkey", DEFAULT_HOTKEY_DICTATION))
            return cap
        except Exception as ex:
            if self.tray:
                self.tray.notify("Microphone", str(ex), error=True)
            return None

    def build_tray(self) -> TrayApp:
        hotkey = self.cfg.get("hotkey") or DEFAULT_HOTKEY_DICTATION

        def toggle_action(icon, item):
            self.toggle()

        def set_mode(mode: str):
            def action(icon, item):
                self.cfg["delivery_mode"] = mode
                config.save(self.app, self.cfg)
            return action

        menu = [
            pystray.MenuItem("Toggle dictation", toggle_action, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda item: f"Delivery: type  {'✓' if self.cfg.get('delivery_mode', 'type') == 'type' else ''}",
                set_mode("type"),
            ),
            pystray.MenuItem(
                lambda item: f"Delivery: clipboard  {'✓' if self.cfg.get('delivery_mode') == 'clipboard' else ''}",
                set_mode("clipboard"),
            ),
            pystray.MenuItem(
                lambda item: f"Delivery: guarded  {'✓' if self.cfg.get('delivery_mode') == 'guarded' else ''}",
                set_mode("guarded"),
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
