"""Level 5, first part: two forms of the same root compared (SPEC §2.12-c)."""

import pytest

from quran_harness import __main__ as cli
from quran_harness import ingest
from quran_harness.buckwalter import to_arabic
from quran_harness.comparison import compare_forms, render
from quran_harness.config import load_config
from quran_harness.families import forms_for
from quran_harness.units import FormSettings

CONFIG = load_config()
META = {"reading": "hafs", "code_version": "test"}


def form(db, typed):
    """The most frequent form a typed spelling covers (common spelling allowed: عالم for عَٰلِم)."""
    return next(iter(forms_for(db, typed, FormSettings.from_config(CONFIG))))


@pytest.fixture(scope="module")
def alim(db):
    return compare_forms(db, form(db, to_arabic("EAlm")), form(db, to_arabic("ElAm")), "waqf-souple", CONFIG)


@pytest.fixture(scope="module")
def yaqdir(db):
    return compare_forms(db, to_arabic("yaqodir"), to_arabic("qadiyr"), "waqf-souple", CONFIG)


def test_common_spelling_finds_the_uthmani_forms(db):
    assert form(db, to_arabic("EAlm")) == to_arabic("Ea`lim")  # superscript alef in the text
    assert len(forms_for(db, to_arabic("EAlm"), FormSettings.from_config(CONFIG))) >= 1


def test_alim_and_allam_meet_on_the_root_ghyb_in_every_pair(alim):
    """The example of the research notes: عالم with الغيب, علام with الغيوب (case ب)."""
    assert (len(alim.first.rows), len(alim.second.rows), len(alim.cross)) == (13, 4, 52)
    assert all("ب" in pair.cases for pair in alim.cross)
    assert all(any(to_arabic("gyb") in x.roots for x, _ in pair.same_root) for pair in alim.cross)


def test_alim_and_allam_covary_on_the_word_after_them(alim):
    (cov,) = alim.covariations
    assert cov.fillers[0].most_common(1)[0] == (to_arabic("{logayob"), 12)
    assert cov.fillers[1].most_common(1)[0] == (to_arabic("{loguyuwb"), 4)


def test_yaqdir_and_qadir_meet_on_yasha_and_shay(yaqdir):
    """يقدر with يشاء and شيء, قدير with يشاء and شيء (research notes)."""
    assert len(yaqdir.cross) == 12 * 37
    shared = sum(1 for p in yaqdir.cross if any(to_arabic("$yA") in x.roots for x, _ in p.same_form + p.same_root))
    assert shared / len(yaqdir.cross) > 0.8


def test_behaviour_dimensions(yaqdir):
    a, b = yaqdir.first, yaqdir.second
    assert (len(a.suras), len(b.suras)) == (10, 23)  # 1. dispersion
    assert b.positions["fin"] == 36 and b.aya_positions["last_segment"] == 33  # 4, 5: قدير ends the segment, and the aya
    assert a.left[to_arabic("wa")] == 9 and b.left[to_arabic("$aYo'")] == 33  # 12. immediate frame
    assert a.formula_rows == 11 and b.formula_rows == 34  # 2. formulas
    assert sum(b.types.values()) == 37 * 36 // 2  # 14. typology


def test_letters_and_pronouns_are_counted_apart(yaqdir):
    letters = {x.form for p in yaqdir.cross for x, _ in p.letters}
    same = {x.form for p in yaqdir.cross for x, _ in p.same_form}
    assert to_arabic("wa") in letters and to_arabic("wa") not in same


def test_two_roots_are_never_compared(db):
    with pytest.raises(ValueError):
        compare_forms(db, to_arabic("yaqodir"), form(db, to_arabic("EAlm")), "waqf-souple", CONFIG)


def test_rendering(yaqdir):
    text = render(yaqdir, META)
    for part in ("مقارنة صيغتين", "أ. الوصف", "ب. التصنيف والتمثيل", "ج. التحليل", "أ. مقارنة مقاطع الصيغتين"):
        assert part in text


def test_command_line(built_db, monkeypatch, capsys):
    monkeypatch.setattr(ingest, "DB_PATH", built_db)
    assert cli.main(["comparer", to_arabic("EAlm"), to_arabic("ElAm"), "--pause", "souple"]) == 0
    assert "مقارنة صيغتين" in capsys.readouterr().out
    assert cli.main(["comparer", to_arabic("yqdr"), to_arabic("EAlm")]) == 1
