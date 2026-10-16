"""Lot C, level 0: the identity of a root, Quran side (SPEC §2.0). Test root قدر, then every root."""

import pytest

from quran_harness import __main__ as cli
from quran_harness import ingest
from quran_harness.buckwalter import to_arabic
from quran_harness.root_identity import identity, nature_of, pattern_of

QDR = to_arabic("qdr")


@pytest.mark.parametrize(
    "root, nature",
    [
        ("qdr", "صحيح — سالم"),
        ("Amn", "صحيح — مهموز"),  # an alef in a root of the corpus stands for a hamza
        ("rbb", "صحيح — مضعّف"),
        ("wjd", "معتل — مثال"),
        ("qwl", "معتل — أجوف"),
        ("hdy", "معتل — ناقص"),
        ("wqy", "معتل — لفيف مفروق"),
        ("Twy", "معتل — لفيف مقرون"),
    ],
)
def test_nature_of_the_root_letters(root, nature):
    assert nature_of(to_arabic(root)) == nature


def test_pattern_is_read_only_where_the_radicals_are_all_found():
    assert pattern_of(to_arabic("qadiyrN"), QDR, noun=True) == to_arabic("faEiyl")
    assert pattern_of(to_arabic("qa`dir"), QDR, noun=True) == to_arabic("faAEil")  # superscript alef written as an alef
    assert pattern_of(to_arabic("qa`diruwna"), QDR, noun=True) == to_arabic("faAEil")
    assert pattern_of(to_arabic("qaAla"), to_arabic("qwl")) is None  # weak root: not guessed


def test_qdr_every_occurrence_is_in_exactly_one_box(db):
    found = identity(db, QDR)
    assert (found.total, found.n_verbs, found.n_nouns) == (132, 41, 91)
    refs = [ref for boxes in (found.verbs, found.nouns) for entries in boxes.values() for e in entries for ref in e.refs]
    assert len(refs) == len(set(refs)) == 132


def test_qdr_verbs(db):
    found = identity(db, QDR)
    assert set(found.verbs) == {
        ("فَعَلَ", "ماضٍ معلوم"),
        ("فَعَلَ", "ماضٍ مجهول"),
        ("فَعَلَ", "مضارع معلوم"),
        ("فَعَّلَ", "ماضٍ معلوم"),
        ("فَعَّلَ", "مضارع معلوم"),
        ("فَعَّلَ", "أمر"),
    }
    present = found.verbs[("فَعَلَ", "مضارع معلوم")]
    yaqdir = [e for e in present if e.form == to_arabic("yaqodir")]
    assert sum(len(e.refs) for e in yaqdir) == 12  # D-02 again, now split by mood
    assert "مضارع مجهول" in found.absent_verbs and "اسْتَفْعَلَ" in found.absent_verbs
    assert found.bab["باب"] == "فَعَلَ يَفْعِلُ"


def test_qdr_nouns_use_only_what_the_corpus_states_or_an_ambiguous_box(db):
    found = identity(db, QDR)
    kinds = {kind for kind, _, _ in found.nouns}
    assert {"اسم الفاعل", "اسم المفعول", "مصدر"} <= kinds
    assert "ambiguë : صيغة مبالغة / صفة مشبهة" in kinds  # قَدِير : فَعِيل (D-23)
    assert ("اسم الفاعل", "VIII", "مُفْتَعِل") in found.nouns


def test_attached_letters_do_not_change_the_box(db):
    """لَقَدِير and قَدِير: the لَ is shown in the form and ignored for the classification (CHANGELOG v12)."""
    found = identity(db, QDR)
    box = found.nouns[("ambiguë : صيغة مبالغة / صفة مشبهة", "I", "فَعِيل")]
    assert {to_arabic("qadiyr"), to_arabic("laqadiyr")} <= {e.form for e in box}


def test_every_root_of_the_text_is_classified_whole(db):
    """The method is not tied to قدر: for every root, the boxes hold each occurrence once."""
    roots = [root for (root,) in db.execute("SELECT DISTINCT root FROM unit_roots")]
    assert len(roots) == 1642
    for root in roots:
        found = identity(db, root)
        refs = [ref for boxes in (found.verbs, found.nouns) for entries in boxes.values() for e in entries for ref in e.refs]
        assert len(refs) == found.total, root
    stems = db.execute(
        """SELECT count(*) FROM word_segments s JOIN units u ON u.word_id = s.word_id
           WHERE s.kind = 'stem' AND s.root IS NOT NULL AND u.part != 1 AND u.aya > 0"""
    ).fetchone()[0]
    assert stems == 49968


def test_command_line(built_db, monkeypatch, capsys):
    monkeypatch.setattr(ingest, "DB_PATH", built_db)
    assert cli.main(["identite", QDR]) == 0
    output = capsys.readouterr().out
    assert "## الأفعال" in output and "## الأسماء" in output and "132 occurrences" in output
    assert "non calculées" in output  # forms not used in the Quran: lot F
