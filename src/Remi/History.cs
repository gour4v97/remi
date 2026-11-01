using System.Text.Json;
using System.Text.Json.Serialization;

namespace Remi;

public sealed record HistoryEntry(
    string Id,
    string At,
    string Transcript,
    string Command,
    string Detail,
    bool Ok,
    string? Error,
    long Ms);

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
                if (new FileInfo(Paths.HistoryFile).Length > 2_000_000) Compact();
            }
            catch { /* best effort */ }
        }
    }

    static void Compact()
    {
        var all = Load(null);
        if (all.Count <= 500) return;
        File.WriteAllLines(Paths.HistoryFile, all.TakeLast(500).Select(e => JsonSerializer.Serialize(e, JsonOpts)));
    }

    public static List<HistoryEntry> Load(int? last)
    {
        lock (Lock)
        {
            var list = new List<HistoryEntry>();
            if (!File.Exists(Paths.HistoryFile)) return list;
            foreach (var line in File.ReadLines(Paths.HistoryFile))
            {
                if (line.Length == 0) continue;
                try { list.Add(JsonSerializer.Deserialize<HistoryEntry>(line, JsonOpts)!); }
                catch { /* skip corrupt line */ }
            }
            return last is { } n ? list.TakeLast(n).ToList() : list;
        }
    }
}
