"""Step 5: comparison of two stretches of text (SPEC §2).

The structure tests use abstract tokens (a, b, c…), not Quranic text. The tests on
the real text compare the passages quoted by the SPEC, found by the `exemples` report.
"""

import pytest

from quran_harness import compare
from quran_harness.compare import DIFFERENCE, IDENTITY_PARTIAL, IDENTITY_TOTAL, SIMILARITY, Block, Pair, Settings
from quran_harness.config import load_config
from quran_harness.elements import Element, ElementLoader, parse_span

SETTINGS = Settings(frozenset({0}), frozenset({1, 2, 3}), 2, 2, True)


def el(written: str, core: str | None = None, lemma: str | None = None, root: str | None = None) -> Element:
    """A toy word: by default it is its own core and its own lemma, and has no root."""
    lemma = written if lemma is None else lemma
    return Element("0:0:0", 0, written, written, core or written, frozenset({lemma}), frozenset({root} if root else ()), "N")


def words(text: str) -> list[Element]:
    return [el(token) for token in text.split()]


# --- Equivalence scale --------------------------------------------------------


def test_level_0_same_word():
    assert compare.equivalence_level(el("ab"), el("ab")) == 0


def test_level_1_same_word_once_clitics_are_set_aside():
    assert compare.equivalence_level(el("w-ab", core="ab", lemma="AB"), el("ab-h", core="ab", lemma="AB")) == 1


def test_level_2_same_lemma():
    assert compare.equivalence_level(el("abu", lemma="AB"), el("aba", lemma="AB")) == 2


def test_level_3_same_root():
    assert compare.equivalence_level(el("ab", lemma="X", root="R"), el("cd", lemma="Y", root="R")) == 3


def test_unrelated_words_have_no_level():
    assert compare.equivalence_level(el("ab", root="R"), el("cd", root="S")) is None


def test_two_words_written_alike_with_different_lemmas_are_not_the_same_word():
    assert compare.equivalence_level(el("ab", lemma="X"), el("ab", lemma="Y")) is None
    assert compare.equivalence_level(el("ab", lemma="X", root="R"), el("ab", lemma="Y", root="R")) == 3


# --- Structure of a comparison ------------------------------------------------


def test_identical_stretches():
    result = compare.compare(words("a b c d"), words("a b c d"), SETTINGS)
    assert result.relation == IDENTITY_TOTAL
    assert result.blocks == (Block(0, 0, 4),)
    assert (result.extra_a, result.extra_b, result.same_order) == ((), (), True)


def test_two_identical_parts_around_extra_elements():
    """Structure of case 1 of the SPEC: "identité partielle, 2 parties"."""
    result = compare.compare(words("a b c d e f g X Y h i"), words("a b c d e f g h i"), SETTINGS)
    assert result.relation == IDENTITY_PARTIAL
    assert result.blocks == (Block(0, 0, 7), Block(9, 7, 2))
    assert (result.extra_a, result.extra_b, result.same_order) == ((7, 8), (), True)


def test_same_blocks_in_a_different_order():
    """Structure of case 3 of the SPEC."""
    result = compare.compare(words("a b c d e f"), words("a b e f c d"), SETTINGS)
    assert result.relation == IDENTITY_PARTIAL
    assert sorted(block.length for block in result.blocks) == [2, 2, 2]
    assert (result.extra_a, result.extra_b, result.same_order) == ((), (), False)


def test_identical_block_with_a_similar_pair_and_an_extra_element():
    """Structure of case 2 of the SPEC."""
    a = [el("q"), el("i"), el("rb-y", core="rb", lemma="RB"), *words("y r l s w")]
    b = [el("i"), el("rb-k", core="rb", lemma="RB"), *words("y r l s w")]
    result = compare.compare(a, b, SETTINGS)
    assert result.relation == IDENTITY_PARTIAL
    assert result.blocks == (Block(3, 2, 5),)
    assert result.pairs == (Pair(1, 0, 0), Pair(2, 1, 1))
    assert (result.extra_a, result.extra_b) == ((0,), ())


def test_similarity_without_any_identical_block():
    """Structure of case 4 of the SPEC: the reference form and one more element in common."""
    a = [el("x"), el("ref"), el("m"), el("ala-h", core="alay", lemma="ALA"), el("y")]
    b = [el("z"), el("ref"), el("ala", lemma="ALA"), el("t")]
    result = compare.compare(a, b, SETTINGS)
    assert result.relation == SIMILARITY
    assert result.blocks == ()
    assert [pair.level for pair in result.pairs] == [0, 2]


def test_difference_when_only_the_reference_form_is_common():
    result = compare.compare(words("x ref y"), words("z t ref"), SETTINGS)
    assert result.relation == DIFFERENCE
    assert result.common == 1


def test_reference_form_may_be_left_out_of_the_count():
    strict = Settings(frozenset({0}), frozenset({1, 2, 3}), 2, 2, reference_counts_as_element=False)
    a, b = words("x ref m y"), words("z ref t y")
    assert compare.compare(a, b, SETTINGS).relation == SIMILARITY
    assert compare.compare(a, b, strict).relation == DIFFERENCE


def test_a_single_identical_element_is_not_a_block():
    result = compare.compare(words("a x b"), words("a y b"), SETTINGS)
    assert result.blocks == ()
    assert result.relation == SIMILARITY


def test_each_element_is_used_once():
    result = compare.compare(words("a b a b"), words("a b"), SETTINGS)
    assert result.blocks == (Block(0, 0, 2),)
    assert result.extra_a == (2, 3)


def test_comparison_is_the_same_both_ways():
    a, b = words("a b c x d e"), words("d e y a b c")
    forward, backward = compare.compare(a, b, SETTINGS), compare.compare(b, a, SETTINGS)
    assert forward.relation == backward.relation
    assert forward.common == backward.common
    assert (forward.extra_a, forward.extra_b) == (backward.extra_b, backward.extra_a)


def test_settings_come_from_the_configuration():
    assert Settings.from_config(load_config()) == SETTINGS


# --- The passages quoted by the SPEC, on the real text -------------------------


@pytest.fixture(scope="module")
def spans(db):
    config = load_config()
    config["reference_form"]["match_level"] = 1
    loader = ElementLoader(db, config)
    return lambda text: loader.span(*parse_span(text))


def texts(elements, indexes) -> list[str]:
    return [elements[i].written for i in indexes]


def test_spec_case_2(spans):
    """Partial identity, a similar pair (ربي / ربك) and one extra element."""
    a, b = spans("34:36:1-8"), spans("17:30:1-7")
    result = compare.compare(a, b, SETTINGS)
    assert result.relation == IDENTITY_PARTIAL
    assert result.blocks == (Block(3, 2, 5),)
    assert [(a[p.a_index].ref, b[p.b_index].ref, p.level) for p in result.pairs] == [
        ("34:36:2", "17:30:1", 0),
        ("34:36:3", "17:30:2", 1),
    ]
    assert ([a[i].ref for i in result.extra_a], result.extra_b) == (["34:36:1"], ())
    assert result.same_order


def test_spec_case_3(spans):
    """The same blocks in a different order."""
    result = compare.compare(spans("14:18:13-18"), spans("2:264:28-33"), SETTINGS)
    assert result.relation == IDENTITY_PARTIAL
    assert result.blocks == (Block(0, 0, 2), Block(2, 4, 2), Block(4, 2, 2))
    assert (result.pairs, result.extra_a, result.extra_b, result.same_order) == ((), (), (), False)


def test_spec_case_4(spans):
    """Similarity (على ~ عليه) and different elements."""
    a, b = spans("90:5:1-6"), spans("16:75:4-9")
    result = compare.compare(a, b, SETTINGS)
    assert result.relation == SIMILARITY
    assert result.blocks == ()
    assert [(a[p.a_index].ref, b[p.b_index].ref, p.level) for p in result.pairs] == [
        ("90:5:4", "16:75:7", 0),
        ("90:5:5", "16:75:8", 2),
    ]
    assert (len(result.extra_a), len(result.extra_b)) == (4, 4)


def test_span_must_lie_inside_the_aya(spans):
    with pytest.raises(ValueError):
        spans("90:5:1-99")
    with pytest.raises(ValueError):
        parse_span("90:5")
