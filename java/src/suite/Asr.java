package suite;

import java.io.InputStream;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/** Local ASR via whisper.cpp's whisper-cli.exe (bootstrapped from the official release). */
public final class Asr {
    private Asr() {}

    static final String WHISPER_ZIP_URL =
            "https://github.com/ggerganov/whisper.cpp/releases/download/b5454/whisper-bin-x64.zip";
    static final Path WHISPER_CLI = Config.LOCALAPPDATA.resolve("bin").resolve("whisper-cli.exe");
    private static final Pattern SEGMENT = Pattern.compile("^\\[[^\\]]+\\]\\s*(.*)$");

    public static synchronized Path ensureWhisperCli() throws Exception {
        if (Files.exists(WHISPER_CLI)) return WHISPER_CLI;
        Files.createDirectories(Config.LOCALAPPDATA.resolve("bin"));
        System.out.println("downloading whisper.cpp CLI from " + WHISPER_ZIP_URL + " ...");
        Path zip = Config.LOCALAPPDATA.resolve("bin").resolve("whisper-bin.zip");
        try (InputStream in = URI.create(WHISPER_ZIP_URL).toURL().openStream()) {
            Files.copy(in, zip, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
        }
        try (ZipInputStream zin = new ZipInputStream(Files.newInputStream(zip))) {
            ZipEntry e;
            byte[] buf = new byte[1 << 16];
            while ((e = zin.getNextEntry()) != null) {
                if (e.isDirectory()) continue;
                String name = Path.of(e.getName()).getFileName().toString();
                if (name.toLowerCase().endsWith(".exe") || name.toLowerCase().endsWith(".dll")) {
                    try (var out = Files.newOutputStream(Config.LOCALAPPDATA.resolve("bin").resolve(name))) {
                        int n;
                        while ((n = zin.read(buf)) > 0) out.write(buf, 0, n);
                    }
                }
            }
        }
        Files.deleteIfExists(zip);
        if (!Files.exists(WHISPER_CLI)) throw new IllegalStateException("whisper-cli.exe missing from archive");
        return WHISPER_CLI;
    }

    /** pcm: 16 kHz mono s16le. Returns raw transcript text. */
    public static String transcribePcm(byte[] pcm, Config cfg, String language) throws Exception {
        Path exe = ensureWhisperCli();
        Path model = cfg.modelPath(cfg.get("local_model", "large-v3-turbo-q5_0"));
        if (!Files.exists(model)) {
            throw new IllegalStateException("model '" + cfg.get("local_model", "") + "' not found");
        }
        Path wav = Config.LOCALAPPDATA.resolve("utterance.wav");
        WavUtil.writeWav(wav, pcm);

        String lang = switch (language) {
            case "en" -> "en";
            case "hi" -> "hi";
            default -> "auto";
        };
        ProcessBuilder pb = new ProcessBuilder(
                exe.toString(), "--model", model.toString(), "--file", wav.toString(),
                "--language", lang, "--no-gpu", "-t", "8");
        pb.redirectErrorStream(false);
        Process proc = pb.start();
        String stdout = new String(proc.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        String stderr = new String(proc.getErrorStream().readAllBytes(), StandardCharsets.UTF_8);
        if (!proc.waitFor(10, java.util.concurrent.TimeUnit.MINUTES) && proc.isAlive()) {
            proc.destroyForcibly();
            throw new IllegalStateException("whisper-cli timed out");
        }
        if (proc.exitValue() != 0) {
            throw new IllegalStateException("whisper-cli failed: "
                    + stderr.substring(Math.max(0, stderr.length() - 300)));
        }
        StringBuilder out = new StringBuilder();
        for (String line : stdout.split("\\R")) {
            Matcher m = SEGMENT.matcher(line.trim());
            if (m.matches() && !m.group(1).isEmpty()) out.append(m.group(1));
        }
        return out.toString();
    }

    public static int peakAmplitude(byte[] pcm) {
        int peak = 0;
        for (int i = 0; i + 1 < pcm.length; i += 2) {
            int s = (pcm[i] & 0xFF) | (pcm[i + 1] << 8);
            if (s >= 0x8000) s -= 0x10000;
            peak = Math.max(peak, Math.abs(s));
        }
        return peak;
    }
}
