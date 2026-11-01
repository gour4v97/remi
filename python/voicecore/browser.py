"""Chrome DevTools Protocol client (Edge/Chrome): HTTP for tabs, WebSocket for JS eval."""
import json
import time
import urllib.request
import urllib.error

import websocket


def is_cdp_up(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def find_browser_exe() -> str | None:
    from . import config
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        str(config.LOCALAPPDATA / r"Google\Chrome\Application\chrome.exe"),
    ]
    import os
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def launch(exe: str, port: int, profile_dir: str | None, wait_s: int = 8) -> bool:
    import subprocess
    args = [exe, f"--remote-debugging-port={port}"]
    if profile_dir:
        from . import config
        profile_dir = str(profile_dir)
        os_makedirs(profile_dir)
        args += [f"--user-data-dir={profile_dir}", "--no-first-run", "--no-default-browser-check"]
    else:
        args.append("--restore-last-session")
    subprocess.Popen(args)
    deadline = time.time() + wait_s
    while time.time() < deadline:
        if is_cdp_up(port):
            return True
        time.sleep(0.3)
    return False


def os_makedirs(p: str):
    import os
    os.makedirs(p, exist_ok=True)


def tabs(port: int) -> list[dict]:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=3) as r:
        data = json.loads(r.read().decode("utf-8"))
    return [t for t in data
            if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]


def new_tab(port: int, url: str):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/json/new?{urllib.parse.quote(url, safe='')}", method="PUT")
    with urllib.request.urlopen(req, timeout=5) as r:
        r.read()


def activate_tab(port: int, tab_id: str):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/activate/{tab_id}", timeout=3) as r:
        r.read()


def close_tab(port: int, tab_id: str):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/close/{tab_id}", timeout=3) as r:
        r.read()


def eval_js(port: int, js: str) -> str | None:
    pages = tabs(port)
    if not pages:
        return None
    ws_url = pages[0]["webSocketDebuggerUrl"]
    ws = websocket.create_connection(ws_url, timeout=6)
    try:
        ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate",
                            "params": {"expression": js, "returnByValue": True, "awaitPromise": True}}))
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
