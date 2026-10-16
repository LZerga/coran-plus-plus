"""Step 5: the fiche of a reference form (MVP criteria of SPEC §7)."""

from collections import Counter

import pytest

from quran_harness import __main__ as cli
from quran_harness import __version__, compare, fiche, ingest
from quran_harness.buckwalter import to_arabic
from quran_harness.config import load_config

YAQDIR = to_arabic("yqdr")
QADARA, QADDARA = to_arabic("qadara"), to_arabic("qad~ara")


def configured(match_level: int, pause_level: str) -> dict:
    config = load_config()
    config["reference_form"]["match_level"] = match_level
    config["segmentation"]["pause_level"] = pause_level
    return config


@pytest.fixture(scope="module")
def yaqdir(db):
    """The form without clitics, on the "souple" segments: the settings that reproduce the document."""
    fiches = fiche.build(db, YAQDIR, configured(1, "souple"), with_stats=False)
    return {f.lemma: f for f in fiches}


def test_two_words_written_alike_get_one_fiche_each(yaqdir):
    assert list(yaqdir) == [QADARA, QADDARA]
    assert yaqdir[QADDARA].occurrences == ["73:20:17"]


def test_identity_card(yaqdir):
    card = yaqdir[QADARA]
    assert len(card.occurrences) == 12
    assert len({ref.rsplit(":", 1)[0] for ref in card.occurrences}) == 12  # SPEC §7: found in 12 ayas
    assert len(card.uses) == 12
    assert sorted(card.writings.values(), reverse=True) == [9, 2, 1]
    assert Counter(use.position for use in card.uses) == {"milieu": 6, "fin": 6}
    assert card.parameters == {
        "lecture": "hafs",
        "forme": "sans clitiques",
        "découpage": "waqf-souple",
        "comparaison": "sans voyelles",
        "code": __version__,
    }


def test_reference_form_is_marked_in_each_segment(yaqdir):
    for use in yaqdir[QADARA].uses:
        assert all(use.elements[i].core == YAQDIR for i in use.ref_indexes)
        sura, aya, positions = use.ref.split(":")
        start, end = (int(n) for n in positions.split("-"))
        assert [e.ref for e in use.elements] == [f"{sura}:{aya}:{pos}" for pos in range(start, end + 1)]


def test_companions_named_by_the_spec_are_found(yaqdir):
    """SPEC §7: the associations of يقدر with يشاء and شيء."""
    companions = {c.form: c for c in yaqdir[QADARA].companions if c.kind == "b"}
    yashaa, shay = companions[to_arabic("y$A'")], companions[to_arabic("$Y'")]
    assert (len(yashaa.refs), len(yashaa.segments), yashaa.before, yashaa.after) == (9, 9, 9, 0)
    assert (shay.refs, shay.before, shay.after) == (["16:75:9", "16:76:10"], 0, 2)


def test_companions_are_sorted_into_the_three_kinds(yaqdir):
    card = yaqdir[QADARA]
    kinds = Counter(c.kind for c in card.companions)
    assert kinds["a"] == 0 and kinds["b"] > 0 and kinds["c"] > 0
    assert all(c.root for c in card.companions if c.kind == "a")
    assert all(not c.root for c in card.companions if c.kind == "c")
    # every companion occurrence is a word of one of the segments, and none is the reference form
    in_segments = {e.ref for use in card.uses for e in use.elements}
    listed = [ref for c in card.companions for ref in c.refs]
    assert set(listed) <= in_segments - set(card.occurrences)
    assert len(listed) == sum(len(use.elements) - len(use.ref_indexes) for use in card.uses)


def test_what_is_attached_to_the_form(yaqdir):
    assert {form: len(refs) for (form, _), refs in yaqdir[QADARA].attached.items()} == {to_arabic("wa"): 9}


def test_preposition_written_with_a_pronoun_is_named_as_such(yaqdir):
    lahu = next(c for c in yaqdir[QADARA].companions if c.refs == ["29:62:9", "34:39:11"])
    assert (lahu.kind, lahu.form, lahu.nature) == ("c", to_arabic("l"), "lettre + pronom")


def test_segments_are_compared_two_by_two(yaqdir):
    pairs = yaqdir[QADARA].pairs
    assert len(pairs) == 12 * 11 // 2
    assert Counter(p.comparison.relation for p in pairs) == {
        compare.IDENTITY_PARTIAL: 37,
        compare.SIMILARITY: 20,
        compare.DIFFERENCE: 9,
    }
    # every element of both segments is accounted for exactly once
    for p in pairs:
        c = p.comparison
        assert c.common + len(c.extra_a) == len(p.a.elements)
        assert c.common + len(c.extra_b) == len(p.b.elements)


def test_spec_defaults_find_the_written_form_only(db):
    """With the defaults of the SPEC (word as written, strict pauses) the form is in 3 ayas."""
    cards = fiche.build(db, YAQDIR, load_config(), with_stats=False)
    assert [(c.lemma, len(c.occurrences), c.parameters["découpage"]) for c in cards] == [
        (QADARA, 3, "waqf-strict"),
        (QADDARA, 1, "waqf-strict"),
    ]


def test_too_many_pairs_are_not_compared(db):
    config = configured(1, "souple")
    config["relations"]["max_pairs"] = 10
    card = fiche.build(db, YAQDIR, config, with_stats=False)[0]
    assert (card.pairs, card.pairs_skipped) == ([], 66)
    assert "Non calculée : 66 paires" in fiche.render(card)


def test_rendered_fiche_shows_parameters_blocks_and_references(yaqdir):
    text = fiche.render(yaqdir[QADARA])
    for expected in ("## A. Carte d'identité", "## B. Compagnons", "## Comparaison des segments", "lecture : hafs", f"code : {__version__}", "34:39:1-11", "66 paires"):
        assert expected in text


def test_unknown_form_has_no_fiche(db):
    assert fiche.build(db, "zzz", load_config()) == []


def test_command_line(built_db, monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(ingest, "DB_PATH", built_db)
    out = tmp_path / "fiche.md"
    assert cli.main(["fiche-v0", YAQDIR, "--sans-stats", "--niveau", "noyau", "--pause", "souple", "--sortie", str(out)]) == 0
    assert "découpage : waqf-souple" in out.read_text(encoding="utf-8")
    assert cli.main(["comparer", "14:18:13-18", "2:264:28-33", "--niveau", "noyau"]) == 0
    output = capsys.readouterr().out
    assert "ordre différent" in output and "identité partielle" in output
    assert cli.main(["fiche-v0", "zzz"]) == 1
