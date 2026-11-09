"""Text delivery subsystem: Win32 SendInput Unicode keyboard typing and clipboard management."""
from __future__ import annotations

import ctypes
import logging
import time

try:
    import pyperclip
except ImportError:
    pyperclip = None

from remi.core.registry import ToolRegistry

logger = logging.getLogger(__name__)

# Safe Win32 dynamic loader
try:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    IS_WINDOWS = True
except (AttributeError, OSError):
    user32 = None
    kernel32 = None
    IS_WINDOWS = False


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_uint),
        ("time", ctypes.c_uint),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_uint), ("u", _INPUTUNION)]


KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1


def _key(vk: int, scan: int, flags: int) -> INPUT:
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.u.ki = KEYBDINPUT(vk, scan, flags, 0, None)
    return inp


def type_text(text: str) -> None:
    """Type Unicode text into the current foreground window via Win32 SendInput."""
    if not IS_WINDOWS or user32 is None:
        logger.info(f"[Mock Text Delivery]: {text}")
        return

    time.sleep(0.15)
    inputs: list[INPUT] = []
    for ch in text:
        if ch == "\r":
            continue
        if ch == "\n":
            inputs.append(_key(0x0D, 0, 0))  # VK_RETURN
            inputs.append(_key(0x0D, 0, KEYEVENTF_KEYUP))
            continue
        inputs.append(_key(0, ord(ch), KEYEVENTF_UNICODE))
        inputs.append(_key(0, ord(ch), KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))

    if not inputs:
        return

    arr = (INPUT * len(inputs))(*inputs)
    sent = user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))
    if sent != len(inputs):
        raise RuntimeError(f"SendInput delivered {sent}/{len(inputs)} - target window may have elevated integrity.")


def set_clipboard(text: str) -> None:
    """Copy text to system clipboard."""
    if pyperclip:
        try:
            pyperclip.copy(text)
        except Exception as ex:
            logger.warning(f"Failed to copy to clipboard: {ex}")


def foreground_hwnd() -> int:
    """Return handle of current active window."""
    if IS_WINDOWS and user32 is not None:
        return user32.GetForegroundWindow()
    return 0


@ToolRegistry.register("delivery")
class DeliveryService:
    """Registered delivery service supporting type and clipboard modes."""

    def deliver(self, text: str, mode: str = "type", start_hwnd: int = 0) -> str:
        set_clipboard(text)
        if mode == "clipboard":
            return "clipboard"
        if mode == "guarded" and foreground_hwnd() != start_hwnd:
            return "clipboard (guarded fallback)"
        type_text(text)
        return "type"
