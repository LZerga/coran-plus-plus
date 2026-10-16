"""Step 9: the summary only says what was computed, and says where each line comes from.

No test calls a real model: a fake one stands in, so that what the harness does with
a good answer and with a bad one can be checked.
"""

import json
from datetime import date
from types import SimpleNamespace

import pytest

from quran_harness import __main__ as cli
from quran_harness import assistant, fiche, ingest
from quran_harness.assistant import CALCULE, NOTE, SOURCE, WITHOUT_MODEL, AssistantUnavailable, check
from quran_harness.buckwalter import to_arabic
from quran_harness.config import load_config

YAQDIR = to_arabic("yqdr")
YASHAA = to_arabic("y$A'")


def configured() -> dict:
    config = load_config()
    config["reference_form"]["match_level"] = 1
    config["segmentation"]["pause_level"] = "souple"
    config["statistics"]["permutations"] = 200
    return config


@pytest.fixture(scope="module")
def card(db):
    return fiche.build(db, YAQDIR, configured(), with_stats=False)[0]


@pytest.fixture(scope="module")
def facts(card):
    return {f.id: f.text for f in assistant.facts_of(card, 8)}


def answering(summary: list[dict], suggestions: list[dict] | None = None):
    """A fake model: records what it was sent and returns a fixed answer."""
    calls = []

    def complete(system: str, user: str, schema: dict) -> dict:
        calls.append((system, json.loads(user), schema))
        return {"summary": summary, "suggestions": suggestions or []}

    complete.calls = calls
    return complete


def summarise(db, card, completer=None, notes=()):
    return assistant.summarise(db, card, configured(), "core", completer, list(notes))


# --- Facts --------------------------------------------------------------------


def test_facts_are_the_numbers_of_the_fiche(card, facts):
    assert facts["F1"].startswith(f"La forme {YAQDIR}")
    assert "12 occurrences, dans 12 versets et 12 segments" in facts["F1"]
    assert "waqf-souple" in facts["F1"]
    yashaa = next(text for text in facts.values() if text.startswith(f"Le mot {YASHAA} "))
    assert "est dans 9 des 12 segments de la forme : 9 fois avant elle, 0 fois après" in yashaa
    assert any("66 paires" in text for text in facts.values())
    assert any("3 groupes, de tailles 9, 2, 1" in text for text in facts.values())


def test_facts_say_when_no_random_control_was_run(facts):
    assert any(text.startswith("Aucun contrôle aléatoire n'a été lancé") for text in facts.values())
    assert not any("au-dessus du hasard" in text for text in facts.values())


def test_facts_carry_the_reading_of_the_random_control(db):
    controlled = fiche.build(db, YAQDIR, configured())[0]
    texts = [f.text for f in assistant.facts_of(controlled, 8)]
    assert any("200 mélanges" in text for text in texts)
    yashaa = next(text for text in texts if text.startswith(f"Le mot {YASHAA} "))
    assert "Il est dans 104 segments du texte" in yashaa and "lecture du contrôle : au-dessus du hasard" in yashaa


def test_candidates_come_from_the_index_of_the_root(db, card):
    candidates = assistant.candidates_of(db, card, "core", 5)
    assert [c.id for c in candidates][:3] == ["S1", "S2", "S3"]
    assert any(to_arabic("yqdrwn") in c.text and "3 occurrences dans 3 versets" in c.text for c in candidates)
    assert not any(c.text.startswith(f"La forme {YAQDIR} ") for c in candidates)  # not the form itself


# --- Checking a sentence ------------------------------------------------------

KNOWN = {"F1": f"La forme {YAQDIR} a 12 occurrences dans 12 versets.", "F2": f"Le mot {YASHAA} est dans 9 des 12 segments."}


@pytest.mark.parametrize(
    "text, cited, problem",
    [
        (f"{YAQDIR} revient 12 fois.", ["F1"], None),
        (f"{YASHAA} l'accompagne dans 9 segments sur 12.", ["F2"], None),
        (f"{YAQDIR} revient 12 fois.", [], "ne cite aucun fait"),
        (f"{YAQDIR} revient 12 fois.", ["F9"], "cite un fait inexistant (F9)"),
        (f"{YAQDIR} revient 13 fois.", ["F1"], "nombre absent des faits cités (13)"),
        (f"{YAQDIR} revient 9 fois.", ["F1"], "nombre absent des faits cités (9)"),  # 9 is in F2, not in the fact cited
        (f"{to_arabic('rzq')} revient 12 fois.", ["F1"], f"mot arabe absent des faits cités ({to_arabic('rzq')})"),
        (f"{YAQDIR} signifie « mesurer » et revient 12 fois.", ["F1"], "mot d'interprétation « signifie »"),
        (f"{YAQDIR} revient 12 fois car le thème est central.", ["F1"], "mot d'interprétation « car »"),
    ],
)
def test_check(text, cited, problem):
    assert check(text, cited, KNOWN) == problem


# --- Summary without a model --------------------------------------------------


def test_summary_without_a_model_is_the_list_of_facts(db, card, facts):
    summary = summarise(db, card)
    assert summary.engine == WITHOUT_MODEL and not summary.rejected and not summary.notice
    computed = [s for s in summary.statements if s.kind == CALCULE]
    assert [(s.text, s.basis) for s in computed] == [(text, (fact_id,)) for fact_id, text in facts.items()]
    assert summary.suggestions and all(s.kind == CALCULE and s.basis[0].startswith("S") for s in summary.suggestions)


def test_every_line_says_where_it_comes_from(db, card):
    """SPEC step 9: computed, quoted from a source, and human note are told apart."""
    note = {"form": YAQDIR, "lemma": "", "author": "L. Z.", "date": "2026-10-10", "text": "À rapprocher du segment 34:39."}
    summary = summarise(db, card, notes=[note])
    kinds = {s.kind for s in summary.statements}
    assert kinds == {CALCULE, SOURCE, NOTE}
    sources = [s for s in summary.statements if s.kind == SOURCE]
    assert {s.basis for s in sources} >= {("tanzil-uthmani",), ("qac-morphology",)}
    (human,) = [s for s in summary.statements if s.kind == NOTE]
    assert (human.text, human.basis) == ("À rapprocher du segment 34:39.", ("L. Z.", "2026-10-10"))
    text = assistant.render(card, summary)
    assert "[calculé · F1]" in text and "[cité d'une source · tanzil-uthmani]" in text and "[note humaine · L. Z., 2026-10-10]" in text


def test_notes_are_kept_to_their_form_and_lemma(card):
    notes = [
        {"form": YAQDIR, "lemma": card.lemma, "author": "a", "date": "2026-01-01", "text": "du bon lemme"},
        {"form": YAQDIR, "lemma": to_arabic("qad~ara"), "author": "a", "date": "2026-01-01", "text": "d'un autre lemme"},
        {"form": to_arabic("qwm"), "lemma": "", "author": "a", "date": "2026-01-01", "text": "d'une autre forme"},
    ]
    assert [s.text for s in assistant.note_statements(card, notes)] == ["du bon lemme"]


def test_notes_file(tmp_path):
    path = tmp_path / "notes.yaml"
    assert assistant.load_notes(path) == []
    assistant.add_note(YAQDIR, " première ", "L. Z.", path=path, today=date(2026, 10, 10))
    assistant.add_note(YAQDIR, "seconde", "L. Z.", lemma="x", path=path, today=date(2026, 10, 11))
    assert assistant.load_notes(path) == [
        {"form": YAQDIR, "lemma": "", "author": "L. Z.", "date": "2026-10-10", "text": "première"},
        {"form": YAQDIR, "lemma": "x", "author": "L. Z.", "date": "2026-10-11", "text": "seconde"},
    ]
    with pytest.raises(ValueError):
        assistant.add_note(YAQDIR, "sans auteur", " ", path=path)


# --- Summary with a model -----------------------------------------------------


def test_model_is_sent_the_facts_and_nothing_else(db, card, facts):
    model = answering([{"text": f"{YAQDIR} a 12 occurrences.", "facts": ["F1"]}])
    summarise(db, card, model)
    ((system, sent, schema),) = model.calls
    assert set(sent) == {"faits", "candidats", "nombre_de_suggestions"}
    assert {f["id"]: f["texte"] for f in sent["faits"]} == facts
    assert all(c["id"].startswith("S") for c in sent["candidats"])
    assert schema == assistant.OUTPUT_SCHEMA and "n'interprète pas" in system


def test_sentences_that_only_restate_facts_are_kept(db, card):
    model = answering(
        [
            {"text": f"{YAQDIR} revient 12 fois, dans 12 versets.", "facts": ["F1"]},
            {"text": "Ses segments se répartissent en 3 groupes.", "facts": ["F15"]},
        ],
        [{"candidate": "S3", "reason": "Elle partage le même lemme.", "facts": ["S3"]}],
    )
    summary = summarise(db, card, model)
    assert summary.engine == "claude-opus-5-5" and not summary.rejected
    computed = [s for s in summary.statements if s.kind == CALCULE]
    assert [(s.text, s.basis) for s in computed] == [
        (f"{YAQDIR} revient 12 fois, dans 12 versets.", ("F1",)),
        ("Ses segments se répartissent en 3 groupes.", ("F15",)),
    ]
    assert any(s.kind == SOURCE for s in summary.statements)  # sources are still shown, and not written by the model
    (suggestion,) = summary.suggestions
    assert suggestion.basis == ("S3",) and suggestion.text.endswith("Elle partage le même lemme.")


def test_what_the_model_invents_is_thrown_away(db, card):
    model = answering(
        [
            {"text": f"{YAQDIR} revient 12 fois.", "facts": ["F1"]},
            {"text": f"{YAQDIR} revient 40 fois dans le texte.", "facts": ["F1"]},
            {"text": f"{YAQDIR} signifie mesurer.", "facts": ["F1"]},
            {"text": f"Le mot {to_arabic('ktAb')} l'accompagne.", "facts": ["F1"]},
            {"text": "La forme est très fréquente.", "facts": []},
        ],
        [
            {"candidate": "S99", "reason": "Forme voisine.", "facts": []},
            {"candidate": "S1", "reason": "Elle a 500 occurrences.", "facts": []},
        ],
    )
    summary = summarise(db, card, model)
    assert [s.text for s in summary.statements if s.kind == CALCULE] == [f"{YAQDIR} revient 12 fois."]
    assert [reason for _, reason in summary.rejected] == [
        "nombre absent des faits cités (40)",
        "mot d'interprétation « signifie »",
        f"mot arabe absent des faits cités ({to_arabic('ktAb')})",
        "ne cite aucun fait",
        "candidat hors de la liste proposée",
        "nombre absent des faits cités (500)",
    ]
    assert summary.suggestions and all(s.basis[0].startswith("S") for s in summary.suggestions)  # the computed ones
    assert "Phrases du modèle écartées par la vérification (6)" in assistant.render(card, summary)


def test_summary_falls_back_to_the_facts_when_nothing_survives(db, card, facts):
    summary = summarise(db, card, answering([{"text": "Ce mot exprime la puissance.", "facts": ["F1"]}]))
    assert summary.engine == WITHOUT_MODEL
    assert summary.notice == "aucune phrase du modèle n'a passé la vérification"
    assert [s.text for s in summary.statements if s.kind == CALCULE] == list(facts.values())
    assert len(summary.rejected) == 1


def test_summary_falls_back_to_the_facts_when_the_model_is_unavailable(db, card, facts):
    def unavailable(system, user, schema):
        raise AssistantUnavailable("l'API Anthropic est injoignable")

    summary = summarise(db, card, unavailable)
    assert (summary.engine, summary.notice) == (WITHOUT_MODEL, "l'API Anthropic est injoignable")
    assert [s.text for s in summary.statements if s.kind == CALCULE] == list(facts.values())
    assert "Modèle non utilisé : l'API Anthropic est injoignable" in assistant.render(card, summary)


# --- The call to Claude, with the SDK replaced by a stand-in --------------------


class FakeAnthropic:
    """Stands in for `anthropic.Anthropic`: records the request, returns a canned response."""

    requests: list[dict] = []
    response = None

    def __init__(self):
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        FakeAnthropic.requests.append(kwargs)
        return FakeAnthropic.response


def response(stop_reason: str, *blocks) -> SimpleNamespace:
    return SimpleNamespace(stop_reason=stop_reason, content=list(blocks))


@pytest.fixture
def fake_sdk(monkeypatch):
    anthropic = pytest.importorskip("anthropic")
    FakeAnthropic.requests = []
    monkeypatch.setattr(anthropic, "Anthropic", FakeAnthropic)
    return FakeAnthropic


def test_request_sent_to_claude(fake_sdk):
    answer = {"summary": [], "suggestions": []}
    fake_sdk.response = response(
        "end_turn", SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=json.dumps(answer))
    )
    complete = assistant.anthropic_completer(load_config())
    assert complete("consignes", "{}", assistant.OUTPUT_SCHEMA) == answer
    (request,) = fake_sdk.requests
    assert request["model"] == "claude-opus-5-5"
    assert request["system"] == "consignes" and request["messages"] == [{"role": "user", "content": "{}"}]
    assert request["output_config"] == {"effort": "medium", "format": {"type": "json_schema", "schema": assistant.OUTPUT_SCHEMA}}
    assert (request["fallbacks"], request["betas"]) == ("default", ["server-side-fallback-2026-07-01"])
    assert "thinking" not in request and "temperature" not in request  # neither is accepted as a setting by this model


@pytest.mark.parametrize(
    "canned, message",
    [
        (response("refusal"), "le modèle a décliné la demande"),
        (response("max_tokens", SimpleNamespace(type="text", text='{"summary": [')), "réponse du modèle coupée avant la fin"),
        (response("end_turn", SimpleNamespace(type="thinking", thinking="")), "réponse du modèle sans texte"),
        (response("end_turn", SimpleNamespace(type="text", text="pas du JSON")), "réponse du modèle illisible"),
    ],
)
def test_unusable_answers_are_reported_not_used(fake_sdk, canned, message):
    fake_sdk.response = canned
    with pytest.raises(AssistantUnavailable, match=message):
        assistant.anthropic_completer(load_config())("consignes", "{}", assistant.OUTPUT_SCHEMA)


def test_missing_credentials_are_reported(monkeypatch):
    pytest.importorskip("anthropic")
    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ANTHROPIC_CONFIG_DIR", "Z:/absent")  # no stored profile either: nothing can be sent
    with pytest.raises(AssistantUnavailable, match="identifiant|appel au modèle impossible"):
        assistant.anthropic_completer(load_config())("consignes", "{}", assistant.OUTPUT_SCHEMA)


# --- Command line -------------------------------------------------------------


def test_command_line(built_db, monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(ingest, "DB_PATH", built_db)
    monkeypatch.setattr(assistant, "NOTES_PATH", tmp_path / "notes.yaml")
    assert cli.main(["note", YAQDIR, "note d'essai", "--auteur", "L. Z."]) == 0
    capsys.readouterr()
    assert cli.main(["resume", YAQDIR, "--niveau", "noyau", "--pause", "souple", "--sans-stats"]) == 0
    output = capsys.readouterr().out
    assert "Rédaction : sans modèle" in output and "[calculé · F1]" in output and "## Formes à comparer" in output
    assert "[note humaine · L. Z., " in output and "note d'essai" in output
    assert cli.main(["resume", to_arabic("qdr"), "--racine", "--niveau", "noyau", "--sans-stats"]) == 0
    assert f"La racine {to_arabic('qdr')}" in capsys.readouterr().out
    assert cli.main(["resume", "zzz"]) == 1
    assert len(assistant.load_notes()) == 1  # the note went to the temporary file, not to data/notes.yaml


def test_tests_do_not_touch_the_real_notes_file():
    """The notes file belongs to the people who write notes; the test suite must leave it alone."""
    real = assistant.PROJECT_ROOT / "data" / "notes.yaml"
    assert assistant.NOTES_PATH == real
    assert not any(note.get("text") == "note d'essai" for note in assistant.load_notes(real))
