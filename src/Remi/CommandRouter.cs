using System.Text.Json;
using System.Text.RegularExpressions;

namespace Remi;

public sealed record CommandOutcome(string Spoken, string Detail, bool Ok);

/// <summary>
/// Maps a (romanized) transcript to a browser action. Understands English and
/// Hinglish command words — Hindi speech is transliterated to Roman before routing.
/// </summary>
public static class CommandRouter
{
    static readonly Dictionary<string, string> Sites = new(StringComparer.OrdinalIgnoreCase)
    {
        ["youtube"] = "https://www.youtube.com",
        ["google"] = "https://www.google.com",
        ["gmail"] = "https://mail.google.com",
        ["mail"] = "https://mail.google.com",
        ["whatsapp"] = "https://web.whatsapp.com",
        ["chatgpt"] = "https://chatgpt.com",
        ["github"] = "https://github.com",
        ["instagram"] = "https://www.instagram.com",
        ["insta"] = "https://www.instagram.com",
        ["facebook"] = "https://www.facebook.com",
        ["reddit"] = "https://www.reddit.com",
        ["wikipedia"] = "https://www.wikipedia.org",
        ["amazon"] = "https://www.amazon.in",
        ["flipkart"] = "https://www.flipkart.com",
        ["twitter"] = "https://x.com",
        ["x"] = "https://x.com",
        ["linkedin"] = "https://www.linkedin.com",
        ["netflix"] = "https://www.netflix.com",
        ["hotstar"] = "https://www.hotstar.com",
        ["maps"] = "https://www.google.com/maps",
        ["drive"] = "https://drive.google.com",
        ["spotify"] = "https://open.spotify.com",
    };

    public static async Task<CommandOutcome> RunAsync(string text, Config cfg, CancellationToken ct)
    {
        var t = Regex.Replace(text.Trim().ToLowerInvariant(), @"\s+", " ");
        if (t.Length == 0) return Fail("nothing heard", "empty transcript");

        // Hinglish word order: "youtube kholo" / "gmail khol do" → "youtube" / "gmail"
        var stripped = Regex.Replace(t, @"\s+(khol(?:o|a)?(?:\s+do|dena)?|open karo|khol de)$", "");
        if (stripped != t) t = stripped;

        // tab switching first — "peeche wapas" style phrases overlap with back/forward
        if (Is(t, "next tab", "agla tab", "agle tab", "next tab kholo"))
            return await StepTabAsync(cfg, +1, ct);
        if (Is(t, "previous tab", "pichla tab", "pichle tab", "last tab"))
            return await StepTabAsync(cfg, -1, ct);
        if (Is(t, "new tab", "naya tab", "naya tab kholo", "new tab kholo"))
            return await GuardedAsync(cfg, ct, port => { return Browser.NewTabAsync(port, "about:blank"); }, "new tab");
        if (Is(t, "close tab", "tab band karo", "tab band", "band karo", "close tab karo"))
            return await CloseTabAsync(cfg, ct);

        if (Is(t, "refresh", "refresh karo", "reload", "reload karo"))
            return await EvalAsync(cfg, "location.reload(); 'refreshing'", "refreshing page", ct);
        if (Is(t, "go back", "back", "wapas jao", "wapas", "peeche jao"))
            return await EvalAsync(cfg, "history.back(); 'going back'", "going back", ct);
        if (Is(t, "forward", "aage jao", "go forward"))
            return await EvalAsync(cfg, "history.forward(); 'going forward'", "going forward", ct);

        if (t.StartsWith("scroll") || t.Contains("scroll") || Is(t, "niche", "neeche", "upar", "sabse niche", "sabse upar"))
        {
            var js = t.Contains("top") || t.Contains("sabse upar")
                ? "window.scrollTo(0,0); 'top'"
                : t.Contains("bottom") || t.Contains("sabse niche")
                    ? "window.scrollTo(0, document.body.scrollHeight); 'bottom'"
                    : t.Contains("up") || t.Contains("upar")
                        ? "window.scrollBy(0,-600); 'scrolled up'"
                        : "window.scrollBy(0,600); 'scrolled down'";
            var label = js.Contains("'top'") ? "scrolled to top"
                : js.Contains("'bottom'") ? "scrolled to bottom"
                : js.Contains("up") ? "scrolled up" : "scrolled down";
            return await EvalAsync(cfg, js, label, ct);
        }

        if (Is(t, "play", "pause", "play karo", "pause karo", "chalao", "roko", "resume", "video chalao", "gaana chalao", "music chalao"))
            return await EvalAsync(cfg,
                "(function(){var el=document.querySelector('video')||document.querySelector('audio');if(!el)return 'no media on this page';if(el.paused){el.play();return 'playing';}el.pause();return 'paused';})()",
                "media toggle", ct);

        var click = StartsWith(t, "click karo", "click", "dabao", "press");
        if (click is not null && click.Length > 0)
            return await EvalAsync(cfg, ClickJs(click), $"clicked '{click}'", ct);

        var typeText = StartsWith(t, "type karo", "type", "likho", "write");
        if (typeText is not null && typeText.Length > 0)
            return await EvalAsync(cfg, TypeJs(typeText), $"typed '{typeText}'", ct);

        if (Is(t, "read title", "title batao", "kya page hai", "what page", "which page"))
            return await EvalAsync(cfg, "document.title", "page title", ct);

        // "X kholo" / "open X" first — so "youtube kholo" opens YouTube instead of searching
        var open = StartsWith(t, "open", "kholo", "khol", "launch", "jao");
        if (open is not null && open.Length > 0)
        {
            var site = open.Trim().TrimEnd('.', '!', '?');
            if (Sites.TryGetValue(site, out var url))
                return await OpenAsync(cfg, url, $"opening {site}");
            if (LooksLikeDomain(site))
                return await OpenAsync(cfg, "https://" + site, $"opening {site}");
            return await OpenAsync(cfg, $"https://www.google.com/search?q={Uri.EscapeDataString(open)}", $"search: {open}");
        }

        var yt = StartsWith(t, "youtube");
        if (yt is not null && yt.Length > 0)
            return await OpenAsync(cfg, $"https://www.youtube.com/results?search_query={Uri.EscapeDataString(yt)}", $"youtube: {yt}");

        var search = StartsWith(t, "search karo", "search", "google", "dhundo", "dhoondo");
        if (search is not null && search.Length > 0)
            return await OpenAsync(cfg, $"https://www.google.com/search?q={Uri.EscapeDataString(search)}", $"search: {search}");

        if (Sites.TryGetValue(t, out var direct))
            return await OpenAsync(cfg, direct, $"opening {t}");
        if (LooksLikeDomain(t))
            return await OpenAsync(cfg, "https://" + t, $"opening {t}");

        return Fail($"didn't understand: {t}", "unrecognized command");
    }

    // ---------- helpers ----------

    static CommandOutcome Fail(string spoken, string detail) => new(spoken, detail, false);

    static bool Is(string t, params string[] phrases) => phrases.Contains(t);

    static string? StartsWith(string t, params string[] prefixes)
    {
        foreach (var raw in prefixes)
        {
            var p = raw.Trim();
            if (p.Length == 0) continue;
            if (t == p) return "";
            if (t.StartsWith(p + " ")) return t[(p.Length + 1)..].Trim();
        }
        return null;
    }

    static bool LooksLikeDomain(string s) =>
        Regex.IsMatch(s, @"^[a-z0-9-]+(\.[a-z0-9-]+)+(/.*)?$") && s.Contains('.');

    static async Task<CommandOutcome> GuardedAsync(Config cfg, CancellationToken ct, Func<int, Task> action, string label)
    {
        if (!await EnsureCdpAsync(cfg)) return Fail("browser not reachable", $"no CDP on port {cfg.CdpPort}");
        await action(cfg.CdpPort);
        return new CommandOutcome(label, label, true);
    }

    static async Task<CommandOutcome> OpenAsync(Config cfg, string url, string spoken)
    {
        if (!await EnsureCdpAsync(cfg)) return Fail("browser not reachable", $"no CDP on port {cfg.CdpPort}");
        await Browser.NewTabAsync(cfg.CdpPort, url);
        return new CommandOutcome(spoken, url, true);
    }

    static async Task<CommandOutcome> EvalAsync(Config cfg, string js, string label, CancellationToken ct)
    {
        if (!await EnsureCdpAsync(cfg)) return Fail("browser not reachable", $"no CDP on port {cfg.CdpPort}");
        var result = await Browser.EvalAsync(cfg.CdpPort, js, ct);
        if (result is null || result == "error") return Fail($"{label} failed", result ?? "no response");
        return new CommandOutcome(result, result, true);
    }

    static async Task<CommandOutcome> StepTabAsync(Config cfg, int delta, CancellationToken ct)
    {
        if (!await EnsureCdpAsync(cfg)) return Fail("browser not reachable", $"no CDP on port {cfg.CdpPort}");
        var tabs = await Browser.TabsAsync(cfg.CdpPort);
        if (tabs.Count == 0) return Fail("no open tabs", "empty tab list");
        // CDP /json order is most-recently-used; step through it and activate.
        var idx = (0 + delta + tabs.Count) % tabs.Count; // MRU slot 0 is active; neighbor = delta
        await Browser.ActivateTabAsync(cfg.CdpPort, tabs[idx].Id);
        return new CommandOutcome($"tab: {tabs[idx].Title}", tabs[idx].Url, true);
    }

    static async Task<CommandOutcome> CloseTabAsync(Config cfg, CancellationToken ct)
    {
        if (!await EnsureCdpAsync(cfg)) return Fail("browser not reachable", $"no CDP on port {cfg.CdpPort}");
        var tabs = await Browser.TabsAsync(cfg.CdpPort);
        if (tabs.Count == 0) return Fail("no open tabs", "empty tab list");
        await Browser.CloseTabAsync(cfg.CdpPort, tabs[0].Id);
        return new CommandOutcome("closed tab", tabs[0].Url, true);
    }

    public static async Task<bool> EnsureCdpAsync(Config cfg)
    {
        if (await Browser.IsCdpUpAsync(cfg.CdpPort)) return true;
        if (!cfg.AutoLaunchBrowser) return false;
        var exe = Browser.FindBrowserExecutable(cfg.BrowserPath);
        if (exe is null) return false;
        var profileDir = cfg.BrowserProfile == "default"
            ? null
            : Path.Combine(Paths.AppDataLocal, "browser-profile");
        return await Browser.LaunchAsync(exe, cfg.CdpPort, profileDir);
    }

    static string ClickJs(string target)
    {
        var q = JsonSerializer.Serialize(target.ToLowerInvariant());
        return ClickJsTemplate.Replace("__Q__", q);
    }

    const string ClickJsTemplate =
        """
        (function(){var q=__Q__;var els=document.querySelectorAll('a,button,[role=button],input[type=submit]');for(var i=0;i<els.length;i++){var e=els[i];if(!e.offsetParent)continue;var txt=((e.innerText||e.value||'')+'').trim().toLowerCase();if(txt&&txt.includes(q)){e.click();return 'clicked: '+txt.slice(0,40);}}return 'not found: '+q;})()
        """;

    static string TypeJs(string text)
    {
        var q = JsonSerializer.Serialize(text);
        return TypeJsTemplate.Replace("__Q__", q);
    }

    const string TypeJsTemplate =
        """
        (function(){var ae=document.activeElement;if(!ae||(ae.tagName!=='INPUT'&&ae.tagName!=='TEXTAREA'&&!ae.isContentEditable))return 'no input focused';document.execCommand('insertText',false,__Q__);return 'typed';})()
        """;
}
