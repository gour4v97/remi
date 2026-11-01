package suite;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/** Local-only JSONL history (no JSON library — hand-escaped). */
public final class History {
    private History() {}

    public record Entry(String id, String at, String transcript, String detail,
                        boolean ok, String error, long ms) {}

    public static void append(Config cfg, String transcript, String detail, boolean ok, String error, long ms) {
        String json = "{\"id\":\"" + UUID.randomUUID().toString().replace("-", "") + "\""
                + ",\"at\":\"" + Instant.now() + "\""
                + ",\"transcript\":\"" + escape(transcript) + "\""
                + ",\"detail\":\"" + escape(detail) + "\""
                + ",\"ok\":" + ok
                + (error != null ? ",\"error\":\"" + escape(error) + "\"" : "")
                + ",\"ms\":" + ms + "}\n";
        try {
            Files.createDirectories(cfg.historyPath().getParent());
            Files.writeString(cfg.historyPath(), json, StandardCharsets.UTF_8,
                    StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        } catch (IOException ignored) {
        }
    }

    public static List<Entry> load(Config cfg, int last) {
        List<Entry> out = new ArrayList<>();
        Path p = cfg.historyPath();
        if (!Files.exists(p)) return out;
        try {
            for (String line : Files.readAllLines(p, StandardCharsets.UTF_8)) {
                if (line.isBlank()) continue;
                out.add(new Entry(
                        extract(line, "id"), extract(line, "at"), extract(line, "transcript"),
                        extract(line, "detail"),
                        line.contains("\"ok\":true"),
                        line.contains("\"error\"") ? extract(line, "error") : null,
                        parseLong(extract(line, "ms"))));
            }
        } catch (IOException ignored) {
        }
        return out.subList(Math.max(0, out.size() - last), out.size());
    }

    private static long parseLong(String s) {
        try {
            return Long.parseLong(s);
        } catch (Exception e) {
            return 0;
        }
    }

    static String extract(String json, String key) {
        var m = java.util.regex.Pattern.compile("\"" + key + "\":\"([^\"]*)\"").matcher(json);
        return m.find() ? m.group(1) : "";
    }

    public static String escape(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\").replace("\"", "\\\"")
                .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t");
    }
}
