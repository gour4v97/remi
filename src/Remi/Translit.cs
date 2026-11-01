using System.Text;

namespace Remi;

/// <summary>
/// Devanagari → readable Roman (Hinglish) transliteration, e.g. "कैसे हो" → "kaise ho".
/// Deterministic, no external dependency. Non-Devanagari text passes through unchanged,
/// which is what makes mixed Hinglish output work: only the Hindi parts are transliterated.
/// </summary>
public static class Translit
{
    static readonly Dictionary<char, string> Vowels = new()
    {
        // standalone long vowels get doubled spellings ("aap", "aaj", "mein/een", "hoon") — matches Hinglish habit
        ['अ'] = "a", ['आ'] = "aa", ['इ'] = "i", ['ई'] = "ee", ['उ'] = "u", ['ऊ'] = "oo",
        ['ए'] = "e", ['ऐ'] = "ai", ['ओ'] = "o", ['औ'] = "au", ['ऋ'] = "ri",
        ['ॲ'] = "e", ['ऍ'] = "e", ['ऑ'] = "o", ['ऒ'] = "o",
    };

    static readonly Dictionary<char, string> Consonants = new()
    {
        ['क'] = "k", ['ख'] = "kh", ['ग'] = "g", ['घ'] = "gh", ['ङ'] = "n",
        ['च'] = "ch", ['छ'] = "chh", ['ज'] = "j", ['झ'] = "jh", ['ञ'] = "n",
        ['ट'] = "t", ['ठ'] = "th", ['ड'] = "d", ['ढ'] = "dh", ['ण'] = "n",
        ['त'] = "t", ['थ'] = "th", ['द'] = "d", ['ध'] = "dh", ['न'] = "n",
        ['प'] = "p", ['फ'] = "ph", ['ब'] = "b", ['भ'] = "bh", ['म'] = "m",
        ['य'] = "y", ['र'] = "r", ['ल'] = "l", ['व'] = "v",
        ['श'] = "sh", ['ष'] = "sh", ['स'] = "s", ['ह'] = "h", ['ळ'] = "l",
        // nukta consonants (precomposed codepoints)
        ['\u0958'] = "q",   // क़
        ['\u0959'] = "kh",  // ख़
        ['\u095A'] = "g",   // ग़
        ['\u095B'] = "z",   // ज़
        ['\u095C'] = "r",   // ड़
        ['\u095D'] = "rh",  // ढ़
        ['\u095E'] = "f",   // फ़
        ['\u095F'] = "y",   // य़
    };

    static readonly Dictionary<char, string> Matras = new()
    {
        ['ा'] = "a", ['ि'] = "i", ['ी'] = "i", ['ु'] = "u", ['ू'] = "u",
        ['े'] = "e", ['ै'] = "ai", ['ो'] = "o", ['ौ'] = "au",
        ['ृ'] = "ri", ['ॄ'] = "ri", ['ॢ'] = "l", ['ॉ'] = "o", ['ॅ'] = "e", ['ॊ'] = "o",
    };

    public static bool HasDevanagari(string s)
    {
        foreach (var c in s)
            if (c is >= '\u0900' and <= '\u097F') return true;
        return false;
    }

    public static string ToRoman(string text)
    {
        if (!HasDevanagari(text)) return text;
        var sb = new StringBuilder(text.Length + 16);
        int i = 0;
        while (i < text.Length)
        {
            char c = text[i];

            if (c == '\u093C') { i++; continue; }               // stray combining nukta
            if (c == '\u200C' || c == '\u200D') { i++; continue; } // ZWNJ / ZWJ

            if (Consonants.TryGetValue(c, out var cons))
            {
                // common conjuncts with friendlier romanizations
                if (c == 'ज' && i + 2 < text.Length && text[i + 1] == '्' && text[i + 2] == 'ञ')
                {
                    sb.Append("gy"); i += 3; continue;
                }
                if (c == 'क' && i + 2 < text.Length && text[i + 1] == '्' && text[i + 2] == 'ष')
                {
                    sb.Append("ksh"); i += 3; continue;
                }
                sb.Append(cons);
                i++;
                if (i < text.Length && text[i] == '्') { i++; continue; }   // halant: suppress inherent 'a'
                if (i < text.Length && Matras.ContainsKey(text[i])) continue; // following matra supplies the vowel
                if (i >= text.Length || !IsLetterish(text[i])) continue;    // word-final: drop inherent 'a'
                sb.Append('a');                                             // inherent short 'a' mid-word
                continue;
            }

            if (Vowels.TryGetValue(c, out var v)) { sb.Append(v); i++; continue; }
            if (Matras.TryGetValue(c, out var m)) { sb.Append(m); i++; continue; }

            switch (c)
            {
                case 'ं':
                    sb.Append(i + 1 < text.Length && text[i + 1] is 'प' or 'ब' or 'म' ? "m" : "n");
                    i++;
                    break;
                case 'ँ': sb.Append('n'); i++; break;                    // chandrabindu
                case 'ः': sb.Append('h'); i++; break;                    // visarga
                case '।': sb.Append('.'); i++; break;                    // danda
                case '॥': sb.Append('.'); i++; break;                    // double danda
                case 'ऽ': i++; break;
                default:
                    if (c is >= '\u0966' and <= '\u096F') { sb.Append((char)('0' + (c - '\u0966'))); i++; break; } // ०-९
                    sb.Append(c); i++;
                    break;
            }
        }
        return sb.ToString();
    }

    static bool IsLetterish(char c) =>
        (c is >= '\u0900' and <= '\u097F') || char.IsLetter(c) || char.IsDigit(c) || c is '\u200C' or '\u200D';
}
