using NAudio.CoreAudioApi;

namespace VoiceTrans;

/// <summary>voisu-style readiness checks with PASS/WARN/FAIL outcomes.</summary>
public static class Doctor
{
    public static (int Fails, int Warns, string Report) RunAll()
    {
        var lines = new List<string>();
        int fails = 0, warns = 0;
        void Check(string name, string status, string detail)
        {
            lines.Add($"[{status}] {name}: {detail}");
            if (status == "FAIL") fails++;
            else if (status == "WARN") warns++;
        }

        try
        {
            var cfg = Config.Load();
            Check("config", "PASS",
                $"delivery={cfg.DeliveryMode} writing={cfg.WritingMode} language={cfg.Language} asr={cfg.AsrMode}");

            var hk = Hotkey.Parse(cfg.TriggerHotkey);
            Check("hotkey-spec", hk is null ? "FAIL" : "PASS", cfg.TriggerHotkey + (hk is null ? " is not a valid combo" : ""));

            int devs = 0;
            try
            {
                devs = new MMDeviceEnumerator()
                    .EnumerateAudioEndPoints(DataFlow.Capture, DeviceState.Active).Count();
            }
            catch { /* count stays 0 */ }
            Check("microphone", devs > 0 ? "PASS" : "FAIL", $"{devs} active capture device(s)");

            if (ModelManager.IsInstalled(cfg.LocalModel))
            {
                Check("local-model", "PASS",
                    cfg.LocalModel + (ModelManager.VerifySha(cfg.LocalModel) ? " (sha256 ok)" : " (sha256 sidecar missing)"));
            }
            else
            {
                Check("local-model", cfg.AsrMode == "local" ? "FAIL" : "WARN",
                    $"'{cfg.LocalModel}' not installed — run: voice-trans model download {cfg.LocalModel}");
            }

            if (cfg.GroqEnabled || cfg.AsrMode == "cloud")
            {
                var hasKey = KeyStore.Get("groq") is not null;
                Check("groq-key", hasKey ? "PASS" : "FAIL", hasKey ? "key present" : "cloud enabled but no key — run: voice-trans auth set groq");
            }

            var dict = PronunciationDictionary.Load(Paths.DictionaryFile);
            Check("dictionary", dict.Count > 0 ? "PASS" : "WARN", $"{dict.Count} term(s) in {Paths.DictionaryFile}");

            var (clipOk, clipDetail) = ClipboardRoundTrip();
            Check("clipboard", clipOk ? "PASS" : "FAIL", clipOk ? "round-trip ok" : clipDetail);

            var status = Ipc.Send("status");
            if (status is not null) Check("daemon", "PASS", "running — " + status);
            else Check("daemon", "WARN", "not running (start with: voice-trans)");
        }
        catch (Exception ex)
        {
            Check("config", "FAIL", ex.Message);
        }

        lines.Add($"{fails} failure(s), {warns} warning(s)");
        return (fails, warns, string.Join(Environment.NewLine, lines));
    }

    static (bool Ok, string Detail) ClipboardRoundTrip()
    {
        bool ok = false;
        string detail = "test failed or timed out";
        var t = new Thread(() =>
        {
            try
            {
                var old = Clipboard.ContainsText() ? Clipboard.GetText() : null;
                Clipboard.SetText("voisu-doctor-probe");
                ok = Clipboard.GetText() == "voisu-doctor-probe";
                if (old is not null) Clipboard.SetText(old);
                detail = ok ? "round-trip ok" : "read-back mismatch";
            }
            catch (Exception ex) { detail = ex.Message; }
        });
        t.SetApartmentState(ApartmentState.STA);
        t.Start();
        t.Join(4000);
        return (ok, detail);
    }
}
