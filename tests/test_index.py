"""Step 3 validation: the index of roots and forms, on the real database."""

from collections import Counter

import pytest

from quran_harness.buckwalter import to_arabic
from quran_harness.config import form_level, load_config
from quran_harness.index import forms_of_root, occurrences_of_form, search_key, unrooted_occurrences

YAQDIR = to_arabic("yqdr")
QAWM = to_arabic("qwm")
QADARA, QADDARA = to_arabic("qadara"), to_arabic("qad~ara")

# SPEC §5 step 3 and §7: the form يقدر is found in 12 ayas.
YAQDIR_AYAS = ["13:26", "16:75", "16:76", "17:30", "28:82", "29:62", "30:37", "34:36", "34:39", "39:52", "42:12", "90:5"]


def ayas(occurrences) -> list[str]:
    return [o.ref.rsplit(":", 1)[0] for o in occurrences]


def test_yaqdir_without_clitics_is_in_the_12_ayas_of_the_spec(db):
    found = [o for o in occurrences_of_form(db, YAQDIR, "core") if o.lemma == QADARA]
    assert ayas(found) == YAQDIR_AYAS


def test_yaqdir_as_written_is_in_3_ayas_only(db):
    found = [o for o in occurrences_of_form(db, YAQDIR, "written") if o.lemma == QADARA]
    assert ayas(found) == ["16:75", "16:76", "90:5"]


def test_homograph_of_yaqdir_is_kept_apart_by_its_lemma(db):
    found = [o for o in occurrences_of_form(db, YAQDIR, "core") if o.lemma != QADARA]
    assert [(o.lemma, o.ref) for o in found] == [(QADDARA, "73:20:17")]


@pytest.mark.parametrize("level, occurrences, n_ayas", [("written", 79, 73), ("core", 278, 253), ("bare", 343, 312)])
def test_qawm_counts_at_each_level(db, level, occurrences, n_ayas):
    """SPEC says "about 150": no level gives it (QUESTIONS.md, Q15). Figures recorded as observed."""
    found = occurrences_of_form(db, QAWM, level)
    assert {o.lemma for o in found} == {to_arabic("qawom")}
    assert (len(found), len(set(ayas(found)))) == (occurrences, n_ayas)


def test_lemma_qawm_has_383_occurrences(db):
    rows = [r for r in forms_of_root(db, QAWM, "bare") if r.lemma == to_arabic("qawom")]
    assert sum(r.occurrences for r in rows) == 383


def test_root_can_be_typed_with_a_hamza(db):
    assert forms_of_root(db, to_arabic(">mn"), "core") == forms_of_root(db, to_arabic("Amn"), "core")
    assert forms_of_root(db, to_arabic(">mn"), "core")


def test_form_can_be_typed_with_vowels_and_a_plain_alef(db):
    typed = to_arabic("Aloqawomi")  # plain alef, vowels
    assert search_key(typed) == to_arabic("Alqwm")
    assert len(occurrences_of_form(db, typed, "core")) == 62


def test_every_word_has_its_forms_and_nothing_is_rewritten(db):
    rows = db.execute(
        """SELECT w.text_raw, w.text_norm2, f.core_raw, f.core_norm2, f.bare_norm2
           FROM words w LEFT JOIN word_forms f ON f.word_id = w.id"""
    ).fetchall()
    assert len(rows) == 77881
    for text, norm2, core, core_norm2, bare_norm2 in rows:
        assert core and core in text  # the core is a piece of the word as written
        assert core_norm2 in norm2 and bare_norm2 in core_norm2


def test_words_without_clitics_are_their_own_core(db):
    different = db.execute(
        """SELECT count(*) FROM words w JOIN word_forms f ON f.word_id = w.id
           WHERE f.proclitics = 0 AND f.complement_pronouns = f.elided_pronouns AND f.core_raw != w.text_raw"""
    )
    assert different.fetchone()[0] == 0


def test_root_index_leaves_the_sura_opening_basmala_out(db):
    assert db.execute("SELECT count(*) FROM root_index WHERE aya = 0").fetchone()[0] == 0
    assert unrooted_occurrences(db, to_arabic("bsm"), "written") == (0, 112)


def test_index_sizes(db):
    assert db.execute("SELECT count(DISTINCT root), count(DISTINCT lemma) FROM root_index").fetchone() == (1642, 4657)
    # one row per word and root: 49 967 words carry a root, one of them carries two
    assert db.execute("SELECT count(*), count(DISTINCT word_id) FROM root_index").fetchone() == (49968, 49967)


def test_corrected_fork_changes_the_root_of_757_words(db):
    kinds = dict(db.execute("SELECT kind, count(*) FROM root_differences GROUP BY kind"))
    assert kinds == {"added": 374, "removed": 73, "changed": 310}


def test_pronoun_rule_agrees_with_masaq_on_all_but_420_words(db):
    assert db.execute("SELECT count(*) FROM pronoun_checks").fetchone()[0] == 420
    patterns = Counter(
        db.execute("SELECT subject_ours, complement_ours, subject_masaq, complement_masaq FROM pronoun_checks").fetchall()
    )
    # Never does MASAQ see a subject where the rule sees a complement only, on more than a handful of words.
    assert patterns[(0, 1, 1, 0)] < 20


def test_configuration_selects_the_spec_default_level():
    assert form_level(load_config()) == "written"
    assert form_level({"reference_form": {"match_level": 1, "article_is_clitic": False}}) == "core"
    assert form_level({"reference_form": {"match_level": 1, "article_is_clitic": True}}) == "bare"
