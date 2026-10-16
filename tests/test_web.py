"""Step 8: the web interface answers with the same results as the command line."""

import csv
import io
import json

import pytest
from fastapi.testclient import TestClient

from quran_harness import __version__, export, fiche
from quran_harness.buckwalter import to_arabic
from quran_harness.config import default_choices, load_config, with_choices
from quran_harness.web import create_app

YAQDIR, YAQDIRUN, QDR = to_arabic("yqdr"), to_arabic("yqdrwn"), to_arabic("qdr")
QALB, FUAD = to_arabic("qlb"), to_arabic("f>d")
SETTINGS = {"niveau": "noyau", "pause": "souple"}


@pytest.fixture(scope="module")
def client(built_db):
    return TestClient(create_app(built_db))


def rows_of(response) -> list[dict]:
    assert response.headers["content-type"].startswith("text/csv")
    text = response.content.decode("utf-8")
    assert text.startswith("﻿")  # spreadsheet programs need it to read the Arabic
    return list(csv.DictReader(io.StringIO(text.lstrip("﻿"))))


def test_page_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Corrélations coraniques" in response.text and "/api/fiche" in response.text


def test_meta_gives_the_choices_and_the_defaults_of_the_configuration(client):
    meta = client.get("/api/meta").json()
    assert meta["version"] == __version__
    assert [n["id"] for n in meta["niveaux"]] == ["ecrit", "noyau", "nu"]
    assert meta["pauses"] == ["strict", "souple", "verset"]
    assert meta["defaults"] == {"niveau": "ecrit", "pause": "strict", "lecture": "hafs"}
    assert meta["lectures"] == ["hafs"]


def test_fiche_of_a_form(client):
    data = client.get("/api/fiche", params={"q": YAQDIR, **SETTINGS}).json()
    assert [len(f["occurrences"]) for f in data["fiches"]] == [12, 1]  # one fiche per lemma
    card = data["fiches"][0]
    assert card["parameters"] == {
        "lecture": "hafs",
        "forme": "sans clitiques",
        "découpage": "waqf-souple",
        "comparaison": "sans voyelles",
        "code": __version__,
    }
    assert (card["ayas"], len(card["segments"]), card["positions"]) == (12, 12, {"fin": 6, "milieu": 6})
    assert card["statistics"] is None and all(c["stats"] is None for c in card["companions"])
    assert card["pairs"]["total"] == 66 and len(card["pairs"]["rows"]) == 66
    assert [len(g["members"]) for g in card["groups"]] == [9, 2, 1]
    assert card["readings"]["companions_unchanged"] == len(card["companions"])


def test_every_line_can_show_its_arabic_text_and_references(client):
    """SPEC step 8: each row unfolds to the Arabic text and its references."""
    card = client.get("/api/fiche", params={"q": YAQDIR, **SETTINGS}).json()["fiches"][0]
    segments = {s["ref"]: s for s in card["segments"]}
    for segment in card["segments"]:
        sura, aya, positions = segment["ref"].split(":")
        start, end = (int(n) for n in positions.split("-"))
        assert [w["ref"] for w in segment["words"]] == [f"{sura}:{aya}:{pos}" for pos in range(start, end + 1)]
        assert any(w["reference"] for w in segment["words"]) and all(w["text"] for w in segment["words"])
    for companion in card["companions"]:
        assert len(companion["segment_refs"]) == companion["segments"]
        words = {w["ref"] for ref in companion["segment_refs"] for w in segments[ref]["words"]}
        assert set(companion["refs"]) <= words
    for pair in card["pairs"]["rows"]:
        assert len(pair["a_roles"]) == len(segments[pair["a"]]["words"])
        assert len(pair["b_roles"]) == len(segments[pair["b"]]["words"])


def test_page_and_command_line_give_the_same_fiche(client, db):
    config = with_choices(load_config(), "noyau", "souple")
    expected = export.fiche_to_dict(fiche.build(db, YAQDIR, config, with_stats=False)[0])
    expected = json.loads(json.dumps(expected))  # as it travels: tuples become lists
    served = client.get("/api/fiche", params={"q": YAQDIR, **SETTINGS}).json()["fiches"][0]
    summary = served.pop("summary")
    assert served == expected
    assert summary["engine"] == "sans modèle" and summary["statements"][0]["basis"] == ["F1"]
    assert {s["kind"] for s in summary["statements"]} >= {"calculé", "cité d'une source"}


def test_summary_asked_from_a_model_falls_back_without_credentials(client, monkeypatch):
    """With no credentials the page still gets the facts, and is told why the model was not used."""
    pytest.importorskip("anthropic")
    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ANTHROPIC_CONFIG_DIR", "Z:/absent")
    plain = client.get("/api/resume", params={"q": YAQDIR, **SETTINGS}).json()
    asked = client.get("/api/resume", params={"q": YAQDIR, "ia": "true", **SETTINGS}).json()
    assert plain["notice"] == "" and asked["notice"]
    assert asked["engine"] == "sans modèle" and asked["statements"] == plain["statements"]
    assert client.get("/api/resume", params={"q": YAQDIR, "index": 9, **SETTINGS}).status_code == 404


def test_defaults_are_those_of_the_configuration(client):
    assert default_choices(load_config()) == ("ecrit", "strict")
    card = client.get("/api/fiche", params={"q": YAQDIR}).json()["fiches"][0]
    assert (card["parameters"]["forme"], card["parameters"]["découpage"]) == ("mot écrit", "waqf-strict")
    assert len(card["occurrences"]) == 3


def test_fiche_with_the_random_control(client, monkeypatch):
    import quran_harness.web as web

    def quick_config():
        config = load_config()
        config["statistics"]["permutations"] = 300  # fewer could not pass the threshold over 53 companions
        return config

    monkeypatch.setattr(web, "load_config", quick_config)
    card = client.get("/api/fiche", params={"q": YAQDIR, "stats": "true", **SETTINGS}).json()["fiches"][0]
    assert card["statistics"]["permutations"] == 300
    yashaa = next(c for c in card["companions"] if c["form"] == to_arabic("y$A'"))
    assert yashaa["stats"]["reading"] == "au-dessus du hasard"
    assert set(yashaa["stats"]["controls"]) == {"corpus", "sura"}


def test_fiche_of_a_root(client):
    data = client.get("/api/fiche", params={"q": QDR, "mode": "racine", **SETTINGS}).json()
    (card,) = data["fiches"]
    assert card["form"] == f"racine {QDR}" and card["root"] == QDR
    assert len(card["occurrences"]) == 132  # every word of the root
    assert not [c for c in card["companions"] if c["kind"] == "a"]  # words of the root are the reference itself


def test_two_forms_side_by_side(client):
    data = client.get("/api/comparer", params={"a": YAQDIR, "b": YAQDIRUN, **SETTINGS}).json()
    assert data["counts"] == {"même forme associée": 8, "même racine, formes différentes": 5, "aucune": 51}
    assert data["notes"] and "plusieurs lemmes" in data["notes"][0]
    assert (data["first"]["occurrences"], data["second"]["occurrences"]) == (12, 3)


def test_two_roots_side_by_side(client):
    """SPEC step 8: compare two roots, for instance قلب and فؤاد."""
    data = client.get("/api/comparer", params={"a": QALB, "b": FUAD, "mode": "racine", **SETTINGS}).json()
    assert (data["first"]["form"], data["second"]["form"]) == (f"racine {QALB}", f"racine {to_arabic('fAd')}")
    assert data["first"]["occurrences"] > data["second"]["occurrences"] > 0
    assert sum(data["counts"].values()) == len(data["rows"])
    assert data["counts"]["même forme associée"] > 0


@pytest.mark.parametrize("table, expected_rows", [("segments", 12), ("compagnons", 53), ("paires", 66), ("lectures", 0)])
def test_csv_export(client, table, expected_rows):
    response = client.get("/api/fiche.csv", params={"q": YAQDIR, "table": table, **SETTINGS})
    assert response.status_code == 200 and "attachment" in response.headers["content-disposition"]
    rows = rows_of(response)
    assert len(rows) == expected_rows
    for row in rows:  # every row says how it was computed
        assert (row["lecture"], row["découpage"], row["code"]) == ("hafs", "waqf-souple", __version__)


def test_csv_of_companions_matches_the_fiche(client):
    rows = rows_of(client.get("/api/fiche.csv", params={"q": YAQDIR, "table": "compagnons", **SETTINGS}))
    yashaa = next(r for r in rows if r["compagnon"] == to_arabic("y$A'"))
    assert (yashaa["segments"], yashaa["avant"], yashaa["après"], yashaa["famille"]) == ("9", "9", "0", "b")
    assert len(yashaa["références"].split()) == 9


def test_csv_of_the_second_lemma_and_of_a_comparison(client):
    rows = rows_of(client.get("/api/fiche.csv", params={"q": YAQDIR, "table": "segments", "index": 1, **SETTINGS}))
    assert [r["segment"] for r in rows] == ["73:20:16-19"]
    rows = rows_of(client.get("/api/comparer.csv", params={"a": YAQDIR, "b": YAQDIRUN, **SETTINGS}))
    assert len(rows) == 64


@pytest.mark.parametrize(
    "url, params, status",
    [
        ("/api/fiche", {"q": "zzz"}, 404),
        ("/api/fiche", {"q": "  "}, 400),
        ("/api/fiche", {"q": YAQDIR, "niveau": "autre"}, 400),
        ("/api/fiche", {"q": YAQDIR, "pause": "autre"}, 400),
        ("/api/fiche", {"q": YAQDIR, "mode": "autre"}, 400),
        ("/api/fiche", {"q": YAQDIR, "lecture": "warsh"}, 400),
        ("/api/fiche.csv", {"q": YAQDIR, "table": "autre"}, 400),
        ("/api/fiche.csv", {"q": YAQDIR, "table": "segments", "index": 9, **SETTINGS}, 404),
        ("/api/comparer", {"a": YAQDIR, "b": "zzz"}, 404),
    ],
)
def test_wrong_requests_get_a_clear_answer(client, url, params, status):
    response = client.get(url, params=params)
    assert response.status_code == status
    assert response.json()["detail"]


def test_missing_database_is_reported(tmp_path):
    response = TestClient(create_app(tmp_path / "absent.db")).get("/api/fiche", params={"q": YAQDIR})
    assert response.status_code == 503 and "build" in response.json()["detail"]
