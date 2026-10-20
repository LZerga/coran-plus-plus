"""Frames and slots of a root, and the formal concepts of its forms."""

import pytest

from quran_harness import __main__ as cli
from quran_harness import frames, ingest
from quran_harness.buckwalter import to_arabic
from quran_harness.concepts import Concept, concepts

QLB = to_arabic("qlb")


@pytest.fixture(scope="module")
def qalb(db):
    return frames.build(db, QLB, "waqf-souple")


def branch(branches, buckwalter):
    return next(b for b in branches if b.cell == to_arabic(buckwalter))


def test_poisson_tail():
    assert frames._poisson_tail(0, 2.0) == 1.0
    assert abs(frames._poisson_tail(1, 2.0) - (1 - 2.718281828 ** -2)) < 1e-6


def test_every_occurrence_of_the_root_is_read(qalb):
    assert qalb.occurrences == 168
    assert sum(b.count for b in qalb.continuations) == 168 == sum(b.count for b in qalb.antecedents)


def test_marad_follows_the_root_far_more_than_chance(qalb):
    """في قلوبهم مرض : مرض right after a form of قلب 12 times, expected about 0.02."""
    marad = branch(qalb.continuations, "maraD")
    assert marad.count == 12 and marad.expected < 0.1 and marad.established
    assert marad.forms.most_common(1)[0][1] == 11


def test_the_verb_inqalaba_opens_on_ala_and_a_part_of_the_body(qalb):
    from quran_harness.normalize import Level, normalize

    ala = branch(qalb.continuations, "EalaY")
    assert {normalize(x, Level.NO_VOWELS) for x in ala.second} >= {to_arabic("Eqbyh"), to_arabic("wjhh")}


def test_slots_come_back_with_their_fillers(qalb):
    slot = next(s for s in qalb.slots if s.before == to_arabic("fiY") and s.after == to_arabic("maraD"))
    assert sum(slot.fillers.values()) == 11


def test_formal_concepts_are_the_intersections():
    context = {"a": frozenset({"x", "y"}), "b": frozenset({"y", "z"}), "c": frozenset({"y"})}
    found = {(c.extent, c.intent) for c in concepts(context)}
    assert (frozenset({"a", "b", "c"}), frozenset({"y"})) in found
    assert (frozenset({"a"}), frozenset({"x", "y"})) in found
    assert all(isinstance(c, Concept) for c in concepts(context))


def test_command_line(built_db, monkeypatch, capsys):
    monkeypatch.setattr(ingest, "DB_PATH", built_db)
    assert cli.main(["cadres", QLB, "--pause", "souple"]) == 0
    assert "القوالب والخانات" in capsys.readouterr().out
    assert cli.main(["cadres", "zzz"]) == 1
