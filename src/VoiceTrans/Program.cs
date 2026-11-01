using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32;

namespace VoiceTrans;

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

    static void LogCrash(string kind, Exception? ex)
    {
        try
        {
            File.AppendAllText(Path.Combine(Paths.AppDataLocal, "crash.log"),
                $"{DateTime.Now:yyyy-MM-dd HH:mm:ss} [{kind}] {ex}\n\n");
        }
        catch { /* never crash the crash logger */ }
    }

    static int RunDaemon()
    {
        using var mutex = new Mutex(true, @"Local\voice-trans-daemon", out var created);
        if (!created)
        {
            Console.Error.WriteLine("voice-trans daemon is already running.");
            return 1;
        }
        var hwnd = GetConsoleWindow();
        if (hwnd != IntPtr.Zero) ShowWindow(hwnd, SW_HIDE);

        // a hidden tray app must never die silently — capture everything to crash.log
        Application.SetUnhandledExceptionMode(UnhandledExceptionMode.CatchException);
        Application.ThreadException += (_, e) => LogCrash("ThreadException", e.Exception);
        AppDomain.CurrentDomain.UnhandledException += (_, e) => LogCrash("Unhandled", e.ExceptionObject as Exception);

        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);

        if (!File.Exists(Paths.DictionaryFile))
        {
            File.WriteAllText(Paths.DictionaryFile,
                """
                # voice-trans pronunciation dictionary — one term per line.
                # Lines starting with '#' are comments ('C#' survives — comment must start the line or follow a space).
                # Use it for names and jargon the recogniser gets wrong, Latin or Devanagari:
                Namaste
                Kubernetes
                """);
        }

        using var app = new DaemonApp();
        app.Run();
        return 0;
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
                if (resp is null)
                {
                    Console.WriteLine("daemon not running (start with: voice-trans)");
                    return 1;
                }
                Console.WriteLine(resp);
                return 0;

            case "doctor":
                var (fails, _, report) = Doctor.RunAll();
                Console.WriteLine(report);
                return fails == 0 ? 0 : 2;

            case "history":
                return HistoryCmd(args);

            case "export":
                if (args.Length < 2) { Console.WriteLine("usage: voice-trans export <id>"); return 1; }
                var json = History.Export(args[1]);
                if (json is null) { Console.WriteLine($"no history record matches '{args[1]}'"); return 1; }
                Console.WriteLine(json);
                return 0;

            case "delivery":
                return SetValidated("delivery_mode", Arg(args),
                    v => v is "type" or "clipboard" or "guarded",
                    (c, v) => c.DeliveryMode = v,
                    "type | clipboard | guarded");

            case "writing":
                return SetValidated("writing_mode", Arg(args),
                    v => v is "smart" or "literal",
                    (c, v) => c.WritingMode = v,
                    "smart | literal");

            case "language":
                return SetValidated("language", Arg(args),
                    v => v is "auto" or "en" or "hi" or "hinglish",
                    (c, v) => c.Language = v,
                    "auto | en | hi | hinglish");

            case "asr":
                return SetValidated("asr_mode", Arg(args),
                    v => v is "local" or "cloud",
                    (c, v) => c.AsrMode = v,
                    "local | cloud");

            case "model":
                return ModelCmd(args);

            case "auth":
                return AuthCmd(args);

            case "autostart":
                return AutostartCmd(Arg(args));

            case "replay":
                if (args.Length < 2) { Console.WriteLine("usage: voice-trans replay <file.wav>"); return 1; }
                return ReplayCmd(args[1]);

            case "convert":
                if (args.Length < 3) { Console.WriteLine("usage: voice-trans convert <in.wav> <out.wav>"); return 1; }
                var cpcm = WavFileTo16kMono(args[1]);
                if (cpcm is null) { Console.WriteLine("could not decode input WAV"); return 1; }
                File.WriteAllBytes(args[2], Wav.ToWav(cpcm));
                Console.WriteLine($"wrote {args[2]} ({cpcm.Length / 32000.0:F1}s, canonical 16 kHz mono s16)");
                return 0;

            case "translit":
                if (args.Length < 2) { Console.WriteLine("usage: voice-trans translit <devanagari text>"); return 1; }
                Console.WriteLine(Translit.ToRoman(string.Join(" ", args[1..])));
                return 0;

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

    static string Arg(string[] args) => args.Length > 1 ? args[1].ToLowerInvariant() : "";

    static int SetValidated(string key, string value, Func<string, bool> valid, Action<Config, string> apply, string usage)
    {
        if (!valid(value))
        {
            Console.WriteLine($"{key}: got '{value}', expected: {usage}");
            return 1;
        }
        var cfg = Config.Load();
        apply(cfg, value);
        Config.Save(cfg);
        Console.WriteLine($"{key} = {value}  (picked up at the next dictation)");
        return 0;
    }

    static int ReplayCmd(string path)
    {
        if (!File.Exists(path)) { Console.WriteLine($"file not found: {path}"); return 1; }
        var pcm = WavFileTo16kMono(path);
        if (pcm is null) { Console.WriteLine("could not decode WAV (16/24/32-bit PCM or float, any rate)"); return 1; }

        Console.WriteLine($"replaying {path} ({pcm.Length / 32000.0:F1}s of audio)…");
        var cfg = Config.Load();
        void ClipboardSetter(string text) => SetTextSta(text);
        var outcome = DictationPipeline.RunAsync(
            pcm, (long)(pcm.Length / 32.0), "replay", null, cfg.DeliveryMode, ClipboardSetter, CancellationToken.None)
            .GetAwaiter().GetResult();

        if (!outcome.Ok)
        {
            Console.WriteLine($"replay failed: {outcome.Error}");
            return 2;
        }
        Console.WriteLine($"transcript [{outcome.Entry.Backend}, {outcome.Entry.Language}]: {outcome.Transcript}");
        Console.WriteLine($"delivered via {outcome.DeliveryMethod}" +
            (outcome.Fallback ? $" (fallback: {outcome.FallbackReason})" : "") +
            $" — transcribed in {outcome.Entry.TranscribeMs} ms");
        return 0;
    }

    /// <summary>Clipboard writes need OLE STA; async pipeline continuations may be on a threadpool thread.</summary>
    static void SetTextSta(string text)
    {
        if (Thread.CurrentThread.GetApartmentState() == ApartmentState.STA)
        {
            Clipboard.SetText(text);
            return;
        }
        Exception? err = null;
        var t = new Thread(() =>
        {
            try { Clipboard.SetText(text); }
            catch (Exception ex) { err = ex; }
        });
        t.SetApartmentState(ApartmentState.STA);
        t.Start();
        t.Join(4000);
        if (err is not null) throw err;
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

    static int HistoryCmd(string[] args)
    {
        int? last = 20;
        bool json = false;
        foreach (var a in args.Skip(1))
        {
            if (a == "--json") json = true;
            else if (int.TryParse(a, out var n)) last = Math.Clamp(n, 1, 10_000);
        }
        var entries = History.Load(last);
        if (json)
        {
            var opts = new System.Text.Json.JsonSerializerOptions
            {
                PropertyNamingPolicy = System.Text.Json.JsonNamingPolicy.CamelCase,
                WriteIndented = true,
                DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull,
            };
            Console.WriteLine(System.Text.Json.JsonSerializer.Serialize(entries, opts));
            return 0;
        }
        if (entries.Count == 0) { Console.WriteLine("no history yet"); return 0; }
        foreach (var e in entries.AsEnumerable().Reverse())
        {
            var at = DateTime.TryParse(e.StartedAt, out var t) ? t.ToLocalTime().ToString("MM-dd HH:mm:ss") : e.StartedAt;
            var transcript = e.Error is not null ? $"ERROR: {e.Error}" : e.Transcript.Replace("\n", " ");
            if (transcript.Length > 80) transcript = transcript[..77] + "...";
            Console.WriteLine($"{e.Id[..8]}  {at}  {e.RecordingMs / 1000.0:F1}s  {e.Backend,-22} {e.DeliveryMethod,-9}  {transcript}");
        }
        return 0;
    }

    static int ModelCmd(string[] args)
    {
        var sub = args.Length > 1 ? args[1].ToLowerInvariant() : "list";
        if (sub == "list")
        {
            Console.WriteLine($"models dir: {Paths.ModelsDir}");
            foreach (var name in ModelManager.Names)
            {
                var installed = ModelManager.IsInstalled(name);
                var en = name.EndsWith(".en") ? "  (english-only)" : "";
                Console.WriteLine($"  {name,-16} {(installed ? "installed" : "         ")}  ~{ModelManager.SizeMb(name)} MB{en}");
            }
            Console.WriteLine("\nmultilingual models handle Hindi and Hinglish; .en models are English-only.");
            return 0;
        }
        if (sub == "download")
        {
            var name = args.Length > 2 ? args[2] : "";
            if (!ModelManager.IsValid(name))
            {
                Console.WriteLine($"unknown model '{name}'. available: {string.Join(", ", ModelManager.Names)}");
                return 1;
            }
            if (ModelManager.IsInstalled(name))
            {
                Console.WriteLine($"{name} already installed" + (ModelManager.VerifySha(name) ? " (sha256 ok)" : " (sha256 MISMATCH — consider re-downloading)"));
                return 0;
            }
            Console.WriteLine($"downloading ggml-{name}.bin (~{ModelManager.SizeMb(name)} MB) from huggingface.co/ggerganov/whisper.cpp …");
            try
            {
                ModelManager.DownloadAsync(name,
                    (done, total) =>
                    {
                        if (total > 0)
                        {
                            var pct = (int)(done * 100 / total);
                            Console.Write($"\r  {pct,3}%  {done / 1048576.0:F0} / {total / 1048576.0:F0} MB");
                        }
                        else Console.Write($"\r  {done / 1048576.0:F0} MB");
                    },
                    CancellationToken.None).GetAwaiter().GetResult();
                Console.WriteLine($"\ninstalled: {ModelManager.PathFor(name)}");
                return 0;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"\ndownload failed: {ex.Message}");
                return 1;
            }
        }
        if (sub == "remove")
        {
            var name = args.Length > 2 ? args[2] : "";
            if (!ModelManager.IsInstalled(name)) { Console.WriteLine($"'{name}' is not installed"); return 1; }
            ModelManager.Remove(name);
            Console.WriteLine($"removed {name}");
            return 0;
        }
        // `voice-trans model <name>` — make an installed model the active one
        if (ModelManager.IsValid(sub))
        {
            if (!ModelManager.IsInstalled(sub))
            {
                Console.WriteLine($"'{sub}' is not installed — run: voice-trans model download {sub}");
                return 1;
            }
            var cfg = Config.Load();
            cfg.LocalModel = sub;
            Config.Save(cfg);
            Console.WriteLine($"local_model = {sub}  (picked up at the next dictation)");
            return 0;
        }
        Console.WriteLine("usage: voice-trans model list | download <name> | remove <name> | <name>");
        return 1;
    }

    static int AuthCmd(string[] args)
    {
        var sub = args.Length > 1 ? args[1].ToLowerInvariant() : "status";
        var provider = args.Length > 2 ? args[2].ToLowerInvariant() : "groq";
        if (sub == "set")
        {
            Console.Write($"Enter {provider} API key (input hidden): ");
            var sb = new StringBuilder();
            while (true)
            {
                var k = Console.ReadKey(intercept: true);
                if (k.Key == ConsoleKey.Enter) break;
                if (k.Key == ConsoleKey.Backspace && sb.Length > 0) sb.Length--;
                else if (!char.IsControl(k.KeyChar)) sb.Append(k.KeyChar);
            }
            Console.WriteLine();
            if (sb.Length == 0) { Console.WriteLine("empty key, not stored"); return 1; }
            KeyStore.Set(provider, sb.ToString());
            Console.WriteLine($"{provider} key stored (DPAPI-encrypted, current Windows user only)");
            return 0;
        }
        if (sub == "clear") { KeyStore.Clear(provider); Console.WriteLine($"{provider} key cleared"); return 0; }
        var has = KeyStore.Get(provider) is not null;
        Console.WriteLine($"{provider}: {(has ? "key present" : "no key")}");
        return has ? 0 : 1;
    }

    static int AutostartCmd(string value)
    {
        const string runKey = @"Software\Microsoft\Windows\CurrentVersion\Run";
        const string valueName = "voice-trans";
        switch (value)
        {
            case "on":
                using (var k = Registry.CurrentUser.CreateSubKey(runKey))
                    k.SetValue(valueName, $"\"{Environment.ProcessPath}\"");
                Console.WriteLine("autostart enabled (HKCU Run)");
                return 0;
            case "off":
                using (var k = Registry.CurrentUser.OpenSubKey(runKey, writable: true))
                    k?.DeleteValue(valueName, throwOnMissingValue: false);
                Console.WriteLine("autostart disabled");
                return 0;
            case "status":
            case "":
                var cur = Registry.CurrentUser.OpenSubKey(runKey)?.GetValue(valueName) as string;
                Console.WriteLine(cur is null ? "autostart is off" : $"autostart is on: {cur}");
                return 0;
            default:
                Console.WriteLine("usage: voice-trans autostart on | off | status");
                return 1;
        }
    }

    static void PrintHelp()
    {
        Console.WriteLine("""
            voice-trans — push-to-talk dictation for Windows (Hindi / English / Hinglish)

              voice-trans                     run the daemon (tray icon + trigger hotkey)
              voice-trans toggle              start/stop recording in the running daemon
              voice-trans status              daemon status
              voice-trans stop                quit the daemon
              voice-trans doctor              readiness checks
              voice-trans history [N] [--json]
              voice-trans export <id>
              voice-trans delivery <type|clipboard|guarded>
              voice-trans writing <smart|literal>
              voice-trans language <auto|en|hi|hinglish>
              voice-trans asr <local|cloud>
              voice-trans model list | download <name> | remove <name> | <name>
              voice-trans auth set groq | auth clear groq | auth status
              voice-trans autostart <on|off|status>
              voice-trans translit <text>     Devanagari → Roman (debug helper)

            default trigger hotkey: ctrl+alt+space (press once to start, again to stop)
            """);
    }
}
