package suite;

import java.util.Comparator;
import java.util.List;
import java.util.regex.Pattern;

/** Voice Trans (Java port) — hotkey → record → whisper → type/clipboard into the focused app. */
public final class VoiceTransApp {
    public static final String APP = "voice-trans-java";
    public static final String HOTKEY_DEFAULT = "ctrl+alt+space";

    private final Config cfg;
    private final Tray.Holder tray;
    private Capture capture;
    private final Object gate = new Object();
    private volatile boolean busy;

    public VoiceTransApp(Config cfg) {
        this.cfg = cfg;
        String hotkey = cfg.get("hotkey", HOTKEY_DEFAULT);
        tray = Tray.create(APP, "V", Tray.VIOLET, hotkey + " to dictate");
        tray.add("Toggle dictation", this::toggle);
        tray.addSeparator();
        for (String mode : new String[]{"type", "clipboard", "guarded"}) {
            String m = mode;
            tray.add("Delivery: " + mode + (cfg.get("delivery_mode", "type").equals(m) ? "  ✓" : ""),
                    () -> {
                        cfg.set("delivery_mode", m);
                        cfg.save();
                    });
        }
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
            tray.setState("thinking", "transcribing...");
            Thread.ofVirtual().start(() -> {
                byte[] pcm = c.stopAndRead();
                process(pcm);
                busy = false;
                tray.setState("idle", cfg.get("hotkey", HOTKEY_DEFAULT) + " to dictate");
            });
        }
    }

    void process(byte[] pcm) {
        long started = System.currentTimeMillis();
        try {
            if (pcm.length < 9600) throw new IllegalStateException("Recording too short.");
            if (Asr.peakAmplitude(pcm) <= 32) throw new IllegalStateException("Silent recording — is the right mic selected?");
            String text = Asr.transcribePcm(pcm, cfg, cfg.get("language", "hinglish"));
            if ("hinglish".equals(cfg.get("language", "hinglish"))) text = Translit.toRoman(text);
            text = Translit.smartWriting(text, cfg.get("writing_mode", "smart"));
            text = applyDictionary(text);
            if (text.isBlank()) throw new IllegalStateException("Empty transcript.");

            String mode = cfg.get("delivery_mode", "type");
            Win.setClipboard(text); // recoverability guarantee first, like the .NET suite
            if (!"clipboard".equals(mode)) Win.typeText(text);
            History.append(cfg, text, "clipboard".equals(mode) ? "clipboard" : "type", true, null,
                    System.currentTimeMillis() - started);
        } catch (Exception ex) {
            History.append(cfg, "", "error", false, ex.getMessage(), System.currentTimeMillis() - started);
            tray.notify(APP + " failed", ex.getMessage(), true);
        }
    }

    /** Reuses the .NET suite's dictionary file (same format). */
    List<String> loadDictionary() {
        List<String> terms = new java.util.ArrayList<>();
        java.nio.file.Path p = java.nio.file.Path.of(System.getenv("APPDATA"), "voice-trans", "dictionary.txt");
        if (!java.nio.file.Files.exists(p)) return terms;
        try {
            for (String line : java.nio.file.Files.readAllLines(p)) {
                String s = line.strip();
                if (s.isEmpty() || s.startsWith("#")) continue;
                int idx = s.indexOf(" #");
                if (idx >= 0) s = s.substring(0, idx).strip();
                if (!s.isEmpty()) terms.add(s);
            }
        } catch (Exception ignored) {
        }
        terms.sort(Comparator.comparingInt(String::length).reversed());
        return terms;
    }

    String applyDictionary(String text) {
        for (String term : loadDictionary()) {
            Pattern p = Pattern.compile("(?<![\\w\\u0900-\\u097F])"
                    + Pattern.quote(term) + "(?![\\w\\u0900-\\u097F])", Pattern.CASE_INSENSITIVE);
            text = p.matcher(text).replaceAll(java.util.regex.Matcher.quoteReplacement(term));
        }
        return text;
    }

    public void run() throws Exception {
        Win.registerHotkey(cfg.get("hotkey", HOTKEY_DEFAULT), 1, this::toggle);
        tray.display();
        System.out.println("Voice Trans (Java) — hotkey: " + cfg.get("hotkey", HOTKEY_DEFAULT));
        System.out.println("NOTE: stop the .NET voice-trans daemon first (same hotkey).");
        Thread.currentThread().join();
    }
}
