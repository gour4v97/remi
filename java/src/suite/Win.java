package suite;

import com.sun.jna.Pointer;
import com.sun.jna.platform.win32.BaseTSD;
import com.sun.jna.platform.win32.WinDef;
import com.sun.jna.platform.win32.WinUser;

import java.awt.Toolkit;
import java.awt.datatransfer.StringSelection;
import java.util.ArrayList;
import java.util.List;

/** Win32 interop via JNA: hotkey, SendInput typing, clipboard, foreground window. */
public final class Win {
    private Win() {}

    public static final int WM_HOTKEY = 0x0312;
    public static final int MOD_ALT = 0x1, MOD_CONTROL = 0x2, MOD_SHIFT = 0x4, MOD_WIN = 0x8;
    public static final int MOD_NOREPEAT = 0x4000;

    // ---------- hotkey ----------

    /** Registers a hotkey and loops GetMessage on a daemon thread; runnable fires per press. */
    public static void registerHotkey(String spec, int id, Runnable onPress) {
        long[] mvk = parseHotkey(spec);
        if (mvk == null) return;
        boolean ok = com.sun.jna.platform.win32.User32.INSTANCE.RegisterHotKey(
                null, id, (int) mvk[0], (int) mvk[1]);
        if (!ok) return;
        Thread t = new Thread(() -> {
            WinUser.MSG msg = new WinUser.MSG();
            while (true) {
                int r = com.sun.jna.platform.win32.User32.INSTANCE.GetMessage(msg, null, 0, 0);
                if (r <= 0) return;
                if (msg.message == WM_HOTKEY && msg.wParam.intValue() == id) {
                    try {
                        onPress.run();
                    } catch (Exception ignored) {
                    }
                }
            }
        }, "hotkey-" + id);
        t.setDaemon(true);
        t.start();
    }

    /** "ctrl+alt+space" → {mods | MOD_NOREPEAT, vk}, or null if invalid. */
    public static long[] parseHotkey(String spec) {
        if (spec == null || spec.isBlank()) return null;
        int mods = 0;
        Integer vk = null;
        for (String raw : spec.toLowerCase().split("\\+")) {
            String p = raw.trim();
            switch (p) {
                case "ctrl", "control" -> mods |= MOD_CONTROL;
                case "alt" -> mods |= MOD_ALT;
                case "shift" -> mods |= MOD_SHIFT;
                case "win", "windows", "meta" -> mods |= MOD_WIN;
                default -> {
                    Integer k = namedKey(p);
                    if (k == null || vk != null) return null;
                    vk = k;
                }
            }
        }
        if (vk == null) return null;
        return new long[]{mods | MOD_NOREPEAT, vk};
    }

    static Integer namedKey(String p) {
        return switch (p) {
            case "space" -> 0x20;
            case "enter", "return" -> 0x0D;
            case "escape", "esc" -> 0x1B;
            case "tab" -> 0x09;
            case "backspace" -> 0x08;
            case "delete", "del" -> 0x2E;
            case "insert", "ins" -> 0x2D;
            case "home" -> 0x24;
            case "end" -> 0x23;
            case "pageup" -> 0x21;
            case "pagedown" -> 0x22;
            case "capslock" -> 0x14;
            default -> {
                if (p.length() == 1 && Character.isLetterOrDigit(p.charAt(0)))
                    yield (int) Character.toUpperCase(p.charAt(0));
                if (p.length() > 1 && p.charAt(0) == 'f') {
                    try {
                        int f = Integer.parseInt(p.substring(1));
                        if (f >= 1 && f <= 24) yield 0x70 + f - 1;
                    } catch (NumberFormatException ignored) {
                    }
                }
                yield null;
            }
        };
    }

    // ---------- SendInput typing ----------

    public static void typeText(String text) throws InterruptedException {
        Thread.sleep(150);
        List<WinUser.INPUT> inputs = new ArrayList<>();
        for (char ch : text.toCharArray()) {
            if (ch == '\r') continue;
            if (ch == '\n') {
                inputs.add(key(0x0D, 0, 0));
                inputs.add(key(0x0D, 0, WinUser.KEYBDINPUT.KEYEVENTF_KEYUP));
                continue;
            }
            inputs.add(key(0, ch, WinUser.KEYBDINPUT.KEYEVENTF_UNICODE));
            inputs.add(key(0, ch, WinUser.KEYBDINPUT.KEYEVENTF_UNICODE | WinUser.KEYBDINPUT.KEYEVENTF_KEYUP));
        }
        if (inputs.isEmpty()) return;
        WinUser.INPUT[] arr = inputs.toArray(new WinUser.INPUT[0]);
        WinDef.DWORD sentDw = com.sun.jna.platform.win32.User32.INSTANCE.SendInput(new WinDef.DWORD((long) arr.length), arr, arr[0].size());
        int sent = sentDw.intValue();
        if (sent != arr.length) {
            throw new IllegalStateException("SendInput delivered " + sent + "/" + arr.length
                    + " — focused window may be elevated");
        }
    }

    private static WinUser.INPUT key(int vk, int scan, int flags) {
        WinUser.INPUT inp = new WinUser.INPUT();
        inp.type = new WinDef.DWORD(WinUser.INPUT.INPUT_KEYBOARD);
        inp.input.setType("ki");
        inp.input.ki = new WinUser.KEYBDINPUT();
        inp.input.ki.wVk = new WinDef.WORD(vk);
        inp.input.ki.wScan = new WinDef.WORD(scan);
        inp.input.ki.dwFlags = new WinDef.DWORD(flags);
        inp.input.ki.time = new WinDef.DWORD(0);
        inp.input.ki.dwExtraInfo = new BaseTSD.ULONG_PTR(0);
        return inp;
    }

    // ---------- clipboard / foreground ----------

    public static void setClipboard(String text) {
        StringSelection sel = new StringSelection(text);
        Toolkit.getDefaultToolkit().getSystemClipboard().setContents(sel, sel);
    }

    public static long foregroundHwnd() {
        WinDef.HWND hwnd = com.sun.jna.platform.win32.User32.INSTANCE.GetForegroundWindow();
        return hwnd == null ? 0 : Pointer.nativeValue(hwnd.getPointer());
    }
}
