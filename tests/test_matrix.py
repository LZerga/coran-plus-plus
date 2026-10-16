"""Lot D, level 3: alignment matrices and their check against the pairs (SPEC §2.5, §2.6)."""

import pytest

from quran_harness.buckwalter import to_arabic
from quran_harness.config import load_config
from quran_harness.families import Family, FamilySettings, analyse
from quran_harness.matrix import FIXED, RELATIVE, VARIABLE, ColumnReading, build, build_all, template
from quran_harness.pairs import PairSettings

CONFIG = load_config()
PAIRS = PairSettings.from_config(CONFIG)
RELATIVE_MIN = CONFIG["matrix"]["relative_min"]
YAQDIR = to_arabic("yaqodir")
OTHERS = ("16:75", "16:76", "90:5")  # the uses the document sets apart from the formula of the 9


def test_template_writes_fixed_optional_variable_and_relative_columns():
    readings = [
        ColumnReading(VARIABLE, True, (("Ø", 2), ("a", 1))),
        ColumnReading(VARIABLE, False, (("b", 2), ("c", 1))),
        ColumnReading(FIXED, False, (("P", 3),)),
        ColumnReading(RELATIVE, False, (("d", 3), ("e", 1))),
        ColumnReading(FIXED, True, (("f", 2), ("Ø", 1))),
    ]
    assert template(readings) == "[{a}] {b|c} P d* [f]"


@pytest.fixture(scope="module")
def souple(db):
    return analyse(db, YAQDIR, "waqf-souple", PAIRS, FamilySettings.from_config(CONFIG))


def test_formula_of_the_nine_gives_the_template_of_the_spec(souple):
    """SPEC §2.11: [intro] [ذات] يبسط الرزق لمن يشاء [من عباده] ويقدر [له] — the waw is its own cell (D-02)."""
    nine = [i for i, row in enumerate(souple.rows) if not row.segment_ref.startswith(OTHERS)]
    assert len(nine) == 9
    m = build(souple, Family(nine, 1.0), RELATIVE_MIN)

    def forms(k):
        return {souple.rows[r].cells[c].form for r, c in zip(m.rows, m.columns[k].cells) if c is not None}

    def form_at(ref):
        return next(cell.form for row in souple.rows for cell in row.cells if cell.ref == ref)

    pivot = next(k for k, column in enumerate(m.columns) if column.is_pivot)
    assert m.readings[pivot].kind == FIXED and not m.readings[pivot].optional
    # [ذات] يبسط الرزق لمن يشاء [من عباده] و يقدر [له]
    assert forms(pivot - 8) == {form_at("13:26:1"), form_at("34:36:3"), form_at("17:30:2")}  # الله / ربي / ربك
    assert m.readings[pivot - 8].optional  # 42:12 has none
    assert [m.readings[k].kind for k in range(pivot - 7, pivot - 3)] == [FIXED] * 4
    assert forms(pivot - 7) == {form_at("13:26:2")} and forms(pivot - 4) == {form_at("13:26:5")}
    assert forms(pivot - 3) == {form_at("29:62:6")} and m.readings[pivot - 3].optional  # من
    assert forms(pivot - 2) == {form_at("29:62:7")} and m.readings[pivot - 2].optional  # عباده
    assert m.readings[pivot - 1].kind == FIXED  # the waw, its own cell (D-02)
    assert form_at("29:62:9") in forms(pivot + 1) and m.readings[pivot + 1].optional  # له
    # Observed: 2 pairs out of 36 where the matrix does not give a direct pairing. The segments of the
    # text are longer than the extracts of the document (Q25); the SPEC expects none.
    assert len(m.differences) == 2


def test_with_the_settings_of_the_user_every_row_has_its_pivot_in_the_pivot_column(souple):
    (m,) = build_all(souple, RELATIVE_MIN)
    assert len(m.rows) == 12
    (pivot,) = [column for column in m.columns if column.is_pivot]
    assert all(cell == souple.rows[r].pivot for r, cell in zip(m.rows, pivot.cells))


def test_an_isolated_use_has_a_one_row_matrix(souple):
    balad = [i for i, row in enumerate(souple.rows) if row.segment_ref.startswith("90:5")]
    m = build(souple, Family(balad, 1.0), RELATIVE_MIN)
    assert len(m.columns) == len(souple.rows[balad[0]].cells) and not m.differences
    assert all(reading.kind == FIXED for reading in m.readings)
