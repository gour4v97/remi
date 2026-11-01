namespace VoiceTrans;

/// <summary>Canonical audio everywhere is 16 kHz mono s16le PCM (same as voisu); wrap it as WAV for the ASR engines.</summary>
public static class Wav
{
    public static byte[] ToWav(ReadOnlySpan<byte> pcm, int sampleRate = 16000, short channels = 1, short bitsPerSample = 16)
    {
        int blockAlign = channels * (bitsPerSample / 8);
        int byteRate = sampleRate * blockAlign;
        using var ms = new MemoryStream(44 + pcm.Length);
        using var w = new BinaryWriter(ms);
        w.Write("RIFF"u8);
        w.Write(36 + pcm.Length);
        w.Write("WAVE"u8);
        w.Write("fmt "u8);
        w.Write(16);
        w.Write((short)1); // PCM
        w.Write(channels);
        w.Write(sampleRate);
        w.Write(byteRate);
        w.Write((short)blockAlign); // blockAlign is a 2-byte field in the WAV spec
        w.Write(bitsPerSample);
        w.Write("data"u8);
        w.Write(pcm.Length);
        w.Write(pcm);
        w.Flush();
        return ms.ToArray();
    }

    /// <summary>Peak absolute sample; used for silence detection (voisu rejects recordings with peak &lt;= 32).</summary>
    public static short PeakAmplitude(ReadOnlySpan<byte> pcm)
    {
        short peak = 0;
        for (int i = 0; i + 1 < pcm.Length; i += 2)
        {
            short s = (short)(pcm[i] | (pcm[i + 1] << 8));
            short a = s >= 0 ? s : (short)-s;
            if (a > peak) peak = a;
        }
        return peak;
    }
}
