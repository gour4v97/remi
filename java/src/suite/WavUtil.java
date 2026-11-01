package suite;

import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.Path;

/** PCM → WAV wrapping and simple linear resampling. */
public final class WavUtil {
    private WavUtil() {}

    public static byte[] toWav(byte[] pcm, int sampleRate) {
        ByteArrayOutputStream out = new ByteArrayOutputStream(44 + pcm.length);
        int blockAlign = 2, byteRate = sampleRate * blockAlign;
        try {
            out.writeBytes(new byte[]{'R', 'I', 'F', 'F'});
            out.write(int32(36 + pcm.length));
            out.writeBytes(new byte[]{'W', 'A', 'V', 'E', 'f', 'm', 't', ' '});
            out.write(int32(16));
            out.write(int16(1));       // PCM
            out.write(int16(1));       // mono
            out.write(int32(sampleRate));
            out.write(int32(byteRate));
            out.write(int16(blockAlign)); // 2-byte field per the WAV spec
            out.write(int16(16));      // bits
            out.writeBytes(new byte[]{'d', 'a', 't', 'a'});
            out.write(int32(pcm.length));
            out.writeBytes(pcm);
        } catch (java.io.IOException impossible) {
            // ByteArrayOutputStream never throws
        }
        return out.toByteArray();
    }

    public static void writeWav(Path path, byte[] pcm) throws Exception {
        Files.write(path, toWav(pcm, 16000));
    }

    private static byte[] int32(int v) {
        return ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putInt(v).array();
    }

    private static byte[] int16(int v) {
        return ByteBuffer.allocate(2).order(ByteOrder.LITTLE_ENDIAN).putShort((short) v).array();
    }

    /** Linear-interpolation resample of mono s16le PCM (speech-quality MVP). */
    public static byte[] resample16k(byte[] pcm, int srcRate) {
        if (srcRate == 16000 || pcm.length < 4) return pcm;
        int srcLen = pcm.length / 2;
        int dstLen = (int) ((long) srcLen * 16000 / srcRate);
        short[] src = new short[srcLen];
        for (int i = 0; i < srcLen; i++) {
            int s = (pcm[i * 2] & 0xFF) | (pcm[i * 2 + 1] << 8);
            src[i] = (short) s;
        }
        byte[] out = new byte[dstLen * 2];
        for (int i = 0; i < dstLen; i++) {
            double pos = i * (double) (srcLen - 1) / Math.max(1, dstLen - 1);
            int i0 = (int) pos;
            int i1 = Math.min(srcLen - 1, i0 + 1);
            double frac = pos - i0;
            double v = src[i0] + (src[i1] - src[i0]) * frac;
            int s = (int) Math.round(v);
            if (s > 32767) s = 32767;
            if (s < -32768) s = -32768;
            out[i * 2] = (byte) (s & 0xFF);
            out[i * 2 + 1] = (byte) ((s >> 8) & 0xFF);
        }
        return out;
    }
}
