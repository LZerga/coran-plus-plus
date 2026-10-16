"""Step 2 validation: the database holds the base text unchanged, fully annotated."""

import json

import pytest

from quran_harness import __version__, qac
from quran_harness.buckwalter import to_arabic
from quran_harness.ingest import AlignmentError, align_aya
from quran_harness.normalize import Level, normalize
from quran_harness.sources import check, load_manifest
from quran_harness.tanzil import read_lines

SOURCES = {s.id: s for s in load_manifest()}


def seg(word: int, n: int, form: str, features: str = "STEM|POS:N") -> qac.Segment:
    return qac.Segment(1, 1, word, n, form, "N", features)


# --- Alignment on toy words ---------------------------------------------------


def test_words_align_one_to_one():
    corpus = [[seg(1, 1, "bi", "PREFIX|bi+"), seg(1, 2, "somi")], [seg(2, 1, "qdr")]]
    aligned = align_aya([to_arabic("bisomi"), to_arabic("qdr")], corpus)
    assert [len(a.segments) for a in aligned] == [2, 1]
    assert [a.note for a in aligned] == [None, None]


def test_same_count_keeps_positions_and_records_the_difference():
    aligned = align_aya([to_arabic("qdr")], [[seg(1, 1, "qdrA")]])
    assert [a.note for a in aligned] == ["letters"]


def test_encoding_difference_is_not_a_letter_difference():
    aligned = align_aya([to_arabic("$ayo_#FA")], [[seg(1, 1, "$ayo'FA")]])
    assert [a.note for a in aligned] == ["encoding"]


def test_corpus_word_with_two_stems_is_split_over_two_base_words():
    corpus = [[seg(1, 1, "baEoda"), seg(1, 2, "maA")], [seg(2, 1, "qdr")]]
    aligned = align_aya([to_arabic("baEoda"), to_arabic("maA"), to_arabic("qdr")], corpus)
    assert [[s.form_bw for s in a.segments] for a in aligned] == [["baEoda"], ["maA"], ["qdr"]]
    assert [a.note for a in aligned] == ["split", "split", None]


def test_corpus_word_that_cannot_be_split_is_shared():
    aligned = align_aya([to_arabic("<ilo"), to_arabic("yaAsiyna")], [[seg(1, 1, "<ilo yaAsiyna")]])
    assert [a.note for a in aligned] == ["shared", "shared"]
    assert aligned[0].segments == aligned[1].segments


def test_unexplained_count_difference_stops_the_ingestion():
    word = to_arabic("qdr")
    with pytest.raises(AlignmentError):
        align_aya([word, word], [[seg(1, 1, "qdr")]])
    with pytest.raises(AlignmentError):
        align_aya([word], [[seg(1, 1, "qdr")], [seg(2, 1, "qdr")]])


# --- The real database --------------------------------------------------------


def test_text_rebuilt_from_the_database_equals_the_raw_file(db):
    rebuilt: dict[tuple[int, int], list[str]] = {}
    for sura, aya, text, sign in db.execute("SELECT sura, aya, text_raw, sign_after FROM words ORDER BY id"):
        line = rebuilt.setdefault((sura, max(aya, 1)), [])
        line.append(text)
        if sign:
            line.append(sign)
    raw = {(s, a): text for s, a, text in read_lines(SOURCES["tanzil-uthmani"].path)}
    assert {key: " ".join(line) for key, line in rebuilt.items()} == raw


def test_word_counts(db):
    assert db.execute("SELECT count(*) FROM words").fetchone()[0] == 77881
    assert db.execute("SELECT count(*) FROM words WHERE aya = 0").fetchone()[0] == 448
    assert db.execute("SELECT count(DISTINCT sura), count(*) FROM ayas").fetchone() == (114, 6236)
    assert db.execute("SELECT count(*) FROM (SELECT DISTINCT sura, aya FROM words WHERE aya > 0)").fetchone()[0] == 6236


def test_every_word_of_an_aya_is_annotated(db):
    missing = db.execute("SELECT count(*) FROM words WHERE aya > 0 AND (qac_ref IS NULL OR stem_count = 0)")
    assert missing.fetchone()[0] == 0


def test_basmala_before_aya_1_has_no_invented_annotation(db):
    annotated = db.execute("SELECT count(*) FROM words WHERE aya = 0 AND (qac_ref IS NOT NULL OR root IS NOT NULL)")
    assert annotated.fetchone()[0] == 0


def test_no_corpus_segment_is_lost(db):
    corpus = qac.read_words(SOURCES["qac-morphology"].path)
    expected = {s.location for words in corpus.values() for word in words for s in word}
    stored = {row[0] for row in db.execute("SELECT DISTINCT qac_location FROM word_segments")}
    assert stored == expected


def test_normalised_columns_follow_the_documented_levels(db):
    for raw, norm1, norm2 in db.execute("SELECT text_raw, text_norm1, text_norm2 FROM words"):
        assert norm1 == normalize(raw, Level.NO_RECITATION_MARKS)
        assert norm2 == normalize(raw, Level.NO_VOWELS)


def test_differences_with_the_corpus_are_recorded(db):
    notes = dict(db.execute("SELECT kind, count(*) FROM alignment_notes GROUP BY kind"))
    assert notes == {"encoding": 317, "letters": 2, "split": 6, "shared": 2}
    letters = db.execute(
        "SELECT w.ref FROM alignment_notes n JOIN words w ON w.id = n.word_id WHERE n.kind = 'letters' ORDER BY w.id"
    )
    assert [row[0] for row in letters] == ["12:39:1", "12:41:1"]


@pytest.mark.parametrize(
    "ref, text, root, lemma, clitic_forms",  # in Buckwalter transliteration
    [
        ("1:1:1", "bisomi", "smw", "{som", ["bi"]),
        ("13:26:6", "wayaqodiru", "qdr", "qadara", ["wa"]),
        ("16:75:7", "yaqodiru", "qdr", "qadara", []),
        ("73:20:17", "yuqad~iru", "qdr", "qad~ara", []),
        ("2:264:29", "yaqodiruwna", "qdr", "qadara", ["wna"]),
    ],
)
def test_annotation_is_attached_to_the_right_word(db, ref, text, root, lemma, clitic_forms):
    row = db.execute("SELECT text_raw, root, lemma, clitics FROM words WHERE ref = ?", (ref,)).fetchone()
    assert row[:3] == (to_arabic(text), to_arabic(root), to_arabic(lemma))
    assert [c["form"] for c in json.loads(row[3])] == [to_arabic(form) for form in clitic_forms]


def test_word_covered_by_a_two_stem_corpus_word(db):
    rows = db.execute("SELECT ref, text_raw, qac_ref, root FROM words WHERE ref IN ('2:181:3', '2:181:4') ORDER BY id")
    assert rows.fetchall() == [
        ("2:181:3", to_arabic("baEoda"), "2:181:3", to_arabic("bEd")),
        ("2:181:4", to_arabic("maA"), "2:181:3", None),
    ]


def test_meta_records_code_version_and_source_hashes(db):
    meta = dict(db.execute("SELECT key, value FROM meta"))
    assert meta["code_version"] == __version__
    for source_id in ("tanzil-uthmani", "tanzil-simple-clean", "qac-morphology"):
        assert meta[f"sha256:{source_id}"] == SOURCES[source_id].sha256


def test_raw_files_are_untouched_after_ingestion(db):
    for source_id in ("tanzil-uthmani", "tanzil-simple-clean", "qac-morphology"):
        assert check(SOURCES[source_id]) == "ok"
