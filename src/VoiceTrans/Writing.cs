using System.Text;
using System.Text.RegularExpressions;

namespace VoiceTrans;

/// <summary>
/// Writing modes, mirroring voisu: "literal" is the fails-closed identity path,
/// "smart" applies deterministic local formatting only (no cloud, never rewrites wording).
/// Handles English and Hindi (Devanagari) spoken punctuation.
/// </summary>
public static class Writing
{
    static readonly (string Spoken, string Repl)[] SpokenPunct =
    {
        ("full stop", "."), ("period", "."), ("comma", ","), ("question mark", "?"),
        ("exclamation mark", "!"), ("exclamation point", "!"), ("colon", ":"), ("semicolon", ";"),
        ("new line", "\n"), ("next line", "\n"), ("new paragraph", "\n\n"),
        ("अल्प विराम", ","), ("पूर्ण विराम", "।"), ("दंड", "।"),
        ("प्रश्न चिह्न", "?"), ("विस्मयादिबोधक चिह्न", "!"),
    };

    public static string Apply(string text, string writingMode, string language)
    {
        text = text.Trim();
        if (writingMode != "smart") return text;

        foreach (var (spoken, repl) in SpokenPunct)
        {
            text = Regex.Replace(
                text,
                "(?<!\\S)" + Regex.Escape(spoken) + "(?!\\S)",
                repl.Replace("$", "$$"),
                RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
        }

        // collapse horizontal whitespace, keep line breaks
        text = Regex.Replace(text, "[ \\t\\u00A0]+", " ");
        text = Regex.Replace(text, " ?\n ?", "\n");
        text = text.Trim();

        // spacing after punctuation (avoid splitting decimals like 3.14)
        text = Regex.Replace(text, "([,;:!?।])\\s*", "$1 ");
        text = Regex.Replace(text, "(?<!\\d)\\.(?![\\d\\w])", ". ");
        text = Regex.Replace(text, " +", " ").Trim();

        text = CapitalizeSentences(text);

        // Hindi sentence ends with danda, not a bare stop
        if (Translit.HasDevanagari(text) && text.Length > 0 && !IsTerminal(text[^1]))
            text += "।";

        return text;
    }

    static bool IsTerminal(char c) => c is '.' or '!' or '?' or '।' or ':' or ',' or '\n';

    static string CapitalizeSentences(string t)
    {
        var sb = new StringBuilder(t.Length);
        bool capNext = true;
        for (int i = 0; i < t.Length; i++)
        {
            char c = t[i];
            if (capNext && char.IsAsciiLetter(c))
            {
                sb.Append(char.ToUpperInvariant(c));
                capNext = false;
                continue;
            }
            if (char.IsLetter(c)) capNext = false;
            sb.Append(c);
            if (c is '.' or '!' or '?' or '।' or '\n') capNext = true;
        }
        // standalone "i" → "I" (English only)
        return Regex.Replace(sb.ToString(), "(?<![A-Za-z])i(?![A-Za-z'])", "I");
    }
}
