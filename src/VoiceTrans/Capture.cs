using NAudio.CoreAudioApi;
using NAudio.Wave;

namespace VoiceTrans;

/// <summary>
/// Microphone capture, canonical 16 kHz mono s16le PCM.
/// Primary path is WaveInEvent (WinMM does the format conversion for us);
/// falls back to WASAPI + Media Foundation resampling if the driver refuses.
/// </summary>
public sealed class MicCapture : IDisposable
{
    readonly List<byte> _buf = new();
    readonly object _lock = new();
    readonly ManualResetEventSlim _stopped = new(false);
    WaveInEvent? _wi;
    WasapiCapture? _wac;
    WaveFormat? _srcFormat;

    public void Start()
    {
        if (TryStartWaveIn()) return;
        if (TryStartWasapi()) return;
        throw new InvalidOperationException("No usable microphone found (or it rejected 16 kHz capture).");
    }

    bool TryStartWaveIn()
    {
        try
        {
            var wi = new WaveInEvent
            {
                DeviceNumber = 0,
                WaveFormat = new WaveFormat(16000, 16, 1),
                BufferMilliseconds = 50,
            };
            wi.DataAvailable += OnData;
            wi.RecordingStopped += OnStopped;
            wi.StartRecording();
            _wi = wi;
            return true;
        }
        catch
        {
            return false;
        }
    }

    bool TryStartWasapi()
    {
        try
        {
            var device = new MMDeviceEnumerator()
                .EnumerateAudioEndPoints(DataFlow.Capture, DeviceState.Active)
                .FirstOrDefault();
            if (device is null) return false;
            var wac = new WasapiCapture(device);
            _srcFormat = wac.WaveFormat;
            wac.DataAvailable += OnData;
            wac.RecordingStopped += OnStopped;
            wac.StartRecording();
            _wac = wac;
            return true;
        }
        catch
        {
            return false;
        }
    }

    void OnData(object? sender, WaveInEventArgs e)
    {
        if (e.BytesRecorded <= 0) return;
        lock (_lock)
        {
            for (int i = 0; i < e.BytesRecorded; i++) _buf.Add(e.Buffer[i]);
        }
    }

    void OnStopped(object? sender, StoppedEventArgs e) => _stopped.Set();

    /// <summary>Stops capture and returns 16 kHz mono s16le PCM.</summary>
    public byte[] StopAndRead()
    {
        try
        {
            _wi?.StopRecording();
            _wac?.StopRecording();
        }
        catch { /* already stopped */ }
        _stopped.Wait(3000);
        byte[] raw;
        lock (_lock) raw = _buf.ToArray();
        if (_wac is not null && _srcFormat is { } fmt &&
            (fmt.SampleRate != 16000 || fmt.Channels != 1 || fmt.BitsPerSample != 16))
        {
            return ConvertTo16kMono16(raw, fmt);
        }
        return raw;
    }

    static byte[] ConvertTo16kMono16(byte[] raw, WaveFormat src)
    {
        using var srcMs = new MemoryStream(raw);
        using var rawStream = new RawSourceWaveStream(srcMs, src);
        using var resampler = new MediaFoundationResampler(rawStream, new WaveFormat(16000, 16, 1))
        {
            ResamplerQuality = 60,
        };
        using var outMs = new MemoryStream();
        var buf = new byte[64 * 1024];
        int n;
        while ((n = resampler.Read(buf, 0, buf.Length)) > 0) outMs.Write(buf, 0, n);
        return outMs.ToArray();
    }

    public void Dispose()
    {
        try { _wi?.Dispose(); } catch { }
        try { _wac?.Dispose(); } catch { }
        _stopped.Dispose();
    }
}
