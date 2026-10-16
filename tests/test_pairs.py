"""Lot D, level 1: direct comparison of two segments (SPEC §2.2, §2.3, §2.11).

Structure tests use abstract cells (a, b, c…), not Quranic text. The cases of the
SPEC are taken from the text by their references (QUESTIONS.md, Q8, Q24).
"""

import pytest

from quran_harness import __main__ as cli
from quran_harness import ingest
from quran_harness.buckwalter import to_arabic
from quran_harness.config import load_config
from quran_harness.pairs import (
    E0,
    E1,
    E2,
    E3,
    E4,
    LETTER_CHANGED,
    R1_PARTIAL,
    R1_TOTAL,
    R2,
    R3,
    Cell,
    PairSettings,
    cells_of_span,
    compare,
    relation,
)

SETTINGS = PairSettings.from_config(load_config())


def cell(form: str, base: str | None = None, attached: tuple[str, ...] = (), root: str = "") -> Cell:
    return Cell(0, "0:0:0", "0:0:0", form, form, base or form, attached, frozenset(root.split()))


def seg(text: str) -> list[Cell]:
    return [cell(token) for token in text.split()]


def run(a: str, b: str, pivot: str = "P"):
    x, y = seg(a), seg(b)
    return compare(x, [c.form for c in x].index(pivot), y, [c.form for c in y].index(pivot), SETTINGS)


# --- Codes E ---------------------------------------------------------------------


def test_codes_between_two_cells():
    assert relation(cell("ab"), cell("ab")) == (E0, "")
    assert relation(cell("ala", "ala"), cell("alayh", "ala", ("suffix:PRON:h",))) == (E1, "")
    assert relation(cell("rbi", "rb", ("suffix:PRON:y",)), cell("rbk", "rb", ("suffix:PRON:k",))) == (E2, "")
    assert relation(cell("brbk", "rb", ("prefix:P:b",)), cell("lrbk", "rb", ("prefix:P:l",))) == (E2, LETTER_CHANGED)
    assert relation(cell("ySA", root="$yA"), cell("$y", root="$yA")) == (E3, "")
    assert relation(cell("Allh", root="Alh"), cell("rbk", root="rbb")) == (E4, "")


# --- Structure -------------------------------------------------------------------


def test_equal_segments_are_r1_total():
    assert run("a b P c", "a b P c").types == (R1_TOTAL,)


def test_nothing_in_common_but_the_pivot_is_r3_at_once():
    signature = run("a b P", "c d P")
    assert signature.types == (R3,) and signature.filtered


def test_addition_is_one_o1_per_run_of_cells():
    signature = run("a b P x c d", "a b P x")
    assert signature.types == (R1_PARTIAL,)
    assert [(op.kind, op.a) for op in signature.operations] == [("O1", (4, 5))]
    assert signature.operations[0].distance == "éloigné"


def test_inversion_counts_the_inverted_pairs_of_units():
    signature = run("P x a b c d", "P x c d a b")
    assert signature.order[1] == (1, 3, 2) and signature.inversions == 1
    assert [op.kind for op in signature.operations] == ["O3"]


def test_a_block_cut_by_an_addition_is_o1_not_o4():
    """SPEC §2.11, case 1, expects O1 alone where an addition cuts a block (QUESTIONS.md, Q29)."""
    cut = run("P a b x", "P a z b x")
    assert "O1" in cut.kinds() and "O4" not in cut.kinds()


def test_pivot_moving_from_middle_to_end_is_o5():
    signature = run("a P b", "c a P")
    assert "O5" in signature.kinds()


def test_pivot_counts_among_the_common_elements_when_asked():
    x, y = [cell("a"), cell("P"), cell("ala", "ala")], [cell("b"), cell("P"), cell("alayh", "ala", ("suffix:PRON:h",))]
    assert compare(x, 1, y, 1, SETTINGS).types == (R2,)
    strict = PairSettings(SETTINGS.min_block, SETTINGS.r2_min_common, False)
    assert compare(x, 1, y, 1, strict).types == (R3,)


# --- The cases of the SPEC, by references ---------------------------------------------

YAQDIR, YAQDIRUN = to_arabic("yaqodir"), to_arabic("yaqodiruwn")


def real(db, span_a, span_b, pivot=YAQDIR):
    a, b = cells_of_span(db, *span_a), cells_of_span(db, *span_b)
    pa = next(i for i, c in enumerate(a) if c.form == pivot)
    pb = next(i for i, c in enumerate(b) if c.form == pivot)
    return a, b, compare(a, pa, b, pb, SETTINGS)


def texts(cells, indexes):
    return [cells[i].ref for i in indexes]


def test_case_1_two_blocks_and_two_additions(db):
    """34:39 / 34:36 (the second phrase of the SPEC is not in the text, Q8 and Q24)."""
    a, b, s = real(db, (34, 39, 1, 11), (34, 36, 1, 8))
    assert s.types == (R1_PARTIAL,)
    assert [blk.length for blk in s.blocks] == [7, 2]  # قل … يشاء | و يقدر
    o1 = [texts(a, op.a) for op in s.operations if op.kind == "O1"]
    assert o1 == [["34:39:8", "34:39:9"], ["34:39:11"]]  # من عباده ; له
    assert "O2" not in s.kinds() and "O3" not in s.kinds()


def test_case_2_identity_and_similarity_together(db):
    a, b, s = real(db, (34, 36, 1, 8), (17, 30, 1, 7))
    assert s.types == (R1_PARTIAL, R2)
    assert [(op.kind, op.detail, texts(a, op.a), texts(b, op.b)) for op in s.operations] == [
        ("O1", "Ø dans B", ["34:36:1"], []),  # قل
        ("O2", "E2", ["34:36:3"], ["17:30:2"]),  # ربي / ربك
    ]


def test_case_3_same_blocks_in_another_order(db):
    a, b, s = real(db, (14, 18, 13, 18), (2, 264, 28, 33), YAQDIRUN)
    assert s.types == (R1_PARTIAL,)
    assert len(s.blocks) == 3 and s.inversions == 1
    assert [op.kind for op in s.operations] == ["O3"]


def test_case_4_ala_and_alayhi(db):
    a, b, s = real(db, (90, 5, 1, 6), (16, 75, 4, 9))
    assert s.types == (R2,)  # the pivot counts (Q23)
    e1 = [op for op in s.operations if op.kind == "O2" and op.detail == "E1"]
    assert [(texts(a, op.a), texts(b, op.b)) for op in e1] == [(["90:5:5"], ["16:75:8"])]
    assert set(s.codes) <= {E0, E1, E4, "Ø"}


def test_case_5_yasha_and_shay(db):
    """The document quotes « ما يشاء ويقدر », not in the text; 42:12 « لمن يشاء ويقدر » stands for it (Q24)."""
    a, b, s = real(db, (16, 75, 6, 9), (42, 12, 7, 9))
    assert s.types == (R2,)
    assert any(op.kind == "O2" and op.detail == "E3" for op in s.operations)
    assert "O5" in s.kinds()


def test_command_line(built_db, monkeypatch, capsys):
    monkeypatch.setattr(ingest, "DB_PATH", built_db)
    assert cli.main(["paire", "34:36:1-8", "17:30:1-7", "--pivot", to_arabic("yqdr")]) == 0
    output = capsys.readouterr().out
    assert "R1 partiel" in output and "R2" in output and "O2 E2" in output


@pytest.mark.parametrize("code", [E0, E1, E2, E3, E4])
def test_every_code_has_a_label_in_the_signature(code):
    assert code.startswith("E")
