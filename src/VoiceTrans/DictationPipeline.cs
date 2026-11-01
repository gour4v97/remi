using System.Diagnostics;
using VoiceTrans.Asr;

namespace VoiceTrans;

public sealed record PipelineOutcome(
    bool Ok,
    string? Error,
    string? Transcript,
    string DeliveryMethod,
    bool Fallback,
    string? FallbackReason,
    HistoryEntry Entry);

/// <summary>
/// Shared dictation pipeline: validate → transcribe (local/cloud) → hinglish transliteration →
/// writing mode → dictionary → deliver → history. Used by the daemon and by `voice-trans replay`.
/// </summary>
public static class DictationPipeline
{
    const int MinRecordingBytes = 9600;   // 0.3 s at 16 kHz s16le mono
    const short SilentPeakThreshold = 32; // same as voisu

    public static async Task<PipelineOutcome> RunAsync(
        byte[] pcm, long recMs, string source,
        FocusSnapshot? guard, string deliveryMode, Action<string> setClipboard, CancellationToken ct)
    {
        var outcome = await RunCoreAsync(pcm, recMs, source, guard, deliveryMode, setClipboard, ct);
        History.Append(outcome.Entry);
        return outcome;
    }

    static async Task<PipelineOutcome> RunCoreAsync(
        byte[] pcm, long recMs, string source,
        FocusSnapshot? guard, string deliveryMode, Action<string> setClipboard, CancellationToken ct)
    {
        try
        {
            if (pcm.Length < MinRecordingBytes)
                throw new InvalidOperationException("Recording too short (< 0.3 s).");
            var peak = Wav.PeakAmplitude(pcm);
            if (peak <= SilentPeakThreshold)
                throw new InvalidOperationException($"Silent recording (peak {peak}) — is the right mic selected?");

            var cfg = Config.Load();
            var dict = PronunciationDictionary.Load(Paths.DictionaryFile);

            AsrResult asr;
            if (cfg.AsrMode == "cloud")
            {
                // fail closed, like voisu — never silently fall back to local
                if (!cfg.GroqEnabled)
                    throw new InvalidOperationException(
                        "Cloud mode is selected but groq is not enabled — set 'asr local' or enable Groq in the tray menu.");
                asr = await new GroqAsr().TranscribeAsync(pcm, cfg, ct);
            }
            else
            {
                asr = await new LocalWhisper().TranscribeAsync(
                    pcm, cfg.LocalModel, cfg.Language, dict.Terms, ct);
            }

            var text = asr.Text;
            if (cfg.Language == "hinglish")
                text = Translit.ToRoman(text); // Devanagari → Roman; English passes through
            text = Writing.Apply(text, cfg.WritingMode, cfg.Language);
            text = dict.Apply(text);
            if (string.IsNullOrWhiteSpace(text))
                throw new InvalidOperationException("Empty transcript.");

            var deliverSw = Stopwatch.StartNew();
            var result = Delivery.Deliver(text, deliveryMode, guard, setClipboard);
            deliverSw.Stop();

            var entry = new HistoryEntry(
                Id: Guid.NewGuid().ToString("N"),
                StartedAt: DateTime.UtcNow.ToString("o"),
                RecordingMs: recMs,
                Backend: asr.Backend,
                Language: asr.Language ?? cfg.Language,
                Transcript: text,
                DeliveryMethod: result.Method,
                Fallback: result.Fallback,
                FallbackReason: result.FallbackReason,
                Error: null,
                TranscribeMs: asr.Ms,
                DeliverMs: deliverSw.ElapsedMilliseconds);

            return new PipelineOutcome(true, null, text, result.Method, result.Fallback, result.FallbackReason, entry);
        }
        catch (OperationCanceledException)
        {
            return Fail("cancelled");
        }
        catch (Exception ex)
        {
            return Fail(ex.Message);
        }

        PipelineOutcome Fail(string message) => new(
            false, message, null, "none", false, null,
            new HistoryEntry(
                Id: Guid.NewGuid().ToString("N"),
                StartedAt: DateTime.UtcNow.ToString("o"),
                RecordingMs: recMs,
                Backend: source,
                Language: null,
                Transcript: "",
                DeliveryMethod: "none",
                Fallback: false,
                FallbackReason: null,
                Error: message,
                TranscribeMs: 0,
                DeliverMs: 0));
    }
}
