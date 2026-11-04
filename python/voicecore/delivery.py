"""Text delivery: SendInput Unicode typing + clipboard (voisu's order of guarantees)."""
import ctypes
import time

import pyperclip

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_uint), ("time", ctypes.c_uint),
                ("dwExtraInfo", ctypes.c_void_p)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_uint), ("u", _INPUTUNION)]


KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1


def type_text(text: str):
    """Types text into the focused window (works for Devanagari too)."""
    time.sleep(0.15)
    inputs = []
    for ch in text:
        if ch == "\r":
            continue
        if ch == "\n":
            inputs.append(_key(0x0D, 0, 0))   # VK_RETURN
            inputs.append(_key(0x0D, 0, KEYEVENTF_KEYUP))
            continue
        inputs.append(_key(0, ord(ch), KEYEVENTF_UNICODE))
        inputs.append(_key(0, ord(ch), KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))
    if not inputs:
        return
    arr = (INPUT * len(inputs))(*inputs)
    sent = user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))
    if sent != len(inputs):
        raise RuntimeError(f"SendInput delivered {sent}/{len(inputs)} — focused window may be elevated")


def _key(vk: int, scan: int, flags: int) -> INPUT:
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.u.ki = KEYBDINPUT(vk, scan, flags, 0, None)
    return inp


def set_clipboard(text: str):
    pyperclip.copy(text)


def foreground_hwnd() -> int:
    return user32.GetForegroundWindow()
