"""Levelled normalisation of the Uthmani text (SPEC §3, documented in docs/NORMALISATION.md).

Normalisation only deletes code points; it never substitutes one letter for another.
Every code point of the base text belongs to exactly one class below, so a new
version of the text that brings an unknown sign is detected instead of ignored.
"""

from __future__ import annotations

import re
from enum import IntEnum


class Level(IntEnum):
    RAW = 0  # brut : le texte tel quel
    NO_RECITATION_MARKS = 1  # sans signes de récitation
    NO_VOWELS = 2  # sans voyelles : lettres écrites sur la ligne et hamza


# Letters written on the line, hamza forms included.
LETTERS = frozenset(chr(c) for c in range(0x0621, 0x064B) if c not in range(0x063B, 0x0641)) | {"ٱ"}
TATWEEL = "ـ"
HAMZA_ABOVE = "ٔ"  # a hamza with no seat of its own, carried by a tatweel

# Signs that guide recitation without being a letter or a vowel of the word.
RECITATION_MARKS = frozenset(
    "ٓ"  # maddah above
    "ۖۗۘۙۚۛ"  # pause marks
    "ۜ"  # small high seen
    "۞"  # rub el hizb
    "۟"  # small high rounded zero (letter never pronounced)
    "۠"  # small high upright rectangular zero (letter silent when continuing)
    "ۢ"  # small high meem (iqlab)
    "ۣ"  # small low seen
    "۩"  # sajdah
    "۪۫۬"  # imala, ishmam, tashil
    "ۭ"  # small low meem (iqlab)
)

# Vowels, and small letters added above or below the line.
VOWEL_MARKS = frozenset(
    "ًٌٍ"  # tanween
    "َُِ"  # fatha, damma, kasra
    "ّ"  # shadda
    "ْ"  # sukun
    "ٰ"  # superscript alef
    "ۥۦ"  # small waw, small yeh
    "ۧۨ"  # small high yeh, small high noon
)

KNOWN_CHARACTERS = LETTERS | RECITATION_MARKS | VOWEL_MARKS | {TATWEEL, HAMZA_ABOVE, " "}

# Once the small letter it carried is gone, a tatweel is left with nothing to carry.
_DANGLING_TATWEEL = re.compile(f"{TATWEEL}(?!{HAMZA_ABOVE})")


def normalize(text: str, level: Level | int) -> str:
    level = Level(level)
    if level is Level.RAW:
        return text
    dropped = RECITATION_MARKS if level is Level.NO_RECITATION_MARKS else RECITATION_MARKS | VOWEL_MARKS
    result = "".join(ch for ch in text if ch not in dropped)
    if level is Level.NO_VOWELS:
        result = _DANGLING_TATWEEL.sub("", result)
    return result


def letters_only(text: str) -> str:
    """Letters on the line, nothing else: used to align two editions of the text."""
    return "".join(ch for ch in text if ch in LETTERS)


def unknown_characters(text: str) -> set[str]:
    return set(text) - KNOWN_CHARACTERS


# --- The form (D-03, D-04) ------------------------------------------------------

SHADDA = "ّ"
TANWEEN_FATH = "ً"
SUPERSCRIPT_ALEF = "ٰ"
# What the last letter carries and the form leaves out (D-04): short vowels, tanween,
# sukun, and the small waw or yeh that lengthens the vowel of a pronoun.
FINAL_VOWEL_MARKS = frozenset("ًٌٍَُِْۥۦ")
# A tanween fath is written on the letter before its alef (مَرَضًا, هُدًى).
_TANWEEN_SEATS = frozenset("اى")


def split_final_vowel(text: str) -> tuple[str, str]:
    """(text without its final vowel, the marks removed). `text` is at level 1.

    Only marks are removed, never a letter: the alef of مَرَضًا stays, so a change of
    letters remains a difference of form (D-04). A shadda or a superscript alef on
    the last letter is not a vowel of الإعراب and stays too.
    """
    end = len(text)
    while end and text[end - 1] in FINAL_VOWEL_MARKS:
        end -= 1
    kept, removed = text[:end], text[end:]
    if len(kept) >= 2 and kept[-1] in _TANWEEN_SEATS and kept[-2] == TANWEEN_FATH:
        kept, removed = kept[:-2] + kept[-1], TANWEEN_FATH + removed
    return kept, removed


def drop_liaison_alef(text: str) -> str:
    """Remove the superscript alef of a final ى, which the text leaves out before an alef wasla (عَلَىٰ / عَلَى)."""
    return text[:-1] if text.endswith("ى" + SUPERSCRIPT_ALEF) else text


def drop_assimilation_shadda(text: str) -> str:
    """Remove the shadda a first letter takes from the word before it (لَّا → لَا). Level 1 text."""
    return text[0] + text[2:] if len(text) > 1 and text[1] == SHADDA and text[0] in LETTERS else text
