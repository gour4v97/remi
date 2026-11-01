"""Config + paths. Hand-parsed flat TOML (read via tomllib, written flat)."""
import os
import tomllib
from pathlib import Path

APPDATA = Path(os.environ["APPDATA"]) / "remi-suite-py"
LOCALAPPDATA = Path(os.environ["LOCALAPPDATA"]) / "remi-suite-py"
VT_MODELS = Path(os.environ["LOCALAPPDATA"]) / "voice-trans" / "models"  # borrow from the .NET suite
BIN_DIR = LOCALAPPDATA / "bin"


def ensure_dirs():
    APPDATA.mkdir(parents=True, exist_ok=True)
    LOCALAPPDATA.mkdir(parents=True, exist_ok=True)
    BIN_DIR.mkdir(parents=True, exist_ok=True)


DEFAULTS = {
    "hotkey": "",  # each app sets its own default
    "local_model": "large-v3-turbo-q5_0",
    "delivery_mode": "type",       # voice-trans only
    "writing_mode": "smart",
    "language": "hinglish",
    "cdp_port": 9222,
    "voice_feedback": True,
    "auto_launch_browser": True,
    "max_recording_seconds": 120,
}


def config_path(app: str) -> Path:
    return APPDATA / f"{app}.toml"


def load(app: str) -> dict:
    ensure_dirs()
    cfg = dict(DEFAULTS)
    p = config_path(app)
    if p.exists():
        try:
            data = tomllib.loads(p.read_text(encoding="utf-8"))
            for k in cfg:
                if k in data:
                    cfg[k] = data[k]
        except Exception:
            pass  # fail closed to defaults
    cfg["app"] = app
    return cfg


def save(app: str, cfg: dict):
    ensure_dirs()
    lines = [f"# remi-suite-py {app} config", ""]
    for k in DEFAULTS:
        if k in cfg:
            v = cfg[k]
            lines.append(f'{k} = "{v}"' if isinstance(v, str) else f"{k} = {str(v).lower() if isinstance(v, bool) else v}")
    tmp = config_path(app).with_suffix(".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp, config_path(app))


def model_path(name: str) -> Path:
    """Remi-suite models dir first, then borrow the .NET suite's models (same ggml format)."""
    own = LOCALAPPDATA / "models" / f"ggml-{name}.bin"
    if own.exists():
        return own
    borrowed = VT_MODELS / f"ggml-{name}.bin"
    if borrowed.exists():
        return borrowed
    return own


def history_path(app: str) -> Path:
    return LOCALAPPDATA / f"{app}-history.jsonl"
