using System.Speech.Synthesis;

namespace Remi;

/// <summary>Spoken confirmations via Windows SAPI TTS (Microsoft David/Zira).</summary>
public static class Speech
{
    static SpeechSynthesizer? _synth;
    static readonly object Lock = new();

    public static void Say(string text, bool enabled)
    {
        if (!enabled || string.IsNullOrWhiteSpace(text)) return;
        lock (Lock)
        {
            try
            {
                _synth ??= new SpeechSynthesizer();
                _synth.SpeakAsyncCancelAll();
                _synth.SpeakAsync(text);
            }
            catch { /* TTS is best-effort feedback, never a failure */ }
        }
    }
}
