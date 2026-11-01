"""Spoken confirmations via SAPI (pyttsx3) with a cached engine — re-initing
pyttsx3 per phrase costs a noticeable pause, so the engine is created once."""
_lock = __import__("threading").Lock()
_engine = None


def say(text: str, enabled: bool):
    global _engine
    if not enabled or not text:
        return
    with _lock:
        try:
            if _engine is None:
                import pyttsx3
                _engine = pyttsx3.init()
            _engine.say(text)
            _engine.runAndWait()
        except Exception:
            _engine = None  # re-init next time; TTS is best-effort
