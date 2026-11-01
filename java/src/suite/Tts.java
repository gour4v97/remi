package suite;

/** Spoken confirmations via Windows SAPI through PowerShell (no extra deps). */
public final class Tts {
    private Tts() {}

    public static void say(String text, boolean enabled) {
        if (!enabled || text == null || text.isBlank()) return;
        Thread t = new Thread(() -> {
            try {
                String ps = "Add-Type -AssemblyName System.Speech; "
                        + "(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('"
                        + text.replace("'", "''") + "')";
                new ProcessBuilder("powershell", "-NoProfile", "-Command", ps)
                        .start();
            } catch (Exception ignored) {
                // TTS is best-effort feedback
            }
        }, "tts");
        t.setDaemon(true);
        t.start();
    }
}
