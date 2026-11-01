package suite;

import javax.sound.sampled.AudioFormat;
import javax.sound.sampled.AudioSystem;
import javax.sound.sampled.DataLine;
import javax.sound.sampled.TargetDataLine;
import java.io.ByteArrayOutputStream;

/** Microphone capture via javax.sound.sampled → 16 kHz mono s16le bytes. */
public final class Capture {
    private TargetDataLine line;
    private final ByteArrayOutputStream buf = new ByteArrayOutputStream(1 << 20);
    private volatile boolean running;
    private Thread reader;
    private int nativeRate = -1;

    public void start() throws Exception {
        AudioFormat fmt16k = new AudioFormat(16000f, 16, 1, true, false);
        Exception last = null;
        try {
            line = open(fmt16k);
        } catch (Exception e) {
            last = e;
            // device refused 16 kHz — try common native rates and resample on stop
            for (int rate : new int[]{48000, 44100, 22050, 8000}) {
                try {
                    line = open(new AudioFormat(rate, 16, 1, true, false));
                    nativeRate = rate;
                    break;
                } catch (Exception ignored) {
                    line = null;
                }
            }
            if (line == null) throw last;
        }
        line.start();
        running = true;
        reader = new Thread(() -> {
            byte[] chunk = new byte[6400];
            while (running) {
                int n = line.read(chunk, 0, chunk.length);
                if (n > 0) synchronized (buf) {
                    buf.write(chunk, 0, n);
                }
            }
        }, "mic-reader");
        reader.setDaemon(true);
        reader.start();
    }

    private static TargetDataLine open(AudioFormat fmt) throws Exception {
        TargetDataLine l = (TargetDataLine) AudioSystem.getLine(new DataLine.Info(TargetDataLine.class, fmt));
        l.open(fmt);
        return l;
    }

    public byte[] stopAndRead() {
        running = false;
        try {
            if (line != null) {
                line.stop();
                line.close();
            }
        } catch (Exception ignored) {
        }
        if (reader != null) {
            try {
                reader.join(2000);
            } catch (InterruptedException ignored) {
            }
        }
        byte[] raw;
        synchronized (buf) {
            raw = buf.toByteArray();
            buf.reset();
        }
        if (nativeRate > 0 && nativeRate != 16000) raw = WavUtil.resample16k(raw, nativeRate);
        return raw;
    }
}
