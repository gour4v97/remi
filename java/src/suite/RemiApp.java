package suite;

/** Remi (Java port) — hotkey → record → whisper → command grammar → CDP browser action → TTS. */
public final class RemiApp {
    public static final String APP = "remi-java";
    public static final String HOTKEY_DEFAULT = "ctrl+alt+b";

    private final Config cfg;
    private final Tray.Holder tray;
    private Capture capture;
    private final Object gate = new Object();
    private volatile boolean busy;

    public RemiApp(Config cfg) {
        this.cfg = cfg;
        String hotkey = cfg.get("hotkey", HOTKEY_DEFAULT);
        tray = Tray.create(APP, "R", Tray.VIOLET, hotkey + " to speak a command");
        tray.add("Speak a command", this::toggle);
        tray.add("Start browser (voice control)", this::startBrowser);
        tray.addSeparator();
        tray.add("Voice feedback" + (cfg.getBool("voice_feedback", true) ? "  ✓" : ""), () -> {
            cfg.set("voice_feedback", String.valueOf(!cfg.getBool("voice_feedback", true)));
            cfg.save();
        });
    }

    void startBrowser() {
        String exe = Cdp.findBrowserExe();
        if (exe == null) {
            tray.notify(APP, "No Edge/Chrome found", true);
            return;
        }
        String profile = "default".equals(cfg.get("browser_profile", "remi"))
                ? null : Config.LOCALAPPDATA.resolve("browser-profile").toString();
        Thread.ofVirtual().start(() -> {
            boolean ok = Cdp.launch(exe, cfg.getInt("cdp_port", 9222), profile, 8);
            tray.notify(APP, ok ? "Browser started with voice control." : "Debug port did not respond.", !ok);
        });
    }

    void toggle() {
        synchronized (gate) {
            if (busy) return;
            if (capture == null) {
                try {
                    Capture c = new Capture();
                    c.start();
                    capture = c;
                    tray.setState("recording", cfg.get("hotkey", HOTKEY_DEFAULT) + " to stop");
                } catch (Exception ex) {
                    tray.notify(APP, "Microphone: " + ex.getMessage(), true);
                }
                return;
            }
            Capture c = capture;
            capture = null;
            busy = true;
            tray.setState("thinking", "thinking...");
            Thread.ofVirtual().start(() -> {
                byte[] pcm = c.stopAndRead();
                process(pcm);
                busy = false;
                tray.setState("idle", cfg.get("hotkey", HOTKEY_DEFAULT) + " to speak");
            });
        }
    }

    void process(byte[] pcm) {
        long started = System.currentTimeMillis();
        try {
            if (pcm.length < 9600) throw new IllegalStateException("Recording too short.");
            if (Asr.peakAmplitude(pcm) <= 32) throw new IllegalStateException("Silent recording — is the right mic selected?");
            String text = Asr.transcribePcm(pcm, cfg, "hinglish");
            text = Translit.toRoman(text).trim();
            if (text.isEmpty()) throw new IllegalStateException("Empty transcript.");
            Router.Outcome outcome = Router.run(text, cfg);
            History.append(cfg, text, outcome.detail(), outcome.ok(), outcome.ok() ? null : outcome.spoken(),
                    System.currentTimeMillis() - started);
            Tts.say(outcome.ok() ? outcome.spoken() : "Sorry. " + outcome.spoken(),
                    cfg.getBool("voice_feedback", true));
            if (!outcome.ok()) tray.notify("Remi (Java)", outcome.spoken(), true);
        } catch (Exception ex) {
            History.append(cfg, "", "error", false, ex.getMessage(), System.currentTimeMillis() - started);
            Tts.say("Sorry, that failed.", cfg.getBool("voice_feedback", true));
            tray.notify(APP + " failed", ex.getMessage(), true);
        }
    }

    public void run() throws Exception {
        Win.registerHotkey(cfg.get("hotkey", HOTKEY_DEFAULT), 1, this::toggle);
        tray.display();
        System.out.println("Remi (Java) — hotkey: " + cfg.get("hotkey", HOTKEY_DEFAULT));
        System.out.println("NOTE: stop the .NET remi daemon first (same hotkey).");
        Thread.currentThread().join();
    }
}
