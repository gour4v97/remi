"""System tray runner and global hotkey integration for Remi Suite applications."""
from __future__ import annotations

import logging
import os
import threading
from typing import Any, Callable

try:
    import keyboard
except ImportError:
    keyboard = None

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    pystray = None
    Image = None
    ImageDraw = None

from remi.core.constants import COLORS

logger = logging.getLogger(__name__)


def make_icon(color: tuple[int, int, int], letter: str) -> Any:
    """Generate a 64x64 RGBA circular icon with specified background color and letter."""
    if Image is None or ImageDraw is None:
        return None
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=color + (255,))
    d.text((24, 16), letter, fill="white")
    return img


class TrayApp:
    """System tray icon manager with global hotkey handler and dynamic menu states."""

    def __init__(
        self,
        app: str,
        hotkey: str,
        letter: str,
        idle_color: tuple[int, int, int],
        menu_items: list[Any],
    ):
        self.app = app
        self.letter = letter
        self.idle_color = idle_color
        self._state = "idle"
        self._lock = threading.Lock()
        self.on_toggle: Callable[[], None] | None = None

        if pystray is not None and Image is not None:
            self._icon = pystray.Icon(
                app,
                make_icon(idle_color, letter),
                f"{app} - {hotkey} to act",
                menu=pystray.Menu(*menu_items, pystray.MenuItem("Quit", self._quit)),
            )
        else:
            self._icon = None

        if keyboard is not None:
            try:
                keyboard.add_hotkey(hotkey, self._hotkey_pressed)
            except Exception as ex:
                logger.warning(f"Could not bind hotkey {hotkey}: {ex}")

    def set_state(self, state: str, note: str = "") -> None:
        """Update current tray state (e.g. idle, recording, thinking)."""
        with self._lock:
            self._state = state
        color = {"recording": COLORS["recording"], "thinking": COLORS["thinking"]}.get(state, self.idle_color)
        if self._icon is not None and Image is not None:
            try:
                self._icon.icon = make_icon(color, self.letter)
                self._icon.title = f"{self.app} - {note}"
            except Exception:
                pass

    def notify(self, title: str, message: str, error: bool = False) -> None:
        """Display desktop system notification."""
        if self._icon is not None:
            try:
                self._icon.notify(message, title)
            except Exception:
                pass

    def _hotkey_pressed(self) -> None:
        if self.on_toggle:
            threading.Thread(target=self.on_toggle, daemon=True).start()

    def _quit(self, icon, item) -> None:
        if icon:
            icon.stop()
        os._exit(0)

    def run(self) -> None:
        """Run system tray event loop."""
        if self._icon is not None:
            self._icon.run()
        else:
            logger.info(f"{self.app} running without GUI tray backend.")


def simple_menu(pairs: list[tuple[str, Callable]]) -> list[Any]:
    """Helper to convert list of (label, callback) tuples to pystray menu items."""
    if pystray is None:
        return []
    return [pystray.MenuItem(label, action) for label, action in pairs]
