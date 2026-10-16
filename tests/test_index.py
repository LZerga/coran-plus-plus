"""Step 3: the word forms of the corpus and the annotation checks, on the real database.

The index of forms itself is built on the cells (tests/test_units.py); no lemma is read.
"""

from collections import Counter

from quran_harness.buckwalter import to_arabic
from quran_harness.index import search_key


def test_a_typed_form_is_matched_without_vowels_and_with_a_plain_alef():
    assert search_key(to_arabic("Aloqawomi")) == to_arabic("Alqwm")
    assert search_key(to_arabic("{loqawomi")) == to_arabic("Alqwm")


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


def test_root_index_leaves_the_sura_opening_basmala_out_and_has_no_lemma(db):
    assert db.execute("SELECT count(*) FROM root_index WHERE aya = 0").fetchone()[0] == 0
    assert "lemma" not in {row[1] for row in db.execute("PRAGMA table_info(root_index)")}


def test_index_sizes(db):
    assert db.execute("SELECT count(DISTINCT root) FROM root_index").fetchone()[0] == 1642
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
