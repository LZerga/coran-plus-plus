"""The base text is split into words and put back together without any change."""

import pytest

from quran_harness.sources import load_manifest
from quran_harness.tanzil import Word, read_lines, read_words, rebuild_lines, split_lines

SOURCE = next(s for s in load_manifest() if s.id == "tanzil-uthmani")

TOY = [
    (1, 1, "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ"),
    (1, 2, "a b ۚ c ۖ"),
    (2, 1, "بِّسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ الٓمٓ"),
    (2, 2, "d ۛ e ۛ f"),
    (9, 1, "g h"),
]


def test_pause_marks_stay_with_the_word_they_follow():
    words = [w for w in split_lines(TOY) if (w.sura, w.aya) == (1, 2)]
    assert words == [
        Word(1, 2, 1, "a"),
        Word(1, 2, 2, "b", "ۚ"),
        Word(1, 2, 3, "c", "ۖ"),
    ]


def test_basmala_before_aya_1_is_kept_apart_as_aya_0():
    words = split_lines(TOY)
    assert [w.ref for w in words if w.sura == 2 and w.aya < 2] == ["2:0:1", "2:0:2", "2:0:3", "2:0:4", "2:1:1"]
    assert [w.ref for w in words if w.sura == 1 and w.aya == 1] == ["1:1:1", "1:1:2", "1:1:3", "1:1:4"]
    assert [w.ref for w in words if w.sura == 9] == ["9:1:1", "9:1:2"]


def test_toy_text_is_rebuilt_exactly():
    assert rebuild_lines(split_lines(TOY)) == {(s, a): text for s, a, text in TOY}


def test_missing_basmala_is_an_error():
    with pytest.raises(ValueError):
        split_lines([TOY[0], (2, 1, "a b c d e")])


def test_sign_without_a_word_before_is_an_error():
    with pytest.raises(ValueError):
        split_lines([(1, 1, "ۚ a")])


def test_base_text_is_rebuilt_exactly():
    """Step 2 validation: no word lost, none modified."""
    raw = {(s, a): text for s, a, text in read_lines(SOURCE.path)}
    assert rebuild_lines(read_words(SOURCE.path)) == raw


def test_unicode_normalisation_would_alter_the_base_text():
    """Why the code never applies NFC/NFD: the file is not in Unicode canonical order."""
    import unicodedata

    altered = sum(1 for _, _, text in read_lines(SOURCE.path) if unicodedata.normalize("NFC", text) != text)
    assert altered > 0


def test_base_text_word_counts():
    words = read_words(SOURCE.path)
    assert len(words) == 77881
    assert sum(1 for w in words if w.aya == 0) == 4 * 112
