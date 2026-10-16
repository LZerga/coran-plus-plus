import pytest

from quran_harness.buckwalter import BUCKWALTER_TO_ARABIC, to_arabic


def test_table_is_one_to_one():
    assert len(set(BUCKWALTER_TO_ARABIC.values())) == len(BUCKWALTER_TO_ARABIC)


@pytest.mark.parametrize(
    "buckwalter, arabic",
    [
        ("bi", "بِ"),
        ("{ll~ahi", "ٱللَّهِ"),  # shadda, then fatha
        ("r~aHoma`ni", "رَّحْمَٰنِ"),
        ("qdr", "قدر"),
        ("<ilo yaAsiyna", "إِلْ يَاسِينَ"),
    ],
)
def test_to_arabic(buckwalter, arabic):
    assert to_arabic(buckwalter) == arabic


def test_unknown_character_is_an_error():
    with pytest.raises(ValueError):
        to_arabic("qdr2")
    assert to_arabic("qdr2", passthrough="2") == "قدر2"
