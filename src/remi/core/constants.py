"""Core constants, catalogs, and default configurations for Remi Suite."""
from typing import Final

# Application identifiers
APP_NAME: Final[str] = "remi"
APP_DISPLAY_NAME: Final[str] = "Remi Voice Assistant"
APP_VERSION: Final[str] = "0.2.0"
APP_PUBLISHER: Final[str] = "GAURAV"
APP_AUTHOR: Final[str] = "GAURAV"
APP_COPYRIGHT: Final[str] = "Copyright (c) 2026 GAURAV. All rights reserved."

APP_BROWSER_ID: Final[str] = "remi-py"
APP_DICTATION_ID: Final[str] = "voice-trans-py"

# Default hotkeys
DEFAULT_HOTKEY_BROWSER: Final[str] = "ctrl+alt+b"
DEFAULT_HOTKEY_DICTATION: Final[str] = "ctrl+alt+space"

# Model catalog: name -> approximate size in MB
MODEL_CATALOG: Final[dict[str, int]] = {
    "tiny": 75,
    "base": 142,
    "small": 487,
    "medium": 1527,
    "large-v3-turbo": 1620,
    "large-v3-turbo-q5_0": 574,
}

DEFAULT_MODEL: Final[str] = "large-v3-turbo-q5_0"
DEFAULT_ASR_PORT: Final[int] = 9177
DEFAULT_CDP_PORT: Final[int] = 9222
DEFAULT_SAMPLE_RATE: Final[int] = 16000

# UI Theme / Tray colors (RGB tuples)
COLORS: Final[dict[str, tuple[int, int, int]]] = {
    "idle": (74, 144, 217),        # Calm blue
    "recording": (229, 72, 77),    # Active red
    "thinking": (245, 166, 35),    # Processing orange
    "violet": (124, 92, 217),      # Browser violet
    "success": (46, 204, 113),     # Green
}

# Supported navigation sites
SITES: Final[dict[str, str]] = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "mail": "https://mail.google.com",
    "whatsapp": "https://web.whatsapp.com",
    "chatgpt": "https://chatgpt.com",
    "github": "https://github.com",
    "instagram": "https://www.instagram.com",
    "insta": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "reddit": "https://www.reddit.com",
    "wikipedia": "https://www.wikipedia.org",
    "amazon": "https://www.amazon.in",
    "flipkart": "https://www.flipkart.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "linkedin": "https://www.linkedin.com",
    "netflix": "https://www.netflix.com",
    "hotstar": "https://www.hotstar.com",
    "maps": "https://www.google.com/maps",
    "drive": "https://drive.google.com",
    "spotify": "https://open.spotify.com",
    # Browser-internal pages
    "history": "chrome://history",
    "downloads": "chrome://downloads",
    "bookmarks": "chrome://bookmarks",
    "settings": "chrome://settings",
    "extensions": "chrome://extensions",
}
