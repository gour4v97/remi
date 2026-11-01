namespace Remi;

/// <summary>Parses and describes hotkey specs like "ctrl+alt+space", "f9", "ctrl+shift+d", "capslock".</summary>
public static class Hotkey
{
    public const uint MOD_ALT = 0x1, MOD_CONTROL = 0x2, MOD_SHIFT = 0x4, MOD_WIN = 0x8, MOD_NOREPEAT = 0x4000;

    static readonly Dictionary<string, uint> Named = new()
    {
        ["space"] = 0x20, ["enter"] = 0x0D, ["return"] = 0x0D, ["escape"] = 0x1B, ["esc"] = 0x1B,
        ["tab"] = 0x09, ["backspace"] = 0x08, ["delete"] = 0x2E, ["del"] = 0x2E,
        ["insert"] = 0x2D, ["ins"] = 0x2D, ["home"] = 0x24, ["end"] = 0x23,
        ["pageup"] = 0x21, ["pagedown"] = 0x22, ["up"] = 0x26, ["down"] = 0x28,
        ["left"] = 0x25, ["right"] = 0x27, ["capslock"] = 0x14, ["scrolllock"] = 0x91,
        ["numlock"] = 0x90, ["pause"] = 0x13, ["printscreen"] = 0x2C,
        ["`"] = 0xC0, [";"] = 0xBA, ["="] = 0xBB, [","] = 0xBC, ["-"] = 0xBD, ["."] = 0xBE,
        ["/"] = 0xBF, ["["] = 0xDB, ["\\"] = 0xDC, ["]"] = 0xDD, ["'"] = 0xDE,
    };

    public static (uint Mods, uint Vk)? Parse(string spec)
    {
        if (string.IsNullOrWhiteSpace(spec)) return null;
        uint mods = 0;
        uint? vk = null;
        foreach (var rawPart in spec.Split('+'))
        {
            var p = rawPart.Trim().ToLowerInvariant();
            if (p.Length == 0) return null;
            switch (p)
            {
                case "ctrl" or "control": mods |= MOD_CONTROL; continue;
                case "alt": mods |= MOD_ALT; continue;
                case "shift": mods |= MOD_SHIFT; continue;
                case "win" or "windows" or "meta": mods |= MOD_WIN; continue;
            }
            uint k;
            if (Named.TryGetValue(p, out var n)) k = n;
            else if (p.Length == 1 && char.IsAsciiLetter(p[0])) k = (uint)char.ToUpperInvariant(p[0]);
            else if (p.Length == 1 && char.IsAsciiDigit(p[0])) k = (uint)p[0];
            else if (p.Length > 1 && p[0] == 'f' && int.TryParse(p[1..], out var f) && f is >= 1 and <= 24) k = (uint)(0x70 + f - 1);
            else return null;
            if (vk is not null) return null; // two non-modifier keys in one combo
            vk = k;
        }
        if (vk is null) return null;
        return (mods | MOD_NOREPEAT, vk.Value);
    }

    public static string Describe(uint mods, uint vk)
    {
        var parts = new List<string>();
        if ((mods & MOD_CONTROL) != 0) parts.Add("ctrl");
        if ((mods & MOD_ALT) != 0) parts.Add("alt");
        if ((mods & MOD_SHIFT) != 0) parts.Add("shift");
        if ((mods & MOD_WIN) != 0) parts.Add("win");
        parts.Add(NameOf(vk));
        return string.Join("+", parts);
    }

    static string NameOf(uint vk)
    {
        foreach (var (n, v) in Named)
            if (v == vk) return n;
        if (vk is >= 0x41 and <= 0x5A) return ((char)vk).ToString().ToLowerInvariant();
        if (vk is >= 0x70 and <= 0x87) return "f" + (vk - 0x70 + 1);
        return "0x" + vk.ToString("X");
    }
}
