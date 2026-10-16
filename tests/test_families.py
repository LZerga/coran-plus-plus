"""Lot D, level 2: families traced by the typology (SPEC §2.4)."""

import pytest

from quran_harness import __main__ as cli
from quran_harness import ingest
from quran_harness.buckwalter import to_arabic
from quran_harness.config import load_config
from quran_harness.families import FamilySettings, analyse, trace
from quran_harness.pairs import R1_PARTIAL, R2, R3, PairSettings, Signature

PAIRS = PairSettings.from_config(load_config())
YAQDIR = to_arabic("yaqodir")
NAHL, BALAD = {"16:75", "16:76"}, "90:5"


def sig(types, common):
    return Signature(tuple(types), (), (), (), ((), ()), 0, {}, common)


def test_r3_pairs_link_nothing_and_isolated_uses_stand_alone():
    signatures = {(0, 1): sig([R1_PARTIAL], 3), (0, 2): sig([R3], 0), (1, 2): sig([R3], 0)}
    families = trace([None] * 3, signatures, FamilySettings(1, 0.5))
    assert [(f.rows, f.isolated) for f in families] == [([0, 1], False), ([2], True)]


def test_link_needs_enough_common_elements_besides_the_pivot():
    signatures = {(0, 1): sig([R2], 1)}
    assert len(trace([None] * 2, signatures, FamilySettings(1, 0.5))) == 1
    assert len(trace([None] * 2, signatures, FamilySettings(2, 0.5))) == 2


def test_a_chain_with_low_cohesion_is_cut_at_its_weakest_link_and_the_cut_is_kept():
    """0-1-2-3 linked in a chain only: 3 linking pairs out of 6, cohesion 50 %; with 60 % the weakest link goes."""
    signatures = {(i, j): sig([R3], 0) for i in range(4) for j in range(i + 1, 4)}
    signatures |= {(0, 1): sig([R1_PARTIAL], 4), (1, 2): sig([R2], 1), (2, 3): sig([R1_PARTIAL], 4)}
    families = trace([None] * 4, signatures, FamilySettings(1, 0.6))
    assert [f.rows for f in families] == [[0, 1], [2, 3]]
    assert all(f.cuts == [(1, 2, 1)] for f in families)


def ayas(analysis, family):
    return {":".join(analysis.rows[i].segment_ref.split(":")[:2]) for i in family.rows}


@pytest.mark.parametrize("scheme", ["waqf-souple", "waqf-strict"])
def test_yaqdir_with_the_settings_of_the_user_makes_one_family(db, scheme):
    """Observed, not forced (QUESTIONS.md, Q23): with a link from one element besides the pivot, the
    12 uses hold together — the detached waw, الله and شيء / يشاء join النحل to the formula of the
    9, and على / عليه with أحد join البلد to النحل. The document's 9 / 2 / 1 is not reached."""
    analysis = analyse(db, YAQDIR, scheme, PAIRS, FamilySettings.from_config(load_config()))
    assert len(analysis.rows) == 12
    assert len(analysis.families) == 1 and len(analysis.families[0].rows) == 12


@pytest.mark.parametrize("link, groups", [(1, [12]), (2, [12]), (3, [11, 1])])
def test_yaqdir_families_under_each_link_threshold(db, link, groups):
    analysis = analyse(db, YAQDIR, "waqf-souple", PAIRS, FamilySettings(link, 0.5))
    assert [len(f.rows) for f in analysis.families] == groups
    if link == 3:
        assert ayas(analysis, analysis.families[1]) == {BALAD}  # isolated use, as in the document


def test_command_line(built_db, monkeypatch, capsys):
    monkeypatch.setattr(ingest, "DB_PATH", built_db)
    assert cli.main(["familles", to_arabic("yqdr"), "--pause", "souple"]) == 0
    output = capsys.readouterr().out
    assert "66 paires" in output and "waqf-souple" in output and "retenue" in output
