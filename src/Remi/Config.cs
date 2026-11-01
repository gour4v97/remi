namespace Remi;

/// <summary>Hand-parsed flat TOML config, re-read at every voice command.</summary>
public sealed class Config
{
    public string TriggerHotkey { get; set; } = "ctrl+alt+b";
    public string LocalModel { get; set; } = "large-v3-turbo-q5_0";
    public int CdpPort { get; set; } = 9222;
    public bool VoiceFeedback { get; set; } = true;
    public bool AutoLaunchBrowser { get; set; } = true;
    public string BrowserPath { get; set; } = "";   // empty = auto-detect Edge/Chrome
    public string BrowserProfile { get; set; } = "remi"; // dedicated profile (reliable CDP); "default" = main profile (browser must be fully closed)
    public int MaxRecordingSeconds { get; set; } = 60;

    static readonly object FileLock = new();

    public static Config Load()
    {
        var c = new Config();
        lock (FileLock)
        {
            if (!File.Exists(Paths.ConfigFile))
            {
                SaveCore(c);
            }
            else
            {
                foreach (var raw in File.ReadAllLines(Paths.ConfigFile))
                {
                    var line = StripComment(raw).Trim();
                    int eq = line.IndexOf('=');
                    if (eq <= 0) continue;
                    var key = line[..eq].Trim();
                    var val = line[(eq + 1)..].Trim().Trim('"');
                    switch (key)
                    {
                        case "trigger_hotkey": c.TriggerHotkey = val; break;
                        case "local_model": c.LocalModel = val; break;
                        case "cdp_port": if (int.TryParse(val, out var p)) c.CdpPort = Math.Clamp(p, 1024, 65535); break;
                        case "voice_feedback": c.VoiceFeedback = val is "true" or "1"; break;
                        case "auto_launch_browser": c.AutoLaunchBrowser = val is "true" or "1"; break;
                        case "browser_path": c.BrowserPath = val; break;
                        case "browser_profile": c.BrowserProfile = val; break;
                        case "max_recording_seconds":
                            if (int.TryParse(val, out var mx)) c.MaxRecordingSeconds = Math.Clamp(mx, 5, 300);
                            break;
                    }
                }
            }
        }
        if (!ModelManager.IsValid(c.LocalModel)) c.LocalModel = "large-v3-turbo-q5_0";
        return c;
    }

    public static void Save(Config c)
    {
        lock (FileLock) SaveCore(c);
    }

    static void SaveCore(Config c)
    {
        var text =
            $"""
            # remi configuration (flat TOML; picked up at the next voice command)
            trigger_hotkey = "{c.TriggerHotkey}"      # restart the daemon to apply
            local_model = "{c.LocalModel}"            # tiny | base | small | large-v3-turbo-q5_0 | large-v3-turbo
            cdp_port = {c.CdpPort}                        # Chrome DevTools Protocol port
            voice_feedback = {(c.VoiceFeedback ? "true" : "false")}       # spoken confirmations
            auto_launch_browser = {(c.AutoLaunchBrowser ? "true" : "false")}  # start browser with debug port when needed
            browser_path = "{c.BrowserPath}"          # empty = auto-detect Edge/Chrome
            browser_profile = "{c.BrowserProfile}"    # "remi" = dedicated profile (reliable voice control); "default" = your main profile
            max_recording_seconds = {c.MaxRecordingSeconds}
            """;
        var tmp = Paths.ConfigFile + ".tmp";
        File.WriteAllText(tmp, text);
        File.Move(tmp, Paths.ConfigFile, overwrite: true);
    }

    static bool StripCommentLine(string line) => line.TrimStart().StartsWith('#');

    static string StripComment(string line)
    {
        bool inStr = false;
        for (int i = 0; i < line.Length; i++)
        {
            var ch = line[i];
            if (ch == '"') inStr = !inStr;
            else if (ch == '#' && !inStr) return line[..i];
        }
        return line;
    }
}
