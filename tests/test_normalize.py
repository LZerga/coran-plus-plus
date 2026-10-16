"""Normalisation levels (SPEC §3). Examples are words of the base text.

The examples are written in Buckwalter transliteration, not in Arabic script:
the base text does not follow Unicode canonical order (shadda before vowel,
alef followed by maddah), and an editor may silently reorder an Arabic literal.
"""

import pytest

from quran_harness.buckwalter import to_arabic
from quran_harness.normalize import (
    LETTERS,
    RECITATION_MARKS,
    VOWEL_MARKS,
    Level,
    letters_only,
    normalize,
    unknown_characters,
)
from quran_harness.sources import load_manifest
from quran_harness.tanzil import read_lines

SMALL_HIGH_YEH = "ۧ"  # not in the corpus transliteration table

EXAMPLES = [
    # raw, without recitation marks, without vowels
    ("wayaqodiru", "wayaqodiru", "wyqdr"),
    ("min[", "min", "mn"),  # small high meem (iqlab)
    ("{ls~amaA^'i", "{ls~amaA'i", "{lsmA'"),  # maddah
    ("'aAmanuwA@", "'aAmanuwA", "'AmnwA"),  # rounded zero on a silent alef
    ("{lr~aHoma`ni", "{lr~aHoma`ni", "{lrHmn"),  # superscript alef goes with the vowels
    ("lahu,", "lahu,", "lh"),  # small waw goes with the vowels
    ("$ayo_#FA", "$ayo_#FA", "$y_#A"),  # hamza carried by a tatweel is kept
]
EXAMPLES = [tuple(to_arabic(text) for text in example) for example in EXAMPLES]
# The tatweel goes away with the small yeh it carried.
IBRAHIM = to_arabic("<ibora`hi_") + SMALL_HIGH_YEH + to_arabic("ma")
EXAMPLES.append((IBRAHIM, IBRAHIM, to_arabic("<brhm")))


@pytest.mark.parametrize("raw, level1, level2", EXAMPLES)
def test_levels(raw, level1, level2):
    assert normalize(raw, Level.RAW) == raw
    assert normalize(raw, Level.NO_RECITATION_MARKS) == level1
    assert normalize(raw, Level.NO_VOWELS) == level2


@pytest.mark.parametrize("raw, level1, level2", EXAMPLES)
def test_levels_are_nested_and_stable(raw, level1, level2):
    assert normalize(level1, Level.NO_VOWELS) == level2
    assert normalize(level1, Level.NO_RECITATION_MARKS) == level1
    assert normalize(level2, Level.NO_VOWELS) == level2


@pytest.mark.parametrize("raw, level1, level2", EXAMPLES)
def test_normalisation_only_deletes(raw, level1, level2):
    remaining = iter(raw)
    assert all(ch in remaining for ch in level2)


def test_classes_do_not_overlap():
    assert not LETTERS & RECITATION_MARKS
    assert not LETTERS & VOWEL_MARKS
    assert not RECITATION_MARKS & VOWEL_MARKS


def test_letters_only():
    assert letters_only(to_arabic("wabi{lo_#aAxirapi")) == to_arabic("wb{lAxrp")


def test_unknown_characters_are_reported():
    assert unknown_characters(to_arabic("yaqodiru")) == set()
    assert unknown_characters(to_arabic("yaqodiru") + "!") == {"!"}


def test_every_character_of_the_base_text_is_classified():
    source = next(s for s in load_manifest() if s.id == "tanzil-uthmani")
    unknown = set()
    for _, _, text in read_lines(source.path):
        unknown |= unknown_characters(text)
    assert unknown == set()
