"""The word without its clitics. Words are written in Buckwalter transliteration."""

from typing import NamedTuple

import pytest

from quran_harness import alt_roots, masaq
from quran_harness.buckwalter import BUCKWALTER_TO_ARABIC, to_arabic
from quran_harness.forms import WordForm, analyse, has_attached_subject

ARABIC_TO_BUCKWALTER = {arabic: latin for latin, arabic in BUCKWALTER_TO_ARABIC.items()}


def to_latin(text: str) -> str:
    return "".join(ARABIC_TO_BUCKWALTER[ch] for ch in text)


class Seg(NamedTuple):
    kind: str
    tag: str
    form: str
    features: str


def prefix(form: str, feature: str, tag: str = "P") -> Seg:
    return Seg("prefix", tag, to_arabic(form), f"PREFIX|{feature}")


def stem(form: str, tag: str, features: str = "") -> Seg:
    return Seg("stem", tag, to_arabic(form), f"STEM|POS:{tag}|{features}".rstrip("|"))


def pron(form: str, pgn: str) -> Seg:
    return Seg("suffix", "PRON", to_arabic(form), f"SUFFIX|PRON:{pgn}")


def form_of(segments: list[Seg], text: str | None = None) -> tuple:
    """(core, bare, subject pronouns, complement pronouns), core and bare in Buckwalter."""
    result = analyse(to_arabic(text) if text else "".join(s.form for s in segments), segments)
    return to_latin(result.core), to_latin(result.bare), result.subject_pronouns, result.complement_pronouns


def test_proclitic_is_set_aside():
    assert form_of([prefix("wa", "w:CONJ+"), stem("yaqodiru", "V", "IMPF|3MS")]) == ("yaqodiru", "yaqodiru", 0, 0)


def test_article_stays_in_the_core_and_leaves_the_bare_form():
    segments = [prefix("wa", "w:CONJ+"), prefix("{lo", "Al+", "DET"), stem("Haq~i", "N")]
    assert form_of(segments) == ("{loHaq~i", "Haq~i", 0, 0)
    assert analyse("".join(s.form for s in segments), segments).has_article


def test_subject_pronoun_is_part_of_the_verb():
    assert form_of([stem("yaqodiru", "V", "IMPF|3MP"), pron("wna", "3MP")]) == ("yaqodiruwna", "yaqodiruwna", 1, 0)


def test_object_pronoun_is_set_aside():
    assert form_of([stem("xalaqa", "V", "PERF|3MS"), pron("kumo", "2MP")]) == ("xalaqa", "xalaqa", 0, 1)


def test_subject_then_object_pronoun():
    segments = [stem("razaqo", "V", "PERF|1P"), pron("na`", "1P"), pron("humo", "3MP")]
    assert form_of(segments) == ("razaqona`", "razaqona`", 1, 1)


def test_no_subject_pronoun_after_an_emphatic_nun():
    nun = Seg("suffix", "EMPH", to_arabic("n~a"), "SUFFIX|+n:EMPH")
    segments = [stem("tubay~inu", "V", "IMPF|2MP"), nun, pron("hu", "3MS")]
    assert form_of(segments) == ("tubay~inun~a", "tubay~inun~a", 0, 1)


def test_possessive_pronoun_on_a_noun():
    assert form_of([prefix("li", "l:P+"), stem("qawomi", "N"), pron("hi", "3MS")]) == ("qawomi", "qawomi", 0, 1)


def test_preposition_written_with_a_pronoun_keeps_the_preposition():
    assert form_of([prefix("la", "l:P+"), stem("hu", "PRON", "3MS")]) == ("la", "la", 0, 1)
    with_conjunction = [prefix("wa", "w:CONJ+"), prefix("bi", "bi+"), stem("hi", "PRON", "3MS")]
    assert form_of(with_conjunction) == ("bi", "bi", 0, 1)


def test_independent_pronoun_is_not_a_complement():
    assert form_of([prefix("wa", "w:CIRC+"), stem("humo", "PRON", "3MP")]) == ("humo", "humo", 0, 0)


def test_pronoun_annotated_but_not_written_is_counted_as_elided():
    segments = [prefix("ya`", "ya+", "VOC"), stem("qawomi", "N"), pron("", "1S")]
    result = analyse("".join(s.form for s in segments), segments)
    assert (result.core, result.complement_pronouns, result.elided_pronouns) == (to_arabic("qawomi"), 1, 1)


def test_boundaries_are_found_despite_a_different_hamza_encoding():
    """Base text: hamza on a tatweel. Corpus: bare hamza. The result is cut from the base text."""
    segments = [prefix("wa", "w:CONJ+"), prefix("bi", "bi+"), prefix("{lo", "Al+", "DET"), stem("'aAxirapi", "N")]
    assert form_of(segments, text="wabi{lo_#aAxirapi") == ("{lo_#aAxirapi", "_#aAxirapi", 0, 0)


def test_word_without_annotation_is_left_whole():
    assert analyse("abc", []) == WordForm("abc", "abc", False, 0, 0, 0)


def test_unexplained_word_is_an_error():
    with pytest.raises(ValueError):
        analyse(to_arabic("qdr"), [prefix("wa", "w:CONJ+"), stem("qdr", "N")])


@pytest.mark.parametrize(
    "features, expected",
    [
        ("STEM|POS:V|PERF|LEM:x|ROOT:y|3MS", False),
        ("STEM|POS:V|PERF|LEM:x|ROOT:y|3FS", False),
        ("STEM|POS:V|PERF|(IV)|LEM:x|ROOT:y|3MP", True),
        ("STEM|POS:V|PERF|LEM:x|ROOT:y|1P", True),
        ("STEM|POS:V|IMPF|LEM:x|ROOT:y|3MS", False),
        ("STEM|POS:V|IMPF|LEM:x|ROOT:y|1P", False),
        ("STEM|POS:V|IMPF|LEM:x|ROOT:y|3MP|MOOD:JUS", True),
        ("STEM|POS:V|IMPF|LEM:x|ROOT:y|2D", True),
        ("STEM|POS:V|IMPV|LEM:x|ROOT:y|2MS", False),
        ("STEM|POS:V|IMPV|LEM:x|ROOT:y|2MP", True),
    ],
)
def test_which_verb_forms_carry_a_subject_pronoun(features, expected):
    assert has_attached_subject(features) is expected


# --- MASAQ and the corrected fork ---------------------------------------------


def masaq_row(kind: str, tag: str, role: str, segment: str = "x") -> dict[str, str]:
    return {"Morph_Type": kind, "Morph_Tag": tag, "Syntactic_Role": role, "Segmented_Word": segment}


@pytest.mark.parametrize(
    "row, expected",
    [
        (masaq_row("Suffix", "SUBJ_PRON", "AGNT"), "subject"),
        (masaq_row("Suffix", "POSS_PRON", "AGNT"), "subject"),  # irregular tag, clear role
        (masaq_row("Suffix", "SUBJ_PRON", "OBJ"), "complement"),
        (masaq_row("Suffix", "POSS_PRON", "GEN_CONS"), "complement"),
        (masaq_row("Suffix", "PRON_3MS", "PREP_OBJ"), "complement"),
        (masaq_row("Stem", "PRON", "PREP_OBJ"), "complement"),
        (masaq_row("Stem", "PRON", "SUBJ"), None),
        (masaq_row("Suffix", "PVSUFF_SUBJ:3MS", "", "(null)"), None),
        (masaq_row("Suffix", "REL_PRON", "PREP_OBJ"), None),
        (masaq_row("Suffix", "NSUFF_FEM_SG", ""), None),
    ],
)
def test_masaq_pronoun_kind(row, expected):
    assert masaq.pronoun_kind(row) == expected


def test_fold_hamza_writes_every_hamza_as_an_alef():
    assert alt_roots.fold_hamza(to_arabic(">mn")) == to_arabic("Amn")
    assert alt_roots.fold_hamza(to_arabic("s>l")) == to_arabic("sAl")
    assert alt_roots.fold_hamza(to_arabic("qdr")) == to_arabic("qdr")
