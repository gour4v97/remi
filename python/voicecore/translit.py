"""Devanagari → readable Roman (Hinglish) transliteration. Port of the C# Translit."""
import re

VOWELS = {"अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo",
          "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "ऋ": "ri",
          "ॲ": "e", "ऍ": "e", "ऑ": "o", "ऒ": "o"}

CONSONANTS = {"क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n",
              "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n",
              "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
              "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
              "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
              "य": "y", "र": "r", "ल": "l", "व": "v",
              "श": "sh", "ष": "sh", "स": "s", "ह": "h", "ळ": "l",
              "\u0958": "q", "\u0959": "kh", "\u095A": "g", "\u095B": "z",
              "\u095C": "r", "\u095D": "rh", "\u095E": "f", "\u095F": "y"}

MATRAS = {"ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u",
          "े": "e", "ै": "ai", "ो": "o", "ौ": "au",
          "ृ": "ri", "ॄ": "ri", "ॢ": "l", "ॉ": "o", "ॅ": "e", "ॊ": "o"}


def has_devanagari(s: str) -> bool:
    return any("\u0900" <= c <= "\u097F" for c in s)


def _letterish(c: str) -> bool:
    return ("\u0900" <= c <= "\u097F") or c.isalnum() or c in "\u200c\u200d"


def to_roman(text: str) -> str:
    if not has_devanagari(text):
        return text
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "\u093C" or c in "\u200c\u200d":
            i += 1
            continue
        if c in CONSONANTS:
            # friendly conjuncts: ज्ञ → gy, क्ष → ksh
            if c == "ज" and i + 2 < n and text[i + 1] == "्" and text[i + 2] == "ञ":
                out.append("gy"); i += 3; continue
            if c == "क" and i + 2 < n and text[i + 1] == "्" and text[i + 2] == "ष":
                out.append("ksh"); i += 3; continue
            out.append(CONSONANTS[c])
            i += 1
            if i < n and text[i] == "्":        # halant: no inherent vowel
                i += 1; continue
            if i < n and text[i] in MATRAS:      # following matra supplies the vowel
                continue
            if i >= n or not _letterish(text[i]):  # word-final: drop inherent 'a'
                continue
            out.append("a")                      # inherent short 'a' mid-word
            continue
        if c in VOWELS:
            out.append(VOWELS[c]); i += 1; continue
        if c in MATRAS:
            out.append(MATRAS[c]); i += 1; continue
        if c == "ं":
            out.append("m" if (i + 1 < n and text[i + 1] in "पबम") else "n")
        elif c == "ँ":
            out.append("n")
        elif c == "ः":
            out.append("h")
        elif c in "।॥":
            out.append(".")
        elif c == "ऽ":
            pass
        elif "\u0966" <= c <= "\u096F":
            out.append(chr(ord("0") + ord(c) - 0x0966))
        else:
            out.append(c)
        i += 1
    return "".join(out)


def smart_writing(text: str, mode: str) -> str:
    """Port of the C# Writing.Apply (deterministic, no cloud)."""
    text = text.strip()
    if mode != "smart":
        return text
    spoken = [("full stop", "."), ("period", "."), ("comma", ","), ("question mark", "?"),
              ("exclamation mark", "!"), ("exclamation point", "!"), ("colon", ":"), ("semicolon", ";"),
              ("new line", "\n"), ("next line", "\n"), ("new paragraph", "\n\n"),
              ("अल्प विराम", ","), ("पूर्ण विराम", "।"), ("दंड", "।"),
              ("प्रश्न चिह्न", "?"), ("विस्मयादिबोधक चिह्न", "!")]
    for phrase, repl in spoken:
        text = re.sub(r"(?<!\S)" + re.escape(phrase) + r"(?!\S)", repl, text, flags=re.IGNORECASE)
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text).strip()
    text = re.sub(r"([,;:!?।])\s*", r"\1 ", text)
    text = re.sub(r"(?<!\d)\.(?![\d\w])", ". ", text)
    text = re.sub(r" +", " ", text).strip()
    # capitalize sentence starts
    res, cap = [], True
    for c in text:
        if cap and c.isascii() and c.isalpha():
            res.append(c.upper()); cap = False; continue
        if c.isalpha():
            cap = False
        res.append(c)
        if c in ".!?\n":
            cap = True
    text = re.sub(r"(?<![A-Za-z])i(?![A-Za-z'])", "I", "".join(res))
    if has_devanagari(text) and text and text[-1] not in ".!?।:,\n":
        text += "।"
    return text
