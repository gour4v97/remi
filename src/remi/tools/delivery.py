"""Text delivery subsystem: Win32 SendInput Unicode keyboard typing, fast Ctrl+V clipboard paste, and clipboard management."""
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
VK_CONTROL = 0x11
VK_V = 0x56
VK_RETURN = 0x0D


def _key(vk: int, scan: int, flags: int) -> INPUT:
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.u.ki = KEYBDINPUT(vk, scan, flags, 0, None)
    return inp


def paste_text(text: str) -> bool:
    """Instantly paste text into foreground window via system clipboard and Ctrl+V.
    
    10x - 50x faster than simulating individual keystrokes for long paragraphs.
    """
    if not text:
        return True
    set_clipboard(text)

    if IS_WINDOWS and user32 is not None:
        time.sleep(0.04)  # Small yield to ensure target window sees updated clipboard
        # Press Ctrl, Press V, Release V, Release Ctrl
        inputs = [
            _key(VK_CONTROL, 0, 0),
            _key(VK_V, 0, 0),
            _key(VK_V, 0, KEYEVENTF_KEYUP),
            _key(VK_CONTROL, 0, KEYEVENTF_KEYUP),
        ]
        arr = (INPUT * len(inputs))(*inputs)
        sent = user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))
        return sent == len(inputs)

    # Cross-platform fallback: try keyboard library if installed
    try:
        import keyboard
        keyboard.send("ctrl+v")
        return True
    except Exception:
        pass

    # Fallback to simulated keystrokes if Ctrl+V fails
    type_text(text)
    return True


def type_text(text: str) -> None:
    """Type Unicode text into the current foreground window (Windows, Linux, macOS)."""
    # 1. Windows: Win32 SendInput Unicode keyboard event
    if IS_WINDOWS and user32 is not None:
        time.sleep(0.05)
        inputs: list[INPUT] = []
        for ch in text:
            if ch == "\r":
                continue
            if ch == "\n":
                inputs.append(_key(VK_RETURN, 0, 0))
                inputs.append(_key(VK_RETURN, 0, KEYEVENTF_KEYUP))
                continue
            inputs.append(_key(0, ord(ch), KEYEVENTF_UNICODE))
            inputs.append(_key(0, ord(ch), KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))

        if not inputs:
            return

        arr = (INPUT * len(inputs))(*inputs)
        sent = user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))
        if sent != len(inputs):
            raise RuntimeError(f"SendInput delivered {sent}/{len(inputs)} - target window may have elevated integrity.")
        return

    # 2. Linux: xdotool or wtype if available
    import shutil
    import subprocess
    if shutil.which("xdotool"):
        try:
            subprocess.run(["xdotool", "type", "--clearmodifiers", "--", text], check=True)
            return
        except Exception:
            pass
    elif shutil.which("wtype"):
        try:
            subprocess.run(["wtype", "--", text], check=True)
            return
        except Exception:
            pass

    # 3. macOS: osascript
    if shutil.which("osascript"):
        try:
            escaped = text.replace('\\', '\\\\').replace('"', '\\"')
            script = f'tell application "System Events" to keystroke "{escaped}"'
            subprocess.run(["osascript", "-e", script], check=True)
            return
        except Exception:
            pass

    logger.info(f"[Text Delivery fallback]: {text}")


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
    """Registered delivery service supporting paste, type and clipboard modes."""

    def deliver(self, text: str, mode: str = "paste", start_hwnd: int = 0) -> str:
        set_clipboard(text)
        if mode == "clipboard":
            return "clipboard"
        if mode == "guarded" and foreground_hwnd() != start_hwnd:
            return "clipboard (guarded fallback)"
        if mode == "type":
            type_text(text)
            return "type"
        # Default modern high-speed mode
        paste_text(text)
        return "paste"
