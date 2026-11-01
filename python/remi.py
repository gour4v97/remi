"""Remi (Python port) — voice-controlled browser for Windows.

Press the hotkey, speak a command (English/Hindi/Hinglish), press again.
Local Whisper → command grammar → Chrome DevTools Protocol → spoken confirmation.
"""
import argparse
import sys
import threading
import time

import pystray

from voicecore import asr, browser, config, history, router
from voicecore.app import TrayApp, COLORS
from voicecore.translit import to_roman

APP = "remi-py"
HOTKEY_DEFAULT = "ctrl+alt+b"
LETTER, IDLE_COLOR = "R", COLORS["violet"]

_state = {"capturing": None, "busy": False}
_lock = threading.Lock()


def speak(text: str, enabled: bool):
    if not enabled or not text:
        return
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    except Exception:
        pass  # TTS is best-effort feedback


def process(pcm: bytes, cfg, tray: TrayApp):
    started = time.time()
    try:
        if len(pcm) < 9600:
            raise RuntimeError("Recording too short.")
        if asr.peak_amplitude(pcm) <= 32:
            raise RuntimeError("Silent recording — is the right mic selected?")
        text = asr.transcribe_pcm(pcm, cfg["local_model"], "hinglish")
        text = to_roman(text).strip()
        if not text:
            raise RuntimeError("Empty transcript.")
        outcome = router.run(text, cfg)
        history.append(APP, {"transcript": text, "detail": outcome.detail,
                             "ok": outcome.ok, "ms": int((time.time() - started) * 1000)})
        speak(outcome.spoken if outcome.ok else f"Sorry. {outcome.spoken}",
              cfg.get("voice_feedback", True))
        if not outcome.ok:
            tray.notify("Remi (py)", outcome.spoken, error=True)
    except Exception as ex:
        history.append(APP, {"transcript": "", "detail": "error", "ok": False,
                             "error": str(ex), "ms": int((time.time() - started) * 1000)})
        speak("Sorry, that failed.", cfg.get("voice_feedback", True))
        tray.notify("Remi (py) failed", str(ex), error=True)


def toggle(tray: TrayApp, cfg):
    with _lock:
        if _state["busy"]:
            return
        if _state["capturing"] is None:
            try:
                from voicecore.capture import MicCapture
                cap = MicCapture()
                cap.start()
            except Exception as ex:
                tray.notify("Microphone", str(ex), error=True)
                return
            _state["capturing"] = cap
            tray.set_state("recording", cfg.get("hotkey", HOTKEY_DEFAULT))
            return
        cap = _state["capturing"]
        _state["capturing"] = None
        _state["busy"] = True
    pcm = cap.stop_and_read()
    _state["busy"] = False
    tray.set_state("idle", cfg.get("hotkey", HOTKEY_DEFAULT))
    threading.Thread(target=process, args=(pcm, cfg, tray), daemon=True).start()


def say_text(text: str) -> int:
    cfg = config.load(APP)
    outcome = router.run(text, cfg)
    history.append(APP, {"transcript": text, "detail": outcome.detail,
                         "ok": outcome.ok, "ms": 0})
    print(f"command : {outcome.ok}")
    print(f"result  : {outcome.spoken}")
    print(f"detail  : {outcome.detail}")
    return 0 if outcome.ok else 2


def say_audio(path: str) -> int:
    import wave
    import numpy as np
    cfg = config.load(APP)
    with wave.open(path, "rb") as w:
        rate, ch, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if width != 2:
        raise RuntimeError("only 16-bit WAV supported")
    samples = np.frombuffer(raw, dtype=np.int16)
    if ch > 1:
        samples = samples.reshape(-1, ch).mean(axis=1).astype(np.int16)
    if rate != 16000:
        from voicecore.capture import _resample_16k
        pcm = _resample_16k(samples.tobytes(), rate)
    else:
        pcm = samples.tobytes()
    text = asr.transcribe_pcm(pcm, cfg["local_model"], "hinglish")
    text = to_roman(text).strip()
    print(f"heard    : {text}")
    outcome = router.run(text, cfg)
    history.append(APP, {"transcript": text, "detail": outcome.detail,
                         "ok": outcome.ok, "ms": 0})
    print(f"command  : {outcome.ok}")
    print(f"result   : {outcome.spoken}")
    print(f"detail   : {outcome.detail}")
    return 0 if outcome.ok else 2


def build_tray(cfg) -> TrayApp:
    hotkey = cfg.get("hotkey") or HOTKEY_DEFAULT

    def toggle_action(icon, item):
        toggle(tray, cfg)

    def start_browser(icon, item):
        exe = browser.find_browser_exe()
        if not exe:
            tray.notify("Remi (py)", "No Edge/Chrome found", error=True)
            return
        profile = None if cfg.get("browser_profile", "remi") == "default" else str(config.LOCALAPPDATA / "browser-profile")
        ok = browser.launch(exe, cfg["cdp_port"], profile)
        tray.notify("Remi (py)", "Browser started with voice control." if ok else "Debug port did not respond.", not ok)

    def toggle_feedback(icon, item):
        cfg["voice_feedback"] = not cfg.get("voice_feedback", True)
        config.save(APP, cfg)

    menu = [
        pystray.MenuItem("Speak a command", toggle_action, default=True),
        pystray.MenuItem("Start browser (voice control)", start_browser),
        pystray.MenuItem(lambda item: f"Voice feedback  {'✓' if cfg.get('voice_feedback', True) else ''}",
                         toggle_feedback),
    ]
    tray = TrayApp(APP, hotkey, LETTER, IDLE_COLOR, menu)
    tray.on_toggle = lambda: toggle(tray, cfg)
    return tray


def main():
    ap = argparse.ArgumentParser(description="Remi (Python port) — voice-controlled browser")
    ap.add_argument("cmd", nargs="?", default="start",
                    choices=["start", "say", "say-audio", "history", "doctor"])
    ap.add_argument("payload", nargs="?", help="command text / wav path")
    args = ap.parse_args()

    cfg = config.load(APP)
    cfg.setdefault("hotkey", HOTKEY_DEFAULT)

    if args.cmd == "say":
        if not args.payload:
            print('usage: remi.py say "open youtube"')
            return 1
        return say_text(args.payload)
    if args.cmd == "say-audio":
        if not args.payload:
            print("usage: remi.py say-audio <file.wav>")
            return 1
        return say_audio(args.payload)
    if args.cmd == "history":
        for e in reversed(history.load(APP, 20)):
            what = e.get("detail", "") if e.get("ok") else f"ERROR: {e.get('error')}"
            print(f"{e.get('at', '')[:19]}  {e.get('transcript', '')[:30]:30}  {what[:60]}")
        return 0
    if args.cmd == "doctor":
        print(f"model    : {cfg['local_model']} -> {'found' if config.model_path(cfg['local_model']).exists() else 'MISSING'}")
        print(f"browser  : {browser.find_browser_exe() or 'NOT FOUND'}")
        print(f"cdp      : {'up' if browser.is_cdp_up(cfg['cdp_port']) else 'down'} on port {cfg['cdp_port']}")
        return 0

    print(f"Remi (Python) — hotkey: {cfg['hotkey']} — tray icon starting…")
    print("NOTE: stop the .NET remi daemon first if it is running (same hotkey).")
    tray = build_tray(cfg)
    tray.run()


if __name__ == "__main__":
    sys.exit(main())
