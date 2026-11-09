"""Chrome DevTools Protocol (CDP) client for browser automation over HTTP & WebSockets."""
from __future__ import annotations

import json
import logging
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import websocket
except ImportError:
    websocket = None

from remi.core import config
from remi.core.registry import ToolRegistry

logger = logging.getLogger(__name__)


def is_cdp_up(port: int) -> bool:
    """Check if Chrome DevTools Protocol endpoint is responding on the given port."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def find_browser_exe() -> str | None:
    """Locate Microsoft Edge or Google Chrome executable on the host system."""
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        str(config.LOCALAPPDATA / r"Google\Chrome\Application\chrome.exe"),
        # Linux / WSL fallback
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/usr/bin/microsoft-edge",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def launch(exe: str, port: int, profile_dir: str | None = None, wait_s: int = 8) -> bool:
    """Launch browser with remote debugging enabled."""
    args = [exe, f"--remote-debugging-port={port}"]
    if profile_dir:
        os.makedirs(profile_dir, exist_ok=True)
        args += [f"--user-data-dir={profile_dir}", "--no-first-run", "--no-default-browser-check"]
    else:
        args.append("--restore-last-session")

    try:
        subprocess.Popen(args)
    except Exception as ex:
        logger.error(f"Failed to spawn browser process: {ex}")
        return False

    deadline = time.time() + wait_s
    while time.time() < deadline:
        if is_cdp_up(port):
            return True
        time.sleep(0.3)
    return False


def tabs(port: int) -> list[dict]:
    """Retrieve list of currently open page targets."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=3) as r:
            data = json.loads(r.read().decode("utf-8"))
        return [t for t in data if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
    except Exception as ex:
        logger.debug(f"tabs query failed: {ex}")
        return []


def new_tab(port: int, url: str) -> None:
    """Open a new tab with the target URL via CDP."""
    encoded_url = urllib.parse.quote(url, safe="")
    req = urllib.request.Request(f"http://127.0.0.1:{port}/json/new?{encoded_url}", method="PUT")
    with urllib.request.urlopen(req, timeout=5) as r:
        r.read()


def activate_tab(port: int, tab_id: str) -> None:
    """Bring tab into foreground."""
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/activate/{tab_id}", timeout=3) as r:
        r.read()


def close_tab(port: int, tab_id: str) -> None:
    """Close tab by id."""
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/close/{tab_id}", timeout=3) as r:
        r.read()


def eval_js(port: int, js: str) -> str | None:
    """Evaluate arbitrary JavaScript inside the active page tab via WebSocket."""
    if websocket is None:
        raise RuntimeError("websocket-client is required for eval_js.")
    pages = tabs(port)
    if not pages:
        return None
    ws_url = pages[0]["webSocketDebuggerUrl"]
    ws = websocket.create_connection(ws_url, timeout=6)
    try:
        ws.send(
            json.dumps(
                {
                    "id": 1,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": js,
                        "returnByValue": True,
                        "awaitPromise": True,
                        "userGesture": True,
                    },
                }
            )
        )
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == 1:
                result = msg.get("result", {}).get("result", {})
                if "value" in result:
                    v = result["value"]
                    return v if isinstance(v, str) else str(v)
                if "description" in result:
                    return result["description"]
                return "ok"
    finally:
        ws.close()


@ToolRegistry.register("browser")
class BrowserClient:
    """High-level client wrapper around CDP protocol."""

    def __init__(self, port: int = 9222):
        self.port = port

    def is_up(self) -> bool:
        return is_cdp_up(self.port)

    def open_url(self, url: str) -> None:
        new_tab(self.port, url)

    def execute(self, js: str) -> str | None:
        return eval_js(self.port, js)
