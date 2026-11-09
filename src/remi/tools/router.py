"""Natural language and Hinglish command grammar mapped to browser actions and local answers.

Direct port of Remi Suite CommandRouter with extensible structure.
"""
from __future__ import annotations

import datetime
import re
import time
import urllib.parse
from dataclasses import dataclass

from remi.core.constants import SITES
from remi.core.registry import ToolRegistry
from remi.tools import browser

CLICK_JS = (
    "(function(){var q=__Q__;var els=document.querySelectorAll('a,button,[role=button],"
    "input[type=submit]');for(var i=0;i<els.length;i++){var e=els[i];if(!e.offsetParent)continue;"
    "var txt=((e.innerText||e.value||'')+'').trim().toLowerCase();"
    "if(txt&&txt.includes(q)){e.click();return 'clicked: '+txt.slice(0,40);}}"
    "return 'not found: '+q;})()"
)

TYPE_JS = (
    "(function(){var ae=document.activeElement;if(!ae||(ae.tagName!=='INPUT'&&"
    "ae.tagName!=='TEXTAREA'&&!ae.isContentEditable))return 'no input focused';"
    "document.execCommand('insertText',false,__Q__);return 'typed';})()"
)

FIND_JS = (
    "(function(){if(!window.find(__Q__))return 'not found: '+__Q__;"
    "return 'found';})()"
)

ZOOM_JS = (
    "(function(){var b=document.body;var z=parseFloat(b.style.zoom)||1;"
    "if(__M__==='in')z=Math.min(3,z+0.1);else if(__M__==='out')z=Math.max(0.3,z-0.1);else z=1;"
    "b.style.zoom=z;return 'zoom '+(z*100).toFixed(0)+' percent';})()"
)

VOLUME_JS = (
    "(function(){var el=document.querySelector('video')||document.querySelector('audio');"
    "if(!el)return 'no media on this page';"
    "if(__D__===0){el.muted=!el.muted;return el.muted?'muted':'unmuted';}"
    "el.muted=false;el.volume=Math.min(1,Math.max(0,el.volume+__D__));"
    "return 'volume '+(el.volume*100).toFixed(0)+' percent';})()"
)


@dataclass
class Outcome:
    """Execution result of a voice command."""
    ok: bool
    spoken: str
    detail: str


def _is(t: str, *phrases: str) -> bool:
    return t in phrases


def _starts_with(t: str, *prefixes: str) -> str | None:
    for p in prefixes:
        p = p.strip()
        if not p:
            continue
        if t == p:
            return ""
        if t.startswith(p + " "):
            return t[len(p) + 1:].strip()
    return None


def _looks_like_domain(s: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)+(/.*)?", s)) and "." in s


def ensure_cdp(cfg: dict) -> bool:
    """Ensure CDP endpoint is active, launching browser if necessary."""
    port = cfg.get("cdp_port", 9222)
    if browser.is_cdp_up(port):
        return True
    if not cfg.get("auto_launch_browser", True):
        return False
    exe = browser.find_browser_exe()
    if not exe:
        return False
    from remi.core import config
    profile = None if cfg.get("browser_profile", "remi") == "default" else str(config.LOCALAPPDATA / "browser-profile")
    return browser.launch(exe, port, profile)


def _open(cfg: dict, url: str, spoken: str) -> Outcome:
    if not ensure_cdp(cfg):
        return Outcome(False, "browser not reachable", f"no CDP on port {cfg.get('cdp_port', 9222)}")
    browser.new_tab(cfg.get("cdp_port", 9222), url)
    return Outcome(True, spoken, url)


def _eval(cfg: dict, js: str, label: str) -> Outcome:
    if not ensure_cdp(cfg):
        return Outcome(False, "browser not reachable", f"no CDP on port {cfg.get('cdp_port', 9222)}")
    try:
        result = browser.eval_js(cfg.get("cdp_port", 9222), js)
    except Exception as ex:
        return Outcome(False, f"{label} failed", str(ex))
    if not result or result == "error":
        return Outcome(False, f"{label} failed", result or "no response")
    return Outcome(True, result, result)


def _step_tab(cfg: dict, delta: int) -> Outcome:
    port = cfg.get("cdp_port", 9222)
    if not ensure_cdp(cfg):
        return Outcome(False, "browser not reachable", f"no CDP on port {port}")
    pages = browser.tabs(port)
    if not pages:
        return Outcome(False, "no open tabs", "empty tab list")
    idx = (0 + delta + len(pages)) % len(pages)
    browser.activate_tab(port, pages[idx]["id"])
    return Outcome(True, f"tab: {pages[idx].get('title', 'tab')}", pages[idx].get("url", ""))


def _close_tab(cfg: dict) -> Outcome:
    port = cfg.get("cdp_port", 9222)
    if not ensure_cdp(cfg):
        return Outcome(False, "browser not reachable", f"no CDP on port {port}")
    pages = browser.tabs(port)
    if not pages:
        return Outcome(False, "no open tabs", "empty tab list")
    browser.close_tab(port, pages[0]["id"])
    return Outcome(True, "closed tab", pages[0].get("url", ""))


def run(text: str, cfg: dict) -> Outcome:
    """Parse text command (English / Hinglish) and execute browser or system action."""
    t = re.sub(r"\s+", " ", text.strip().lower())
    if not t:
        return Outcome(False, "nothing heard", "empty transcript")

    # Hinglish word order normalization: "youtube kholo" -> "youtube"
    stripped = re.sub(r"\s+(khol(?:o|a)?(?:\s+do|dena)?|open karo|khol de)$", "", t)
    if stripped != t:
        t = stripped

    # Tab navigation
    if _is(t, "next tab", "agla tab", "agle tab", "next tab kholo"):
        return _step_tab(cfg, +1)
    if _is(t, "previous tab", "pichla tab", "pichle tab", "last tab"):
        return _step_tab(cfg, -1)
    if _is(t, "new tab", "naya tab", "naya tab kholo", "new tab kholo"):
        return _open(cfg, "about:blank", "new tab")
    if _is(t, "close tab", "tab band karo", "tab band", "band karo", "close tab karo"):
        return _close_tab(cfg)
    if _is(t, "refresh", "refresh karo", "reload", "reload karo"):
        return _eval(cfg, "location.reload(); 'refreshing'", "refreshing page")
    if _is(t, "go back", "back", "wapas jao", "wapas", "peeche jao"):
        return _eval(cfg, "history.back(); 'going back'", "going back")
    if _is(t, "forward", "aage jao", "go forward"):
        return _eval(cfg, "history.forward(); 'going forward'", "going forward")

    # Scrolling
    if "scroll" in t or _is(t, "niche", "neeche", "upar", "sabse niche", "sabse upar"):
        if "top" in t or "sabse upar" in t:
            js, label = "window.scrollTo(0,0); 'top'", "scrolled to top"
        elif "bottom" in t or "sabse niche" in t:
            js, label = "window.scrollTo(0, document.body.scrollHeight); 'bottom'", "scrolled to bottom"
        elif "up" in t or "upar" in t:
            js, label = "window.scrollBy(0,-600); 'scrolled up'", "scrolled up"
        elif "left" in t or "bayen" in t or "baen" in t:
            js, label = "window.scrollBy(-400,0); 'scrolled left'", "scrolled left"
        elif "right" in t or "dayen" in t or "dain" in t:
            js, label = "window.scrollBy(400,0); 'scrolled right'", "scrolled right"
        else:
            js, label = "window.scrollBy(0,600); 'scrolled down'", "scrolled down"
        return _eval(cfg, js, label)

    # Media Play / Pause
    if _is(t, "play", "pause", "play karo", "pause karo", "chalao", "roko", "resume",
           "video chalao", "gaana chalao", "music chalao"):
        return _eval(
            cfg,
            "(function(){var el=document.querySelector('video')||document.querySelector('audio');"
            "if(!el)return 'no media on this page';if(el.paused){el.play();return 'playing';}"
            "el.pause();return 'paused';})()",
            "media toggle",
        )

    # Click element
    click = _starts_with(t, "click karo", "click", "dabao", "press")
    if click:
        q = click.lower().replace("\\", "\\\\").replace('"', '\\"')
        return _eval(cfg, CLICK_JS.replace("__Q__", f'"{q}"'), f"clicked '{click}'")

    # Type text
    typ = _starts_with(t, "type karo", "type", "likho", "write")
    if typ:
        q = typ.replace("\\", "\\\\").replace('"', '\\"')
        return _eval(cfg, TYPE_JS.replace("__Q__", f'"{q}"'), f"typed '{typ}'")

    # Read page title
    if _is(t, "read title", "title batao", "kya page hai", "what page", "which page"):
        return _eval(cfg, "document.title", "page title")

    # Media: Volume & Mute
    if _is(t, "mute", "mute karo", "unmute", "unmute karo", "awaaz band karo"):
        return _eval(cfg, VOLUME_JS.replace("__D__", "0"), "mute toggle")
    if _is(t, "volume up", "volume badhao", "awaaz badhao", "awaaz badao"):
        return _eval(cfg, VOLUME_JS.replace("__D__", "0.1"), "volume up")
    if _is(t, "volume down", "volume kam karo", "awaaz kam karo"):
        return _eval(cfg, VOLUME_JS.replace("__D__", "-0.1"), "volume down")

    # Zoom
    if _is(t, "zoom in", "zoom karo", "bada karo", "bada karo page"):
        return _eval(cfg, ZOOM_JS.replace("__M__", "'in'"), "zoom in")
    if _is(t, "zoom out", "chhota karo", "chota karo"):
        return _eval(cfg, ZOOM_JS.replace("__M__", "'out'"), "zoom out")
    if _is(t, "reset zoom", "normal zoom", "zoom reset"):
        return _eval(cfg, ZOOM_JS.replace("__M__", "'reset'"), "zoom reset")

    # Fullscreen
    if _is(t, "fullscreen", "full screen", "full screen karo", "poori screen"):
        return _eval(
            cfg,
            "(function(){if(document.fullscreenElement)return 'already fullscreen';"
            "document.documentElement.requestFullscreen();return 'fullscreen';})()",
            "fullscreen",
        )
    if _is(t, "exit fullscreen", "full screen band karo", "screen band karo"):
        return _eval(
            cfg,
            "(function(){if(!document.fullscreenElement)return 'not fullscreen';"
            "document.exitFullscreen();return 'exited fullscreen';})()",
            "exit fullscreen",
        )

    # Find on page / Print / Select All / Copy
    find = _starts_with(t, "find", "find karo", "page me dhundo", "page pe dhundo")
    if find:
        q = find.replace("\\", "\\\\").replace('"', '\\"')
        return _eval(cfg, FIND_JS.replace("__Q__", f'"{q}"'), f"find '{find}'")
    if _is(t, "print", "print karo", "print page"):
        return _eval(cfg, "window.print(); 'opening print dialog'", "print dialog")
    if _is(t, "select all", "sab select karo"):
        return _eval(cfg, "document.execCommand('selectAll')?'selected all':'select failed'", "select all")
    if _is(t, "copy", "copy karo", "copy this"):
        return _eval(cfg, "document.execCommand('copy')?'copied':'nothing selected to copy'", "copy selection")

    # Local instant answers (offline)
    if _is(t, "what time", "what time is it", "what time is it now", "time batao", "time kya hua", "kitne baje hain", "samay kya hai"):
        now = time.strftime("%I:%M %p").lstrip("0")
        return Outcome(True, f"it's {now}", now)
    if _is(t, "what date", "what date is it", "what date is today", "date batao", "aaj ki tarikh", "aaj kya tarikh hai"):
        today = datetime.date.today().strftime("%B %d, %Y")
        return Outcome(True, f"today is {today}", today)

    # Duplicate tab
    if _is(t, "duplicate tab", "tab copy karo"):
        port = cfg.get("cdp_port", 9222)
        if not ensure_cdp(cfg):
            return Outcome(False, "browser not reachable", f"no CDP on port {port}")
        pages = browser.tabs(port)
        if not pages:
            return Outcome(False, "no open tabs", "empty tab list")
        return _open(cfg, pages[0]["url"], "duplicated tab")

    # Site launch or search fallback
    open_payload = _starts_with(t, "open", "kholo", "khol", "launch", "jao", "go to", "goto")
    if open_payload:
        site = open_payload.strip().rstrip(".!?")
        if site.lower() in SITES:
            return _open(cfg, SITES[site.lower()], f"opening {site}")
        if _looks_like_domain(site):
            return _open(cfg, "https://" + site, f"opening {site}")
        return _open(cfg, "https://www.google.com/search?q=" + urllib.parse.quote(open_payload), f"search: {open_payload}")

    # YouTube search
    yt = _starts_with(t, "youtube")
    if yt:
        return _open(cfg, "https://www.youtube.com/results?search_query=" + urllib.parse.quote(yt), f"youtube: {yt}")

    # Web search
    search = _starts_with(t, "search karo", "search", "google", "dhundo", "dhoondo")
    if search:
        return _open(cfg, "https://www.google.com/search?q=" + urllib.parse.quote(search), f"search: {search}")

    if t in SITES:
        return _open(cfg, SITES[t], f"opening {t}")
    if _looks_like_domain(t):
        return _open(cfg, "https://" + t, f"opening {t}")

    # Check registered modular skills (OpenJarvis pattern)
    try:
        from remi.skills import SkillManager
        mgr = SkillManager()
        handled, spoken, detail = mgr.match_and_execute(t, cfg)
        if handled:
            return Outcome(True, spoken, detail)
    except Exception:
        pass

    # Local SLM/LLM Intent Resolution Fallback (OpenJarvis pattern)
    if cfg.get("llm_enabled", True):
        try:
            from remi.engine.llm import IntentResolver
            resolver = IntentResolver(cfg=cfg)
            if resolver.is_ready():
                res = resolver.resolve(text)
                if res and isinstance(res, dict):
                    action = res.get("action", "speak")
                    spoken = res.get("spoken", "done")
                    detail = res.get("detail", action)
                    if action == "open_url" and res.get("url"):
                        return _open(cfg, res["url"], spoken)
                    elif action == "search" and res.get("search_query"):
                        q = res["search_query"]
                        return _open(cfg, f"https://www.google.com/search?q={urllib.parse.quote(q)}", spoken)
                    elif action == "speak":
                        return Outcome(True, spoken, detail)
        except Exception:
            pass

    return Outcome(False, f"didn't understand: {t}", "unrecognized command")


@ToolRegistry.register("router")
class CommandRouter:
    """Pluggable command router registered in ToolRegistry."""

    def __init__(self, cfg: dict | None = None):
        self.cfg = cfg or {}

    def execute(self, text: str, cfg: dict | None = None) -> Outcome:
        c = cfg or self.cfg
        return run(text, c)
