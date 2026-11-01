using System.Text.RegularExpressions;

namespace VoiceTrans;

/// <summary>
/// Personal pronunciation dictionary, voisu-compatible format: one term per line,
/// '#' comments (only at line start or after whitespace, so "C#" survives).
/// Only user-owned terms may rewrite a transcript (voisu rule).
/// Terms work for Latin and Devanagari alike.
/// </summary>
public sealed class PronunciationDictionary
{
    readonly List<string> _terms;

    public PronunciationDictionary(IEnumerable<string> terms)
    {
        _terms = terms
            .Where(t => t.Length > 0)
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .OrderByDescending(t => t.Length)
            .ToList();
    }

    public int Count => _terms.Count;
    public IReadOnlyList<string> Terms => _terms;

    public static PronunciationDictionary Load(string path)
    {
        if (!File.Exists(path)) return new PronunciationDictionary(Array.Empty<string>());
        var terms = File.ReadAllLines(path)
            .Select(l => l.TrimEnd())
            .Select(l => l.StartsWith('#') ? "" : CutAfterComment(l))
            .Select(l => l.Trim())
            .Where(l => l.Length > 0);
        return new PronunciationDictionary(terms);
    }

    static string CutAfterComment(string line)
    {
        int idx = line.IndexOf(" #", StringComparison.Ordinal);
        return idx >= 0 ? line[..idx] : line;
    }

    /// <summary>Case-insensitive whole-word replacement with the dictionary's canonical casing.</summary>
    public string Apply(string text)
    {
        if (_terms.Count == 0) return text;
        foreach (var term in _terms)
        {
            var pattern = "(?<![\\p{L}\\p{Nd}])" + Regex.Escape(term) + "(?![\\p{L}\\p{Nd}])";
            text = Regex.Replace(text, pattern, term, RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
        }
        return text;
    }
}
