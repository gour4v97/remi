using System.Diagnostics;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

namespace VoiceTrans.Asr;

/// <summary>Optional cloud transcription via Groq (OpenAI-compatible), whisper-large-v3. Key stays DPAPI-encrypted locally.</summary>
public sealed class GroqAsr
{
    public async Task<AsrResult> TranscribeAsync(byte[] pcm, Config cfg, CancellationToken ct)
    {
        var key = KeyStore.Get("groq")
            ?? throw new InvalidOperationException("No Groq API key set. Run: voice-trans auth set groq");

        var wav = Wav.ToWav(pcm);
        var sw = Stopwatch.StartNew();

        using var http = new HttpClient { Timeout = TimeSpan.FromSeconds(60) };
        using var form = new MultipartFormDataContent();
        var file = new ByteArrayContent(wav);
        file.Headers.ContentType = new MediaTypeHeaderValue("audio/wav");
        form.Add(file, "file", "audio.wav");
        form.Add(new StringContent("whisper-large-v3"), "model");
        form.Add(new StringContent("json"), "response_format");
        if (cfg.Language is "en" or "hi")
            form.Add(new StringContent(cfg.Language), "language"); // else let the model detect

        using var req = new HttpRequestMessage(HttpMethod.Post, "https://api.groq.com/openai/v1/audio/transcriptions");
        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", key);
        req.Content = form;

        using var resp = await http.SendAsync(req, ct);
        var body = await resp.Content.ReadAsStringAsync(ct);
        if (!resp.IsSuccessStatusCode)
            throw new InvalidOperationException($"Groq API error {(int)resp.StatusCode}: {Truncate(body)}");

        using var doc = JsonDocument.Parse(body);
        var text = doc.RootElement.TryGetProperty("text", out var t) ? t.GetString() ?? "" : "";
        sw.Stop();
        return new AsrResult(text, cfg.Language, "groq:whisper-large-v3", sw.ElapsedMilliseconds);
    }

    static string Truncate(string s) => s.Length > 200 ? s[..200] : s;
}
