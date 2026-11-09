"""Configuration management and platform path resolution for Remi Suite.

Supports typed dataclasses, TOML persistence, and cross-platform fallbacks.
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from remi.core.constants import (
    APP_BROWSER_ID,
    DEFAULT_ASR_PORT,
    DEFAULT_CDP_PORT,
    DEFAULT_HOTKEY_BROWSER,
    DEFAULT_MODEL,
)

# ----------------- Platform Paths -----------------

def get_appdata_dir() -> Path:
    """Return platform config directory (Windows APPDATA or ~/.config/remi)."""
    if "APPDATA" in os.environ:
        return Path(os.environ["APPDATA"]) / "remi-suite-py"
    return Path.home() / ".config" / "remi"


def get_localappdata_dir() -> Path:
    """Return platform local data directory (Windows LOCALAPPDATA or ~/.local/share/remi)."""
    if "LOCALAPPDATA" in os.environ:
        return Path(os.environ["LOCALAPPDATA"]) / "remi-suite-py"
    return Path.home() / ".local" / "share" / "remi"


def get_vt_models_dir() -> Path:
    """Return legacy .NET voice-trans models directory for sharing weights."""
    if "LOCALAPPDATA" in os.environ:
        return Path(os.environ["LOCALAPPDATA"]) / "voice-trans" / "models"
    return Path.home() / ".local" / "share" / "voice-trans" / "models"


APPDATA: Path = get_appdata_dir()
LOCALAPPDATA: Path = get_localappdata_dir()
VT_MODELS: Path = get_vt_models_dir()
BIN_DIR: Path = LOCALAPPDATA / "bin"


def ensure_dirs() -> None:
    """Ensure runtime directories exist."""
    try:
        APPDATA.mkdir(parents=True, exist_ok=True)
        LOCALAPPDATA.mkdir(parents=True, exist_ok=True)
        BIN_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


# ----------------- Dataclass Configs -----------------

@dataclass
class EngineConfig:
    """ASR Inference engine settings."""
    type: str = "whisper_cpp"
    local_model: str = DEFAULT_MODEL
    asr_port: int = DEFAULT_ASR_PORT
    language: str = "hinglish"
    device: str = "auto"  # auto, cuda, cpu


@dataclass
class BrowserConfig:
    """Browser voice controller settings."""
    hotkey: str = DEFAULT_HOTKEY_BROWSER
    cdp_port: int = DEFAULT_CDP_PORT
    auto_launch_browser: bool = True
    browser_profile: str = "remi"
    voice_feedback: bool = True


@dataclass
class DictationConfig:
    """Voice Trans dictation settings."""
    hotkey: str = "ctrl+alt+space"
    delivery_mode: str = "type"  # type, clipboard, guarded
    writing_mode: str = "smart"  # smart, verbatim
    language: str = "hinglish"
    max_recording_seconds: int = 120


@dataclass
class RemiConfig:
    """Unified application configuration."""
    app: str = APP_BROWSER_ID
    engine: EngineConfig = field(default_factory=EngineConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    dictation: DictationConfig = field(default_factory=DictationConfig)


# ----------------- Flat Compatibility Layer -----------------

DEFAULTS: dict[str, Any] = {
    "hotkey": "",
    "local_model": DEFAULT_MODEL,
    "delivery_mode": "type",
    "writing_mode": "smart",
    "language": "hinglish",
    "cdp_port": DEFAULT_CDP_PORT,
    "asr_port": DEFAULT_ASR_PORT,
    "voice_feedback": True,
    "auto_launch_browser": True,
    "browser_profile": "remi",
    "max_recording_seconds": 120,
}


def config_path(app: str) -> Path:
    return APPDATA / f"{app}.toml"


def load(app: str = APP_BROWSER_ID) -> dict[str, Any]:
    """Load flat dictionary config matching legacy voicecore.config."""
    ensure_dirs()
    cfg = dict(DEFAULTS)
    p = config_path(app)
    if p.exists():
        try:
            data = tomllib.loads(p.read_text(encoding="utf-8"))
            for k, v in data.items():
                cfg[k] = v
        except Exception:
            pass  # fail safe to defaults
    cfg["app"] = app
    return cfg


def save(app: str, cfg: dict[str, Any]) -> None:
    """Save dictionary config atomically as TOML."""
    ensure_dirs()
    lines = [f"# remi-suite-py {app} configuration", ""]
    for k, v in cfg.items():
        if k in ("app",):
            continue
        if isinstance(v, bool):
            lines.append(f"{k} = {str(v).lower()}")
        elif isinstance(v, (int, float)):
            lines.append(f"{k} = {v}")
        elif isinstance(v, str):
            lines.append(f'{k} = "{v}"')
    tmp = config_path(app).with_suffix(".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp, config_path(app))


def model_path(name: str) -> Path:
    """Look up ggml model in local models dir, then borrow from .NET suite."""
    own = LOCALAPPDATA / "models" / f"ggml-{name}.bin"
    if own.exists():
        return own
    borrowed = VT_MODELS / f"ggml-{name}.bin"
    if borrowed.exists():
        return borrowed
    return own


def history_path(app: str) -> Path:
    """Return JSONL history path for the specified app."""
    return LOCALAPPDATA / f"{app}-history.jsonl"
