"""Step 7: the other riwayat as differences from the base text (letters and words only)."""

import pytest

from quran_harness import __main__ as cli
from quran_harness import ingest, readings
from quran_harness.buckwalter import to_arabic
from quran_harness.readings import EN_MOINS, EN_PLUS, LETTRES, MOTS, VERSET_ABSENT, Token, Variant
from quran_harness.sources import load_manifest

SOURCES = {s.id: s for s in load_manifest()}
STUDIED = ["shouba", "warsh", "qaloon", "doori", "soosi", "bazzi", "qumbul"]


def ar(*words: str) -> list[str]:
    return [to_arabic(word) for word in words]


def tokens(*words: str, aya: int = 1) -> list[Token]:
    return [Token(aya, to_arabic(word)) for word in words]


# --- Skeleton -----------------------------------------------------------------


@pytest.mark.parametrize(
    "one, other",
    [
        ("{logama`ma", "AlogamaAma"),  # superscript alef / written alef
        ("fiY", "fiy"),  # alef maksura / yeh
        ("yu&ominuwna", "yuwminuwna"),  # hamza on waw / waw
        ("'aAli", "A`li"),  # hamza then alef / alef then superscript alef
        (">an*arotahumo", "Aan*arotahumo"),
    ],
)
def test_spelling_conventions_give_the_same_skeleton(one, other):
    assert readings.skeleton(to_arabic(one)) == readings.skeleton(to_arabic(other))


def test_different_letters_give_different_skeletons():
    assert readings.skeleton(to_arabic("taEomaluwna")) != readings.skeleton(to_arabic("yaEomaluwna"))
    assert readings.skeleton(to_arabic("ma`liki")) != readings.skeleton(to_arabic("maliki"))  # long / short a
    assert readings.skeleton(to_arabic("maliki")) == to_arabic("mlk")


# --- Differences of one sura, on toy words ------------------------------------

BASE = ar("qAl", "rbk", "tEmlwn", "wmAly", "hw", "Alkrym")
AYAS = [1, 1, 1, 2, 2, 2]


def test_identical_texts_have_no_difference():
    variants, stands_for = readings.diff_sura(BASE, AYAS, tokens("qAl", "rbk", "tEmlwn", "wmAly", "hw", "Alkrym"))
    assert variants == []
    assert stands_for == [0, 1, 2, 3, 4, 5]


def test_word_with_other_letters():
    variants, _ = readings.diff_sura(BASE, AYAS, tokens("qAl", "rbk", "yEmlwn", "wmAly", "hw", "Alkrym"))
    assert variants == [Variant(LETTRES, 2, 2, 1, (BASE[2],), (to_arabic("yEmlwn"),))]


def test_same_letters_cut_into_words_differently_are_not_a_difference():
    variants, stands_for = readings.diff_sura(BASE, AYAS, tokens("qAl", "rbk", "tEmlwn", "wmA", "ly", "hw", "Alkrym"))
    assert variants == []
    assert stands_for == [0, 1, 2, 3, 3, 4, 5]


def test_word_missing_from_the_riwaya():
    variants, _ = readings.diff_sura(BASE, AYAS, tokens("qAl", "rbk", "tEmlwn", "wmAly", "Alkrym"))
    assert [(v.kind, v.first, v.last, v.base_words) for v in variants] == [(EN_MOINS, 4, 4, (BASE[4],))]


def test_word_added_by_the_riwaya():
    variants, _ = readings.diff_sura(BASE, AYAS, tokens("qAl", "mn", "rbk", "tEmlwn", "wmAly", "hw", "Alkrym"))
    assert [(v.kind, v.first, v.variant_words) for v in variants] == [(EN_PLUS, 0, (to_arabic("mn"),))]


def test_whole_aya_missing_from_the_file_is_not_a_variant():
    variants, _ = readings.diff_sura(BASE, AYAS, tokens("wmAly", "hw", "Alkrym"))
    assert [(v.kind, v.first, v.last) for v in variants] == [(VERSET_ABSENT, 0, 2)]


def test_group_of_words_replaced_by_another():
    variants, _ = readings.diff_sura(ar("qAl", "Aw", "An", "hw"), [1, 1, 1, 1], tokens("qAl", "wAn", "hw"))
    assert [(v.kind, v.first, v.last, len(v.variant_words)) for v in variants] == [(MOTS, 1, 2, 1)]


OTHERS = [
    ["qAl", "rbk", "yEmlwn", "wmAly", "hw", "Alkrym"],
    ["qAl", "rbk", "tEmlwn", "wmAly", "Alkrym"],
    ["mn", "qAl", "rbk", "tEmlwn", "wmAly", "hw", "Alkrym", "mn"],
    ["wmAly", "hw", "Alkrym"],
    ["qAl", "wrbk", "wtEmlwn", "wmAly", "hw", "AlEZym"],
]


@pytest.mark.parametrize("other", OTHERS)
def test_applying_then_reverting_gives_the_base_text_back(other):
    """SPEC step 7 validation, on toy words."""
    variants, _ = readings.diff_sura(BASE, AYAS, tokens(*other))
    view = readings.apply_variants(BASE, variants)
    assert [word for word, _ in view] == ar(*other)
    assert readings.revert_variants(view, variants, len(BASE)) == BASE


# --- The real files -----------------------------------------------------------


def base_suras(db) -> dict[int, list[tuple[int, int, str]]]:
    suras: dict[int, list[tuple[int, int, str]]] = {}
    for word_id, sura, aya, text in db.execute("SELECT id, sura, aya, text_raw FROM words WHERE aya > 0 ORDER BY id"):
        suras.setdefault(sura, []).append((word_id, aya, text))
    return suras


def test_calibration_file_shows_no_difference(db):
    """The KFGQPC Hafs file is the same riwaya as the base text: the method must find nothing."""
    assert db.execute("SELECT count(*) FROM variants WHERE riwaya = 'hafs'").fetchone()[0] == 0
    assert db.execute("SELECT role FROM riwayat WHERE id = 'hafs'").fetchone()[0] == "calibration"
    assert readings.readings(db) == STUDIED


def test_number_of_differences_per_riwaya(db):
    counts = {}
    for riwaya, kind, n in db.execute("SELECT riwaya, kind, count(*) FROM variants GROUP BY riwaya, kind"):
        counts.setdefault(riwaya, {})[kind] = n
    assert counts == {
        "shouba": {LETTRES: 110},
        "warsh": {LETTRES: 247, MOTS: 2, EN_MOINS: 1, VERSET_ABSENT: 1},
        "qaloon": {LETTRES: 237, MOTS: 2, EN_MOINS: 1, VERSET_ABSENT: 1},
        "doori": {LETTRES: 194, MOTS: 3, VERSET_ABSENT: 1},
        "soosi": {LETTRES: 216, MOTS: 3, VERSET_ABSENT: 1},
        "bazzi": {LETTRES: 209, MOTS: 2, EN_PLUS: 1},
        "qumbul": {LETTRES: 205, MOTS: 1, EN_PLUS: 1},
    }


@pytest.mark.parametrize("riwaya", ["hafs", *STUDIED])
def test_variants_explain_every_letter_and_revert_to_the_base_text(db, riwaya):
    """SPEC step 7 validation: base text + variants = the riwaya, letter for letter; and back."""
    file_suras = readings.read_tokens(SOURCES[f"kfgqpc-{riwaya}"].path)
    for sura, words in base_suras(db).items():
        base = [text for _, _, text in words]
        variants, _ = readings.diff_sura(base, [aya for _, aya, _ in words], file_suras[sura])
        view = readings.apply_variants(base, variants)
        in_view = "".join(readings.skeleton(word) for word, _ in view)
        in_file = "".join(readings.skeleton(token.text) for token in file_suras[sura])
        assert in_view == in_file, f"sourate {sura}"
        assert readings.revert_variants(view, variants, len(base)) == base, f"sourate {sura}"


@pytest.mark.parametrize("riwaya", ["hafs", *STUDIED])
def test_aya_numbering_of_each_riwaya_maps_onto_the_base_text(db, riwaya):
    """Every aya of the riwaya is a stretch of base words; the stretches follow each other."""
    n_ayas = db.execute("SELECT ayas FROM riwayat WHERE id = ?", (riwaya,)).fetchone()[0]
    rows = db.execute(
        "SELECT sura, aya, first_word_id, last_word_id FROM riwaya_ayas WHERE riwaya = ? ORDER BY sura, aya", (riwaya,)
    ).fetchall()
    assert len(rows) == n_ayas
    assert all(first is not None and first <= last for _, _, first, last in rows)
    for (sura_a, _, _, last_a), (sura_b, _, first_b, _) in zip(rows, rows[1:]):
        if sura_a == sura_b:
            assert first_b >= last_a  # an aya starts where the previous one ends, or after
    spans = dict(db.execute("SELECT sura, max(id) FROM words WHERE aya > 0 GROUP BY sura"))
    last_of_sura = {}
    for sura, _, _, last in rows:
        last_of_sura[sura] = last
    assert last_of_sura == spans  # the last aya of each sura ends on the last word of the sura


def test_riwayat_with_the_same_numbering_as_the_base_text_keep_it(db):
    for riwaya in ("hafs", "shouba"):
        different = db.execute(
            """SELECT count(*) FROM riwaya_ayas r JOIN words w ON w.id = r.first_word_id
               WHERE r.riwaya = ? AND (w.sura != r.sura OR w.aya != r.aya)""",
            (riwaya,),
        ).fetchone()[0]
        assert different == 0


def variants_at(db, ref: str) -> dict[str, tuple[str, str, int]]:
    rows = db.execute(
        """SELECT v.riwaya, v.kind, v.variant_skeleton, v.riwaya_aya FROM variants v
           JOIN words w ON w.id = v.first_word_id WHERE w.ref = ?""",
        (ref,),
    )
    return {riwaya: (kind, skeleton, aya) for riwaya, kind, skeleton, aya in rows}


def test_a_word_read_with_another_letter(db):
    found = variants_at(db, "2:259:53")  # نُنشِزُهَا in the base text
    assert set(found) == {"warsh", "qaloon", "doori", "soosi", "bazzi", "qumbul"}
    assert {value[:2] for value in found.values()} == {(LETTRES, to_arabic("nn$rhA"))}
    assert {value[2] for value in found.values()} == {258}  # the aya has another number in these riwayat


def test_a_word_absent_from_two_riwayat(db):
    rows = db.execute(
        """SELECT v.riwaya, w.sura, w.aya, v.base_skeleton, v.variant_text FROM variants v
           JOIN words w ON w.id = v.first_word_id WHERE v.kind = ? ORDER BY v.riwaya""",
        (EN_MOINS,),
    ).fetchall()
    assert rows == [("qaloon", 57, 24, to_arabic("hw"), ""), ("warsh", 57, 24, to_arabic("hw"), "")]


def test_basmala_of_the_first_sura_missing_from_a_file_is_set_apart(db):
    rows = db.execute("SELECT riwaya FROM variants WHERE kind = ? ORDER BY riwaya", (VERSET_ABSENT,)).fetchall()
    assert [r for (r,) in rows] == ["doori", "qaloon", "soosi", "warsh"]
    assert readings.variants_on_words(db, 1, 4) == []  # not handed to the analysis


def test_command_line(built_db, monkeypatch, capsys):
    monkeypatch.setattr(ingest, "DB_PATH", built_db)
    assert cli.main(["lectures"]) == 0
    output = capsys.readouterr().out
    assert "étalonnage" in output and "étudiée" in output
    assert cli.main(["variantes", "2:259"]) == 0
    assert "2:259:53" in capsys.readouterr().out
    assert cli.main(["variantes", "2:1"]) == 0
    assert "Aucun écart" in capsys.readouterr().out
    assert cli.main(["variantes", "999:1"]) == 1
