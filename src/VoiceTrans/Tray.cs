using System.Diagnostics;
using System.Drawing.Drawing2D;

namespace VoiceTrans;

/// <summary>Tray icon + context menu (idle blue / recording red / processing amber) and balloon notifications.</summary>
public sealed class TrayUi : IDisposable
{
    public Action? ToggleRequested;

    readonly DaemonApp _app;
    readonly NotifyIcon _icon;
    readonly Dictionary<string, Icon> _icons = new();

    public TrayUi(DaemonApp app)
    {
        _app = app;
        _icon = new NotifyIcon
        {
            Icon = IconFor("idle"),
            Text = "voice-trans",
            Visible = true,
        };
        var menu = new ContextMenuStrip();
        BuildMenu(menu);
        menu.Opening += (_, e) => { BuildMenu(menu); e.Cancel = false; };
        _icon.ContextMenuStrip = menu;
        _icon.DoubleClick += (_, _) => ToggleRequested?.Invoke();
    }

    public void SetState(DaemonApp.AppState state, string hotkey)
    {
        var key = state switch
        {
            DaemonApp.AppState.Recording => "recording",
            DaemonApp.AppState.Processing => "processing",
            _ => "idle",
        };
        _icon.Icon = IconFor(key);
        _icon.Text = state switch
        {
            DaemonApp.AppState.Recording => $"voice-trans — recording ({hotkey} to stop)",
            DaemonApp.AppState.Processing => "voice-trans — transcribing…",
            _ => $"voice-trans — idle ({hotkey} to dictate)",
        };
    }

    public void Balloon(string title, string message, bool error) =>
        _icon.ShowBalloonTip(4000, title, message, error ? ToolTipIcon.Error : ToolTipIcon.Info);

    void BuildMenu(ContextMenuStrip menu)
    {
        menu.Items.Clear();
        menu.Items.Add("Toggle recording", null, (_, _) => ToggleRequested?.Invoke());
        menu.Items.Add(new ToolStripSeparator());

        var cfg = _app.CurrentConfig();
        menu.Items.Add(Radio($"Delivery: type", cfg.DeliveryMode == "type", () => Set(c => c.DeliveryMode = "type")));
        menu.Items.Add(Radio($"Delivery: clipboard", cfg.DeliveryMode == "clipboard", () => Set(c => c.DeliveryMode = "clipboard")));
        menu.Items.Add(Radio($"Delivery: guarded", cfg.DeliveryMode == "guarded", () => Set(c => c.DeliveryMode = "guarded")));
        menu.Items.Add(Radio("Writing: smart", cfg.WritingMode == "smart", () => Set(c => c.WritingMode = "smart")));
        menu.Items.Add(Radio("Writing: literal", cfg.WritingMode == "literal", () => Set(c => c.WritingMode = "literal")));
        menu.Items.Add(Radio("Language: hinglish", cfg.Language == "hinglish", () => Set(c => c.Language = "hinglish")));
        menu.Items.Add(Radio("Language: hindi", cfg.Language == "hi", () => Set(c => c.Language = "hi")));
        menu.Items.Add(Radio("Language: english", cfg.Language == "en", () => Set(c => c.Language = "en")));
        menu.Items.Add(Radio("Language: auto", cfg.Language == "auto", () => Set(c => c.Language = "auto")));
        menu.Items.Add(Radio("ASR: local", cfg.AsrMode == "local", () => Set(c => c.AsrMode = "local")));
        menu.Items.Add(Radio("ASR: cloud (Groq)", cfg.AsrMode == "cloud", () => Set(c => c.AsrMode = "cloud")));
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add("Open history folder", null, (_, _) => Shell(Paths.AppDataLocal));
        menu.Items.Add("Open config file", null, (_, _) => Shell("/select,\"" + Paths.ConfigFile + "\""));
        menu.Items.Add("Copy diagnostics", null, (_, _) => CopyDiagnostics());
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add("Quit", null, (_, _) => _app.QuitFromTray());
    }

    void Set(Action<Config> mutate) => _app.ApplyModeChange(mutate);

    static ToolStripMenuItem Radio(string text, bool @checked, Action onClick)
    {
        var item = new ToolStripMenuItem(text) { Checked = @checked };
        item.Click += (_, _) => onClick();
        return item;
    }

    void CopyDiagnostics()
    {
        try
        {
            var (fails, _, report) = Doctor.RunAll();
            Clipboard.SetText(report);
            Balloon("voice-trans diagnostics", $"{fails} failure(s) — report copied to clipboard", fails > 0);
        }
        catch (Exception ex)
        {
            Balloon("voice-trans diagnostics", ex.Message, true);
        }
    }

    static void Shell(string argument)
    {
        try
        {
            if (!argument.StartsWith('/'))
                System.Diagnostics.Process.Start(new ProcessStartInfo { FileName = argument, UseShellExecute = true });
            else
                System.Diagnostics.Process.Start(new ProcessStartInfo { FileName = "explorer.exe", Arguments = argument });
        }
        catch { /* best effort */ }
    }

    Icon IconFor(string key)
    {
        if (_icons.TryGetValue(key, out var cached)) return cached;
        var color = key switch
        {
            "recording" => Color.FromArgb(0xE5, 0x48, 0x4D),   // red
            "processing" => Color.FromArgb(0xF5, 0xA6, 0x23),  // amber
            _ => Color.FromArgb(0x4A, 0x90, 0xD9),             // blue
        };
        var icon = MakeIcon(color);
        _icons[key] = icon;
        return icon;
    }

    static Icon MakeIcon(Color color)
    {
        using var bmp = new Bitmap(32, 32);
        using var g = Graphics.FromImage(bmp);
        g.SmoothingMode = SmoothingMode.AntiAlias;
        using var brush = new SolidBrush(color);
        g.FillEllipse(brush, 2, 2, 28, 28);
        using var white = new SolidBrush(Color.White);
        using var font = new Font("Segoe UI", 14f, FontStyle.Bold, GraphicsUnit.Pixel);
        var size = g.MeasureString("V", font);
        g.DrawString("V", font, white, (32 - size.Width) / 2f, (32 - size.Height) / 2f + 1);
        return Icon.FromHandle(bmp.GetHicon());
    }

    public void Dispose()
    {
        _icon.Visible = false;
        _icon.Dispose();
        foreach (var icon in _icons.Values) icon.Dispose();
        _icons.Clear();
    }
}
