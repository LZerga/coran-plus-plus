"""Lot A: the cells (waw of conjunction apart, D-02) and the form without lemma (D-03, D-04)."""

import pytest

from quran_harness import __main__ as cli
from quran_harness import __version__, ingest
from quran_harness.buckwalter import to_arabic
from quran_harness.config import load_config
from quran_harness.normalize import drop_assimilation_shadda, split_final_vowel
from quran_harness.units import FormSettings, by_form, form_of, forms_of_root, occurrences_of_form, segment_sizes

SETTINGS = FormSettings.from_config(load_config())
YAQDIR = to_arabic("yqdr")
# DECISIONS.md, D-02: the 12 ayas of يقدر.
YAQDIR_AYAS = ["13:26", "16:75", "16:76", "17:30", "28:82", "29:62", "30:37", "34:36", "34:39", "39:52", "42:12", "90:5"]


def form(buckwalter: str, core_end: int | None = None, **changes) -> str:
    settings = FormSettings(**{**vars(SETTINGS), **changes})
    return form_of(to_arabic(buckwalter), core_end, settings)[0]


# --- The form ------------------------------------------------------------------


@pytest.mark.parametrize(
    "word, kept, removed",
    [
        ("yaqodiru", "yaqodir", "u"),
        ("yaqodira", "yaqodir", "a"),
        ("yaqodiruwna", "yaqodiruwn", "a"),
        ("rab~i", "rab~", "i"),  # the shadda is not a vowel of الإعراب
        ("EalaY`", "EalaY`", ""),  # neither is the superscript alef
        ("maraDFA", "maraDA", "F"),  # tanween written before its alef: the alef, a letter, stays
        ("hudFY", "hudY", "F"),
        ("$aYo'K", "$aYo'", "K"),
        ("Ealayohimo", "Ealayohim", "o"),
    ],
)
def test_final_vowel_is_split_off_and_no_letter_is_removed(word, kept, removed):
    assert split_final_vowel(to_arabic(word)) == (to_arabic(kept), to_arabic(removed))


def test_assimilation_shadda_of_the_first_letter_is_dropped():
    assert drop_assimilation_shadda(to_arabic("l~aA")) == to_arabic("laA")
    assert drop_assimilation_shadda(to_arabic("rab~i")) == to_arabic("rab~i")


def test_liaison_alef_of_a_final_alef_maqsura_is_dropped():
    assert form("EalaY`") == form("EalaY") == to_arabic("EalaY")
    assert form("EalaY`", assimilation_marks_in_form=True) == to_arabic("EalaY`")


def test_form_settings_can_bring_the_marks_back():
    assert form("m~im~aA") == form("mim~aA") == to_arabic("mim~aA")
    assert form("m~im~aA", assimilation_marks_in_form=True) == to_arabic("m~im~aA")
    assert form("yaqodiru", final_vowel_in_form=True) == to_arabic("yaqodiru")


def test_case_vowel_before_an_attached_pronoun_is_left_out_too():
    """رَبِّى and رَبَّكَ: the vowel of الإعراب is inside the written word."""
    assert form_of(to_arabic("rab~aka"), 5, SETTINGS) == (to_arabic("rab~k"), to_arabic("a"), to_arabic("a"))
    assert form_of(to_arabic("lahu"), 2, SETTINGS)[0] == to_arabic("lah")  # the vowel of a one-letter preposition stays


# --- The cells, on the real database ---------------------------------------------


def test_every_word_is_given_back_by_its_cells(db):
    rows = db.execute(
        """SELECT w.text_raw, group_concat(u.text_raw, ''), count(*) FROM words w
           JOIN (SELECT * FROM units ORDER BY id) u ON u.word_id = w.id GROUP BY w.id"""
    ).fetchall()
    assert len(rows) == 77881
    assert all(text == joined for text, joined, _ in rows)
    assert {n for _, _, n in rows} == {1, 2}


def test_the_six_kinds_of_attached_waw_are_set_apart_at_the_head_of_a_word(db):
    assert db.execute("SELECT part, count(*) FROM units GROUP BY part ORDER BY part").fetchall() == [
        (0, 68346),
        (1, 9535),
        (2, 9535),
    ]
    tags = dict(
        db.execute(
            """SELECT s.features, count(*) FROM units u JOIN word_segments s ON s.word_id = u.word_id AND s.seg_no = 1
               WHERE u.part = 1 GROUP BY s.features"""
        )
    )
    assert tags == {
        "PREFIX|w:CONJ+": 8173,
        "PREFIX|w:REM+": 1034,
        "PREFIX|w:CIRC+": 292,
        "PREFIX|w:P+": 25,
        "PREFIX|w:SUP+": 8,
        "PREFIX|w:COM+": 3,
    }
    # A waw inside a word (أَوَلَمْ) stays: setting it apart would cut the word in three.
    assert db.execute("SELECT count(*) FROM units u JOIN words w ON w.id = u.word_id WHERE w.ref = '30:37:1'").fetchone()[0] == 1
    waw = {text for (text,) in db.execute("SELECT DISTINCT skeleton FROM units WHERE part = 1")}
    assert waw == {to_arabic("w")}


def test_a_radical_waw_and_other_attached_letters_stay_in_the_word(db):
    for buckwalter in ("fqdr", "bqdr", "lqdyr"):
        found = occurrences_of_form(db, to_arabic(buckwalter), SETTINGS)
        assert found and all(o.ref == o.word_ref for o in found)
    assert "3:37:15" in {o.ref for o in occurrences_of_form(db, to_arabic("wjd"), SETTINGS)}  # one cell


def test_cells_are_numbered_along_the_aya(db):
    assert db.execute("SELECT ref, pos FROM units WHERE sura = 34 AND aya = 36 AND pos BETWEEN 7 AND 10 ORDER BY pos").fetchall() == [
        ("34:36:7", 7),
        ("34:36:8a", 8),
        ("34:36:8b", 9),
        ("34:36:9a", 10),
    ]


def test_yaqdir_is_in_the_12_ayas_of_d02(db):
    groups = by_form(occurrences_of_form(db, YAQDIR, SETTINGS))
    assert list(groups) == [to_arabic("yaqodir"), to_arabic("yuqad~ir")]  # kept apart by their vowels, no lemma
    assert [o.aya_ref for o in groups[to_arabic("yaqodir")]] == YAQDIR_AYAS
    assert [o.word_ref for o in groups[to_arabic("yuqad~ir")]] == ["73:20:17"]


def test_typing_the_vowels_selects_one_form(db):
    found = occurrences_of_form(db, to_arabic("yaqodiru"), SETTINGS)
    assert [o.aya_ref for o in found] == YAQDIR_AYAS


def test_forms_of_a_root_cover_all_its_occurrences(db):
    rows = forms_of_root(db, to_arabic("qdr"))
    assert sum(row.occurrences for row in rows) == 132
    assert (rows[0].form, rows[0].occurrences) == (to_arabic("qadiyr"), 37)
    assert forms_of_root(db, to_arabic(">mn")) == forms_of_root(db, to_arabic("Amn")) != []


def test_no_form_is_built_from_the_lemma(db):
    columns = {row[1] for row in db.execute("PRAGMA table_info(units)")}
    assert "lemma" not in columns


def test_each_cell_belongs_to_exactly_one_segment_of_each_scheme(db):
    cells = db.execute("SELECT count(*) FROM units").fetchone()[0]
    for (scheme_id,) in db.execute("SELECT id FROM segmentations").fetchall():
        counted = db.execute(
            "SELECT count(*), count(DISTINCT unit_id) FROM segment_units WHERE segmentation_id = ?", (scheme_id,)
        ).fetchone()
        assert counted == (cells, cells)


@pytest.mark.parametrize("scheme, segments", [("aya", 6236), ("waqf-strict", 6861), ("waqf-souple", 10515)])
def test_segments_are_unchanged_and_counted_in_cells(db, scheme, segments):
    sizes = segment_sizes(db, scheme)
    assert len(sizes) == segments
    assert sum(sizes) == db.execute("SELECT count(*) FROM units WHERE aya > 0").fetchone()[0]


def test_command_line_prints_traceable_output(built_db, monkeypatch, capsys):
    monkeypatch.setattr(ingest, "DB_PATH", built_db)
    assert cli.main(["forme", YAQDIR]) == 0
    output = capsys.readouterr().out
    assert "الرواية : حفص" in output and f"نسخة البرنامج {__version__}" in output
    assert "مرات الورود : 12 ؛ آيات : 12" in output and "مرات الورود : 1 ؛ آيات : 1" in output
    assert "90:5:4" in output
    assert cli.main(["racine", to_arabic("qdr")]) == 0
    assert "المجموع : 132 ؛ الصيغ : 46" in capsys.readouterr().out
