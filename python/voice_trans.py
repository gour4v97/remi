"""Voice Trans (Python port) — push-to-talk dictation for Windows.

Press the hotkey, speak, press again; the transcript is typed into the focused
app. Local Whisper only (whisper.cpp CLI, shared ggml models with the .NET suite).
"""
import argparse
import sys
import threading
import time

import pystray

from voicecore import asr, autostart, config, delivery, history
from voicecore.app import TrayApp, COLORS
from voicecore.translit import smart_writing, to_roman

APP = "voice-trans-py"
HOTKEY_DEFAULT = "ctrl+alt+space"
LETTER, IDLE_COLOR = "V", COLORS["idle"]

_state = {"capturing": None, "start": 0.0, "busy": False}
_lock = threading.Lock()


def load_dictionary() -> list[str]:
    """Reuses the .NET suite's dictionary file (same voisu-compatible format)."""
    p = config.APPDATA.parent / "voice-trans" / "dictionary.txt"
    if not p.exists():
        p = config.APPDATA / "dictionary.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# one term per line; '#' starts a comment (after a space is fine)\nNamaste\n", encoding="utf-8")
    terms = []
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        s = s.split(" #")[0].strip()
        if s:
            terms.append(s)
    return sorted(set(terms), key=len, reverse=True)


def apply_dictionary(text: str, terms: list[str]) -> str:
    import re
    for term in terms:
        text = re.sub(r"(?<![\w" "\u0900-\u097F])" + re.escape(term) + r"(?![\w" "\u0900-\u097F])",
                      term, text, flags=re.IGNORECASE)
    return text


def process(pcm: bytes, cfg, tray: TrayApp):
    started = time.time()
    try:
        if len(pcm) < 9600:
            raise RuntimeError("Recording too short.")
        if asr.peak_amplitude(pcm) <= 32:
            raise RuntimeError("Silent recording — is the right mic selected?")
        text = asr.transcribe_pcm(pcm, cfg["local_model"], cfg.get("language", "hinglish"), cfg)
        if cfg.get("language", "hinglish") == "hinglish":
            text = to_roman(text)
        text = smart_writing(text, cfg.get("writing_mode", "smart"))
        text = apply_dictionary(text, load_dictionary())
        if not text.strip():
            raise RuntimeError("Empty transcript.")

        mode = cfg.get("delivery_mode", "type")
        if mode == "clipboard":
            delivery.set_clipboard(text)
            detail = "clipboard"
        else:
            delivery.set_clipboard(text)  # recoverability guarantee, like the .NET suite
            delivery.type_text(text)
            detail = "type"
        history.append(APP, {"transcript": text, "detail": detail, "ok": True,
                             "ms": int((time.time() - started) * 1000)})
    except Exception as ex:
        history.append(APP, {"transcript": "", "detail": "error", "ok": False,
                             "error": str(ex), "ms": int((time.time() - started) * 1000)})
        tray.notify("Voice Trans (py) failed", str(ex), error=True)


def toggle(tray: TrayApp, cfg):
    with _lock:
        if _state["busy"]:
            return
        if _state["capturing"] is None:
            cap = _start_recording(tray, cfg)
            if cap:
                _state["capturing"] = cap
        else:
            cap = _state["capturing"]
            _state["capturing"] = None
            _state["busy"] = True
    if _state["busy"]:
        pcm = cap.stop_and_read()
        _state["busy"] = False
        tray.set_state("idle", cfg.get("hotkey", HOTKEY_DEFAULT))
        threading.Thread(target=process, args=(pcm, cfg, tray), daemon=True).start()


def _start_recording(tray: TrayApp, cfg):
    try:
        cap = _Mic()
        cap.start()
        tray.set_state("recording", cfg.get("hotkey", HOTKEY_DEFAULT))
        return cap
    except Exception as ex:
        tray.notify("Microphone", str(ex), error=True)
        return None


class _Mic:
    """Thin wrapper over sounddevice matching the C# MicCapture shape."""

    def __init__(self):
        from voicecore.capture import MicCapture
        self._cap = MicCapture()

    def start(self):
        self._cap.start()

    def stop_and_read(self) -> bytes:
        return self._cap.stop_and_read()


def build_tray(cfg) -> TrayApp:
    hotkey = cfg.get("hotkey") or HOTKEY_DEFAULT

    def toggle_action(icon, item):
        toggle(tray, cfg)

    def set_mode(mode):
        def action(icon, item):
            cfg["delivery_mode"] = mode
            config.save(APP, cfg)
        return action

    menu = [
        pystray.MenuItem("Toggle dictation", toggle_action, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(lambda item: f"Delivery: type  {'✓' if cfg.get('delivery_mode','type')=='type' else ''}",
                         set_mode("type")),
        pystray.MenuItem(lambda item: f"Delivery: clipboard  {'✓' if cfg.get('delivery_mode')=='clipboard' else ''}",
                         set_mode("clipboard")),
        pystray.MenuItem(lambda item: f"Delivery: guarded  {'✓' if cfg.get('delivery_mode')=='guarded' else ''}",
                         set_mode("guarded")),
    ]
    tray = TrayApp(APP, hotkey, LETTER, IDLE_COLOR, menu)
    tray.on_toggle = lambda: toggle(tray, cfg)
    return tray


def main():
    ap = argparse.ArgumentParser(description="Voice Trans (Python port)")
    ap.add_argument("cmd", nargs="?", default="start",
                    choices=["start", "history", "model", "autostart"])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cfg = config.load(APP)
    cfg.setdefault("hotkey", HOTKEY_DEFAULT)

    if args.cmd == "model":
        from remi import model_cmd  # shared downloader
        import argparse as _ap
        return model_cmd(_ap.Namespace(payload=args.payload))
    if args.cmd == "autostart":
        return autostart.handle_cli(APP, __file__, args.payload)
    if args.cmd == "history":
        entries = history.load(APP, 20)
        for e in reversed(entries):
            what = e.get("transcript", "") if e.get("ok") else f"ERROR: {e.get('error')}"
            print(f"{e.get('at', '')[:19]}  {what[:90]}")
        return

    asr.prewarm(cfg)
    print(f"Voice Trans (Python) — hotkey: {cfg['hotkey']} — tray icon starting…")
    print("NOTE: stop the .NET voice-trans daemon first if it is running (same hotkey).")
    tray = build_tray(cfg)
    tray.run()


if __name__ == "__main__":
    main()
