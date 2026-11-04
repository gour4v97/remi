"""Shared tray + hotkey runner for the two Python apps."""
import threading

import keyboard
import pystray
from PIL import Image, ImageDraw

COLORS = {"idle": (74, 144, 217), "recording": (229, 72, 77),
          "thinking": (245, 166, 35), "violet": (124, 92, 217)}


def make_icon(color, letter) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=color + (255,))
    d.text((24, 16), letter, fill="white")
    return img


class TrayApp:
    """Hotkey toggle → on_toggle() in a worker thread; tray shows state and menu."""

    def __init__(self, app: str, hotkey: str, letter: str, idle_color, menu_items):
        self.app = app
        self.letter = letter
        self.idle_color = idle_color
        self._state = "idle"
        self._lock = threading.Lock()
        self.on_toggle = None  # set by the concrete app
        self._icon = pystray.Icon(
            app, make_icon(idle_color, letter),
            f"{app} (Python) — {hotkey} to act",
            menu=pystray.Menu(*menu_items, pystray.MenuItem("Quit", self._quit)))
        keyboard.add_hotkey(hotkey, self._hotkey_pressed)

    def set_state(self, state: str, note: str = ""):
        with self._lock:
            self._state = state
        color = {"recording": COLORS["recording"], "thinking": COLORS["thinking"]}.get(state, self.idle_color)
        try:
            self._icon.icon = make_icon(color, self.letter)
            self._icon.title = f"{self.app} (Python) — {note}"
        except Exception:
            pass

    def notify(self, title: str, message: str, error: bool = False):
        try:
            self._icon.notify(message, title)
        except Exception:
            pass

    def _hotkey_pressed(self):
        if self.on_toggle:
            threading.Thread(target=self.on_toggle, daemon=True).start()

    def _quit(self, icon, item):
        icon.stop()
        import os
        os._exit(0)

    def run(self):
        self._icon.run()


def simple_menu(pairs):
    return [pystray.MenuItem(label, action) for label, action in pairs]
