using System.Diagnostics;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Remi;

/// <summary>
/// Browser control over the Chrome DevTools Protocol (works with Edge and Chrome).
/// HTTP endpoints for tab management; a minimal WebSocket client for Runtime.evaluate (JS).
/// The browser must be running with --remote-debugging-port (remi can launch it that way).
/// </summary>
public sealed class Browser
{
    static readonly string[] CandidatePaths =
    {
        @"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        @"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        @"C:\Program Files\Google\Chrome\Application\chrome.exe",
        @"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Google\Chrome\Application\chrome.exe"),
    };

    public static string? FindBrowserExecutable(string configured)
    {
        if (configured.Length > 0 && File.Exists(configured)) return configured;
        return CandidatePaths.FirstOrDefault(File.Exists);
    }

    public static async Task<bool> IsCdpUpAsync(int port)
    {
        try
        {
            using var http = new HttpClient { Timeout = TimeSpan.FromSeconds(2) };
            using var resp = await http.GetAsync($"http://127.0.0.1:{port}/json/version");
            return resp.IsSuccessStatusCode;
        }
        catch { return false; }
    }

    /// <summary>Launches the browser with the debug port and waits (bounded) for CDP to come up.
    /// A dedicated profile dir guarantees the debug port works even if the browser is already running;
    /// pass null to use the main profile (then the browser must be fully closed first).</summary>
    public static async Task<bool> LaunchAsync(string exe, int port, string? profileDir, int waitMs = 8000)
    {
        var args = $"--remote-debugging-port={port}";
        if (!string.IsNullOrEmpty(profileDir))
        {
            Directory.CreateDirectory(profileDir);
            args += $" --user-data-dir=\"{profileDir}\" --no-first-run --no-default-browser-check";
        }
        else
        {
            args += " --restore-last-session";
        }
        Process.Start(new ProcessStartInfo
        {
            FileName = exe,
            Arguments = args,
            UseShellExecute = true,
        });
        var deadline = Environment.TickCount64 + waitMs;
        while (Environment.TickCount64 < deadline)
        {
            if (await IsCdpUpAsync(port)) return true;
            await Task.Delay(300);
        }
        return false;
    }

    public sealed record Tab(
        string Id,
        string Title,
        string Url,
        [property: JsonPropertyName("webSocketDebuggerUrl")] string? WsUrl);

    static readonly JsonSerializerOptions JsonOpts = new() { PropertyNameCaseInsensitive = true };

    public static async Task<List<Tab>> TabsAsync(int port)
    {
        using var http = new HttpClient { Timeout = TimeSpan.FromSeconds(3) };
        var json = await http.GetStringAsync($"http://127.0.0.1:{port}/json");
        var list = JsonSerializer.Deserialize<List<Tab>>(json, JsonOpts) ?? new();
        return list.Where(t => t.WsUrl is not null && t.WsUrl.Contains("/devtools/page/")).ToList();
    }

    public static async Task NewTabAsync(int port, string url)
    {
        using var http = new HttpClient { Timeout = TimeSpan.FromSeconds(5) };
        using var req = new HttpRequestMessage(HttpMethod.Put, $"http://127.0.0.1:{port}/json/new?{Uri.EscapeDataString(url)}");
        using var resp = await http.SendAsync(req);
        resp.EnsureSuccessStatusCode();
    }

    public static async Task ActivateTabAsync(int port, string id)
    {
        using var http = new HttpClient { Timeout = TimeSpan.FromSeconds(3) };
        await http.GetStringAsync($"http://127.0.0.1:{port}/json/activate/{id}");
    }

    public static async Task CloseTabAsync(int port, string id)
    {
        using var http = new HttpClient { Timeout = TimeSpan.FromSeconds(3) };
        await http.GetStringAsync($"http://127.0.0.1:{port}/json/close/{id}");
    }

    /// <summary>Evaluates JS in the most recently active page and returns result.value as a string.</summary>
    public static async Task<string?> EvalAsync(int port, string js, CancellationToken ct)
    {
        var tabs = await TabsAsync(port);
        var target = tabs.FirstOrDefault(t => t.WsUrl is not null);
        if (target is null || target.WsUrl is null) return null;

        using var ws = new ClientWebSocket();
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(ct);
        timeout.CancelAfter(TimeSpan.FromSeconds(6));
        await ws.ConnectAsync(new Uri(target.WsUrl), timeout.Token);

        var payload = JsonSerializer.Serialize(new
        {
            id = 1,
            method = "Runtime.evaluate",
            @params = new { expression = js, returnByValue = true, awaitPromise = true },
        });
        await ws.SendAsync(Encoding.UTF8.GetBytes(payload), WebSocketMessageType.Text, true, timeout.Token);

        var sb = new StringBuilder();
        var buf = new byte[256 * 1024];
        while (true)
        {
            var res = await ws.ReceiveAsync(buf, timeout.Token);
            sb.Append(Encoding.UTF8.GetString(buf, 0, res.Count));
            if (res.EndOfMessage) break;
        }
        var text = sb.ToString();
        using var doc = JsonDocument.Parse(text);
        var root = doc.RootElement;
        if (root.TryGetProperty("result", out var result) &&
            result.TryGetProperty("result", out var inner))
        {
            if (inner.TryGetProperty("value", out var value))
                return value.ValueKind == JsonValueKind.String ? value.GetString() : value.ToString();
            if (inner.TryGetProperty("description", out var desc))
                return desc.GetString();
            return "ok";
        }
        if (root.TryGetProperty("error", out var err))
            return "error: " + (err.TryGetProperty("message", out var em) ? em.GetString() : "unknown");
        return null;
    }
}
