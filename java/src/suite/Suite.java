package suite;

import java.awt.Toolkit;
import java.util.List;

/** Entry point: one jar, two apps + CLI helpers.
 *
 *  remi-suite.jar voice-trans            tray dictation app
 *  remi-suite.jar remi                   tray browser controller
 *  remi-suite.jar remi say "open github" run a text command
 *  remi-suite.jar remi say-audio f.wav   full voice pipeline on a WAV
 *  remi-suite.jar history <app>          recent commands
 *  remi-suite.jar doctor                 readiness checks
 */
public final class Suite {
    public static void main(String[] args) throws Exception {
        System.setProperty("java.awt.headless", "false");
        String verb = args.length > 0 ? args[0].toLowerCase() : "help";
        switch (verb) {
            case "voice-trans" -> new VoiceTransApp(new Config(VoiceTransApp.APP)).run();
            case "remi" -> {
                if (args.length >= 3 && args[1].equals("say")) {
                    System.exit(say(args[2]));
                } else if (args.length >= 3 && args[1].equals("say-audio")) {
                    System.exit(sayAudio(args[2]));
                } else if (args.length >= 2 && args[1].equals("history")) {
                    history("remi-java");
                    System.exit(0);
                }
                new RemiApp(new Config(RemiApp.APP)).run();
            }
            case "history" -> {
                history(args.length > 1 ? args[1] : "remi-java");
                System.exit(0);
            }
            case "doctor" -> {
                doctor();
                System.exit(0);
            }
            default -> help();
        }
    }

    static int say(String text) {
        Config cfg = new Config(RemiApp.APP);
        Router.Outcome o = Router.run(text, cfg);
        History.append(cfg, text, o.detail(), o.ok(), o.ok() ? null : o.spoken(), 0);
        System.out.println("command : " + o.ok());
        System.out.println("result  : " + o.spoken());
        System.out.println("detail  : " + o.detail());
        return o.ok() ? 0 : 2;
    }

    static int sayAudio(String path) throws Exception {
        Config cfg = new Config(RemiApp.APP);
        byte[] raw = java.nio.file.Files.readAllBytes(java.nio.file.Path.of(path));
        // parse WAV: find data chunk, resample if needed
        byte[] pcm = extractPcm16k(raw);
        System.out.println("transcribing " + pcm.length / 32000.0 + "s with "
                + cfg.get("local_model", "") + "...");
        String text = Translit.toRoman(Asr.transcribePcm(pcm, cfg, "hinglish")).trim();
        System.out.println("heard    : " + text);
        Router.Outcome o = Router.run(text, cfg);
        History.append(cfg, text, o.detail(), o.ok(), o.ok() ? null : o.spoken(), 0);
        System.out.println("command  : " + o.ok());
        System.out.println("result   : " + o.spoken());
        System.out.println("detail   : " + o.detail());
        return o.ok() ? 0 : 2;
    }

    /** Minimal WAV parse (16-bit PCM, any rate/channels) → 16 kHz mono s16le. */
    static byte[] extractPcm16k(byte[] wav) throws Exception {
        ByteBufferish buf = new ByteBufferish(wav);
        String riff = buf.string(4);
        buf.u32(); // skip the RIFF size field — "WAVE" sits at offset 8
        String wave = buf.string(4);
        if (!"RIFF".equals(riff) || !"WAVE".equals(wave))
            throw new IllegalArgumentException("not a WAV file");
        int rate = 44100, channels = 1, bits = 16;
        byte[] data = null;
        while (buf.remaining() > 8) {
            String id = buf.string(4);
            int size = (int) buf.u32();
            byte[] chunk = buf.bytes(size);
            switch (id) {
                case "fmt " -> {
                    rate = ((chunk[5] & 0xFF) << 8) | (chunk[4] & 0xFF);
                    channels = ((chunk[3] & 0xFF) << 8) | (chunk[2] & 0xFF);
                    bits = ((chunk[15] & 0xFF) << 8) | (chunk[14] & 0xFF);
                }
                case "data" -> data = chunk;
            }
            if (size % 2 == 1) buf.u32(); // skip pad byte
        }
        if (data == null) throw new IllegalArgumentException("no data chunk");
        if (bits != 16) throw new IllegalArgumentException("only 16-bit WAV supported");
        int n = data.length / (2 * channels);
        short[] mono = new short[n];
        for (int i = 0; i < n; i++) {
            int acc = 0;
            for (int c = 0; c < channels; c++) {
                int s = (data[(i * channels + c) * 2] & 0xFF) | (data[(i * channels + c) * 2 + 1] << 8);
                if (s >= 0x8000) s -= 0x10000;
                acc += s;
            }
            mono[i] = (short) (acc / channels);
        }
        byte[] pcm = new byte[n * 2];
        for (int i = 0; i < n; i++) {
            pcm[i * 2] = (byte) (mono[i] & 0xFF);
            pcm[i * 2 + 1] = (byte) ((mono[i] >> 8) & 0xFF);
        }
        return WavUtil.resample16k(pcm, rate);
    }

    static void history(String app) {
        List<History.Entry> entries = History.load(new Config(app), 20);
        for (int i = entries.size() - 1; i >= 0; i--) {
            History.Entry e = entries.get(i);
            String what = e.ok() ? e.detail() : "ERROR: " + e.error();
            if (what.length() > 60) what = what.substring(0, 57) + "...";
            System.out.printf("%s  %-30s  %s%n", e.at().substring(0, Math.min(19, e.at().length())),
                    e.transcript(), what);
        }
    }

    static void doctor() {
        Config cfg = new Config(RemiApp.APP);
        System.out.println("model    : " + cfg.get("local_model", "") + " -> "
                + (java.nio.file.Files.exists(cfg.modelPath(cfg.get("local_model", ""))) ? "found" : "MISSING"));
        System.out.println("whisper  : " + (java.nio.file.Files.exists(Asr.WHISPER_CLI) ? "ready" : "will download on first use"));
        System.out.println("browser  : " + (Cdp.findBrowserExe() != null ? Cdp.findBrowserExe() : "NOT FOUND"));
        System.out.println("cdp      : " + (Cdp.isUp(cfg.getInt("cdp_port", 9222)) ? "up" : "down")
                + " on port " + cfg.getInt("cdp_port", 9222));
    }

    static void help() {
        System.out.println("""
                remi-suite (Java) — Voice Trans + Remi

                  java -jar remi-suite.jar voice-trans             dictation tray app
                  java -jar remi-suite.jar remi                    browser controller tray app
                  java -jar remi-suite.jar remi say "open github"  text command
                  java -jar remi-suite.jar remi say-audio f.wav    voice pipeline on WAV
                  java -jar remi-suite.jar history [app]           recent activity
                  java -jar remi-suite.jar doctor                  readiness checks

                default hotkeys: ctrl+alt+space (dictation), ctrl+alt+b (browser)
                """);
    }

    /** Tiny big-endian reader for WAV chunk walking. */
    static final class ByteBufferish {
        private final byte[] a;
        private int pos;

        ByteBufferish(byte[] a) {
            this.a = a;
            this.pos = 0;
        }

        String string(int n) {
            String s = new String(a, pos, n, java.nio.charset.StandardCharsets.US_ASCII);
            pos += n;
            return s;
        }

        long u32() {
            long v = (a[pos] & 0xFF) | ((a[pos + 1] & 0xFF) << 8)
                    | ((a[pos + 2] & 0xFF) << 16) | ((long) (a[pos + 3] & 0xFF) << 24);
            pos += 4;
            return v;
        }

        byte[] bytes(int n) {
            byte[] out = new byte[n];
            System.arraycopy(a, pos, out, 0, n);
            pos += n;
            return out;
        }

        int remaining() {
            return a.length - pos;
        }
    }
}
