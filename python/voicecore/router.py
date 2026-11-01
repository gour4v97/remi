"""Command grammar (English + Hinglish) → browser actions. Port of the C# CommandRouter."""
import re
import urllib.parse
import urllib.request

from . import browser

SITES = {
    "youtube": "https://www.youtube.com", "google": "https://www.google.com",
    "gmail": "https://mail.google.com", "mail": "https://mail.google.com",
    "whatsapp": "https://web.whatsapp.com", "chatgpt": "https://chatgpt.com",
    "github": "https://github.com", "instagram": "https://www.instagram.com",
    "insta": "https://www.instagram.com", "facebook": "https://www.facebook.com",
    "reddit": "https://www.reddit.com", "wikipedia": "https://www.wikipedia.org",
    "amazon": "https://www.amazon.in", "flipkart": "https://www.flipkart.com",
    "twitter": "https://x.com", "x": "https://x.com",
    "linkedin": "https://www.linkedin.com", "netflix": "https://www.netflix.com",
    "hotstar": "https://www.hotstar.com", "maps": "https://www.google.com/maps",
    "drive": "https://drive.google.com", "spotify": "https://open.spotify.com",
}

CLICK_JS = ("(function(){var q=__Q__;var els=document.querySelectorAll('a,button,[role=button],"
            "input[type=submit]');for(var i=0;i<els.length;i++){var e=els[i];if(!e.offsetParent)continue;"
            "var txt=((e.innerText||e.value||'')+'').trim().toLowerCase();"
            "if(txt&&txt.includes(q)){e.click();return 'clicked: '+txt.slice(0,40);}}"
            "return 'not found: '+q;})()")

TYPE_JS = ("(function(){var ae=document.activeElement;if(!ae||(ae.tagName!=='INPUT'&&"
           "ae.tagName!=='TEXTAREA'&&!ae.isContentEditable))return 'no input focused';"
           "document.execCommand('insertText',false,__Q__);return 'typed';})()")


class Outcome:
    def __init__(self, ok: bool, spoken: str, detail: str):
        self.ok, self.spoken, self.detail = ok, spoken, detail


def _is(t, *phrases):
    return t in phrases


def _starts_with(t, *prefixes):
    for p in prefixes:
        p = p.strip()
        if not p:
            continue
        if t == p:
            return ""
        if t.startswith(p + " "):
            return t[len(p) + 1:].strip()
    return None


def _looks_like_domain(s):
    return bool(re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)+(/.*)?", s)) and "." in s


def ensure_cdp(cfg) -> bool:
    if browser.is_cdp_up(cfg["cdp_port"]):
        return True
    if not cfg.get("auto_launch_browser", True):
        return False
    exe = browser.find_browser_exe()
    if not exe:
        return False
    from . import config
    profile = None if cfg.get("browser_profile", "remi") == "default" else str(config.LOCALAPPDATA / "browser-profile")
    return browser.launch(exe, cfg["cdp_port"], profile)


def _open(cfg, url, spoken) -> Outcome:
    if not ensure_cdp(cfg):
        return Outcome(False, "browser not reachable", f"no CDP on port {cfg['cdp_port']}")
    browser.new_tab(cfg["cdp_port"], url)
    return Outcome(True, spoken, url)


def _eval(cfg, js, label) -> Outcome:
    if not ensure_cdp(cfg):
        return Outcome(False, "browser not reachable", f"no CDP on port {cfg['cdp_port']}")
    try:
        result = browser.eval_js(cfg["cdp_port"], js)
    except Exception as ex:
        return Outcome(False, f"{label} failed", str(ex))
    if not result or result == "error":
        return Outcome(False, f"{label} failed", result or "no response")
    return Outcome(True, result, result)


def run(text: str, cfg) -> Outcome:
    t = re.sub(r"\s+", " ", text.strip().lower())
    if not t:
        return Outcome(False, "nothing heard", "empty transcript")

    # Hinglish word order: "youtube kholo" → "youtube"
    stripped = re.sub(r"\s+(khol(?:o|a)?(?:\s+do|dena)?|open karo|khol de)$", "", t)
    if stripped != t:
        t = stripped

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

    if "scroll" in t or _is(t, "niche", "neeche", "upar", "sabse niche", "sabse upar"):
        if "top" in t or "sabse upar" in t:
            js, label = "window.scrollTo(0,0); 'top'", "scrolled to top"
        elif "bottom" in t or "sabse niche" in t:
            js, label = "window.scrollTo(0, document.body.scrollHeight); 'bottom'", "scrolled to bottom"
        elif "up" in t or "upar" in t:
            js, label = "window.scrollBy(0,-600); 'scrolled up'", "scrolled up"
        else:
            js, label = "window.scrollBy(0,600); 'scrolled down'", "scrolled down"
        return _eval(cfg, js, label)

    if _is(t, "play", "pause", "play karo", "pause karo", "chalao", "roko", "resume",
           "video chalao", "gaana chalao", "music chalao"):
        return _eval(cfg, "(function(){var el=document.querySelector('video')||document.querySelector('audio');"
                          "if(!el)return 'no media on this page';if(el.paused){el.play();return 'playing';}"
                          "el.pause();return 'paused';})()", "media toggle")

    click = _starts_with(t, "click karo", "click", "dabao", "press")
    if click:
        q = click.lower().replace("\\", "\\\\").replace('"', '\\"')
        return _eval(cfg, CLICK_JS.replace("__Q__", f'"{q}"'), f"clicked '{click}'")

    typ = _starts_with(t, "type karo", "type", "likho", "write")
    if typ:
        q = typ.replace("\\", "\\\\").replace('"', '\\"')
        return _eval(cfg, TYPE_JS.replace("__Q__", f'"{q}"'), f"typed '{typ}'")

    if _is(t, "read title", "title batao", "kya page hai", "what page", "which page"):
        return _eval(cfg, "document.title", "page title")

    # "X kholo" / "open X" before youtube-search so "youtube kholo" opens the site
    open_payload = _starts_with(t, "open", "kholo", "khol", "launch", "jao")
    if open_payload:
        site = open_payload.strip().rstrip(".!?")
        if site.lower() in SITES:
            return _open(cfg, SITES[site.lower()], f"opening {site}")
        if _looks_like_domain(site):
            return _open(cfg, "https://" + site, f"opening {site}")
        return _open(cfg, "https://www.google.com/search?q=" + urllib.parse.quote(open_payload),
                     f"search: {open_payload}")

    yt = _starts_with(t, "youtube")
    if yt:
        return _open(cfg, "https://www.youtube.com/results?search_query=" + urllib.parse.quote(yt),
                     f"youtube: {yt}")

    search = _starts_with(t, "search karo", "search", "google", "dhundo", "dhoondo")
    if search:
        return _open(cfg, "https://www.google.com/search?q=" + urllib.parse.quote(search),
                     f"search: {search}")

    if t in SITES:
        return _open(cfg, SITES[t], f"opening {t}")
    if _looks_like_domain(t):
        return _open(cfg, "https://" + t, f"opening {t}")

    return Outcome(False, f"didn't understand: {t}", "unrecognized command")


def _step_tab(cfg, delta) -> Outcome:
    if not ensure_cdp(cfg):
        return Outcome(False, "browser not reachable", f"no CDP on port {cfg['cdp_port']}")
    pages = browser.tabs(cfg["cdp_port"])
    if not pages:
        return Outcome(False, "no open tabs", "empty tab list")
    idx = (0 + delta + len(pages)) % len(pages)
    browser.activate_tab(cfg["cdp_port"], pages[idx]["id"])
    return Outcome(True, f"tab: {pages[idx]['title']}", pages[idx]["url"])


def _close_tab(cfg) -> Outcome:
    if not ensure_cdp(cfg):
        return Outcome(False, "browser not reachable", f"no CDP on port {cfg['cdp_port']}")
    pages = browser.tabs(cfg["cdp_port"])
    if not pages:
        return Outcome(False, "no open tabs", "empty tab list")
    browser.close_tab(cfg["cdp_port"], pages[0]["id"])
    return Outcome(True, "closed tab", pages[0]["url"])
