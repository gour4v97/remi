package suite;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Properties;

/** Per-app config as Properties under %APPDATA%\remi-suite-java. */
public final class Config {
    public static final Path APPDATA =
            Path.of(System.getenv("APPDATA"), "remi-suite-java");
    public static final Path LOCALAPPDATA =
            Path.of(System.getenv("LOCALAPPDATA"), "remi-suite-java");
    public static final Path VT_MODELS =
            Path.of(System.getenv("LOCALAPPDATA"), "voice-trans", "models"); // borrow ggml models

    private final String app;
    private final Properties props = new Properties();

    public Config(String app) {
        this.app = app;
        defaults();
        Path p = path();
        if (Files.exists(p)) {
            try (InputStream in = Files.newInputStream(p)) {
                props.load(new java.io.InputStreamReader(in, StandardCharsets.UTF_8));
            } catch (IOException ignored) {
                // fail closed to defaults
            }
        } else {
            save();
        }
    }

    private void defaults() {
        props.setProperty("hotkey", "");
        props.setProperty("local_model", "large-v3-turbo-q5_0");
        props.setProperty("delivery_mode", "type");
        props.setProperty("writing_mode", "smart");
        props.setProperty("language", "hinglish");
        props.setProperty("cdp_port", "9222");
        props.setProperty("voice_feedback", "true");
        props.setProperty("auto_launch_browser", "true");
        props.setProperty("browser_profile", "remi");
    }

    public Path path() {
        return APPDATA.resolve(app + ".properties");
    }

    public String get(String key, String def) {
        String v = props.getProperty(key);
        return (v == null || v.isBlank()) ? def : v;
    }

    public boolean getBool(String key, boolean def) {
        return Boolean.parseBoolean(get(key, String.valueOf(def)));
    }

    public int getInt(String key, int def) {
        try {
            return Integer.parseInt(get(key, String.valueOf(def)));
        } catch (NumberFormatException e) {
            return def;
        }
    }

    public void set(String key, String value) {
        props.setProperty(key, value);
    }

    public void save() {
        try {
            Files.createDirectories(APPDATA);
            try (OutputStream out = Files.newOutputStream(path())) {
                props.store(new java.io.OutputStreamWriter(out, StandardCharsets.UTF_8), "remi-suite-java " + app);
            }
        } catch (IOException ignored) {
        }
    }

    public Path modelPath(String name) {
        Path own = LOCALAPPDATA.resolve("models").resolve("ggml-" + name + ".bin");
        if (Files.exists(own)) return own;
        Path borrowed = VT_MODELS.resolve("ggml-" + name + ".bin");
        return Files.exists(borrowed) ? borrowed : own;
    }

    public Path historyPath() {
        return LOCALAPPDATA.resolve(app + "-history.jsonl");
    }
}
