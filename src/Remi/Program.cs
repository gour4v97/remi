using System.Runtime.InteropServices;
using System.Text;
using NAudio.CoreAudioApi;

namespace Remi;

public static class Program
{
    [DllImport("kernel32.dll")] static extern IntPtr GetConsoleWindow();
    [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    const int SW_HIDE = 0;

    [STAThread]
    public static int Main(string[] args)
    {
        try { Console.OutputEncoding = Encoding.UTF8; } catch { }
        try
        {
            if (args.Length == 0 || (args.Length == 1 && args[0].Equals("start", StringComparison.OrdinalIgnoreCase)))
                return RunDaemon();
            return Cli.Run(args);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("error: " + ex.Message);
            return 1;
        }
    }

    static int RunDaemon()
    {
        using var mutex = new Mutex(true, @"Local\remi-daemon", out var created);
        if (!created)
        {
            Console.Error.WriteLine("remi daemon is already running.");
            return 1;
        }
        var hwnd = GetConsoleWindow();
        if (hwnd != IntPtr.Zero) ShowWindow(hwnd, SW_HIDE);

        Application.SetUnhandledExceptionMode(UnhandledExceptionMode.CatchException);
        Application.ThreadException += (_, e) => LogCrash("ThreadException", e.Exception);
        AppDomain.CurrentDomain.UnhandledException += (_, e) => LogCrash("Unhandled", e.ExceptionObject as Exception);

        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);

        using var app = new DaemonApp();
        app.Run();
        return 0;
    }

    static void LogCrash(string kind, Exception? ex)
    {
        try
        {
            File.AppendAllText(Paths.CrashLogFile, $"{DateTime.Now:yyyy-MM-dd HH:mm:ss} [{kind}] {ex}\n\n");
        }
        catch { /* never crash the crash logger */ }
    }
}

public static class Cli
{
    public static int Run(string[] args)
    {
        var verb = args[0].ToLowerInvariant();
        switch (verb)
        {
            case "toggle":
            case "stop":
            case "status":
                var resp = Ipc.Send(verb);
                if (resp is null) { Console.WriteLine("remi daemon not running (start with: remi)"); return 1; }
                Console.WriteLine(resp);
                return 0;

            case "say":
                if (args.Length < 2) { Console.WriteLine("usage: remi say \"<command>\""); return 1; }
                return SayCmd(string.Join(" ", args[1..]));

            case "say-audio":
                if (args.Length < 2) { Console.WriteLine("usage: remi say-audio <file.wav>"); return 1; }
                return SayAudioCmd(args[1]);

            case "history":
                return HistoryCmd();

            case "doctor":
                return Doctor();

            case "model":
                return ModelCmd(args);

            case "help":
            case "--help":
            case "-h":
                PrintHelp();
                return 0;

            default:
                Console.WriteLine($"unknown command '{args[0]}'\n");
                PrintHelp();
                return 1;
        }
    }

    /// <summary>Full voice pipeline from a WAV file: transcribe → romanize → route → execute.</summary>
    static int SayAudioCmd(string path)
    {
        if (!File.Exists(path)) { Console.WriteLine($"file not found: {path}"); return 1; }
        var pcm = WavFileTo16kMono(path);
        if (pcm is null) { Console.WriteLine("could not decode WAV"); return 1; }
        var cfg = Config.Load();
        Console.WriteLine($"transcribing {pcm.Length / 32000.0:F1}s with {cfg.LocalModel}…");
        var whisper = new Remi.Asr.LocalWhisper();
        var asr = whisper.TranscribeAsync(pcm, cfg.LocalModel, "hinglish", Array.Empty<string>(), CancellationToken.None)
            .GetAwaiter().GetResult();
        var text = Translit.ToRoman(asr.Text).Trim();
        Console.WriteLine($"heard    : {text}");
        var sw = System.Diagnostics.Stopwatch.StartNew();
        var outcome = CommandRouter.RunAsync(text, cfg, CancellationToken.None).GetAwaiter().GetResult();
        sw.Stop();
        Console.WriteLine($"command  : {outcome.Ok}");
        Console.WriteLine($"result   : {outcome.Spoken}");
        Console.WriteLine($"detail   : {outcome.Detail}");
        History.Append(new HistoryEntry(
            Guid.NewGuid().ToString("N"), DateTime.UtcNow.ToString("o"),
            text, outcome.Ok ? outcome.Detail : "unrecognized", outcome.Spoken,
            outcome.Ok, outcome.Ok ? null : outcome.Spoken, sw.ElapsedMilliseconds));
        return outcome.Ok ? 0 : 2;
    }

    /// <summary>Runs a text command through the router (no voice needed) — used for testing and scripting.</summary>
    static int SayCmd(string text)
    {
        var cfg = Config.Load();
        var sw = System.Diagnostics.Stopwatch.StartNew();
        var outcome = CommandRouter.RunAsync(text, cfg, CancellationToken.None).GetAwaiter().GetResult();
        sw.Stop();
        Console.WriteLine($"command : {outcome.Ok}");
        Console.WriteLine($"result  : {outcome.Spoken}");
        Console.WriteLine($"detail  : {outcome.Detail}");
        History.Append(new HistoryEntry(
            Guid.NewGuid().ToString("N"), DateTime.UtcNow.ToString("o"),
            text, outcome.Ok ? outcome.Detail : "unrecognized", outcome.Spoken,
            outcome.Ok, outcome.Ok ? null : outcome.Spoken, sw.ElapsedMilliseconds));
        return outcome.Ok ? 0 : 2;
    }

    static byte[]? WavFileTo16kMono(string path)
    {
        try
        {
            using var reader = new NAudio.Wave.WaveFileReader(path);
            using var resampler = new NAudio.Wave.MediaFoundationResampler(reader, new NAudio.Wave.WaveFormat(16000, 16, 1))
            {
                ResamplerQuality = 60,
            };
            using var outMs = new MemoryStream();
            var buf = new byte[64 * 1024];
            int n;
            while ((n = resampler.Read(buf, 0, buf.Length)) > 0) outMs.Write(buf, 0, n);
            return outMs.ToArray();
        }
        catch
        {
            return null;
        }
    }

    static int HistoryCmd()
    {
        var entries = History.Load(20);
        if (entries.Count == 0) { Console.WriteLine("no history yet"); return 0; }
        foreach (var e in entries.AsEnumerable().Reverse())
        {
            var at = DateTime.TryParse(e.At, out var t) ? t.ToLocalTime().ToString("MM-dd HH:mm:ss") : e.At;
            var what = e.Ok ? e.Detail : $"ERROR: {e.Error}";
            if (what.Length > 70) what = what[..67] + "...";
            Console.WriteLine($"{e.Id[..8]}  {at}  {e.Transcript,-30}  {what}");
        }
        return 0;
    }

    static int Doctor()
    {
        int fails = 0;
        void Check(string name, bool ok, string detail)
        {
            Console.WriteLine($"[{(ok ? "PASS" : "FAIL")}] {name}: {detail}");
            if (!ok) fails++;
        }
        var cfg = Config.Load();
        Check("config", true, $"hotkey={cfg.TriggerHotkey} model={cfg.LocalModel} cdp={cfg.CdpPort}");

        var hk = Hotkey.Parse(cfg.TriggerHotkey);
        Check("hotkey-spec", hk is not null, cfg.TriggerHotkey);

        int devs = 0;
        try { devs = new MMDeviceEnumerator().EnumerateAudioEndPoints(DataFlow.Capture, DeviceState.Active).Count(); }
        catch { }
        Check("microphone", devs > 0, $"{devs} active capture device(s)");

        Check("local-model", ModelManager.IsInstalled(cfg.LocalModel),
            ModelManager.IsInstalled(cfg.LocalModel) ? cfg.LocalModel : $"'{cfg.LocalModel}' missing — run: remi model download {cfg.LocalModel}");

        var exe = Browser.FindBrowserExecutable(cfg.BrowserPath);
        Check("browser", exe is not null, exe ?? "no Edge/Chrome found — set browser_path in config");

        var cdp = Browser.IsCdpUpAsync(cfg.CdpPort).GetAwaiter().GetResult();
        Check("browser-cdp", cdp, cdp
            ? $"debug port {cfg.CdpPort} up"
            : $"down — start browser via tray menu or `remi browser` (auto-launch is {(cfg.AutoLaunchBrowser ? "on" : "off")})");

        return fails == 0 ? 0 : 2;
    }

    static int ModelCmd(string[] args)
    {
        var sub = args.Length > 1 ? args[1].ToLowerInvariant() : "list";
        if (sub == "list")
        {
            Console.WriteLine($"models dir: {Paths.ModelsDir} (borrows voice-trans models when present)");
            foreach (var name in ModelManager.Names)
            {
                var installed = ModelManager.IsInstalled(name);
                var where = File.Exists(Path.Combine(Paths.ModelsDir, $"ggml-{name}.bin")) ? "" : "  (borrowed from voice-trans)";
                Console.WriteLine($"  {name,-22} {(installed ? "installed" : "         ")}  ~{ModelManager.SizeMb(name)} MB{where}");
            }
            return 0;
        }
        if (sub == "download")
        {
            var name = args.Length > 2 ? args[2] : "";
            if (!ModelManager.IsValid(name)) { Console.WriteLine($"unknown model '{name}'"); return 1; }
            if (ModelManager.IsInstalled(name)) { Console.WriteLine($"{name} already installed"); return 0; }
            Console.WriteLine($"downloading ggml-{name}.bin (~{ModelManager.SizeMb(name)} MB)…");
            try
            {
                ModelManager.DownloadAsync(name,
                    (done, total) => Console.Write($"\r  {(total > 0 ? (int)(done * 100 / total) : 0),3}%  {done / 1048576.0:F0} MB"),
                    CancellationToken.None).GetAwaiter().GetResult();
                Console.WriteLine($"\ninstalled: {ModelManager.PathFor(name)}");
                return 0;
            }
            catch (Exception ex) { Console.WriteLine($"\ndownload failed: {ex.Message}"); return 1; }
        }
        if (ModelManager.IsValid(sub))
        {
            if (!ModelManager.IsInstalled(sub)) { Console.WriteLine($"'{sub}' not installed — run: remi model download {sub}"); return 1; }
            var cfg = Config.Load(); cfg.LocalModel = sub; Config.Save(cfg);
            Console.WriteLine($"local_model = {sub}");
            return 0;
        }
        Console.WriteLine("usage: remi model list | model download <name> | <name>");
        return 1;
    }

    static void PrintHelp()
    {
        Console.WriteLine("""
            remi — voice-controlled browser for Windows (Hindi / English / Hinglish)

              remi                    run the daemon (tray icon + trigger hotkey)
              remi toggle             start/stop listening in the running daemon
              remi status             daemon status (JSON)
              remi stop               quit the daemon
              remi say "<command>"    run a text command directly (testing/scripting)
              remi history            recent commands
              remi doctor             readiness checks
              remi model list | download <name> | <name>

            default trigger hotkey: ctrl+alt+b (press, speak, press again)

            examples (speak these):
              open youtube            youtube lofi beats
              open gmail              search nvidia rtx 4050 price
              scroll down             scroll top
              new tab                 close tab              next tab
              refresh                 go back                read title
              play                    pause                  click subscribe
            """);
    }
}
