using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text.Json;
using Remi.Asr;

namespace Remi;

/// <summary>
/// The remi daemon: hotkey toggle → record → local whisper → command routing →
/// browser action → spoken confirmation → history.
/// </summary>
public sealed class DaemonApp : IDisposable
{
    public enum AppState { Idle, Listening, Thinking }

    const int HotkeyId = 1;
    const int WM_HOTKEY = 0x0312;
    const int MinRecordingBytes = 9600;   // 0.3 s
    const short SilentPeakThreshold = 32;

    sealed class HotkeyForm : Form
    {
        public Action? OnHotkey;
        public HotkeyForm() { ShowInTaskbar = false; FormBorderStyle = FormBorderStyle.None; Opacity = 0; }
        protected override void WndProc(ref Message m)
        {
            if (m.Msg == WM_HOTKEY && m.WParam.ToInt32() == HotkeyId) { OnHotkey?.Invoke(); return; }
            base.WndProc(ref m);
        }
    }

    HotkeyForm _form = null!;
    TrayUi _tray = null!;
    System.Windows.Forms.Timer _maxTimer = null!;
    AppState _state = AppState.Idle;
    MicCapture? _capture;
    DateTime _recStartUtc;
    string _hotkeySpec = "";
    readonly CancellationTokenSource _shutdown = new();

    [DllImport("user32.dll", SetLastError = true)]
    static extern bool RegisterHotKey(IntPtr hWnd, int id, uint fsModifiers, uint vk);
    [DllImport("user32.dll")]
    static extern bool UnregisterHotKey(IntPtr hWnd, int id);

    public void Run()
    {
        _form = new HotkeyForm();
        _ = _form.Handle;
        _form.OnHotkey = RequestToggle;

        _tray = new TrayUi(this);
        _tray.ToggleRequested = RequestToggle;
        _tray.BrowserLaunchRequested = LaunchBrowserFromTray;

        _maxTimer = new System.Windows.Forms.Timer();
        _maxTimer.Tick += (_, _) => RequestToggle();

        RegisterHotkeyFromConfig();
        _ = Task.Run(() => Ipc.ServeAsync(HandleIpc, _shutdown.Token));

        _tray.SetState(AppState.Idle, DescribeHotkey());
        if (_hotkeySpec.Length == 0)
            _tray.Balloon("remi", "Trigger hotkey could not be registered (in use?). Use the tray menu.", true);
        Application.Run();
    }

    string DescribeHotkey() => _hotkeySpec.Length > 0 ? _hotkeySpec : "unregistered";

    void RegisterHotkeyFromConfig()
    {
        var cfg = Config.Load();
        var hk = Hotkey.Parse(cfg.TriggerHotkey);
        if (hk is { } h && RegisterHotKey(_form.Handle, HotkeyId, h.Mods, h.Vk))
            _hotkeySpec = Hotkey.Describe(h.Mods, h.Vk);
    }

    void LaunchBrowserFromTray()
    {
        var cfg = Config.Load();
        var exe = Browser.FindBrowserExecutable(cfg.BrowserPath);
        if (exe is null) { _tray.Balloon("remi", "No Edge or Chrome installation found.", true); return; }
        _ = Task.Run(async () =>
        {
            var profileDir = cfg.BrowserProfile == "default"
                ? null
                : Path.Combine(Paths.AppDataLocal, "browser-profile");
            var ok = await Browser.LaunchAsync(exe, cfg.CdpPort, profileDir);
            _tray.Balloon("remi", ok ? "Browser started with voice control enabled." : "Browser started but debug port did not respond.", !ok);
        });
    }

    // ---------- IPC ----------

    string HandleIpc(string cmd)
    {
        switch (cmd.Trim())
        {
            case "toggle": RequestToggle(); return "ok";
            case "stop": RequestStop(); return "ok";
            case "status": return StatusJson();
            default: return JsonSerializer.Serialize(new { error = "unknown command (toggle | stop | status)" });
        }
    }

    void RequestToggle()
    {
        try { _form.BeginInvoke(OnToggle); } catch (ObjectDisposedException) { }
    }

    void RequestStop()
    {
        try { _form.BeginInvoke(Shutdown); } catch (ObjectDisposedException) { }
    }

    // ---------- state machine (UI thread) ----------

    void OnToggle()
    {
        switch (_state)
        {
            case AppState.Idle: StartRecording(); break;
            case AppState.Listening: StopAndProcess(); break;
            default: break;
        }
    }

    void StartRecording()
    {
        var cfg = Config.Load();
        _capture = new MicCapture();
        try { _capture.Start(); }
        catch (Exception ex)
        {
            _capture.Dispose(); _capture = null;
            _state = AppState.Idle; _tray.SetState(AppState.Idle, DescribeHotkey());
            _tray.Balloon("Microphone", ex.Message, true);
            return;
        }
        _recStartUtc = DateTime.UtcNow;
        _state = AppState.Listening;
        _tray.SetState(AppState.Listening, DescribeHotkey());
        _maxTimer.Interval = Math.Max(5, cfg.MaxRecordingSeconds) * 1000;
        _maxTimer.Start();
    }

    void StopAndProcess()
    {
        _maxTimer.Stop();
        if (_capture is null) { _state = AppState.Idle; _tray.SetState(AppState.Idle, DescribeHotkey()); return; }
        var cap = _capture; _capture = null;
        _state = AppState.Thinking;
        _tray.SetState(AppState.Thinking, DescribeHotkey());

        var pcm = cap.StopAndRead();
        cap.Dispose();
        var recMs = (long)(DateTime.UtcNow - _recStartUtc).TotalMilliseconds;

        _ = Task.Run(async () =>
        {
            try { await ProcessAsync(pcm, recMs); }
            finally
            {
                Ui(() => { _state = AppState.Idle; _tray.SetState(AppState.Idle, DescribeHotkey()); });
            }
        });
    }

    // ---------- pipeline (background thread) ----------

    async Task ProcessAsync(byte[] pcm, long recMs)
    {
        var cfg = Config.Load();
        var sw = Stopwatch.StartNew();
        try
        {
            if (pcm.Length < MinRecordingBytes) throw new InvalidOperationException("Recording too short.");
            if (Wav.PeakAmplitude(pcm) <= SilentPeakThreshold) throw new InvalidOperationException("Silent recording — is the right mic selected?");

            var whisper = new LocalWhisper();
            var asr = await whisper.TranscribeAsync(pcm, cfg.LocalModel, "hinglish", Array.Empty<string>(), _shutdown.Token);
            var text = Translit.ToRoman(asr.Text).Trim();
            if (text.Length == 0) throw new InvalidOperationException("Empty transcript.");

            var outcome = await CommandRouter.RunAsync(text, cfg, _shutdown.Token);
            sw.Stop();

            History.Append(new HistoryEntry(
                Id: Guid.NewGuid().ToString("N"),
                At: DateTime.UtcNow.ToString("o"),
                Transcript: text,
                Command: outcome.Ok ? outcome.Detail : "unrecognized",
                Detail: outcome.Spoken,
                Ok: outcome.Ok,
                Error: outcome.Ok ? null : outcome.Spoken,
                Ms: sw.ElapsedMilliseconds));

            Speech.Say(outcome.Ok ? outcome.Spoken : $"Sorry. {outcome.Spoken}", cfg.VoiceFeedback);
            if (!outcome.Ok)
                Ui(() => _tray.Balloon("remi", outcome.Spoken, true));
        }
        catch (Exception ex)
        {
            sw.Stop();
            History.Append(new HistoryEntry(
                Id: Guid.NewGuid().ToString("N"),
                At: DateTime.UtcNow.ToString("o"),
                Transcript: "",
                Command: "error",
                Detail: "",
                Ok: false,
                Error: ex.Message,
                Ms: sw.ElapsedMilliseconds));
            Speech.Say("Sorry, that failed.", cfg.VoiceFeedback);
            Ui(() => _tray.Balloon("remi failed", ex.Message, true));
        }
    }

    void Ui(Action a)
    {
        try { _form.BeginInvoke(a); } catch (ObjectDisposedException) { }
    }

    internal string StatusJson()
    {
        var cfg = Config.Load();
        return JsonSerializer.Serialize(new
        {
            state = _state.ToString().ToLowerInvariant(),
            hotkey = DescribeHotkey(),
            model = cfg.LocalModel,
            cdp_port = cfg.CdpPort,
            voice_feedback = cfg.VoiceFeedback,
            pid = Environment.ProcessId,
        }, StatusOpts);
    }

    static readonly JsonSerializerOptions StatusOpts = new()
    {
        Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
    };

    internal void ApplyModeChange(Action<Config> mutate)
    {
        var cfg = Config.Load();
        mutate(cfg);
        Config.Save(cfg);
    }

    internal Config CurrentConfig() => Config.Load();

    internal void QuitFromTray() => RequestStop();

    void Shutdown()
    {
        if (_state == AppState.Listening)
        {
            try { _capture?.StopAndRead(); } catch { }
            _capture?.Dispose(); _capture = null;
            _state = AppState.Idle;
        }
        _maxTimer.Stop();
        _shutdown.Cancel();
        try { UnregisterHotKey(_form.Handle, HotkeyId); } catch { }
        _tray.Dispose();
        Application.Exit();
    }

    public void Dispose()
    {
        try { _shutdown.Cancel(); } catch { }
        try { _tray?.Dispose(); } catch { }
        try { _form?.Dispose(); } catch { }
    }
}
