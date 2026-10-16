"""Step 6: association measures and random controls, on toy data with a known answer."""

import math

import numpy as np
import pytest

from quran_harness import stats
from quran_harness.stats import Corpus, benjamini_hochberg, log_likelihood, pmi


def item(name: str) -> tuple[str, str, str]:
    return (name, name, "")


def toy_corpus(segments: list[str], suras: list[int] | None = None) -> Corpus:
    """One string of space-separated words per segment."""
    items, segment_ids, sura_ids, refs = [], [], [], []
    for number, text in enumerate(segments):
        for position, word in enumerate(text.split()):
            items.append(item(word))
            segment_ids.append(number)
            sura_ids.append(suras[number] if suras else 1)
            refs.append(f"{number}:{position}")
    return Corpus(items, segment_ids, sura_ids, refs)


def refs_of(corpus: Corpus, word: str) -> list[str]:
    index = corpus.keys[item(word)]
    return [ref for ref, token in corpus.token_of_ref.items() if corpus.item[token] == index]


# --- Measures -----------------------------------------------------------------


def test_pmi_is_zero_under_independence():
    assert pmi(n_xy=10, n_x=100, n_y=100, n=1000) == pytest.approx(0)


def test_pmi_of_two_words_always_together():
    assert pmi(n_xy=5, n_x=5, n_y=5, n=40) == pytest.approx(3)  # log2(40 / 5)


def test_pmi_without_any_cooccurrence():
    assert pmi(0, 5, 5, 40) == -math.inf


def test_log_likelihood_is_zero_under_independence():
    assert log_likelihood(n_xy=10, n_x=100, n_y=100, n=1000) == pytest.approx(0)


def test_log_likelihood_of_a_perfect_association():
    # two segments, X and Y together in one: each diagonal cell has 1 observed for 0.5 expected
    assert log_likelihood(n_xy=1, n_x=1, n_y=1, n=2) == pytest.approx(4 * math.log(2))


def test_log_likelihood_grows_with_the_association():
    assert log_likelihood(20, 100, 100, 1000) > log_likelihood(12, 100, 100, 1000) > 0


def test_benjamini_hochberg():
    assert benjamini_hochberg([0.01, 0.04, 0.03, 0.5]) == pytest.approx([0.04, 0.04 * 4 / 3, 0.04 * 4 / 3, 0.5])
    assert benjamini_hochberg([]) == []
    assert all(q >= p for p, q in zip([0.2, 0.01, 0.9], benjamini_hochberg([0.2, 0.01, 0.9])))


# --- Counting -----------------------------------------------------------------

# 42 segments of 4 words. X is in 8 of them.
#   Y  always with X, and nowhere else
#   F  frequent: in half of the segments, with X or not alike
#   R  with X once only
SEGMENTS = ["X Y F a"] * 4 + ["X Y b a"] * 3 + ["X Y R a"] + ["F b c d"] * 17 + ["e b c d"] * 12 + ["R b c d"] * 5


def test_cooccurrences_and_marginals_are_counted_in_segments():
    corpus = toy_corpus(SEGMENTS)
    results = corpus.associations(refs_of(corpus, "X"), [item("Y"), item("F"), item("R")], ["corpus"], 50, seed=1)
    assert [(r.n_xy, r.n_x, r.n_y, r.n) for r in results] == [(8, 8, 8, 42), (4, 8, 21, 42), (1, 8, 6, 42)]
    assert results[0].pmi == pytest.approx(math.log2(42 / 8))
    assert results[1].pmi == pytest.approx(0)


def test_a_word_repeated_in_a_segment_counts_once():
    corpus = toy_corpus(["X Y Y Y", "Y a", "b c"])
    (result,) = corpus.associations(refs_of(corpus, "X"), [item("Y")], ["corpus"], 10, seed=1)
    assert (result.n_xy, result.n_y) == (1, 2)


def test_reference_word_is_not_its_own_companion():
    corpus = toy_corpus(["X X a", "X b", "c d"])
    (result,) = corpus.associations(refs_of(corpus, "X"), [item("X")], ["corpus"], 10, seed=1)
    assert result.n_xy == 0


# --- Random control -----------------------------------------------------------


@pytest.fixture(scope="module")
def controlled():
    corpus = toy_corpus(SEGMENTS)
    results = corpus.associations(refs_of(corpus, "X"), [item("Y"), item("F"), item("R")], ["corpus"], 500, seed=7)
    return dict(zip("YFR", results))


def test_true_association_is_above_chance(controlled):
    control = controlled["Y"].controls["corpus"]
    assert control.p_value == pytest.approx(1 / 501)  # no shuffle reaches the observed count
    assert control.expected < 2
    assert controlled["Y"].reading(alpha=0.05, min_cooccurrence=2) == "au-dessus du hasard"


def test_word_found_everywhere_is_explained_by_its_frequency(controlled):
    """SPEC step 6: an association due only to the general frequency of the word is flagged."""
    control = controlled["F"].controls["corpus"]
    assert controlled["F"].n_xy == 4  # found with X four times, yet no more than a shuffle gives
    assert control.p_value > 0.05
    assert 2 < control.expected < 5
    assert controlled["F"].reading(alpha=0.05, min_cooccurrence=2) == "attendu par la seule fréquence du mot"


def test_single_cooccurrence_is_too_rare_to_conclude(controlled):
    assert controlled["R"].reading(alpha=0.05, min_cooccurrence=2) == "trop rare pour conclure"


def test_same_seed_gives_the_same_result():
    corpus = toy_corpus(SEGMENTS)
    run = lambda seed: corpus.associations(refs_of(corpus, "X"), [item("F"), item("R")], ["corpus", "sura"], 200, seed)  # noqa: E731
    assert run(3) == run(3)
    assert run(3) != run(4)


def test_shuffle_keeps_the_words_and_the_segment_sizes():
    corpus = toy_corpus(SEGMENTS)
    rng = np.random.default_rng(0)
    for control in stats.CONTROLS:
        shuffled = corpus._shuffled_segments(rng, control)
        assert sorted(shuffled) == sorted(corpus.segment)
        assert not np.array_equal(shuffled, corpus.segment)


def test_sura_control_keeps_each_word_in_its_sura():
    corpus = toy_corpus(["X Y a b", "c d e f", "X Y g h", "i j k l"], suras=[1, 1, 2, 2])
    rng = np.random.default_rng(0)
    for _ in range(20):
        shuffled = corpus._shuffled_segments(rng, "sura")
        assert set(shuffled[corpus.sura == 1]) == {0, 1} and set(shuffled[corpus.sura == 2]) == {2, 3}


def test_sura_control_is_stricter_for_words_that_only_share_a_sura():
    """X and Y are never in the same segment more than chance inside their sura, but both live only there."""
    sura_1 = ["X a b", "Y c d", "X Y e", "f g h"] * 3
    sura_2 = ["i j k", "l m n", "o p q", "r s t"] * 12
    corpus = toy_corpus(sura_1 + sura_2, suras=[1] * len(sura_1) + [2] * len(sura_2))
    (result,) = corpus.associations(refs_of(corpus, "X"), [item("Y")], ["corpus", "sura"], 500, seed=5)
    assert result.controls["corpus"].p_value < result.controls["sura"].p_value
    assert result.controls["sura"].expected > result.controls["corpus"].expected


def test_unknown_control_is_an_error():
    corpus = toy_corpus(SEGMENTS)
    with pytest.raises(ValueError):
        corpus.associations(refs_of(corpus, "X"), [item("Y")], ["verset"], 5, seed=1)


def test_words_must_come_in_text_order():
    with pytest.raises(ValueError):
        Corpus([item("a"), item("b")], [0, 1], [2, 1])
