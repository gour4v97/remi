using System.Security.Cryptography;

namespace Remi;

/// <summary>
/// Consented local whisper models. Remi looks in its own models dir first, then borrows
/// voice-trans's models (same ggml format) so nothing gets downloaded twice.
/// </summary>
public static class ModelManager
{
    static readonly Dictionary<string, long> Catalog = new()
    {
        ["tiny"] = 75, ["base"] = 142, ["small"] = 487, ["medium"] = 1527, ["large-v3-turbo"] = 1620,
        ["large-v3-turbo-q5_0"] = 574,
    };

    public static IReadOnlyList<string> Names => Catalog.Keys.OrderBy(k => k).ToList();
    public static bool IsValid(string name) => Catalog.ContainsKey(name);
    public static long SizeMb(string name) => Catalog.TryGetValue(name, out var v) ? v : 0;

    public static string PathFor(string name)
    {
        var own = Path.Combine(Paths.ModelsDir, $"ggml-{name}.bin");
        if (File.Exists(own)) return own;
        var borrowed = Path.Combine(Paths.VoiceTransModelsDir, $"ggml-{name}.bin");
        return File.Exists(borrowed) ? borrowed : own;
    }

    public static bool IsInstalled(string name) => IsValid(name) && File.Exists(PathFor(name));

    public static async Task DownloadAsync(string name, Action<long, long> progress, CancellationToken ct)
    {
        if (!IsValid(name)) throw new ArgumentException($"unknown model '{name}'");
        Directory.CreateDirectory(Paths.ModelsDir);
        var url = $"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-{name}.bin";
        var target = Path.Combine(Paths.ModelsDir, $"ggml-{name}.bin");
        var part = target + ".part";

        using var http = new HttpClient { Timeout = Timeout.InfiniteTimeSpan };
        using var resp = await http.GetAsync(url, HttpCompletionOption.ResponseHeadersRead, ct);
        resp.EnsureSuccessStatusCode();
        long total = resp.Content.Headers.ContentLength ?? -1;

        await using var src = await resp.Content.ReadAsStreamAsync(ct);
        await using (var dst = File.Create(part))
        {
            var buf = new byte[1024 * 1024];
            long done = 0;
            int n;
            while ((n = await src.ReadAsync(buf, ct)) > 0)
            {
                await dst.WriteAsync(buf.AsMemory(0, n), ct);
                done += n;
                progress(done, total);
            }
            await dst.FlushAsync(ct);
        } // stream disposed before the rename
        File.Move(part, target, overwrite: true);
        File.WriteAllText(target + ".sha256", HashFile(target) + "  ggml-" + name + ".bin\n");
    }

    public static void Remove(string name)
    {
        var p = Path.Combine(Paths.ModelsDir, $"ggml-{name}.bin");
        if (File.Exists(p)) File.Delete(p);
        if (File.Exists(p + ".sha256")) File.Delete(p + ".sha256");
    }

    static string HashFile(string path)
    {
        using var sha = SHA256.Create();
        using var fs = File.OpenRead(path);
        return Convert.ToHexString(sha.ComputeHash(fs)).ToLowerInvariant();
    }
}
