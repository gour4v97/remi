using System.Diagnostics;

namespace Remi.Asr;

public sealed record AsrResult(string Text, string? Language, string Backend, long Ms);

/// <summary>Local transcription via Whisper.net (whisper.cpp engine, ggml models). Fully offline.</summary>
public sealed class LocalWhisper
{
    // model loads are expensive (~10-20 s for a 574 MB ggml) — load once per process and keep hot
    static readonly System.Collections.Concurrent.ConcurrentDictionary<string, Whisper.net.WhisperFactory> Factories = new();

    static Whisper.net.WhisperFactory FactoryFor(string path) =>
        Factories.GetOrAdd(path, p => Whisper.net.WhisperFactory.FromPath(p));

    public async Task<AsrResult> TranscribeAsync(
        byte[] pcm, string modelName, string language, IReadOnlyList<string> terms, CancellationToken ct)
    {
        string path = ModelManager.PathFor(modelName);
        if (!File.Exists(path))
        {
            throw new InvalidOperationException(
                $"Local model '{modelName}' is not installed. Run: voice-trans model download {modelName}");
        }

        var wav = Wav.ToWav(pcm);
        var sw = Stopwatch.StartNew();

        var factory = FactoryFor(path);
        var builder = factory.CreateBuilder();

        // "hinglish" and "auto" both use whisper's language auto-detect so code-mixed
        // speech works; "en"/"hi" pin the language explicitly.
        builder.WithLanguage(language == "en" ? "en" : language == "hi" ? "hi" : "auto");
        builder.WithThreads(Math.Min(8, Environment.ProcessorCount));

        var prompt = BuildPrompt(terms, language);
        if (prompt.Length > 0) builder.WithPrompt(prompt);

        await using var processor = builder.Build();

        var sb = new System.Text.StringBuilder();
        string? detected = null;
        using var ms = new MemoryStream(wav);
        await foreach (var seg in processor.ProcessAsync(ms, ct))
        {
            if (detected is null)
                detected = seg.Language is { } l ? l.ToString() : null;
            sb.Append(seg.Text);
        }

        sw.Stop();
        return new AsrResult(sb.ToString(), detected, $"local:{modelName}", sw.ElapsedMilliseconds);
    }

    static string BuildPrompt(IReadOnlyList<string> terms, string language)
    {
        var parts = new List<string>();
        if (terms.Count > 0)
        {
            var joined = string.Join(", ", terms);
            if (joined.Length > 400) joined = joined[..400];
            parts.Add(joined);
        }
        if (language == "hinglish")
            parts.Add("Hinglish conversation mixing Hindi and English");
        return string.Join(", ", parts);
    }
}
