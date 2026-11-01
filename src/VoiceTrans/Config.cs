namespace VoiceTrans;

/// <summary>
/// Hand-parsed flat TOML config at %APPDATA%\voice-trans\config.toml (voisu does the same).
/// Invalid values fail closed, like voisu: writing_mode falls back to literal.
/// The daemon re-reads the config at the start of every dictation cycle.
/// </summary>
public sealed class Config
{
    public string DeliveryMode { get; set; } = "type";      // type | clipboard | guarded
    public string WritingMode { get; set; } = "smart";      // smart | literal
    public string AsrMode { get; set; } = "local";          // local | cloud
    public string Language { get; set; } = "hinglish";      // auto | en | hi | hinglish
    public string LocalModel { get; set; } = "small";       // see ModelManager catalog
    public string TriggerHotkey { get; set; } = "ctrl+alt+space";
    public bool GroqEnabled { get; set; } = false;
    public int MaxRecordingSeconds { get; set; } = 120;
    public int HistoryLimit { get; set; } = 1000;

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
                        case "delivery_mode": c.DeliveryMode = val; break;
                        case "writing_mode": c.WritingMode = val; break;
                        case "asr_mode": c.AsrMode = val; break;
                        case "language": c.Language = val; break;
                        case "local_model": c.LocalModel = val; break;
                        case "trigger_hotkey": c.TriggerHotkey = val; break;
                        case "groq_enabled": c.GroqEnabled = val is "true" or "1"; break;
                        case "max_recording_seconds":
                            if (int.TryParse(val, out var mx)) c.MaxRecordingSeconds = Math.Clamp(mx, 5, 600);
                            break;
                        case "history_limit":
                            if (int.TryParse(val, out var hl)) c.HistoryLimit = Math.Clamp(hl, 10, 100_000);
                            break;
                    }
                }
            }
        }

        // fail-closed validation
        if (!Valid(c.DeliveryMode, "type", "clipboard", "guarded")) c.DeliveryMode = "type";
        if (!Valid(c.WritingMode, "smart", "literal")) c.WritingMode = "literal";
        if (!Valid(c.AsrMode, "local", "cloud")) c.AsrMode = "local";
        if (!Valid(c.Language, "auto", "en", "hi", "hinglish")) c.Language = "auto";
        if (!ModelManager.IsValid(c.LocalModel)) c.LocalModel = "small";
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
            # voice-trans configuration (flat TOML; edits picked up at the next dictation)
            delivery_mode = "{c.DeliveryMode}"        # type | clipboard | guarded
            writing_mode = "{c.WritingMode}"          # smart | literal
            asr_mode = "{c.AsrMode}"                  # local | cloud (cloud needs: auth set groq)
            language = "{c.Language}"                 # auto | en | hi | hinglish (hinglish = auto-detect + Roman output)
            local_model = "{c.LocalModel}"            # tiny | base | small | medium | large-v3-turbo
            trigger_hotkey = "{c.TriggerHotkey}"      # e.g. ctrl+alt+space, f9, ctrl+shift+d  (restart daemon to apply)
            groq_enabled = {(c.GroqEnabled ? "true" : "false")}           # cloud transcription toggle
            max_recording_seconds = {c.MaxRecordingSeconds}
            history_limit = {c.HistoryLimit}
            """;
        var tmp = Paths.ConfigFile + ".tmp";
        File.WriteAllText(tmp, text);
        File.Move(tmp, Paths.ConfigFile, overwrite: true);
    }

    static bool Valid(string value, params string[] allowed) => allowed.Contains(value);

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
