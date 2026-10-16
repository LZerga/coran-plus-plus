"""Step 6 on the real text: controlled companions, usage groups (bloc C), two forms side by side."""

import pytest

from quran_harness import __main__ as cli
from quran_harness import fiche, ingest
from quran_harness.buckwalter import to_arabic
from quran_harness.config import load_config
from quran_harness.stats import Corpus

YAQDIR, YAQDIRUN = to_arabic("yqdr"), to_arabic("yqdrwn")
PERMUTATIONS = 200  # enough for the tests; config.yaml asks for 1000


def configured() -> dict:
    config = load_config()
    config["reference_form"]["match_level"] = 1
    config["segmentation"]["pause_level"] = "souple"
    config["statistics"]["permutations"] = PERMUTATIONS
    return config


@pytest.fixture(scope="module")
def card(db):
    return fiche.build(db, YAQDIR, configured())[0]


def companion(card, form: str):
    return next(c for c in card.companions if c.form == to_arabic(form) and c.kind == "b")


def test_every_companion_is_measured_and_controlled(card):
    assert card.statistics["controls"] == ["corpus", "sura"]
    for c in card.companions:
        assert list(c.stats.controls) == ["corpus", "sura"]
        assert c.stats.n_xy == len(c.segments)  # the count of the fiche and the count of the statistics agree
        assert (c.stats.n_x, c.stats.n) == (12, 10515)
        assert c.stats.n_y >= c.stats.n_xy
        for control in c.stats.controls.values():
            assert 1 / (PERMUTATIONS + 1) <= control.p_value <= control.q_value <= 1


def test_companion_found_above_chance(card):
    """يشاء is with يقدر in 9 of its 12 segments; no shuffle comes near."""
    yashaa = companion(card, "y$A'")
    assert (yashaa.stats.n_xy, yashaa.stats.n_y) == (9, 104)
    assert yashaa.stats.controls["corpus"].expected < 1
    assert yashaa.stats.controls["corpus"].p_value == pytest.approx(1 / (PERMUTATIONS + 1))
    assert yashaa.stats.reading(0.05, 2) == "au-dessus du hasard"


def test_frequent_word_is_not_presented_as_significant(card):
    """رب is with يقدر in 3 segments, but it is in 915 segments of the text."""
    rabb = companion(card, "rb")
    assert (rabb.stats.n_xy, rabb.stats.n_y) == (3, 915)
    assert rabb.stats.controls["corpus"].p_value > 0.05
    assert rabb.stats.reading(0.05, 2) == "attendu par la seule fréquence du mot"


def test_companion_seen_once_is_too_rare(card):
    once = [c for c in card.companions if len(c.segments) == 1]
    assert once and all(c.stats.reading(0.05, 2) == "trop rare pour conclure" for c in once)


def test_statistics_are_reproducible(db, card):
    again = fiche.build(db, YAQDIR, configured())[0]
    assert [c.stats for c in again.companions] == [c.stats for c in card.companions]


def test_statistics_can_be_left_out(db):
    plain = fiche.build(db, YAQDIR, configured(), with_stats=False)[0]
    assert plain.statistics is None and all(c.stats is None for c in plain.companions)
    assert "Contrôle aléatoire" not in fiche.render(plain)


def test_corpus_counts_the_segments_of_the_scheme(db):
    corpus = Corpus.load(db, configured(), "waqf-souple")
    assert (len(corpus.item), corpus.n_segments) == (77433, 10515)


def test_rendered_fiche_states_the_control(card):
    text = fiche.render(card)
    assert f"{PERMUTATIONS} permutations ; graine 20261010" in text
    assert "au-dessus du hasard" in text and "attendu par la seule fréquence du mot" in text


# --- Bloc C -------------------------------------------------------------------


def test_usages_are_grouped_by_resemblance(card):
    groups = card.groups
    assert [len(g.members) for g in groups] == [9, 2, 1]
    assert sorted(use.ref for g in groups for use in g.members) == sorted(use.ref for use in card.uses)
    assert [use.ref for use in groups[1].members] == ["16:75:1-19", "16:76:1-19"]
    assert [use.ref for use in groups[2].members] == ["90:5:1-6"]
    assert (groups[0].pairs, groups[1].pairs, groups[2].pairs) == (36, 1, 0)
    assert groups[0].shared_block.split() == [e.text for e in card.uses[0].elements[1:6]]  # 13:26:2-6


def test_similarity_links_make_wider_groups(db):
    config = configured()
    config["usage_groups"]["links"] = ["identity_total", "identity_partial", "similarity"]
    wider = fiche.build(db, YAQDIR, config, with_stats=False)[0]
    assert len(wider.groups) < 3


# --- Two forms of the same root -----------------------------------------------


def test_companions_of_two_forms_side_by_side(db):
    first, second = (fiche.build(db, form, configured(), with_stats=False)[0] for form in (YAQDIR, YAQDIRUN))
    rows = fiche.compare_companions(first, second)
    by_category = {category: [r for r in rows if r.category == category] for category in (fiche.SAME_FORM, fiche.SAME_ROOT, fiche.NO_COUNTERPART)}
    assert {category: len(found) for category, found in by_category.items()} == {
        fiche.SAME_FORM: 8,
        fiche.SAME_ROOT: 5,
        fiche.NO_COUNTERPART: 51,
    }
    shay = next(r for r in by_category[fiche.SAME_FORM] if r.form == to_arabic("$Y'"))
    assert (shay.side, shay.segments) == ("les deux", (2, 3))
    # every companion of each form is listed once
    assert len(rows) == len(first.companions) + len(second.companions) - len(by_category[fiche.SAME_FORM])
    assert all(r.other_forms for r in by_category[fiche.SAME_ROOT])
    assert all(not r.other_forms for r in by_category[fiche.NO_COUNTERPART])


def test_command_line(built_db, monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(ingest, "DB_PATH", built_db)
    out = tmp_path / "formes.md"
    arguments = ["comparer-formes", YAQDIR, YAQDIRUN, "--niveau", "noyau", "--pause", "souple", "--sortie", str(out)]
    assert cli.main(arguments) == 0
    assert "plusieurs lemmes" in capsys.readouterr().out
    assert "même forme associée : 8" in out.read_text(encoding="utf-8")
    assert cli.main(["fiche-v0", YAQDIR, "--sans-stats", "--niveau", "noyau", "--pause", "souple"]) == 0
    assert "## C. Usages regroupés par ressemblance" in capsys.readouterr().out
