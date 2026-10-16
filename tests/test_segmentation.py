"""Step 4 validation: every word belongs to exactly one segment, under each scheme."""

import pytest

from quran_harness import __main__ as cli
from quran_harness import ingest
from quran_harness.buckwalter import to_arabic
from quran_harness.config import load_config
from quran_harness.examples import ACROSS, EQUAL, INSIDE, align_spellings, load_examples, locate
from quran_harness.segmentation import (
    MUANAQA,
    PAUSE_MARKS,
    Scheme,
    schemes_from_config,
    segments_of_aya,
    selected_scheme,
    split_aya,
    summary,
)

SALA, QALA, LAZIM, LA, JAIZ = (PAUSE_MARKS[name] for name in ("sala", "qala", "lazim", "la", "jaiz"))
STRICT = Scheme("waqf-strict", frozenset({LAZIM, QALA}))
SOUPLE = Scheme("waqf-souple", frozenset({LAZIM, QALA, JAIZ, SALA}))
SCHEMES = ["aya", "waqf-strict", "waqf-souple"]


# --- Cutting one aya ----------------------------------------------------------


def test_aya_scheme_keeps_the_aya_whole():
    assert split_aya(["", JAIZ, "", LAZIM, ""], Scheme("aya")) == [(0, 4)]


def test_strict_level_cuts_at_compulsory_and_preferred_pauses_only():
    assert split_aya(["", JAIZ, QALA, SALA, LAZIM, ""], STRICT) == [(0, 2), (3, 4), (5, 5)]


def test_souple_level_cuts_at_every_permitted_pause():
    assert split_aya(["", JAIZ, QALA, SALA, LAZIM, ""], SOUPLE) == [(0, 1), (2, 2), (3, 3), (4, 4), (5, 5)]


def test_forbidden_pause_and_sakt_never_cut():
    assert split_aya(["", LA, "ۜ", ""], SOUPLE) == [(0, 3)]


def test_end_of_aya_always_closes_a_segment():
    assert split_aya([""], STRICT) == [(0, 0)]
    assert split_aya(["", QALA], STRICT) == [(0, 1)]


def test_mark_written_with_another_sign_still_cuts():
    assert split_aya(["", f"ۜ {QALA}", ""], STRICT) == [(0, 1), (2, 2)]


@pytest.mark.parametrize(
    "choice, expected",
    [("none", [(0, 4)]), ("first", [(0, 1), (2, 4)]), ("second", [(0, 2), (3, 4)])],
)
def test_muanaqa_pair_cuts_at_one_mark_at_most(choice, expected):
    signs = ["", MUANAQA, MUANAQA, "", ""]
    assert split_aya(signs, Scheme("x", frozenset({LAZIM}), choice)) == expected


def test_schemes_come_from_the_configuration():
    config = load_config()
    assert [s.name for s in schemes_from_config(config)] == SCHEMES
    assert selected_scheme(config) == "waqf-strict"
    assert selected_scheme({"segmentation": {"scheme": "aya", "pause_level": "strict"}}) == "aya"


def test_forbidden_pause_cannot_be_configured_as_a_closing_mark():
    config = {"segmentation": {"muanaqa": "none", "pause_levels": {"x": ["la"]}}}
    with pytest.raises(ValueError):
        schemes_from_config(config)


# --- The real database --------------------------------------------------------


@pytest.mark.parametrize("scheme", SCHEMES)
def test_every_word_belongs_to_exactly_one_segment(db, scheme):
    """SPEC step 4. The primary key forbids two segments for a word; this checks none is left out."""
    row = db.execute(
        """SELECT count(*), count(DISTINCT sw.word_id) FROM segment_words sw
           JOIN segmentations n ON n.id = sw.segmentation_id WHERE n.name = ?""",
        (scheme,),
    ).fetchone()
    assert row == (77881, 77881)


@pytest.mark.parametrize("scheme", SCHEMES)
def test_segments_are_unbroken_runs_of_words_inside_one_aya(db, scheme):
    rows = db.execute(
        """SELECT s.id, s.sura, s.aya, s.start_pos, s.end_pos, count(*), min(w.pos), max(w.pos),
                  count(DISTINCT w.sura || ':' || w.aya), min(w.sura), min(w.aya)
           FROM segments s JOIN segmentations n ON n.id = s.segmentation_id
           JOIN segment_words sw ON sw.segment_id = s.id JOIN words w ON w.id = sw.word_id
           WHERE n.name = ? GROUP BY s.id""",
        (scheme,),
    ).fetchall()
    for _, sura, aya, start, end, n_words, first, last, n_ayas, w_sura, w_aya in rows:
        assert (first, last, n_words) == (start, end, end - start + 1)
        assert (n_ayas, w_sura, w_aya) == (1, sura, aya)


@pytest.mark.parametrize("scheme", SCHEMES)
def test_segments_of_an_aya_follow_each_other_without_gap(db, scheme):
    rows = db.execute(
        """SELECT s.sura, s.aya, s.seg_no, s.start_pos, s.end_pos FROM segments s
           JOIN segmentations n ON n.id = s.segmentation_id WHERE n.name = ? ORDER BY s.sura, s.aya, s.seg_no""",
        (scheme,),
    ).fetchall()
    expected_start = {}
    for sura, aya, seg_no, start, end in rows:
        assert start == expected_start.get((sura, aya), 1)
        expected_start[(sura, aya)] = end + 1
    lengths = dict(((s, a), n) for s, a, n in db.execute("SELECT sura, aya, count(*) FROM words GROUP BY sura, aya"))
    assert {key: start - 1 for key, start in expected_start.items()} == lengths


@pytest.mark.parametrize("scheme, expected", [("aya", 6236), ("waqf-strict", 6861), ("waqf-souple", 10515)])
def test_number_of_segments_per_scheme(db, scheme, expected):
    assert summary(db, scheme)["segments"] == expected
    with_basmala = db.execute(
        "SELECT count(*) FROM segments s JOIN segmentations n ON n.id = s.segmentation_id WHERE n.name = ?", (scheme,)
    ).fetchone()[0]
    assert with_basmala == expected + 112  # one more segment per sura-opening basmala


def test_closing_marks_match_the_level(db):
    def marks(scheme):
        rows = db.execute(
            """SELECT DISTINCT closing_mark FROM segments s JOIN segmentations n ON n.id = s.segmentation_id
               WHERE n.name = ?""",
            (scheme,),
        )
        return {ch for (mark,) in rows for ch in mark if ch in PAUSE_MARKS.values()}

    assert marks("aya") == set()
    assert marks("waqf-strict") == {LAZIM, QALA}
    assert marks("waqf-souple") == {LAZIM, QALA, JAIZ, SALA}


def test_finer_schemes_only_subdivide_coarser_ones(db):
    def boundaries(scheme):
        rows = db.execute(
            """SELECT s.sura, s.aya, s.end_pos FROM segments s JOIN segmentations n ON n.id = s.segmentation_id
               WHERE n.name = ?""",
            (scheme,),
        )
        return set(rows)

    assert boundaries("aya") <= boundaries("waqf-strict") <= boundaries("waqf-souple")


def test_segments_of_a_known_aya(db):
    assert [s.ref for s in segments_of_aya(db, "waqf-strict", 34, 39)] == ["34:39:1-20"]
    assert [s.ref for s in segments_of_aya(db, "waqf-souple", 34, 39)] == ["34:39:1-11", "34:39:12-17", "34:39:18-20"]


# --- The phrases quoted by the SPEC -------------------------------------------


def test_everyday_spelling_aligns_with_the_base_text():
    ya, ayyuha, nas = to_arabic("yA"), to_arabic(">yhA"), to_arabic("AlnAs")
    base = [to_arabic("ya`^>ay~uhaA"), to_arabic("{ln~aAsu")]
    assert align_spellings([ya, ayyuha, nas], base) == [1, 1, 2]
    # a word spelt differently in the two texts does not prevent the alignment
    assert align_spellings([to_arabic("AlEAlmyn"), ya, ayyuha], [to_arabic("{loEa`lamiyna"), base[0]]) == [1, 2, 2]
    assert align_spellings([nas], base) is None


def test_spec_phrases_are_placed_in_the_text(db):
    found, missing = locate(db, load_examples())
    assert {loc.example.id: loc.ref for loc in found} == {
        "1a": "34:39:1-11",
        "2a": "34:36:1-8",
        "2b": "17:30:1-7",
        "3a": "14:18:13-18",
        "3b": "2:264:28-33",
        "4a": "90:5:1-6",
        "4b": "16:75:4-9",
    }
    # One phrase of the SPEC does not exist in the text as quoted (QUESTIONS.md, Q8).
    assert [(example.id, reason) for example, reason in missing] == [("1b", "introuvable dans le texte")]


def test_how_spec_phrases_fit_the_segments(db):
    found, _ = locate(db, load_examples())
    fits = {loc.example.id: {scheme: relation for scheme, (relation, _) in loc.fits.items()} for loc in found}
    whole = {"aya": EQUAL, "waqf-strict": EQUAL, "waqf-souple": EQUAL}
    souple_only = {"aya": INSIDE, "waqf-strict": INSIDE, "waqf-souple": EQUAL}
    never = {"aya": INSIDE, "waqf-strict": INSIDE, "waqf-souple": INSIDE}
    assert fits == {"1a": souple_only, "2a": never, "2b": souple_only, "3a": souple_only, "3b": souple_only, "4a": whole, "4b": never}
    assert ACROSS not in {relation for example in fits.values() for relation in example.values()}


def test_command_line_reports(built_db, monkeypatch, capsys):
    monkeypatch.setattr(ingest, "DB_PATH", built_db)
    assert cli.main(["decoupages"]) == 0
    output = capsys.readouterr().out
    assert "waqf-strict  (retenu par config.yaml)" in output and "10515" in output
    assert cli.main(["verset", "34:39"]) == 0
    assert "34:39:12-17" in capsys.readouterr().out
    assert cli.main(["exemples"]) == 0
    assert "introuvable dans le texte" in capsys.readouterr().out
    assert cli.main(["verset", "999:1"]) == 1
