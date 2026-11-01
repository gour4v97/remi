using System.Text.Json;
using System.Text.Json.Serialization;

namespace VoiceTrans;

public sealed record HistoryEntry(
    string Id,
    string StartedAt,
    long RecordingMs,
    string Backend,
    string? Language,
    string Transcript,
    string DeliveryMethod,
    bool Fallback,
    string? FallbackReason,
    string? Error,
    long TranscribeMs,
    long DeliverMs);

/// <summary>Local-only JSONL history ring under %LOCALAPPDATA%\voice-trans (analog of voisu's diagnostic store).</summary>
public static class History
{
    static readonly object Lock = new();
    static readonly JsonSerializerOptions JsonOpts = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };

    public static void Append(HistoryEntry e)
    {
        lock (Lock)
        {
            File.AppendAllText(Paths.HistoryFile, JsonSerializer.Serialize(e, JsonOpts) + "\n");
            try
            {
                if (new FileInfo(Paths.HistoryFile).Length > 5_000_000)
                    Compact(Config.Load().HistoryLimit);
            }
            catch { /* compaction is best-effort */ }
        }
    }

    static void Compact(int keep)
    {
        var entries = LoadCore();
        if (entries.Count <= keep) return;
        File.WriteAllLines(Paths.HistoryFile, entries.TakeLast(keep).Select(e => JsonSerializer.Serialize(e, JsonOpts)));
    }

    static List<HistoryEntry> LoadCore()
    {
        var list = new List<HistoryEntry>();
        if (!File.Exists(Paths.HistoryFile)) return list;
        foreach (var line in File.ReadLines(Paths.HistoryFile))
        {
            if (line.Length == 0) continue;
            try { list.Add(JsonSerializer.Deserialize<HistoryEntry>(line, JsonOpts)!); }
            catch { /* skip corrupt line */ }
        }
        return list;
    }

    public static List<HistoryEntry> Load(int? last = null)
    {
        lock (Lock)
        {
            var all = LoadCore();
            return last is { } n ? all.TakeLast(n).ToList() : all;
        }
    }

    public static HistoryEntry? Find(string id)
    {
        var all = Load();
        return all.FirstOrDefault(e => e.Id.Equals(id, StringComparison.OrdinalIgnoreCase))
            ?? all.FirstOrDefault(e => e.Id.StartsWith(id, StringComparison.OrdinalIgnoreCase));
    }

    public static string? Export(string id)
    {
        var e = Find(id);
        if (e is null) return null;
        var opts = new JsonSerializerOptions(JsonOpts) { WriteIndented = true };
        return JsonSerializer.Serialize(new
        {
            record = e,
            redaction = "history never stores credentials or raw audio; nothing else to redact",
            exported_at = DateTime.UtcNow.ToString("o"),
        }, opts);
    }
}
