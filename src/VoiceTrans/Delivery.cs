using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;

namespace VoiceTrans;

public sealed record FocusSnapshot(IntPtr Hwnd, string ProcessName, string Title);

public sealed record DeliveryResult(string Method, bool Fallback, string? FallbackReason);

/// <summary>
/// Transcript delivery, preserving voisu's order of guarantees:
/// guarded mode falls back to the clipboard when focus changed during recording,
/// and clipboard mode never touches the keyboard.
/// </summary>
public static class Delivery
{
    [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int maxCount);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
    [DllImport("user32.dll", SetLastError = true)] static extern uint SendInput(uint nInputs, INPUT[] inputs, int cbSize);

    const uint INPUT_KEYBOARD = 1;
    const uint KEYEVENTF_UNICODE = 0x0004;
    const uint KEYEVENTF_KEYUP = 0x0002;
    const ushort VK_RETURN = 0x0D;

    public static FocusSnapshot CaptureFocus()
    {
        var hwnd = GetForegroundWindow();
        string proc = "", title = "";
        if (hwnd != IntPtr.Zero)
        {
            GetWindowThreadProcessId(hwnd, out var pid);
            try { proc = Process.GetProcessById((int)pid).ProcessName; } catch { }
            var sb = new StringBuilder(512);
            GetWindowText(hwnd, sb, 512);
            title = sb.ToString();
        }
        return new FocusSnapshot(hwnd, proc, title);
    }

    public static bool SameFocus(FocusSnapshot snapshot) =>
        GetForegroundWindow() == snapshot.Hwnd;

    /// <summary>Delivers the transcript; setClipboard must marshal to an STA thread.</summary>
    public static DeliveryResult Deliver(string text, string mode, FocusSnapshot? guard, Action<string> setClipboard)
    {
        if (mode == "clipboard")
        {
            setClipboard(text);
            return new DeliveryResult("clipboard", false, null);
        }
        if (mode == "guarded" && guard is not null && !SameFocus(guard))
        {
            setClipboard(text);
            return new DeliveryResult("clipboard", true, "focus changed during recording");
        }
        TypeText(text);
        return new DeliveryResult("type", false, null);
    }

    /// <summary>Types text into the focused window via KEYEVENTF_UNICODE (works for Devanagari too).</summary>
    public static void TypeText(string text)
    {
        Thread.Sleep(150); // let the focus settle after the stop keypress
        var inputs = new List<INPUT>(text.Length * 2);
        foreach (var ch in text)
        {
            if (ch == '\r') continue;
            if (ch == '\n') { AddKey(inputs, VK_RETURN, '\0'); continue; }
            AddKey(inputs, 0, ch, unicode: true);
        }
        if (inputs.Count == 0) return;
        var arr = inputs.ToArray();
        var sent = SendInput((uint)arr.Length, arr, Marshal.SizeOf<INPUT>());
        if (sent != arr.Length)
        {
            throw new InvalidOperationException(
                $"SendInput delivered {sent}/{arr.Length} events — the focused window may be running elevated.");
        }
    }

    static void AddKey(List<INPUT> list, ushort vk, char ch, bool unicode = false)
    {
        list.Add(new INPUT
        {
            type = INPUT_KEYBOARD,
            u = new InputUnion { ki = new KEYBDINPUT { wVk = vk, wScan = (ushort)ch, dwFlags = unicode ? KEYEVENTF_UNICODE : 0 } },
        });
        list.Add(new INPUT
        {
            type = INPUT_KEYBOARD,
            u = new InputUnion { ki = new KEYBDINPUT { wVk = vk, wScan = (ushort)ch, dwFlags = (unicode ? KEYEVENTF_UNICODE : 0) | KEYEVENTF_KEYUP } },
        });
    }

    [StructLayout(LayoutKind.Sequential)]
    struct KEYBDINPUT
    {
        public ushort wVk;
        public ushort wScan;
        public uint dwFlags;
        public uint time;
        public IntPtr dwExtraInfo;
    }

    [StructLayout(LayoutKind.Sequential)]
    struct MOUSEINPUT
    {
        public int dx;
        public int dy;
        public uint mouseData;
        public uint dwFlags;
        public uint time;
        public IntPtr dwExtraInfo;
    }

    [StructLayout(LayoutKind.Sequential)]
    struct HARDWAREINPUT
    {
        public uint uMsg;
        public ushort wParamL;
        public ushort wParamH;
    }

    [StructLayout(LayoutKind.Explicit)]
    struct InputUnion
    {
        [FieldOffset(0)] public MOUSEINPUT mi;
        [FieldOffset(0)] public KEYBDINPUT ki;
        [FieldOffset(0)] public HARDWAREINPUT hi;
    }

    [StructLayout(LayoutKind.Sequential)]
    struct INPUT
    {
        public uint type;
        public InputUnion u;
    }
}
