using System.Diagnostics;
using System.Drawing.Drawing2D;

namespace Remi;

/// <summary>Tray icon (idle blue / listening red / thinking amber) + menu + balloons.</summary>
public sealed class TrayUi : IDisposable
{
    public Action? ToggleRequested;
    public Action? BrowserLaunchRequested;

    readonly DaemonApp _app;
    readonly NotifyIcon _icon;
    readonly Dictionary<string, Icon> _icons = new();

    public TrayUi(DaemonApp app)
    {
        _app = app;
        _icon = new NotifyIcon
        {
            Icon = IconFor("idle"),
            Text = "remi",
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
            DaemonApp.AppState.Listening => "listening",
            DaemonApp.AppState.Thinking => "thinking",
            _ => "idle",
        };
        _icon.Icon = IconFor(key);
        _icon.Text = state switch
        {
            DaemonApp.AppState.Listening => $"remi — listening ({hotkey} to stop)",
            DaemonApp.AppState.Thinking => "remi — thinking…",
            _ => $"remi — idle ({hotkey} to speak a command)",
        };
    }

    public void Balloon(string title, string message, bool error) =>
        _icon.ShowBalloonTip(4000, title, message, error ? ToolTipIcon.Error : ToolTipIcon.Info);

    void BuildMenu(ContextMenuStrip menu)
    {
        menu.Items.Clear();
        menu.Items.Add("Speak a command", null, (_, _) => ToggleRequested?.Invoke());
        menu.Items.Add("Start browser (voice control)", null, (_, _) => BrowserLaunchRequested?.Invoke());
        menu.Items.Add(new ToolStripSeparator());
        var cfg = _app.CurrentConfig();
        var vf = new ToolStripMenuItem("Voice feedback") { Checked = cfg.VoiceFeedback };
        vf.Click += (_, _) => _app.ApplyModeChange(c => c.VoiceFeedback = !c.VoiceFeedback);
        menu.Items.Add(vf);
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add("Open history folder", null, (_, _) =>
        {
            try { System.Diagnostics.Process.Start(new ProcessStartInfo { FileName = Paths.AppDataLocal, UseShellExecute = true }); }
            catch { }
        });
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add("Quit", null, (_, _) => _app.QuitFromTray());
    }

    Icon IconFor(string key)
    {
        if (_icons.TryGetValue(key, out var cached)) return cached;
        var color = key switch
        {
            "listening" => Color.FromArgb(0xE5, 0x48, 0x4D),   // red
            "thinking" => Color.FromArgb(0xF5, 0xA6, 0x23),    // amber
            _ => Color.FromArgb(0x7C, 0x5C, 0xD9),             // violet
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
        using var font = new Font("Segoe UI", 13f, FontStyle.Bold, GraphicsUnit.Pixel);
        var size = g.MeasureString("R", font);
        g.DrawString("R", font, white, (32 - size.Width) / 2f, (32 - size.Height) / 2f + 1);
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
