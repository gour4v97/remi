package suite;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.Set;

/** Command grammar (English + Hinglish) → browser actions. Port of the C#/Python router. */
public final class Router {
    private Router() {}

    public record Outcome(boolean ok, String spoken, String detail) {}

    static final Set<String> NEXT_TAB = Set.of("next tab", "agla tab", "agle tab", "next tab kholo");
    static final Set<String> PREV_TAB = Set.of("previous tab", "pichla tab", "pichle tab", "last tab");
    static final Set<String> NEW_TAB = Set.of("new tab", "naya tab", "naya tab kholo", "new tab kholo");
    static final Set<String> CLOSE_TAB = Set.of("close tab", "tab band karo", "tab band", "band karo", "close tab karo");

    static final Map<String, String> SITES = Map.ofEntries(
            Map.entry("youtube", "https://www.youtube.com"), Map.entry("google", "https://www.google.com"),
            Map.entry("gmail", "https://mail.google.com"), Map.entry("mail", "https://mail.google.com"),
            Map.entry("whatsapp", "https://web.whatsapp.com"), Map.entry("chatgpt", "https://chatgpt.com"),
            Map.entry("github", "https://github.com"), Map.entry("instagram", "https://www.instagram.com"),
            Map.entry("insta", "https://www.instagram.com"), Map.entry("facebook", "https://www.facebook.com"),
            Map.entry("reddit", "https://www.reddit.com"), Map.entry("wikipedia", "https://www.wikipedia.org"),
            Map.entry("amazon", "https://www.amazon.in"), Map.entry("flipkart", "https://www.flipkart.com"),
            Map.entry("twitter", "https://x.com"), Map.entry("x", "https://x.com"),
            Map.entry("linkedin", "https://www.linkedin.com"), Map.entry("netflix", "https://www.netflix.com"),
            Map.entry("hotstar", "https://www.hotstar.com"), Map.entry("maps", "https://www.google.com/maps"),
            Map.entry("drive", "https://drive.google.com"), Map.entry("spotify", "https://open.spotify.com"));

    static final String CLICK_JS = "(function(){var q=__Q__;var els=document.querySelectorAll('a,button,[role=button],"
            + "input[type=submit]');for(var i=0;i<els.length;i++){var e=els[i];if(!e.offsetParent)continue;"
            + "var txt=((e.innerText||e.value||'')+'').trim().toLowerCase();"
            + "if(txt&&txt.includes(q)){e.click();return 'clicked: '+txt.slice(0,40);}}"
            + "return 'not found: '+q;})()";

    static final String TYPE_JS = "(function(){var ae=document.activeElement;if(!ae||(ae.tagName!=='INPUT'&&"
            + "ae.tagName!=='TEXTAREA'&&!ae.isContentEditable))return 'no input focused';"
            + "document.execCommand('insertText',false,__Q__);return 'typed';})()";

    public static Outcome run(String text, Config cfg) {
        String t = text.trim().toLowerCase().replaceAll("\\s+", " ");
        if (t.isEmpty()) return new Outcome(false, "nothing heard", "empty transcript");

        // Hinglish word order: "youtube kholo" → "youtube"
        String stripped = t.replaceAll("\\s+(khol(?:o|a)?(?:\\s+do|dena)?|open karo|khol de)$", "");
        if (!stripped.equals(t)) t = stripped;
        String fin = t;

        if (NEXT_TAB.contains(fin)) return stepTab(cfg, 1);
        if (PREV_TAB.contains(fin)) return stepTab(cfg, -1);
        if (NEW_TAB.contains(fin)) return open(cfg, "about:blank", "new tab");
        if (CLOSE_TAB.contains(fin)) return closeTab(cfg);
        if (fin.equals("refresh") || fin.equals("refresh karo") || fin.equals("reload") || fin.equals("reload karo"))
            return evalAction(cfg, "location.reload(); 'refreshing'", "refreshing page");
        if (fin.equals("go back") || fin.equals("back") || fin.equals("wapas jao") || fin.equals("wapas") || fin.equals("peeche jao"))
            return evalAction(cfg, "history.back(); 'going back'", "going back");
        if (fin.equals("forward") || fin.equals("aage jao") || fin.equals("go forward"))
            return evalAction(cfg, "history.forward(); 'going forward'", "going forward");

        if (fin.contains("scroll") || Set.of("niche", "neeche", "upar", "sabse niche", "sabse upar").contains(fin)) {
            String js, label;
            if (fin.contains("top") || fin.contains("sabse upar")) {
                js = "window.scrollTo(0,0); 'top'";
                label = "scrolled to top";
            } else if (fin.contains("bottom") || fin.contains("sabse niche")) {
                js = "window.scrollTo(0, document.body.scrollHeight); 'bottom'";
                label = "scrolled to bottom";
            } else if (fin.contains("up") || fin.contains("upar")) {
                js = "window.scrollBy(0,-600); 'scrolled up'";
                label = "scrolled up";
            } else {
                js = "window.scrollBy(0,600); 'scrolled down'";
                label = "scrolled down";
            }
            return evalAction(cfg, js, label);
        }

        if (Set.of("play", "pause", "play karo", "pause karo", "chalao", "roko", "resume",
                "video chalao", "gaana chalao", "music chalao").contains(fin)) {
            return evalAction(cfg, "(function(){var el=document.querySelector('video')||document.querySelector('audio');"
                    + "if(!el)return 'no media on this page';if(el.paused){el.play();return 'playing';}"
                    + "el.pause();return 'paused';})()", "media toggle");
        }

        String click = startsWith(fin, "click karo", "click", "dabao", "press");
        if (click != null && !click.isEmpty()) {
            String q = click.toLowerCase().replace("\\", "\\\\").replace("\"", "\\\"");
            return evalAction(cfg, CLICK_JS.replace("__Q__", "\"" + q + "\""), "clicked '" + click + "'");
        }
        String typ = startsWith(fin, "type karo", "type", "likho", "write");
        if (typ != null && !typ.isEmpty()) {
            String q = typ.replace("\\", "\\\\").replace("\"", "\\\"");
            return evalAction(cfg, TYPE_JS.replace("__Q__", "\"" + q + "\""), "typed '" + typ + "'");
        }

        if (Set.of("read title", "title batao", "kya page hai", "what page", "which page").contains(fin))
            return evalAction(cfg, "document.title", "page title");

        // "X kholo" / "open X" before youtube-search so "youtube kholo" opens the site
        String openPayload = startsWith(fin, "open", "kholo", "khol", "launch", "jao");
        if (openPayload != null && !openPayload.isEmpty()) {
            String site = openPayload.strip().replaceAll("[.!?,]+$", "").toLowerCase();
            if (SITES.containsKey(site)) return open(cfg, SITES.get(site), "opening " + site);
            if (looksLikeDomain(site)) return open(cfg, "https://" + site, "opening " + site);
            return open(cfg, "https://www.google.com/search?q=" + enc(openPayload), "search: " + openPayload);
        }

        String yt = startsWith(fin, "youtube");
        if (yt != null && !yt.isEmpty())
            return open(cfg, "https://www.youtube.com/results?search_query=" + enc(yt), "youtube: " + yt);

        String search = startsWith(fin, "search karo", "search", "google", "dhundo", "dhoondo");
        if (search != null && !search.isEmpty())
            return open(cfg, "https://www.google.com/search?q=" + enc(search), "search: " + search);

        if (SITES.containsKey(fin)) return open(cfg, SITES.get(fin), "opening " + fin);
        if (looksLikeDomain(fin)) return open(cfg, "https://" + fin, "opening " + fin);

        return new Outcome(false, "didn't understand: " + fin, "unrecognized command");
    }

    static String enc(String s) {
        return URLEncoder.encode(s, StandardCharsets.UTF_8);
    }

    static String startsWith(String t, String... prefixes) {
        for (String raw : prefixes) {
            String p = raw.trim();
            if (p.isEmpty()) continue;
            if (t.equals(p)) return "";
            if (t.startsWith(p + " ")) return t.substring(p.length() + 1).trim();
        }
        return null;
    }

    static boolean looksLikeDomain(String s) {
        return s.matches("[a-z0-9-]+(\\.[a-z0-9-]+)+(/.*)?");
    }

    static boolean ensureCdp(Config cfg) {
        int port = cfg.getInt("cdp_port", 9222);
        if (Cdp.isUp(port)) return true;
        if (!cfg.getBool("auto_launch_browser", true)) return false;
        String exe = Cdp.findBrowserExe();
        if (exe == null) return false;
        String profile = "default".equals(cfg.get("browser_profile", "remi"))
                ? null : Config.LOCALAPPDATA.resolve("browser-profile").toString();
        return Cdp.launch(exe, port, profile, 8);
    }

    static Outcome open(Config cfg, String url, String spoken) {
        if (!ensureCdp(cfg)) return new Outcome(false, "browser not reachable",
                "no CDP on port " + cfg.getInt("cdp_port", 9222));
        try {
            Cdp.newTab(cfg.getInt("cdp_port", 9222), url);
            return new Outcome(true, spoken, url);
        } catch (Exception e) {
            return new Outcome(false, "open failed: " + e.getMessage(), url);
        }
    }

    static Outcome evalAction(Config cfg, String js, String label) {
        if (!ensureCdp(cfg)) return new Outcome(false, "browser not reachable",
                "no CDP on port " + cfg.getInt("cdp_port", 9222));
        try {
            String result = Cdp.evalJs(cfg.getInt("cdp_port", 9222), js);
            if (result == null || result.equals("error"))
                return new Outcome(false, label + " failed", result == null ? "no response" : result);
            return new Outcome(true, result, result);
        } catch (Exception e) {
            return new Outcome(false, label + " failed", String.valueOf(e.getMessage()));
        }
    }

    static Outcome stepTab(Config cfg, int delta) {
        int port = cfg.getInt("cdp_port", 9222);
        if (!ensureCdp(cfg)) return new Outcome(false, "browser not reachable", "no CDP on port " + port);
        try {
            var pages = Cdp.tabs(port);
            if (pages.isEmpty()) return new Outcome(false, "no open tabs", "empty tab list");
            int idx = (0 + delta + pages.size()) % pages.size();
            Cdp.activateTab(port, pages.get(idx).id());
            return new Outcome(true, "tab: " + pages.get(idx).title(), pages.get(idx).url());
        } catch (Exception e) {
            return new Outcome(false, "tab switch failed", String.valueOf(e.getMessage()));
        }
    }

    static Outcome closeTab(Config cfg) {
        int port = cfg.getInt("cdp_port", 9222);
        if (!ensureCdp(cfg)) return new Outcome(false, "browser not reachable", "no CDP on port " + port);
        try {
            var pages = Cdp.tabs(port);
            if (pages.isEmpty()) return new Outcome(false, "no open tabs", "empty tab list");
            Cdp.closeTab(port, pages.get(0).id());
            return new Outcome(true, "closed tab", pages.get(0).url());
        } catch (Exception e) {
            return new Outcome(false, "close failed", String.valueOf(e.getMessage()));
        }
    }
}
