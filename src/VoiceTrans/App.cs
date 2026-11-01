using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text.Json;
using VoiceTrans.Asr;

namespace VoiceTrans;

/// <summary>
/// The daemon: hidden message window owns the hotkey; tray shows state;
/// toggle → record → transcribe → polish → deliver → history. Single instance via named mutex (checked in Program).
/// </summary>
public sealed class DaemonApp : IDisposable
{
    public enum AppState { Idle, Recording, Processing }

    const int HotkeyId = 1;
    const int WM_HOTKEY = 0x0312;

    sealed class HotkeyForm : Form
    {
        public Action? OnHotkey;
        public HotkeyForm()
        {
            ShowInTaskbar = false;
            FormBorderStyle = FormBorderStyle.None;
            Opacity = 0;
        }
        protected override void WndProc(ref Message m)
        {
            if (m.Msg == WM_HOTKEY && m.WParam.ToInt32() == HotkeyId)
            {
                OnHotkey?.Invoke();
                return;
            }
            base.WndProc(ref m);
        }
    }

    HotkeyForm _form = null!;
    TrayUi _tray = null!;
    System.Windows.Forms.Timer _maxTimer = null!;
    AppState _state = AppState.Idle;
    MicCapture? _capture;
    FocusSnapshot? _focus;
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
        _ = _form.Handle; // force handle creation so RegisterHotKey has an hwnd
        _form.OnHotkey = RequestToggle;

        _tray = new TrayUi(this);
        _tray.ToggleRequested = RequestToggle;

        _maxTimer = new System.Windows.Forms.Timer();
        _maxTimer.Tick += (_, _) => RequestToggle();

        RegisterHotkeyFromConfig();
        _ = Task.Run(() => Ipc.ServeAsync(HandleIpc, _shutdown.Token));

        _tray.SetState(AppState.Idle, DescribeHotkey());
        if (_hotkeySpec.Length == 0)
            _tray.Balloon("voice-trans", "Trigger hotkey could not be registered (in use?). Toggle from the tray menu.", true);
        Application.Run();
    }

    string DescribeHotkey() => _hotkeySpec.Length > 0 ? _hotkeySpec : "unregistered";

    void RegisterHotkeyFromConfig()
    {
        var cfg = Config.Load();
        _hotkeySpec = "";
        var hk = Hotkey.Parse(cfg.TriggerHotkey);
        if (hk is { } h && RegisterHotKey(_form.Handle, HotkeyId, h.Mods, h.Vk))
            _hotkeySpec = Hotkey.Describe(h.Mods, h.Vk);
    }

    // ---------- IPC ----------

    string HandleIpc(string cmd)
    {
        switch (cmd.Trim())
        {
            case "toggle":
                RequestToggle();
                return "ok";
            case "stop":
                RequestStop();
                return "ok";
            case "status":
                return StatusJson();
            default:
                return JsonSerializer.Serialize(new { error = "unknown command (toggle | stop | status)" });
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
            case AppState.Recording: StopAndProcess(); break;
            default: break; // processing — ignore
        }
    }

    void StartRecording()
    {
        var cfg = Config.Load();
        _focus = Delivery.CaptureFocus();
        _capture = new MicCapture();
        try
        {
            _capture.Start();
        }
        catch (Exception ex)
        {
            _capture.Dispose();
            _capture = null;
            _state = AppState.Idle;
            _tray.SetState(AppState.Idle, DescribeHotkey());
            _tray.Balloon("Microphone", ex.Message, true);
            return;
        }
        _recStartUtc = DateTime.UtcNow;
        _state = AppState.Recording;
        _tray.SetState(AppState.Recording, DescribeHotkey());
        _maxTimer.Interval = Math.Max(5, cfg.MaxRecordingSeconds) * 1000;
        _maxTimer.Start();
    }

    void StopAndProcess()
    {
        _maxTimer.Stop();
        if (_capture is null)
        {
            _state = AppState.Idle;
            _tray.SetState(AppState.Idle, DescribeHotkey());
            return;
        }
        var cap = _capture;
        _capture = null;
        _state = AppState.Processing;
        _tray.SetState(AppState.Processing, DescribeHotkey());

        var pcm = cap.StopAndRead();
        cap.Dispose();
        var recMs = (long)(DateTime.UtcNow - _recStartUtc).TotalMilliseconds;
        var focus = _focus;

        _ = Task.Run(async () =>
        {
            try
            {
                await ProcessAsync(pcm, recMs, focus);
            }
            catch (Exception ex)
            {
                RecordError(recMs, "pipeline", ex.Message);
            }
            finally
            {
                Ui(() =>
                {
                    _state = AppState.Idle;
                    _tray.SetState(AppState.Idle, DescribeHotkey());
                });
            }
        });
    }

    // ---------- pipeline (background thread) ----------

    async Task ProcessAsync(byte[] pcm, long recMs, FocusSnapshot? focus)
    {
        var cfg = Config.Load();
        var outcome = await DictationPipeline.RunAsync(
            pcm, recMs, "daemon", focus, cfg.DeliveryMode, SetClipboardSync, _shutdown.Token);

        if (!outcome.Ok)
            Ui(() => _tray.Balloon("Dictation failed", outcome.Error ?? "unknown error", true));
        else if (outcome.Fallback)
            Ui(() => _tray.Balloon("Focus changed", "Transcript preserved on the clipboard.", false));
    }

    void RecordError(long recMs, string backend, string message)
    {
        History.Append(new HistoryEntry(
            Id: Guid.NewGuid().ToString("N"),
            StartedAt: DateTime.UtcNow.ToString("o"),
            RecordingMs: recMs,
            Backend: backend,
            Language: null,
            Transcript: "",
            DeliveryMethod: "none",
            Fallback: false,
            FallbackReason: null,
            Error: message,
            TranscribeMs: 0,
            DeliverMs: 0));
        Ui(() => _tray.Balloon("Dictation failed", message, true));
    }

    void SetClipboardSync(string text)
    {
        using var done = new ManualResetEventSlim(false);
        Ui(() =>
        {
            try { Clipboard.SetText(text); }
            finally { done.Set(); }
        });
        done.Wait(3000);
    }

    void Ui(Action a)
    {
        try { _form.BeginInvoke(a); } catch (ObjectDisposedException) { }
    }

    // ---------- misc ----------

    internal string StatusJson()
    {
        var cfg = Config.Load();
        return JsonSerializer.Serialize(new
        {
            state = _state.ToString().ToLowerInvariant(),
            hotkey = DescribeHotkey(),
            delivery_mode = cfg.DeliveryMode,
            writing_mode = cfg.WritingMode,
            language = cfg.Language,
            asr_mode = cfg.AsrMode,
            model = cfg.LocalModel,
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
        if (_state == AppState.Recording)
        {
            try { _capture?.StopAndRead(); } catch { }
            _capture?.Dispose();
            _capture = null;
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
