"""Floating, frameless, transparent HUD overlay for real-time voice feedback.

Shows pill-shaped state indicator in top-right or center:
- 🎙️ Listening (red pulsing badge)
- 🧠 Thinking (amber badge while whisper/SLM processes)
- ✅ Done (green badge with recognized command/action)

Built entirely with Python standard library tkinter (zero extra pip dependencies).
Safe on headless environments: fails gracefully if no display server is available.
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

STATE_COLORS = {
    "idle": ("#2B2D42", "#8D99AE", "⚪ Idle"),
    "listening": ("#D90429", "#EF233C", "🎙️ Listening..."),
    "thinking": ("#FF9F1C", "#FFBF69", "🧠 Thinking..."),
    "done": ("#2EC4B6", "#CBF3F0", "✅ Done"),
    "error": ("#E63946", "#F1FAEE", "❌ Error"),
}


class StatusOverlay:
    """Non-blocking, always-on-top desktop overlay indicator."""

    _instance: "StatusOverlay | None" = None
    _lock = threading.Lock()

    def __init__(self, position: str = "top-right"):
        self.position = position
        self._cmd_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._root = None
        self._label = None
        self._detail_label = None
        self._is_running = False

    @classmethod
    def get_instance(cls) -> "StatusOverlay":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def start(self) -> None:
        """Start the overlay GUI loop in a dedicated background thread."""
        if self._is_running:
            return
        self._is_running = True
        self._thread = threading.Thread(target=self._gui_loop, daemon=True)
        self._thread.start()

    def set_state(self, state: str, detail: str = "") -> None:
        """Update overlay state ('listening', 'thinking', 'done', 'idle', 'error')."""
        if not self._is_running:
            self.start()
        self._cmd_queue.put((state, detail))

    def _gui_loop(self) -> None:
        try:
            import tkinter as tk
        except ImportError:
            logger.debug("tkinter not available; overlay disabled.")
            return

        try:
            self._root = tk.Tk()
            self._root.title("Remi HUD")
            self._root.overrideredirect(True)  # Frameless
            self._root.wm_attributes("-topmost", True)  # Always on top
            try:
                self._root.wm_attributes("-alpha", 0.92)  # Slight transparency
            except Exception:
                pass

            # Sizing and positioning
            width, height = 260, 52
            screen_w = self._root.winfo_screenwidth()
            pad_x, pad_y = 30, 40

            if self.position == "top-right":
                x = screen_w - width - pad_x
                y = pad_y
            elif self.position == "top-center":
                x = (screen_w - width) // 2
                y = pad_y
            else:
                x = screen_w - width - pad_x
                y = pad_y

            self._root.geometry(f"{width}x{height}+{x}+{y}")
            self._root.configure(bg="#1E1E2E")

            container = tk.Frame(self._root, bg="#1E1E2E", padx=10, pady=6)
            container.pack(fill="both", expand=True)

            self._label = tk.Label(
                container,
                text="Remi Ready",
                font=("Segoe UI", 10, "bold"),
                fg="#F8F8F2",
                bg="#1E1E2E",
                anchor="w",
            )
            self._label.pack(fill="x")

            self._detail_label = tk.Label(
                container,
                text="Press hotkey to speak",
                font=("Segoe UI", 8),
                fg="#A6ADC8",
                bg="#1E1E2E",
                anchor="w",
            )
            self._detail_label.pack(fill="x")

            # Polling queue for state updates
            self._poll_queue()
            self._root.mainloop()

        except Exception as ex:
            logger.debug(f"Overlay loop error ({ex}); operating in headless mode.")
        finally:
            self._is_running = False

    def _poll_queue(self) -> None:
        if self._root is None:
            return

        try:
            while not self._cmd_queue.empty():
                state, detail = self._cmd_queue.get_nowait()
                bg_color, fg_color, badge = STATE_COLORS.get(state, ("#1E1E2E", "#F8F8F2", state))

                if self._label:
                    self._label.configure(text=badge, fg=fg_color)
                if self._detail_label:
                    short_detail = (detail[:32] + "...") if len(detail) > 35 else detail
                    self._detail_label.configure(text=short_detail or "Ready")
        except Exception:
            pass

        self._root.after(80, self._poll_queue)

    def close(self) -> None:
        if self._root:
            try:
                self._root.quit()
            except Exception:
                pass
