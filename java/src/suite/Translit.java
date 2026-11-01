package suite;

import java.util.Map;
import java.util.regex.Pattern;

/** Devanagari → Roman (Hinglish) transliteration + light smart writing. Port of the C# module. */
public final class Translit {
    private Translit() {}

    static final Map<String, String> VOWELS = Map.ofEntries(
            Map.entry("अ", "a"), Map.entry("आ", "aa"), Map.entry("इ", "i"), Map.entry("ई", "ee"),
            Map.entry("उ", "u"), Map.entry("ऊ", "oo"), Map.entry("ए", "e"), Map.entry("ऐ", "ai"),
            Map.entry("ओ", "o"), Map.entry("औ", "au"), Map.entry("ऋ", "ri"),
            Map.entry("ॲ", "e"), Map.entry("ऍ", "e"), Map.entry("ऑ", "o"), Map.entry("ऒ", "o"));

    static final Map<String, String> CONSONANTS = Map.ofEntries(
            Map.entry("क", "k"), Map.entry("ख", "kh"), Map.entry("ग", "g"), Map.entry("घ", "gh"), Map.entry("ङ", "n"),
            Map.entry("च", "ch"), Map.entry("छ", "chh"), Map.entry("ज", "j"), Map.entry("झ", "jh"), Map.entry("ञ", "n"),
            Map.entry("ट", "t"), Map.entry("ठ", "th"), Map.entry("ड", "d"), Map.entry("ढ", "dh"), Map.entry("ण", "n"),
            Map.entry("त", "t"), Map.entry("थ", "th"), Map.entry("द", "d"), Map.entry("ध", "dh"), Map.entry("न", "n"),
            Map.entry("प", "p"), Map.entry("फ", "ph"), Map.entry("ब", "b"), Map.entry("भ", "bh"), Map.entry("म", "m"),
            Map.entry("य", "y"), Map.entry("र", "r"), Map.entry("ल", "l"), Map.entry("व", "v"),
            Map.entry("श", "sh"), Map.entry("ष", "sh"), Map.entry("स", "s"), Map.entry("ह", "h"), Map.entry("ळ", "l"),
            Map.entry("क़", "q"), Map.entry("ख़", "kh"), Map.entry("ग़", "g"), Map.entry("ज़", "z"),
            Map.entry("ड़", "r"), Map.entry("ढ़", "rh"), Map.entry("फ़", "f"), Map.entry("य़", "y"));

    static final Map<String, String> MATRAS = Map.ofEntries(
            Map.entry("ा", "a"), Map.entry("ि", "i"), Map.entry("ी", "i"), Map.entry("ु", "u"), Map.entry("ू", "u"),
            Map.entry("े", "e"), Map.entry("ै", "ai"), Map.entry("ो", "o"), Map.entry("ौ", "au"),
            Map.entry("ृ", "ri"), Map.entry("ॄ", "ri"), Map.entry("ॢ", "l"), Map.entry("ॉ", "o"),
            Map.entry("ॅ", "e"), Map.entry("ॊ", "o"));

    public static boolean hasDevanagari(String s) {
        return s.chars().anyMatch(c -> c >= 0x0900 && c <= 0x097F);
    }

    private static boolean letterish(int c) {
        return (c >= 0x0900 && c <= 0x097F) || Character.isLetterOrDigit(c) || c == 0x200C || c == 0x200D;
    }

    public static String toRoman(String text) {
        if (!hasDevanagari(text)) return text;
        StringBuilder out = new StringBuilder(text.length() + 16);
        int i = 0, n = text.length();
        while (i < n) {
            String c = String.valueOf(text.charAt(i));
            if (c.equals("\u093C") || c.equals("\u200C") || c.equals("\u200D")) { i++; continue; }

            // two-char units for conjuncts first
            if (i + 2 < n && text.startsWith("ज्" + "ञ", i)) { out.append("gy"); i += 3; continue; }
            if (i + 2 < n && text.startsWith("क्" + "ष", i)) { out.append("ksh"); i += 3; continue; }

            if (CONSONANTS.containsKey(c)) {
                out.append(CONSONANTS.get(c));
                i++;
                if (i < n && text.charAt(i) == '्') { i++; continue; }        // halant
                String matra = i < n ? String.valueOf(text.charAt(i)) : "";
                if (MATRAS.containsKey(matra)) continue;                       // matra supplies vowel
                if (i >= n || !letterish(text.charAt(i))) continue;            // word-final: drop 'a'
                out.append("a");
                continue;
            }
            if (VOWELS.containsKey(c)) { out.append(VOWELS.get(c)); i++; continue; }
            if (MATRAS.containsKey(c)) { out.append(MATRAS.get(c)); i++; continue; }

            switch (c) {
                case "ं" -> {
                    char next = i + 1 < n ? text.charAt(i + 1) : 0;
                    out.append(next == 'प' || next == 'ब' || next == 'म' ? "m" : "n");
                }
                case "ँ" -> out.append("n");
                case "ः" -> out.append("h");
                case "।", "॥" -> out.append(".");
                case "ऽ" -> { }
                default -> {
                    char ch = text.charAt(i);
                    if (ch >= 0x0966 && ch <= 0x096F) out.append((char) ('0' + (ch - 0x0966)));
                    else out.append(ch);
                }
            }
            i++;
        }
        return out.toString();
    }

    private static final Pattern SPOKEN = Pattern.compile(
            "(?<!\\S)(full stop|period|comma|question mark|exclamation mark|exclamation point|colon|semicolon"
                    + "|new line|next line|new paragraph|अल्प विराम|पूर्ण विराम|दंड|प्रश्न चिह्न|विस्मयादिबोधक चिह्न)(?!\\S)",
            Pattern.CASE_INSENSITIVE);

    public static String smartWriting(String text, String mode) {
        text = text.trim();
        if (!"smart".equals(mode)) return text;

        java.util.Map<String, String> map = Map.ofEntries(
                Map.entry("full stop", "."), Map.entry("period", "."), Map.entry("comma", ","),
                Map.entry("question mark", "?"), Map.entry("exclamation mark", "!"),
                Map.entry("exclamation point", "!"), Map.entry("colon", ":"), Map.entry("semicolon", ";"),
                Map.entry("new line", "\n"), Map.entry("next line", "\n"), Map.entry("new paragraph", "\n\n"),
                Map.entry("अल्प विराम", ","), Map.entry("पूर्ण विराम", "।"), Map.entry("दंड", "।"),
                Map.entry("प्रश्न चिह्न", "?"), Map.entry("विस्मयादिबोधक चिह्न", "!"));
        var m = SPOKEN.matcher(text);
        StringBuilder sb = new StringBuilder();
        while (m.find()) {
            String key = m.group(1).toLowerCase();
            m.appendReplacement(sb, java.util.regex.Matcher.quoteReplacement(
                    map.getOrDefault(key, map.getOrDefault(m.group(1), m.group(1)))));
        }
        m.appendTail(sb);
        text = sb.toString();

        text = text.replaceAll("[ \\t\\u00A0]+", " ").replaceAll(" ?\n ?", "\n").trim();
        text = text.replaceAll("([,;:!?।])\\s*", "$1 ");
        text = text.replaceAll("(?<!\\d)\\.(?![\\d\\w])", ". ").replaceAll(" +", " ").trim();

        StringBuilder res = new StringBuilder(text.length());
        boolean cap = true;
        for (char c : text.toCharArray()) {
            if (cap && c < 128 && Character.isLetter(c)) { res.append(Character.toUpperCase(c)); cap = false; continue; }
            if (Character.isLetter(c)) cap = false;
            res.append(c);
            if (c == '.' || c == '!' || c == '?' || c == '\n') cap = true;
        }
        text = res.toString().replaceAll("(?<![A-Za-z])i(?![A-Za-z'])", "I");

        if (hasDevanagari(text) && !text.isEmpty()) {
            char last = text.charAt(text.length() - 1);
            if (".!?।:,\n".indexOf(last) < 0) text += "।";
        }
        return text;
    }
}
