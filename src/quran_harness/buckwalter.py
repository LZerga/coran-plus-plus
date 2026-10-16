"""Extended Buckwalter transliteration used by the Quranic Arabic Corpus.

Table copied from the corpus documentation (https://corpus.quran.com/java/buckwalter.jsp,
read on 2026-10-10). Conversion is strict: an unknown character is an error.
"""

from __future__ import annotations

BUCKWALTER_TO_ARABIC = {
    "'": "ء",
    ">": "أ",
    "&": "ؤ",
    "<": "إ",
    "}": "ئ",
    "A": "ا",
    "b": "ب",
    "p": "ة",
    "t": "ت",
    "v": "ث",
    "j": "ج",
    "H": "ح",
    "x": "خ",
    "d": "د",
    "*": "ذ",
    "r": "ر",
    "z": "ز",
    "s": "س",
    "$": "ش",
    "S": "ص",
    "D": "ض",
    "T": "ط",
    "Z": "ظ",
    "E": "ع",
    "g": "غ",
    "_": "ـ",
    "f": "ف",
    "q": "ق",
    "k": "ك",
    "l": "ل",
    "m": "م",
    "n": "ن",
    "h": "ه",
    "w": "و",
    "Y": "ى",
    "y": "ي",
    "F": "ً",
    "N": "ٌ",
    "K": "ٍ",
    "a": "َ",
    "u": "ُ",
    "i": "ِ",
    "~": "ّ",
    "o": "ْ",
    "^": "ٓ",
    "#": "ٔ",
    "`": "ٰ",
    "{": "ٱ",
    ":": "ۜ",
    "@": "۟",
    '"': "۠",
    "[": "ۢ",
    ";": "ۣ",
    ",": "ۥ",
    ".": "ۦ",
    "!": "ۨ",
    "-": "۪",
    "+": "۫",
    "%": "۬",
    "]": "ۭ",
}


def to_arabic(text: str, passthrough: str = " ") -> str:
    """Convert Buckwalter to Arabic script; `passthrough` characters are kept as they are."""
    try:
        return "".join(ch if ch in passthrough else BUCKWALTER_TO_ARABIC[ch] for ch in text)
    except KeyError as error:
        raise ValueError(f"caractère Buckwalter inconnu {error.args[0]!r} dans {text!r}") from None
